"""Seed the offline book catalog from the user's private CDC download folder."""

import argparse
import hashlib
import json
import shutil
from pathlib import Path
from urllib.parse import urlsplit

from app.documents import InvalidDocument, count_pdf_file
from app.schemas import DocumentInput
from app.store import Store

MAX_BOOKS = 400
MAX_PDF_BYTES = 150 * 1024 * 1024
MAX_PDF_PAGES = 1000
PRIVATE_PERMISSION_NOTE = "User-confirmed local prototype permission"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def document_id_for_file(path: Path, metadata: DocumentInput) -> str:
    """Match documents.document_id while hashing the file in bounded chunks."""
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(1024 * 1024):
            digest.update(chunk)
    digest.update(json.dumps(metadata.model_dump(), sort_keys=True, ensure_ascii=False).encode())
    return digest.hexdigest()[:32]


def _validate_catalog_item(item: dict, source_dir: Path) -> tuple[Path, DocumentInput]:
    filename = item.get("filename")
    if (
        not isinstance(filename, str)
        or Path(filename).name != filename
        or not filename.endswith(".pdf")
    ):
        raise ValueError("A catalog entry has an unsafe or missing PDF filename.")
    source_path = (source_dir / filename).resolve()
    if source_path.parent != source_dir or not source_path.is_file():
        raise ValueError("A catalog PDF is missing from the private download folder.")
    if source_path.stat().st_size < 64 or source_path.stat().st_size > MAX_PDF_BYTES:
        raise ValueError("A catalog PDF is outside the configured size limit.")
    with source_path.open("rb") as source:
        if source.read(5) != b"%PDF-":
            raise ValueError("A catalog file is not a PDF.")
    if sha256_file(source_path) != item.get("sha256"):
        raise ValueError("A catalog PDF does not match its recorded checksum.")
    source_url = item.get("source_page")
    parsed_source = urlsplit(source_url or "")
    if (
        parsed_source.scheme != "https"
        or parsed_source.hostname not in {"moecdc.gov.np", "www.moecdc.gov.np"}
        or not parsed_source.path.startswith("/content/")
    ):
        raise ValueError("A catalog entry does not point to an official CDC source page.")
    try:
        metadata = DocumentInput(
            title=item["title"],
            grade=item.get("grade"),
            subject=item["subject"],
            chapter="Whole book",
            license=PRIVATE_PERMISSION_NOTE,
            source=source_url,
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("A catalog entry has invalid book metadata.") from exc
    return source_path, metadata


def import_catalog(manifest_path: Path, data_dir: Path) -> dict:
    manifest_path = manifest_path.resolve()
    source_dir = manifest_path.parent.resolve()
    try:
        manifest = json.loads(manifest_path.read_text("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("The private book catalog manifest could not be read.") from exc
    if not isinstance(manifest, dict):
        raise ValueError("The private catalog is incomplete or outside the supported size.")
    books = manifest.get("books")
    if (
        manifest.get("complete") is not True
        or not isinstance(books, list)
        or not books
        or len(books) > MAX_BOOKS
    ):
        raise ValueError("The private catalog is incomplete or outside the supported size.")

    store = Store(data_dir)
    imported = 0
    skipped = 0
    for index, item in enumerate(books, start=1):
        if not isinstance(item, dict):
            raise ValueError("The private catalog contains an invalid book entry.")
        source_path, metadata = _validate_catalog_item(item, source_dir)
        try:
            page_count = count_pdf_file(source_path, MAX_PDF_PAGES)
        except InvalidDocument as exc:
            raise ValueError(f"A CDC book could not be read: {item['title']}.") from exc
        identity = document_id_for_file(source_path, metadata)
        storage_name = identity + ".pdf"
        target = store.directory / storage_name
        existing = store.get(identity)
        if target.is_file() and sha256_file(target) == item["sha256"] and existing:
            document = existing
            skipped += 1
        else:
            temporary = target.with_suffix(".pending")
            with source_path.open("rb") as source, temporary.open("wb") as destination:
                shutil.copyfileobj(source, destination, length=1024 * 1024)
            if sha256_file(temporary) != item["sha256"]:
                temporary.unlink(missing_ok=True)
                raise ValueError("A copied book failed its checksum verification.")
            temporary.replace(target)
            was_indexed = bool(existing and existing.get("chunks", 0))
            document = {
                **metadata.model_dump(),
                "id": identity,
                "filename": item["filename"],
                "storage_name": storage_name,
                "status": "ready",
                "pages": page_count,
                "chunks": existing.get("chunks", 0) if existing else 0,
                "ocr_required_pages": existing.get("ocr_required_pages", []) if existing else [],
                "embedding_identity": existing.get("embedding_identity", "") if was_indexed else "",
                "index_status": existing.get("index_status", "indexed")
                if was_indexed
                else "not_indexed",
            }
            store.put(document)
            imported += 1
        if index % 10 == 0 or index == len(books):
            print(f"Processed {index}/{len(books)} private PDFs.", flush=True)
    return {"imported": imported, "already_present": skipped, "total": len(books)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path("/private-cdc-books/catalog.json"),
        help="The catalog generated by scripts/fetch_cdc_k12_books.py.",
    )
    parser.add_argument("--data-dir", type=Path, default=Path("/data"))
    args = parser.parse_args(argv)
    result = import_catalog(args.manifest, args.data_dir)
    print(
        "Private CDC library import complete: "
        f"{result['imported']} added, {result['already_present']} already present, "
        f"{result['total']} total."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
