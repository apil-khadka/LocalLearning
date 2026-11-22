import io
import json

import httpx
from fastapi.testclient import TestClient
from reportlab.pdfgen import canvas

from app.book_search import (
    BookSearchIndex,
    is_front_matter,
    is_readable_text,
    subject_matches,
)
from app.config import Settings
from app.main import create_app
from app.store import Store


def _build_pdf(pages: list[str]) -> bytes:
    buf = io.BytesIO()
    pdf = canvas.Canvas(buf)
    for page_text in pages:
        y = 750
        for line in page_text.splitlines():
            pdf.drawString(40, y, line)
            y -= 16
        pdf.showPage()
    pdf.save()
    return buf.getvalue()


def test_readability_and_front_matter_filters():
    assert is_readable_text(
        "Speed is the distance covered per unit time, whereas velocity also includes direction."
    )
    assert is_readable_text("बल भनेको कुनै वस्तुको अवस्था परिवर्तन गर्ने वा गर्न खोज्ने बाह्य प्रभाव हो।")
    assert not is_readable_text("too short")
    assert not is_readable_text(
        "k|sfzs g]kfn ;/sf/ kf7\\oj|md ljsf; s]Gb| ;fgf]l7dL eStk'/ kf7\\ok':ts"
    )

    assert is_front_matter(1, "Table of Content Unit 1 Force 10 Unit 2 Energy 25")
    assert not is_front_matter(
        15, "6.2 Speed and Velocity: Speed is scalar while velocity is vector."
    )


def test_subject_family_matching():
    assert subject_matches("Science and Technology", "Science")
    assert subject_matches("Science", "Science and Technology")
    assert subject_matches("Mathematics", "Math")
    assert not subject_matches("Mathematics", "Science")


def test_book_search_index_skips_preeti_and_ranks_body_over_toc(tmp_path):
    store = Store(tmp_path)
    pdf = _build_pdf(
        [
            "Contents\n1 Force and Motion 10\n2 Speed and Velocity 18\n3 Energy 30",
            "k|sfzs g]kfn ;/sf/ kf7\\oj|md ljsf; s]Gb| ;fgf]l7dL eStk'/ ;Dk" + "0f{ clwsf/ k",
            (
                "Unit 6 Force and Motion\n"
                "Speed is the distance travelled by an object in unit time.\n"
                "Velocity is the displacement of an object per unit time in a fixed direction."
            ),
        ]
    )
    doc_id = "1" * 32
    (tmp_path / f"{doc_id}.pdf").write_bytes(pdf)
    store.put(
        {
            "id": doc_id,
            "title": "Science and Technology Grade 8",
            "grade": 8,
            "subject": "Science and Technology",
            "chapter": "Whole book",
            "license": "CC0-1.0",
            "source": "CDC fixture",
            "filename": f"{doc_id}.pdf",
            "storage_name": f"{doc_id}.pdf",
            "pages": 3,
            "chunks": 0,
            "status": "ready",
            "index_status": "not_indexed",
            "embedding_identity": "",
            "ocr_required_pages": [],
        }
    )

    index = BookSearchIndex(store)
    count = index.ensure_indexed_for(grade=8, subject="Science")
    assert count == 1
    assert store.get(doc_id)["index_status"] == "not_indexed"

    hits = index.search("What is speed and velocity?", grade=8, subject="Science")
    assert len(hits) == 1
    assert hits[0]["document_id"] == doc_id
    assert hits[0]["page_start"] == 3
    assert "displacement" in hits[0]["text"].lower()

    assert index.search("What is speed and velocity?", grade=9, subject="Science") == []
    assert index.search("What is speed and velocity?", grade=8, subject="Mathematics") == []
    assert index.search("photosynthesis chloroplast", grade=8, subject="Science") == []


