import asyncio
import contextlib
import hmac
import logging
import re
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated
from uuid import uuid4

import httpx
from fastapi import FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from pydantic import ValidationError

from app.config import Settings
from app.dependencies import DependencyUnavailable, LocalServices
from app.documents import (
    InvalidDocument,
    chunks_for,
    document_id,
    extract_file_pages,
    extract_pages,
)
from app.schemas import ChatRequest, ChatResponse, DocumentInput, IndexBookRequest
from app.store import Store
from app.tutor import answer_question, embedding_identity

logger = logging.getLogger("digital_himalaya")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(handler)
logger.setLevel(logging.INFO)
logger.propagate = False


class RequestBoundary:
    """Authenticate before reading uploads; bound even chunked request bodies."""

    def __init__(self, app, settings: Settings):
        self.app, self.settings = app, settings

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        headers = dict(scope["headers"])
        if scope["path"].startswith("/api/admin"):
            token = self.settings.admin_token.get_secret_value()
            if not token:
                return await JSONResponse(
                    {"detail": "Staff access is disabled until configured."},
                    503,
                )(scope, receive, send)
            expected = ("Bearer " + token).encode()
            if not hmac.compare_digest(headers.get(b"authorization", b""), expected):
                return await JSONResponse(
                    {"detail": "Staff sign-in required."},
                    401,
                    headers={"WWW-Authenticate": "Bearer"},
                )(scope, receive, send)
        if scope["method"] in {"POST", "PUT", "PATCH"}:
            limit = (
                self.settings.max_upload_bytes + 65536
                if scope["path"] == "/api/admin/documents"
                else 65536
            )
            body = bytearray()
            while True:
                message = await receive()
                if message["type"] == "http.disconnect":
                    return
                body.extend(message.get("body", b""))
                if len(body) > limit:
                    return await JSONResponse(
                        {"detail": "Request exceeds the size limit."},
                        413,
                    )(scope, receive, send)
                if not message.get("more_body", False):
                    break
            sent = False

            async def bounded_receive():
                nonlocal sent
                if not sent:
                    sent = True
                    return {"type": "http.request", "body": bytes(body), "more_body": False}
                return await receive()

            return await self.app(scope, bounded_receive, send)
        return await self.app(scope, receive, send)


