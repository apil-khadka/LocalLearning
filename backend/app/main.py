import asyncio
import contextlib
import hashlib
import hmac
import logging
import re
import sqlite3
import time
from contextlib import asynccontextmanager
from http.cookies import SimpleCookie
from pathlib import Path
from typing import Annotated
from uuid import uuid4

import httpx
from fastapi import FastAPI, File, Form, HTTPException, Query, Request, Response, UploadFile
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
from app.identity import (
    BootstrapInput,
    ClassInput,
    EnrollmentInput,
    IdentityStore,
    LoginInput,
    PasswordChangeInput,
    PasswordResetInput,
    StudentInput,
    UserInput,
    UserStatusInput,
)
from app.kolibri import fetch_catalog
from app.notes import (
    NoteInput,
    ReviewRequest,
    check_document,
    new_note,
    now,
    revise_note,
    student_view,
)
from app.schemas import ChatRequest, ChatResponse, DocumentInput, IndexBookRequest, Turn
from app.store import Store
from app.tutor import answer_question, embedding_identity

logger = logging.getLogger("digital_himalaya")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(handler)
logger.setLevel(logging.INFO)
logger.propagate = False


def _cookie_value(headers: dict[bytes, bytes], name: str) -> str | None:
    cookie = SimpleCookie()
    try:
        cookie.load(headers.get(b"cookie", b"").decode("latin-1"))
    except Exception:
        return None
    morsel = cookie.get(name)
    return morsel.value if morsel else None


