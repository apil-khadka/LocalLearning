import asyncio
import io

import httpx
from reportlab.pdfgen import canvas

from app.config import Settings
from app.store import Store


def pdf_bytes(text: str | None) -> bytes:
    output = io.BytesIO()
    document = canvas.Canvas(output)
    if text:
        document.drawString(40, 700, text)
    document.showPage()
    document.save()
    return output.getvalue()


def saved_document(identity: str, *, title: str, grade: int | None, subject: str) -> dict:
    return {
        "id": identity,
        "title": title,
        "grade": grade,
        "subject": subject,
        "chapter": "Whole book",
        "license": "Prototype fixture permission",
        "source": "Local test fixture",
        "filename": identity + ".pdf",
        "storage_name": identity + ".pdf",
        "pages": 1,
        "chunks": 0,
        "status": "ready",
        "index_status": "not_indexed",
        "embedding_identity": "",
        "ocr_required_pages": [],
    }


def test_catalog_filters_cross_grade_books_and_paginates(client, settings):
    store = Store(settings.data_dir)
    entries = [
        ("1" * 32, "Grade 1 Birds", 1, "Science"),
        ("2" * 32, "Grade 2 Mathematics", 2, "Mathematics"),
        ("3" * 32, "Grade 2 Plants", 2, "Science"),
        ("4" * 32, "Basic learning reference", None, "Civics"),
    ]
    for identity, title, grade, subject in entries:
        store.put(saved_document(identity, title=title, grade=grade, subject=subject))

    first = client.get("/api/textbooks/catalog?grade=2&limit=1&offset=0").json()
    second = client.get("/api/textbooks/catalog?grade=2&limit=1&offset=1").json()
    filtered = client.get("/api/textbooks/catalog?grade=2&subject=Science&q=Plants").json()

    assert first["total"] == 3
    assert first["items"][0]["title"] == "Grade 2 Mathematics"
    assert first["subjects"] == ["Civics", "Mathematics", "Science"]
    assert second["items"][0]["title"] == "Grade 2 Plants"
    assert [book["title"] for book in filtered["items"]] == ["Grade 2 Plants"]
    assert filtered["total"] == 1
    assert "storage_name" not in first["items"][0]


def test_staff_can_index_one_saved_textbook_in_small_batches(client, settings, staff, stack):
    identity = "a" * 32
    store = Store(settings.data_dir)
    (settings.data_dir / (identity + ".pdf")).write_bytes(pdf_bytes("A" * 5000))
    store.put(saved_document(identity, title="Long science chapter", grade=8, subject="Science"))

    unauthenticated = client.post("/api/admin/index-book", json={"document_id": identity})
    response = client.post(
        "/api/admin/index-book",
        headers=staff,
        json={"document_id": identity},
    )

    assert unauthenticated.status_code == 401
    assert response.status_code == 200, response.text
    assert response.json()["index_status"] == "indexed"
    assert response.json()["chunks"] == 6
    assert len(stack.points) == 6
    assert len([call for call in stack.calls if call == ("POST", "/api/embed")]) == 2

    retry = client.post(
        "/api/admin/index-book",
        headers=staff,
        json={"document_id": identity},
    )
    assert retry.json()["index_status"] == "indexed"
    assert len([call for call in stack.calls if call == ("POST", "/api/embed")]) == 2


def test_failed_book_index_can_be_retried(client, settings, staff, stack):
    identity = "b" * 32
    store = Store(settings.data_dir)
    (settings.data_dir / (identity + ".pdf")).write_bytes(pdf_bytes("Force and motion"))
    store.put(saved_document(identity, title="Force", grade=8, subject="Science"))
    stack.outage = "ollama.test"

    failed = client.post(
        "/api/admin/index-book",
        headers=staff,
        json={"document_id": identity},
    )
    assert failed.status_code == 503
    assert store.get(identity)["index_status"] == "failed"

    stack.outage = None
    retried = client.post(
        "/api/admin/index-book",
        headers=staff,
        json={"document_id": identity},
    )
    assert retried.status_code == 200
    assert retried.json()["index_status"] == "indexed"


def test_scanned_pdf_is_marked_as_needing_ocr(client, settings, staff):
    identity = "c" * 32
    store = Store(settings.data_dir)
    (settings.data_dir / (identity + ".pdf")).write_bytes(pdf_bytes(None))
    store.put(saved_document(identity, title="Scanned chapter", grade=7, subject="Science"))

    response = client.post(
        "/api/admin/index-book",
        headers=staff,
        json={"document_id": identity},
    )

    assert response.status_code == 422
    assert "OCR required" in response.json()["detail"]
    assert store.get(identity)["index_status"] == "needs_ocr"


def test_openai_compatible_embedding_settings_are_independent(tmp_path):
    settings = Settings(
        _env_file=None,
        data_dir=tmp_path,
        ai_enabled=True,
        chat_provider="ollama",
        ollama_base_url="http://ollama.test",
        embed_provider="openai-compatible",
        embed_api_base_url="https://embedding.test/v1",
        embed_api_key="test-embedding-key-that-is-not-real",
        embed_model="school-embedding-model",
        qdrant_url="http://qdrant.test",
        admin_token="test-only-staff-token-that-is-not-a-real-secret",
    )

    class EmbeddingResponseStack:
        def __init__(self):
            self.calls = []

        def __call__(self, request):
            self.calls.append(request)
            return httpx.Response(
                200,
                json={
                    "object": "list",
                    "data": [
                        {"object": "embedding", "index": 0, "embedding": [1.0, 0.0, 0.0]},
                        {"object": "embedding", "index": 1, "embedding": [0.0, 1.0, 0.0]},
                    ],
                    "model": "school-embedding-model",
                    "usage": {"prompt_tokens": 4, "total_tokens": 4},
                },
            )

    from app.dependencies import LocalServices

    mock = EmbeddingResponseStack()

    async def run_embedding():
        async with httpx.AsyncClient(transport=httpx.MockTransport(mock)) as client:
            services = LocalServices(settings, client)
            return await services.embed(["first passage", "second passage"])

    assert asyncio.run(run_embedding()) == [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]]
    assert mock.calls[0].url == "https://embedding.test/v1/embeddings"
    assert mock.calls[0].headers["authorization"] == "Bearer test-embedding-key-that-is-not-real"
    assert "school-embedding-model" in mock.calls[0].content.decode()
