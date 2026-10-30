import hashlib
import io
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pypdf import PdfWriter
from reportlab.pdfgen import canvas

from app.config import Settings
from app.documents import InvalidDocument, count_pages, count_pdf_file, document_id, extract_pages
from app.library_import import document_id_for_file, import_catalog
from app.main import create_app
from app.schemas import DocumentInput
from app.store import Store


def pdf_bytes(text: str | None = "Grade 9 science textbook") -> bytes:
    output = io.BytesIO()
    pdf = canvas.Canvas(output)
    if text:
        pdf.drawString(40, 700, text)
    pdf.showPage()
    pdf.save()
    return output.getvalue()


def encrypted_pdf_bytes(user_password: str) -> bytes:
    output = io.BytesIO()
    writer = PdfWriter()
    writer.add_blank_page(width=100, height=100)
    writer.encrypt(
        user_password=user_password,
        owner_password="owner-secret",
        algorithm="AES-256-R5",
    )
    writer.write(output)
    return output.getvalue()


def private_manifest(tmp_path: Path, content: bytes) -> Path:
    filename = "9-science-grade-9.pdf"
    source = tmp_path / filename
    source.write_bytes(content)
    manifest = {
        "complete": True,
        "books": [
            {
                "grade": 9,
                "title": "Science and Technology Grade 9",
                "subject": "Science and Technology",
                "filename": filename,
                "source_page": "https://moecdc.gov.np/content/61/science-grade-9/",
                "download_url": "https://giwmscdnone.gov.np/media/grade9.pdf",
                "bytes": len(content),
                "sha256": hashlib.sha256(content).hexdigest(),
            }
        ],
    }
    path = tmp_path / "catalog.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    return path


def test_reading_library_import_needs_no_embedding_or_vector_services(tmp_path):
    manifest = private_manifest(tmp_path, pdf_bytes())
    data_dir = tmp_path / "school-data"

    result = import_catalog(manifest, data_dir)

    assert result == {"imported": 1, "already_present": 0, "total": 1}
    books = Store(data_dir).list(grade=9)
    assert len(books) == 1
    book = books[0]
    assert book["title"] == "Science and Technology Grade 9"
    assert book["status"] == "ready"
    assert book["index_status"] == "not_indexed"
    assert book["chunks"] == 0
    served_file = data_dir / book["storage_name"]
    assert served_file.read_bytes().startswith(b"%PDF-")


def test_reading_library_import_is_idempotent(tmp_path):
    manifest = private_manifest(tmp_path, pdf_bytes())
    data_dir = tmp_path / "school-data"

    assert import_catalog(manifest, data_dir)["imported"] == 1
    assert import_catalog(manifest, data_dir) == {
        "imported": 0,
        "already_present": 1,
        "total": 1,
    }
    assert len(Store(data_dir).list()) == 1


def test_private_library_import_checks_manifest_checksum(tmp_path):
    manifest = private_manifest(tmp_path, pdf_bytes())
    (tmp_path / "9-science-grade-9.pdf").write_bytes(pdf_bytes("modified"))

    with pytest.raises(ValueError, match="checksum"):
        import_catalog(manifest, tmp_path / "school-data")


def test_private_library_import_rejects_path_traversal(tmp_path):
    manifest = private_manifest(tmp_path, pdf_bytes())
    data = json.loads(manifest.read_text("utf-8"))
    data["books"][0]["filename"] = "../outside.pdf"
    manifest.write_text(json.dumps(data), encoding="utf-8")

    with pytest.raises(ValueError, match="unsafe"):
        import_catalog(manifest, tmp_path / "school-data")


def test_document_id_for_file_matches_regular_document_import(tmp_path):
    content = pdf_bytes()
    source = tmp_path / "source.pdf"
    source.write_bytes(content)
    metadata = DocumentInput(
        title="Science Grade 9",
        grade=9,
        subject="Science",
        chapter="Whole book",
        license="User-confirmed local prototype permission",
        source="https://moecdc.gov.np/content/61/science-grade-9/",
    )

    assert document_id_for_file(source, metadata) == document_id(content, metadata)


def test_library_validation_accepts_a_scanned_pdf_without_text_extraction():
    scanned_page = pdf_bytes(None)

    assert count_pages(scanned_page, ".pdf", 10) == 1
    with pytest.raises(InvalidDocument, match="OCR required"):
        extract_pages(scanned_page, ".pdf", 10)


def test_library_can_read_pdf_with_empty_user_password(tmp_path):
    encrypted = encrypted_pdf_bytes("")
    path = tmp_path / "blank-user-password.pdf"
    path.write_bytes(encrypted)

    assert count_pages(encrypted, ".pdf", 10) == 1
    assert count_pdf_file(path, 10) == 1


def test_library_does_not_guess_a_nonempty_pdf_password():
    with pytest.raises(InvalidDocument, match="requires a password"):
        count_pages(encrypted_pdf_bytes("private-password"), ".pdf", 10)


def test_kindergarten_and_cross_grade_books_are_visible_in_grade_filters(tmp_path):
    manifest = private_manifest(tmp_path, pdf_bytes("Kindergarten early learning curriculum"))
    data = json.loads(manifest.read_text("utf-8"))
    kindergarten = data["books"][0]
    kindergarten.update(
        {"grade": 0, "title": "Kindergarten curriculum", "subject": "Early Childhood Education"}
    )
    second_pdf = pdf_bytes("Cross-grade reference material")
    (tmp_path / "cross-grade-reference.pdf").write_bytes(second_pdf)
    data["books"].append(
        {
            **data["books"][0],
            "grade": None,
            "title": "Basic level reference material",
            "subject": "General Learning Resources",
            "filename": "cross-grade-reference.pdf",
            "bytes": len(second_pdf),
            "sha256": hashlib.sha256(second_pdf).hexdigest(),
            "download_url": "https://giwmscdnone.gov.np/media/reference.pdf",
        }
    )
    grade_nine_pdf = pdf_bytes("Grade 9 science")
    (tmp_path / "grade-nine-science.pdf").write_bytes(grade_nine_pdf)
    data["books"].append(
        {
            **kindergarten,
            "grade": 9,
            "title": "Science Grade 9",
            "subject": "Science",
            "filename": "grade-nine-science.pdf",
            "bytes": len(grade_nine_pdf),
            "sha256": hashlib.sha256(grade_nine_pdf).hexdigest(),
            "download_url": "https://giwmscdnone.gov.np/media/grade9-science.pdf",
        }
    )
    manifest.write_text(json.dumps(data), encoding="utf-8")
    data_dir = tmp_path / "school-data"

    assert import_catalog(manifest, data_dir)["imported"] == 3
    with TestClient(create_app(Settings(_env_file=None, data_dir=data_dir))) as client:
        kindergarten = client.get("/api/textbooks?grade=0").json()
        grade_nine = client.get("/api/textbooks?grade=9").json()
        all_books = client.get("/api/textbooks").json()

    assert {book["grade"] for book in kindergarten} == {0, None}
    assert {book["grade"] for book in grade_nine} == {9, None}
    assert len(all_books) == 3