class RequestBoundary:
    """Authenticate before reading uploads; bound even chunked request bodies."""

    def __init__(self, app, settings: Settings, identity: IdentityStore):
        self.app, self.settings, self.identity = app, settings, identity

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        headers = dict(scope["headers"])
        if scope["path"].startswith("/api/admin"):
            token = self.settings.admin_token.get_secret_value()
            expected = ("Bearer " + token).encode() if token else b""
            bearer_ok = (
                bool(token)
                and self.identity.user_count() == 0
                and hmac.compare_digest(headers.get(b"authorization", b""), expected)
            )
            session_token = _cookie_value(headers, self.settings.auth_cookie_name)
            signed_in = self.identity.user_for_session(session_token)
            cookie_user_ok = bool(
                signed_in
                and signed_in[0]["role"] in {"teacher", "admin"}
                and not signed_in[0]["must_change_password"]
            )
            if not bearer_ok and not cookie_user_ok and not token:
                has_users = self.identity.user_count() > 0
                return await JSONResponse(
                    {
                        "detail": (
                            "Sign in with a teacher or administrator account."
                            if has_users
                            else "Staff access is disabled until configured."
                        )
                    },
                    401 if has_users else 503,
                )(scope, receive, send)
            if not bearer_ok and not cookie_user_ok:
                return await JSONResponse(
                    {"detail": "Staff sign-in required."},
                    401,
                    headers={"WWW-Authenticate": "Bearer"},
                )(scope, receive, send)
            if (
                cookie_user_ok
                and not bearer_ok
                and scope["method"] in {"POST", "PUT", "PATCH", "DELETE"}
            ):
                csrf = headers.get(b"x-csrf-token", b"").decode("latin-1")
                if not self.identity.verify_csrf(session_token, csrf):
                    return await JSONResponse({"detail": "Request verification failed."}, 403)(
                        scope, receive, send
                    )
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
    identity = IdentityStore(store.path)
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
    app.add_middleware(RequestBoundary, settings=settings, identity=identity)
    app.state.identity = identity

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

    def signed_in(http_request: Request, roles: set[str] | None = None, *, csrf: bool = False):
        session_token = http_request.cookies.get(settings.auth_cookie_name)
        session = identity.user_for_session(session_token)
        if not session:
            raise HTTPException(401, "Sign in to continue.")
        user, _ = session
        if user["must_change_password"] and http_request.url.path not in {
            "/api/auth/me",
            "/api/auth/password",
            "/api/auth/logout",
        }:
            raise HTTPException(403, "Change your initial password before continuing.")
        if roles and user["role"] not in roles:
            raise HTTPException(403, "Your account does not have access to this page.")
        if csrf and not identity.verify_csrf(
            session_token, http_request.headers.get("X-CSRF-Token")
        ):
            raise HTTPException(403, "Request verification failed.")
        return user

    def staff_actor(http_request: Request, *, csrf: bool = False) -> dict:
        session_token = http_request.cookies.get(settings.auth_cookie_name)
        session = identity.user_for_session(session_token)
        if session:
            user, _ = session
            if user["role"] not in {"teacher", "admin"}:
                raise HTTPException(403, "Your account does not have staff access.")
            if user["must_change_password"]:
                raise HTTPException(403, "Change your initial password before continuing.")
            if csrf and not identity.verify_csrf(
                session_token, http_request.headers.get("X-CSRF-Token")
            ):
                raise HTTPException(403, "Request verification failed.")
            return user
        token = settings.admin_token.get_secret_value()
        authorization = http_request.headers.get("Authorization", "").encode()
        if (
            not identity.user_count()
            and token
            and hmac.compare_digest(authorization, ("Bearer " + token).encode())
        ):
            return {"id": "", "display_name": "Initial operator", "role": "admin"}
        raise HTTPException(401, "Sign in with a teacher or administrator account.")

    def issue_session(response: Response, user: dict) -> dict:
        token, csrf_token = identity.create_session(user["id"])
        response.set_cookie(
            settings.auth_cookie_name,
            token,
            max_age=IdentityStore.SESSION_TTL_SECONDS,
            httponly=True,
            secure=settings.auth_cookie_secure,
            samesite="strict",
            path="/",
        )
        return {"user": user, "csrf_token": csrf_token}

    @app.get("/api/auth/status")
    async def auth_status():
        return {
            "users_exist": identity.user_count() > 0,
            "authentication_required": settings.require_auth,
        }

    @app.post("/api/auth/bootstrap", status_code=201)
    async def bootstrap_admin(data: BootstrapInput, http_request: Request, response: Response):
        token = settings.admin_token.get_secret_value()
        authorization = http_request.headers.get("Authorization", "").encode()
        if not token or not hmac.compare_digest(authorization, ("Bearer " + token).encode()):
            raise HTTPException(401, "Initial setup credential is invalid.")
        try:
            user = identity.create_bootstrap_admin(data)
        except sqlite3.IntegrityError as exc:
            raise HTTPException(409, "That username is already in use.") from exc
        if user is None:
            raise HTTPException(409, "Initial setup is already complete.")
        return issue_session(response, user)

    @app.post("/api/auth/login")
    async def login(data: LoginInput, response: Response):
        user = identity.authenticate(data.username, data.password)
        if user is None:
            raise HTTPException(401, "Username or password is incorrect.")
        return issue_session(response, user)

    @app.post("/api/auth/password")
    async def change_password(data: PasswordChangeInput, http_request: Request, response: Response):
        user = signed_in(http_request, csrf=True)
        if not identity.change_password(user["id"], data.current_password, data.new_password):
            raise HTTPException(403, "The current password is incorrect.")
        updated = identity.get_user(user["id"])
        return issue_session(response, updated)

    @app.get("/api/auth/me")
    async def who_am_i(http_request: Request):
        user = signed_in(http_request)
        session = identity.user_for_session(http_request.cookies.get(settings.auth_cookie_name))
        return {"user": user, "csrf_token": session[1] if session else None}

    @app.post("/api/auth/logout", status_code=204)
    async def logout(http_request: Request, response: Response):
        user = signed_in(http_request, csrf=True)
        del user
        identity.delete_session(http_request.cookies.get(settings.auth_cookie_name))
        response.delete_cookie(
            settings.auth_cookie_name,
            path="/",
            secure=settings.auth_cookie_secure,
            httponly=True,
            samesite="strict",
        )

    @app.get("/api/admin/users")
    async def users(http_request: Request, include_disabled: bool = False):
        signed_in(http_request, {"admin"})
        return identity.list_users(include_disabled=include_disabled)

    @app.get("/api/admin/transcript-audit")
    async def transcript_audit(
        http_request: Request,
        limit: int = Query(100, ge=1, le=500),
        offset: int = Query(0, ge=0),
    ):
        signed_in(http_request, {"admin"})
        return identity.list_transcript_audit(limit, offset)

    @app.post("/api/admin/users", status_code=201)
    async def create_user(data: UserInput, http_request: Request):
        signed_in(http_request, {"admin"}, csrf=True)
        try:
            return identity.create_user(data)
        except sqlite3.IntegrityError as exc:
            raise HTTPException(409, "That username is already in use.") from exc

    @app.patch("/api/admin/users/{user_id}")
    async def update_user_status(user_id: str, data: UserStatusInput, http_request: Request):
        actor = signed_in(http_request, {"admin"}, csrf=True)
        if user_id == actor["id"] and data.disabled:
            raise HTTPException(422, "You cannot disable your own account.")
        if not identity.set_user_disabled(user_id, data.disabled):
            raise HTTPException(409, "The account could not be updated.")
        return {"id": user_id, "disabled": data.disabled}

    @app.post("/api/admin/users/{user_id}/password", status_code=204)
    async def reset_user_password(user_id: str, data: PasswordResetInput, http_request: Request):
        actor = signed_in(http_request, {"admin"}, csrf=True)
        if user_id == actor["id"]:
            raise HTTPException(422, "Use the password change page for your own account.")
        if not identity.reset_password(user_id, data.temporary_password):
            raise HTTPException(404, "Active account not found.")

    @app.post("/api/teacher/classes/{class_id}/students/{student_id}/password", status_code=204)
    async def reset_student_password(
        class_id: str,
        student_id: str,
        data: PasswordResetInput,
        http_request: Request,
    ):
        actor = signed_in(http_request, {"teacher", "admin"}, csrf=True)
        if not identity.class_allowed(actor, class_id) or not identity.student_in_class(
            class_id, student_id
        ):
            raise HTTPException(404, "Student account not found in this class.")
        student = identity.get_user(student_id)
        if not student or student["role"] != "student":
            raise HTTPException(404, "Student account not found in this class.")
        if not identity.reset_password(student_id, data.temporary_password):
            raise HTTPException(404, "Student account not found in this class.")

    @app.get("/api/student/dashboard")
    async def student_dashboard(http_request: Request):
        user = signed_in(http_request, {"student"})
        return identity.student_dashboard(user)

    @app.get("/api/account/sessions")
    async def account_sessions(http_request: Request, limit: int = Query(100, ge=1, le=100)):
        user = signed_in(http_request)
        return identity.list_student_sessions(user["id"], limit)

    @app.get("/api/account/sessions/{session_id}")
    async def account_session(session_id: str, http_request: Request):
        user = signed_in(http_request)
        session = identity.get_student_session(session_id, user["id"])
        if not session:
            raise HTTPException(404, "Tutor session not found.")
        return session

    @app.delete("/api/account/sessions/{session_id}", status_code=204)
    async def delete_account_session(session_id: str, http_request: Request):
        user = signed_in(http_request, csrf=True)
        if not identity.delete_student_session(session_id, user["id"]):
            raise HTTPException(404, "Tutor session not found.")

    @app.get("/api/teacher/dashboard")
    async def teacher_dashboard(http_request: Request):
        user = signed_in(http_request, {"teacher", "admin"})
        classes = identity.list_classes(user)
        return {
            "user": user,
            "classes": classes,
            "student_count": sum(len(identity.students_for_class(item["id"])) for item in classes),
            "session_count": sum(item["session_count"] for item in classes),
        }

    @app.post("/api/teacher/classes", status_code=201)
    async def create_class(data: ClassInput, http_request: Request):
        user = signed_in(http_request, {"teacher", "admin"}, csrf=True)
        teacher_id = data.teacher_id or (user["id"] if user["role"] == "teacher" else None)
        if user["role"] == "teacher" and teacher_id != user["id"]:
            raise HTTPException(403, "Teachers can create only their own classes.")
        if not teacher_id:
            raise HTTPException(422, "Choose a teacher for this class.")
        try:
            return identity.create_class(
                name=data.name,
                grade=data.grade,
                creator_id=user["id"],
                teacher_id=teacher_id,
            )
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc

    @app.post("/api/teacher/students", status_code=201)
    async def create_student(data: StudentInput, http_request: Request):
        user = signed_in(http_request, {"teacher", "admin"}, csrf=True)
        class_record = None
        if data.class_id:
            if not identity.class_allowed(user, data.class_id):
                raise HTTPException(404, "Class not found.")
            class_record = identity.get_class(data.class_id)
            if class_record and class_record["grade"] != data.grade:
                raise HTTPException(422, "Student grade must match the selected class.")
        try:
            student = identity.create_user(
                UserInput(
                    username=data.username,
                    display_name=data.display_name,
                    password=data.password,
                    role="student",
                    grade=data.grade,
                )
            )
        except sqlite3.IntegrityError as exc:
            raise HTTPException(409, "That username is already in use.") from exc
        if class_record and not identity.enroll_student(data.class_id, student["id"]):
            raise HTTPException(422, "The student account could not be enrolled.")
        return student

    @app.get("/api/teacher/classes/{class_id}/students")
    async def class_students(class_id: str, http_request: Request):
        user = signed_in(http_request, {"teacher", "admin"})
        if not identity.class_allowed(user, class_id):
            raise HTTPException(404, "Class not found.")
        return identity.students_for_class(class_id)

    @app.post("/api/teacher/classes/{class_id}/students", status_code=201)
    async def enroll_student(class_id: str, data: EnrollmentInput, http_request: Request):
        user = signed_in(http_request, {"teacher", "admin"}, csrf=True)
        if not identity.class_allowed(user, class_id):
            raise HTTPException(404, "Class not found.")
        if not identity.enroll_student(class_id, data.student_id):
            raise HTTPException(
                422,
                "Choose an active learner in this grade who is not assigned to another class.",
            )
        return {"class_id": class_id, "student_id": data.student_id}

    @app.get("/api/teacher/classes/{class_id}/sessions")
    async def class_sessions(
        class_id: str,
        http_request: Request,
        limit: int = Query(100, ge=1, le=100),
    ):
        user = signed_in(http_request, {"teacher", "admin"})
        if not identity.class_allowed(user, class_id):
            raise HTTPException(404, "Class not found.")
        sessions = identity.sessions_for_class(class_id, limit)
        for session in sessions:
            identity.audit_transcript_view(
                user["id"], session["student_id"], session["id"], action="list"
            )
        return sessions

    @app.get("/api/teacher/sessions/{session_id}")
    async def teacher_session(
        session_id: str, http_request: Request, class_id: str | None = Query(None)
    ):
        user = signed_in(http_request, {"teacher", "admin"})
        if user["role"] == "teacher" and (
            not class_id or not identity.class_allowed(user, class_id)
        ):
            raise HTTPException(404, "Tutor session not found.")
        session = identity.get_teacher_session(
            session_id, class_id, include_disabled=user["role"] == "admin"
        )
        if not session:
            raise HTTPException(404, "Tutor session not found.")
        identity.audit_transcript_view(user["id"], session["student_id"], session_id)
        return session

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
            if settings.chat_provider == "lmstudio":
                if not settings.lmstudio_base_url or not settings.lmstudio_model:
                    chat_status = "unconfigured"
                else:
                    try:
                        names = await services.lmstudio_models()
                        chat_status = (
                            "ready" if settings.lmstudio_model in names else "missing_model"
                        )
                    except DependencyUnavailable:
                        chat_status = "unavailable"
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

        async def kolibri_status():
            status = await services.probe_web(
                settings.kolibri_public_url, settings.kolibri_probe_url
            )
            if status["status"] != "reachable":
                return status
            try:
                version, channels = await fetch_catalog(
                    client,
                    settings.kolibri_probe_url or settings.kolibri_public_url,
                    settings.kolibri_public_url,
                    settings.dependency_timeout_seconds,
                )
            except (httpx.HTTPError, ValueError):
                return status
            resources = sum(item["total_resources"] for item in channels if item["available"])
            return {
                **status,
                "version": version,
                "channel_count": len(channels),
                "available_count": sum(1 for item in channels if item["available"]),
                "resource_count": resources,
            }

        models, vectors, kiwix, kolibri = await asyncio.gather(
            local_models(),
            qdrant(),
            services.probe_web(settings.kiwix_public_url, settings.kiwix_probe_url),
            kolibri_status(),
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
            "evaluation_config": {
                "chat_provider": settings.chat_provider,
                "chat_model": settings.active_chat_model,
                "chat_reasoning_effort": settings.chat_reasoning_effort or None,
                "embedding_provider": settings.embed_provider,
                "embedding_model": settings.embed_model,
                "embedding_identity_sha256": hashlib.sha256(
                    embedding_identity(services).encode()
                ).hexdigest(),
                "retrieval_threshold": settings.retrieval_threshold,
                "retrieval_top_k": settings.retrieval_top_k,
                "max_chat_concurrency": settings.max_chat_concurrency,
            },
        }

    @app.get("/api/services")
    async def service_status():
        return await dependency_status()

    @app.get("/api/kolibri/channels")
    async def kolibri_channels():
        if not settings.kolibri_public_url:
            raise DependencyUnavailable("Kolibri is not configured.")
        probe = await services.probe_web(settings.kolibri_public_url, settings.kolibri_probe_url)
        if probe["status"] != "reachable":
            raise DependencyUnavailable("Kolibri is unavailable.")
        try:
            version, channels = await fetch_catalog(
                client,
                settings.kolibri_probe_url or settings.kolibri_public_url,
                settings.kolibri_public_url,
                settings.dependency_timeout_seconds,
            )
        except (httpx.HTTPError, ValueError) as exc:
            raise DependencyUnavailable("Kolibri did not return a usable catalog.") from exc
        return {
            "status": "reachable",
            "url": settings.kolibri_public_url,
            "version": version,
            "channels": channels,
        }

    def valid_note(note_id: str) -> dict:
        note = store.get_note(note_id) if re.fullmatch(r"[a-f0-9]{32}", note_id) else None
        if note is None:
            raise HTTPException(404, "Note not found.")
        return note

    @app.get("/api/notes")
    async def student_notes(
        grade: int | None = Query(None, ge=1, le=12),
        subject: str | None = Query(None, max_length=120),
        document_id: str | None = Query(None, pattern=r"^[a-f0-9]{32}$"),
    ):
        notes = []
        for note in store.list_notes(status="approved"):
            document = store.get(note["document_id"])
            if (
                document is None
                or document["status"] != "ready"
                or (grade is not None and note["grade"] != grade)
                or (subject and note["subject"].casefold() != subject.strip().casefold())
                or (document_id and note["document_id"] != document_id)
            ):
                continue
            notes.append(student_view(note, document, settings.kolibri_public_url))
        notes.sort(key=lambda item: (item["grade"], item["subject"].casefold(), item["title"]))
        return notes

    @app.get("/api/notes/{note_id}")
    async def student_note(note_id: str):
        note = valid_note(note_id)
        document = store.get(note["document_id"])
        if note["status"] != "approved" or document is None or document["status"] != "ready":
            raise HTTPException(404, "Note not found.")
        return student_view(note, document, settings.kolibri_public_url)

    @app.get("/api/admin/notes")
    async def staff_notes():
        return store.list_notes()

    @app.post("/api/admin/notes", status_code=201)
    async def create_note(data: NoteInput, http_request: Request):
        actor = staff_actor(http_request, csrf=True)
        problem = check_document(data, store.get(data.document_id), require_ready=False)
        if problem:
            raise HTTPException(422, problem)
        note = new_note(data, author_id=actor["id"], author_name=actor["display_name"])
        store.put_note(note)
        return note

    @app.put("/api/admin/notes/{note_id}")
    async def update_note(note_id: str, data: NoteInput, http_request: Request):
        actor = staff_actor(http_request, csrf=True)
        existing = valid_note(note_id)
        problem = check_document(data, store.get(data.document_id), require_ready=False)
        if problem:
            raise HTTPException(422, problem)
        note = revise_note(existing, data, editor_id=actor["id"], editor_name=actor["display_name"])
        store.put_note(note)
        return note

    @app.post("/api/admin/notes/{note_id}/review")
    async def review_note(note_id: str, request: ReviewRequest, http_request: Request):
        actor = staff_actor(http_request, csrf=True)
        note = valid_note(note_id)
        if request.status == "approved":
            if note["status"] != "in_review":
                raise HTTPException(409, "Submit the note for review before approving it.")
            if actor["role"] == "teacher" and note.get("author_id") == actor["id"]:
                raise HTTPException(
                    403, "A different teacher or administrator must review your note."
                )
            reviewer = actor["display_name"] if actor["id"] else request.reviewer
            if not reviewer:
                raise HTTPException(422, "Enter the reviewer's name to approve a note.")
            problem = check_document(note, store.get(note["document_id"]), require_ready=True)
            if problem:
                raise HTTPException(422, problem)
            note.update(
                status="approved",
                reviewer=reviewer,
                reviewer_id=actor["id"],
                reviewed_at=now(),
            )
        else:
            note.update(status=request.status, reviewer="", reviewer_id="", reviewed_at=None)
        note["updated_at"] = now()
        store.put_note(note)
        return note

    @app.delete("/api/admin/notes/{note_id}", status_code=204)
    async def delete_note(note_id: str, http_request: Request):
        staff_actor(http_request, csrf=True)
        valid_note(note_id)
        store.delete_note(note_id)

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
    async def chat(request: ChatRequest, http_request: Request):
        if not settings.ai_enabled:
            raise HTTPException(
                503, "The AI tutor is turned off. Your teacher can enable it after review."
            )
        auth = identity.user_for_session(http_request.cookies.get(settings.auth_cookie_name))
        user = auth[0] if auth else None
        if settings.require_auth and not user:
            raise HTTPException(401, "Sign in before using the tutor.")
        if user and user["must_change_password"]:
            raise HTTPException(403, "Change your initial password before using the tutor.")
        if user and not identity.verify_csrf(
            http_request.cookies.get(settings.auth_cookie_name),
            http_request.headers.get("X-CSRF-Token"),
        ):
            raise HTTPException(403, "Request verification failed.")
        effective_request = request
        if user:
            if user["role"] == "student" and user["grade"] and request.grade != user["grade"]:
                raise HTTPException(422, "The tutor grade must match your student account.")
            history = []
            if request.session_id:
                previous = identity.get_student_session(request.session_id, user["id"])
                if not previous:
                    raise HTTPException(404, "Tutor session not found.")
                history = [
                    Turn(
                        role=item["role"],
                        content=(
                            item["content"]
                            + (
                                f"\nLearner attempt: {item['attempt']}"
                                if item.get("attempt")
                                else ""
                            )
                        )[:3000],
                    )
                    for item in previous["messages"][-8:]
                ]
            effective_request = request.model_copy(update={"history": history})
        try:
            await asyncio.wait_for(chat_slots.acquire(), timeout=0.1)
        except TimeoutError as exc:
            raise HTTPException(
                429,
                "The tutor is helping another learner. Try again shortly.",
                headers={"Retry-After": "5"},
            ) from exc
        try:
            reply = await answer_question(effective_request, services, store)
            if user:
                session_id = identity.append_chat_turn(
                    user=user,
                    request=effective_request,
                    reply=reply.model_dump(mode="json"),
                )
                return reply.model_copy(update={"session_id": session_id})
            return reply
        finally:
            chat_slots.release()

    @app.get("/api/admin/index-status")
    async def index_status(http_request: Request):
        staff_actor(http_request)
        return {
            "services": await dependency_status(),
            "documents": [store.public(doc) for doc in store.list(all_states=True)],
        }

    @app.post("/api/admin/index-book")
    async def index_book(request: IndexBookRequest, http_request: Request):
        staff_actor(http_request, csrf=True)
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
        http_request: Request,
        file: Annotated[UploadFile, File()],
        title: str = Form(...),
        grade: int = Form(...),
        subject: str = Form(...),
        chapter: str = Form(...),
        license: str = Form(...),
        source: str = Form(...),
    ):
        staff_actor(http_request, csrf=True)
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
                if existing.get("index_status") == "indexed" and existing[
                    "embedding_identity"
                ] != embedding_identity(services):
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
            document = {
                **metadata.model_dump(),
                "id": identity,
                "filename": filename,
                "storage_name": identity + suffix,
                "status": "ready",
                "pages": len(pages),
                "chunks": 0,
                "ocr_required_pages": missing,
                "embedding_identity": "",
                "index_status": "not_indexed",
            }
            target = store.directory / document["storage_name"]
            temporary = target.with_suffix(".pending")
            try:
                temporary.write_bytes(content)
                temporary.replace(target)
                store.put(document)
            except OSError as exc:
                with contextlib.suppress(FileNotFoundError):
                    temporary.unlink()
                raise HTTPException(
                    507, "The book could not be saved to the school library."
                ) from exc
            return store.public(document)

    return app