def create_app(settings: Settings | None = None, client: httpx.AsyncClient | None = None):
    settings = settings or Settings()
    store = Store(settings.data_dir)
    own_client = client is None
    client = client or httpx.AsyncClient(
        timeout=settings.dependency_timeout_seconds,
        trust_env=False,
    )
    services = LocalServices(settings, client)
    chat_slots = asyncio.Semaphore(settings.max_chat_concurrency)
    ingestion_lock = asyncio.Lock()

    @asynccontextmanager
    async def lifespan(app):
        yield
        if own_client:
            await client.aclose()

    app = FastAPI(
        title="Digital Himalaya",
        version="0.1.0",
        lifespan=lifespan,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    app.add_middleware(RequestBoundary, settings=settings)

    @app.middleware("http")
    async def request_log(request, call_next):
        request_id = uuid4().hex[:12]
        started = time.monotonic()
        try:
            response = await call_next(request)
        except Exception:
            # Keep request bodies, URLs, credentials and exception messages out of logs.
            logger.error("request_failed request_id=%s", request_id)
            response = JSONResponse({"detail": "The server could not complete this request."}, 500)
        response.headers["X-Request-ID"] = request_id
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        logger.info(
            "request request_id=%s method=%s status=%s duration_ms=%.0f",
            request_id,
            request.method,
            response.status_code,
            (time.monotonic() - started) * 1000,
        )
        return response

    @app.exception_handler(DependencyUnavailable)
    async def dependency_error(request, exc):
        return JSONResponse({"detail": str(exc)}, 503)

    @app.get("/api/health")
    async def health():
        return {"status": "ok", "version": "0.1.0", "ai_enabled": settings.ai_enabled}

    async def dependency_status():
        async def local_models():
            chat_status = (
                "configured"
                if settings.chat_provider == "openai-compatible"
                and settings.chat_api_base_url
                and settings.chat_api_key.get_secret_value()
                else "unconfigured"
            )
            embed_status = "configured" if services.embeddings_configured else "unconfigured"
            needs_ollama = settings.chat_provider == "ollama" or settings.embed_provider == "ollama"
            if not needs_ollama:
                return {"chat_model": chat_status, "embeddings": embed_status}
            if not settings.ollama_base_url:
                if settings.chat_provider == "ollama":
                    chat_status = "unconfigured"
                if settings.embed_provider == "ollama":
                    embed_status = "unconfigured"
                return {"chat_model": chat_status, "embeddings": embed_status}
            try:
                names = await services.models()

                def present(name):
                    return (
                        "ready" if name in names or name + ":latest" in names else "missing_model"
                    )

                if settings.chat_provider == "ollama":
                    chat_status = present(settings.ollama_model)
                if settings.embed_provider == "ollama":
                    embed_status = present(settings.embed_model)
            except DependencyUnavailable:
                if settings.chat_provider == "ollama":
                    chat_status = "unavailable"
                if settings.embed_provider == "ollama":
                    embed_status = "unavailable"
            return {"chat_model": chat_status, "embeddings": embed_status}

        async def qdrant():
            if not settings.qdrant_url:
                return "unconfigured"
            try:
                result = await services.qdrant("GET", "/collections")
                if not isinstance(result.get("result", {}).get("collections"), list):
                    return "unavailable"
                return "ready"
            except (DependencyUnavailable, AttributeError):
                return "unavailable"

        models, vectors, kiwix, kolibri = await asyncio.gather(
            local_models(),
            qdrant(),
            services.probe_web(settings.kiwix_public_url, settings.kiwix_probe_url),
            services.probe_web(settings.kolibri_public_url, settings.kolibri_probe_url),
        )
        ai_status = "disabled"
        if settings.ai_enabled:
            chat_status = models["chat_model"]
            if chat_status not in {"ready", "configured"}:
                ai_status = chat_status
            elif settings.qdrant_url and (
                models["embeddings"] not in {"ready", "configured"} or vectors != "ready"
            ):
                ai_status = "unavailable"
            elif settings.chat_provider == "openai-compatible":
                ai_status = "configured"
            else:
                ai_status = "ready"
        return {
            "tutor": {"status": ai_status},
            "kiwix": kiwix,
            "kolibri": kolibri,
            "books": {"status": "ready", "count": len(store.list())},
            "dependencies": {**models, "vectors": vectors},
        }

    @app.get("/api/services")
    async def service_status():
        return await dependency_status()

    @app.get("/api/textbooks")
    async def textbooks(
        grade: int | None = Query(None, ge=0, le=12),
        subject: str | None = Query(None, max_length=120),
    ):
        return [store.public(doc) for doc in store.list(grade=grade, subject=subject)]

    @app.get("/api/textbooks/catalog")
    async def textbook_catalog(
        grade: int | None = Query(None, ge=0, le=12),
        subject: str | None = Query(None, max_length=120),
        q: str | None = Query(None, max_length=120),
        limit: int = Query(24, ge=1, le=48),
        offset: int = Query(0, ge=0, le=100_000),
    ):
        return store.catalog(grade=grade, subject=subject, query=q, limit=limit, offset=offset)

    def get_document(identity: str):
        if not re.fullmatch(r"[a-f0-9]{32}", identity):
            raise HTTPException(404, "Textbook not found.")
        document = store.get(identity)
        if not document or document["status"] != "ready":
            raise HTTPException(404, "Textbook not found.")
        return document

    @app.get("/api/textbooks/{identity}")
    async def textbook(identity: str):
        return store.public(get_document(identity))

    @app.get("/api/textbooks/{identity}/file")
    async def textbook_file(identity: str):
        doc = get_document(identity)
        path = (store.directory / doc["storage_name"]).resolve()
        if path.parent != store.directory or not path.is_file():
            raise HTTPException(404, "Textbook file is unavailable. Ask a teacher to reimport it.")
        media = "application/pdf" if path.suffix == ".pdf" else "text/plain; charset=utf-8"
        return FileResponse(
            path,
            media_type=media,
            filename=doc["filename"],
            content_disposition_type="inline",
            headers={"Content-Security-Policy": "default-src 'none'; frame-ancestors 'self'"},
        )

    @app.post("/api/tutor/chat", response_model=ChatResponse)
    async def chat(request: ChatRequest):
        if not settings.ai_enabled:
            raise HTTPException(
                503, "The AI tutor is turned off. Your teacher can enable it after review."
            )
        try:
            await asyncio.wait_for(chat_slots.acquire(), timeout=0.1)
        except TimeoutError as exc:
            raise HTTPException(
                429,
                "The tutor is helping another learner. Try again shortly.",
                headers={"Retry-After": "5"},
            ) from exc
        try:
            return await answer_question(request, services, store)
        finally:
            chat_slots.release()

    @app.get("/api/admin/index-status")
    async def index_status():
        return {
            "services": await dependency_status(),
            "documents": [store.public(doc) for doc in store.list(all_states=True)],
        }

    @app.post("/api/admin/index-book")
    async def index_book(request: IndexBookRequest):
        if not settings.qdrant_url:
            raise HTTPException(503, "Configure Qdrant before indexing textbook vectors.")
        if not services.embeddings_configured:
            raise HTTPException(503, "Configure an embedding provider before indexing textbooks.")
        if ingestion_lock.locked():
            raise HTTPException(409, "Another document is being indexed. Try again shortly.")
        async with ingestion_lock:
            document = store.get(request.document_id)
            if not document or document.get("status") != "ready":
                raise HTTPException(404, "Textbook not found.")
            current_identity = embedding_identity(services)
            if (
                document.get("index_status") == "indexed"
                and document.get("embedding_identity") == current_identity
            ):
                return store.public(document)
            path = (store.directory / document.get("storage_name", "")).resolve()
            if path.parent != store.directory or not path.is_file():
                raise HTTPException(
                    404,
                    "Textbook file is unavailable. Reimport it before indexing.",
                )
            document["index_status"] = "indexing"
            document.pop("index_error", None)
            store.put(document)
            try:
                pages, missing = await asyncio.to_thread(
                    extract_file_pages,
                    path,
                    settings.max_index_pdf_pages,
                )
                document["ocr_required_pages"] = missing
                chunks = chunks_for(
                    pages,
                    document["id"],
                    DocumentInput.model_validate(document),
                )
                prefix = settings.embed_document_prefix.replace("{title}", document["title"])
                # One book per request and four chunks per provider call bound local resource use.
                for start in range(0, len(chunks), 4):
                    batch = chunks[start : start + 4]
                    vectors = await services.embed([prefix + chunk["text"] for chunk in batch])
                    if start == 0:
                        await services.ensure_collection(len(vectors[0]))
                    await services.qdrant(
                        "PUT",
                        services.collection_path + "/points?wait=true",
                        json={
                            "points": [
                                {
                                    "id": chunk["chunk_id"],
                                    "vector": vector,
                                    "payload": {**chunk, "embedding_identity": current_identity},
                                }
                                for chunk, vector in zip(batch, vectors, strict=True)
                            ]
                        },
                        timeout=settings.model_timeout_seconds,
                    )
                document["chunks"] = len(chunks)
                document["embedding_identity"] = current_identity
                document["index_status"] = "indexed"
            except InvalidDocument as exc:
                document["index_status"] = "needs_ocr" if "OCR required" in str(exc) else "failed"
                store.put(document)
                raise HTTPException(422, str(exc)) from exc
            except DependencyUnavailable:
                document["index_status"] = "failed"
                store.put(document)
                raise
            except Exception as exc:
                document["index_status"] = "failed"
                store.put(document)
                logger.error("textbook_index_failed document_id=%s", document["id"])
                raise HTTPException(
                    503,
                    "Textbook indexing did not complete. Retry when services are ready.",
                ) from exc
            store.put(document)
            return store.public(document)

    @app.post("/api/admin/documents", status_code=201)
    async def import_document(
        file: Annotated[UploadFile, File()],
        title: str = Form(...),
        grade: int = Form(...),
        subject: str = Form(...),
        chapter: str = Form(...),
        license: str = Form(...),
        source: str = Form(...),
    ):
        try:
            metadata = DocumentInput(
                title=title,
                grade=grade,
                subject=subject,
                chapter=chapter,
                license=license,
                source=source,
            )
        except ValidationError as exc:
            raise HTTPException(
                422, "Check grade, title, subject, chapter, license and source."
            ) from exc
        filename = file.filename or ""
        suffix = Path(filename).suffix.lower()
        if (
            suffix not in {".pdf", ".txt"}
            or filename != Path(filename).name
            or "\\" in filename
            or any(ord(c) < 32 for c in filename)
            or len(filename) > 150
        ):
            raise HTTPException(400, "Use a plain filename ending in .pdf or .txt.")
        content = await file.read(settings.max_upload_bytes + 1)
        await file.close()
        if len(content) > settings.max_upload_bytes:
            raise HTTPException(413, "The file exceeds the upload limit.")
        # Reject competing imports instead of retaining arbitrarily many files in memory.
        if ingestion_lock.locked():
            raise HTTPException(409, "Another document is being indexed. Try again shortly.")
        async with ingestion_lock:
            identity = document_id(content, metadata)
            existing = store.get(identity)
            if existing and existing["status"] == "ready":
                if existing["embedding_identity"] != embedding_identity(services):
                    raise HTTPException(
                        409, "Embedding settings changed. Migrate the catalog and index."
                    )
                return store.public(existing)
            try:
                pages, missing = await asyncio.to_thread(
                    extract_pages,
                    content,
                    suffix,
                    settings.max_pdf_pages,
                )
            except InvalidDocument as exc:
                raise HTTPException(422, str(exc)) from exc
            chunks = chunks_for(pages, identity, metadata)
            document = {
                **metadata.model_dump(),
                "id": identity,
                "filename": filename,
                "storage_name": identity + suffix,
                "status": "indexing",
                "pages": len(pages),
                "chunks": len(chunks),
                "ocr_required_pages": missing,
                "embedding_identity": embedding_identity(services),
                "index_status": "indexing",
            }
            store.put(document)
            try:
                # Batches bound model memory and preserve deterministic IDs on retry.
                for start in range(0, len(chunks), 16):
                    batch = chunks[start : start + 16]
                    prefix = settings.embed_document_prefix.replace("{title}", metadata.title)
                    vectors = await services.embed([prefix + chunk["text"] for chunk in batch])
                    if start == 0:
                        await services.ensure_collection(len(vectors[0]))
                    await services.qdrant(
                        "PUT",
                        services.collection_path + "/points?wait=true",
                        json={
                            "points": [
                                {
                                    "id": chunk["chunk_id"],
                                    "vector": vector,
                                    "payload": {
                                        **chunk,
                                        "embedding_identity": embedding_identity(services),
                                    },
                                }
                                for chunk, vector in zip(batch, vectors, strict=True)
                            ]
                        },
                        timeout=settings.model_timeout_seconds,
                    )
                target = store.directory / document["storage_name"]
                temporary = target.with_suffix(".pending")
                temporary.write_bytes(content)
                temporary.replace(target)
                document["status"] = "ready"
                document["index_status"] = "indexed"
                store.put(document)
            except BaseException:
                # A failed/aborted import is invisible to students; same-file retry is idempotent.
                document["status"] = "failed"
                document["index_status"] = "failed"
                store.put(document)
                with contextlib.suppress(FileNotFoundError):
                    (store.directory / (identity + ".pending")).unlink()
                raise
            return store.public(document)

    return app