def test_tutor_uses_local_fts_books_and_skips_retrieval_on_greetings(tmp_path):
    captured = []

    def handler(request):
        if request.method == "POST" and request.url.path == "/api/v1/chat":
            captured.append(json.loads(request.content))
            return httpx.Response(
                200,
                json={
                    "output": [
                        {
                            "type": "message",
                            "content": (
                                "Speed is distance per unit time, while velocity includes "
                                "direction (page 2)."
                            ),
                        }
                    ]
                },
            )
        return httpx.Response(200, json={"models": [{"type": "llm", "key": "phi-4-mini-instruct"}]})

    store = Store(tmp_path)
    pdf = _build_pdf(
        [
            "Contents\n1 Motion 2\n2 Force 8",
            (
                "Velocity is displacement per unit time in a specific direction, "
                "whereas speed has magnitude only without direction."
            ),
        ]
    )
    doc_id = "2" * 32
    (tmp_path / f"{doc_id}.pdf").write_bytes(pdf)
    store.put(
        {
            "id": doc_id,
            "title": "Grade 8 Science Textbook",
            "grade": 8,
            "subject": "Science and Technology",
            "chapter": "Whole book",
            "license": "CC0-1.0",
            "source": "CDC fixture",
            "filename": f"{doc_id}.pdf",
            "storage_name": f"{doc_id}.pdf",
            "pages": 2,
            "chunks": 0,
            "status": "ready",
            "index_status": "not_indexed",
            "embedding_identity": "",
            "ocr_required_pages": [],
        }
    )

    settings = Settings(
        _env_file=None,
        data_dir=tmp_path,
        ai_enabled=True,
        chat_provider="lmstudio",
        lmstudio_base_url="http://lmstudio.test",
        lmstudio_model="phi-4-mini-instruct",
        qdrant_url="",
    )
    upstream = httpx.AsyncClient(transport=httpx.MockTransport(handler), trust_env=False)

    with TestClient(create_app(settings, upstream)) as client:
        greeting = client.post(
            "/api/tutor/chat",
            json={"message": "hi", "grade": 8, "subject": "Science"},
        )
        assert greeting.status_code == 200
        assert greeting.json()["grounding"] == "general"
        assert greeting.json()["sources"] == []

        study = client.post(
            "/api/tutor/chat",
            json={
                "message": "What is velocity and how is it different from speed?",
                "grade": 8,
                "subject": "Science",
            },
        )

    assert study.status_code == 200, study.text
    body = study.json()
    assert body["grounding"] == "textbook"
    assert len(body["sources"]) == 1
    assert body["sources"][0]["document_id"] == doc_id
    assert body["sources"][0]["page_start"] == 2

    assert len(captured) == 2
    assert "why this concept matters" in captured[1]["system_prompt"].lower()
    sent_payload = json.loads(captured[1]["input"])
    assert sent_payload["untrusted_textbook_excerpts"][0]["page"] == 2
    assert "specific direction" in sent_payload["untrusted_textbook_excerpts"][0]["text"]


def test_tutor_followup_uses_prior_user_turn_for_local_fts(tmp_path):
    captured = []

    def handler(request):
        if request.method == "POST" and request.url.path == "/api/v1/chat":
            captured.append(json.loads(request.content))
            return httpx.Response(
                200,
                json={
                    "output": [
                        {"type": "message", "content": "For example, a car at 40 km/h north."}
                    ]
                },
            )
        return httpx.Response(200, json={"models": [{"type": "llm", "key": "phi-4-mini-instruct"}]})

    store = Store(tmp_path)
    pdf = _build_pdf(
        [
            "Contents\n1 Motion 2",
            "Velocity measures both speed and direction of travel, such as walking north.",
        ]
    )
    doc_id = "3" * 32
    (tmp_path / f"{doc_id}.pdf").write_bytes(pdf)
    store.put(
        {
            "id": doc_id,
            "title": "Grade 8 Science Textbook",
            "grade": 8,
            "subject": "Science and Technology",
            "chapter": "Whole book",
            "license": "CC0-1.0",
            "source": "CDC fixture",
            "filename": f"{doc_id}.pdf",
            "storage_name": f"{doc_id}.pdf",
            "pages": 2,
            "chunks": 0,
            "status": "ready",
            "index_status": "not_indexed",
            "embedding_identity": "",
            "ocr_required_pages": [],
        }
    )

    settings = Settings(
        _env_file=None,
        data_dir=tmp_path,
        ai_enabled=True,
        chat_provider="lmstudio",
        lmstudio_base_url="http://lmstudio.test",
        lmstudio_model="phi-4-mini-instruct",
        qdrant_url="",
    )
    upstream = httpx.AsyncClient(transport=httpx.MockTransport(handler), trust_env=False)

    with TestClient(create_app(settings, upstream)) as client:
        followup = client.post(
            "/api/tutor/chat",
            json={
                "message": "Give me an example of that",
                "grade": 8,
                "subject": "Science",
                "history": [{"role": "user", "content": "What is velocity?"}],
            },
        )

    assert followup.status_code == 200, followup.text
    body = followup.json()
    assert body["grounding"] == "textbook"
    assert len(body["sources"]) == 1
    assert body["sources"][0]["page_start"] == 2
    assert len(captured) == 1
