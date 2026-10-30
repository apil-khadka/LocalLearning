import hashlib
import io
import json
import re
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from pypdf import PdfReader

from app.schemas import DocumentInput


class InvalidDocument(Exception):
    pass


def _unlock_empty_password(reader: PdfReader):
    if not reader.is_encrypted:
        return
    try:
        unlocked = reader.decrypt("")
    except Exception as exc:
        raise InvalidDocument("This encrypted PDF could not be opened.") from exc
    if not unlocked:
        raise InvalidDocument("This PDF requires a password.")


def count_pages(content: bytes, suffix: str, max_pages: int) -> int:
    """Validate a library file without extracting text or requiring AI services."""
    if suffix == ".txt":
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise InvalidDocument("Text files must use UTF-8 encoding.") from exc
        if "\x00" in text or not text.strip():
            raise InvalidDocument("This is not a readable text document.")
        return 1
    if suffix != ".pdf" or not content.startswith(b"%PDF-"):
        raise InvalidDocument("The file is not a PDF.")
    try:
        reader = PdfReader(io.BytesIO(content))
        _unlock_empty_password(reader)
        pages = len(reader.pages)
    except InvalidDocument:
        raise
    except Exception as exc:
        raise InvalidDocument("Could not read this PDF.") from exc
    if pages < 1:
        raise InvalidDocument("The PDF has no readable pages.")
    if pages > max_pages:
        raise InvalidDocument(f"This library accepts books of at most {max_pages} pages.")
    return pages


def count_pdf_file(path: Path, max_pages: int) -> int:
    """Count pages from disk so bulk library setup does not load PDFs into RAM."""
    try:
        reader = PdfReader(path)
        _unlock_empty_password(reader)
        pages = len(reader.pages)
    except InvalidDocument:
        raise
    except Exception as exc:
        raise InvalidDocument("Could not read this PDF.") from exc
    if pages < 1:
        raise InvalidDocument("The PDF has no readable pages.")
    if pages > max_pages:
        raise InvalidDocument(f"This library accepts books of at most {max_pages} pages.")
    return pages


def extract_pages(content: bytes, suffix: str, max_pages: int) -> tuple[list[str], list[int]]:
    if suffix == ".txt":
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise InvalidDocument("Text files must use UTF-8 encoding.") from exc
        if "\x00" in text:
            raise InvalidDocument("This is not a readable text document.")
        pages = [text]
    else:
        if not content.startswith(b"%PDF-"):
            raise InvalidDocument("The file is not a PDF.")
        try:
            reader = PdfReader(io.BytesIO(content))
            _unlock_empty_password(reader)
            if len(reader.pages) > max_pages:
                raise InvalidDocument(f"Import at most {max_pages} pages at a time.")
            pages = [page.extract_text() or "" for page in reader.pages]
        except InvalidDocument:
            raise
        except Exception as exc:
            raise InvalidDocument("Could not extract this PDF. Try a searchable PDF.") from exc
    missing = [i + 1 for i, text in enumerate(pages) if not text.strip()]
    if not pages or len(missing) == len(pages):
        raise InvalidDocument("OCR required: this document has no selectable text.")
    if sum(map(len, pages)) > 1_000_000:
        raise InvalidDocument("Too much extracted text. Import a smaller chapter.")
    return pages, missing


def extract_file_pages(path: Path, max_pages: int) -> tuple[list[str], list[int]]:
    """Extract searchable text from a library file without loading the whole PDF into RAM."""
    if path.suffix.lower() == ".txt":
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            raise InvalidDocument("This text file is not readable UTF-8.") from exc
        if "\x00" in text:
            raise InvalidDocument("This is not a readable text document.")
        pages = [text]
    elif path.suffix.lower() == ".pdf":
        try:
            reader = PdfReader(path)
            _unlock_empty_password(reader)
            if not reader.pages or len(reader.pages) > max_pages:
                raise InvalidDocument(
                    f"Index at most {max_pages} pages per textbook. Split larger files first."
                )
            pages = [page.extract_text() or "" for page in reader.pages]
        except InvalidDocument:
            raise
        except Exception as exc:
            raise InvalidDocument("Could not extract this PDF. Try a searchable PDF.") from exc
    else:
        raise InvalidDocument("Only PDF and UTF-8 text books can be indexed.")
    missing = [i + 1 for i, text in enumerate(pages) if not text.strip()]
    if not pages or len(missing) == len(pages):
        raise InvalidDocument("OCR required: this document has no selectable text.")
    if sum(map(len, pages)) > 1_000_000:
        raise InvalidDocument("This textbook has too much extracted text to index safely.")
    return pages, missing


def document_id(content: bytes, metadata: DocumentInput) -> str:
    identity = json.dumps(metadata.model_dump(), sort_keys=True, ensure_ascii=False).encode()
    return hashlib.sha256(content + identity).hexdigest()[:32]


def chunks_for(pages: list[str], identity: str, metadata: DocumentInput) -> list[dict]:
    chunks = []
    for page_number, page in enumerate(pages, start=1):
        text = re.sub(r"\s+", " ", page).strip()
        # Chunk within a page so citations cannot cross a missing/scanned page.
        for start in range(0, len(text), 850):
            excerpt = text[start : start + 1000]
            if not excerpt.strip():
                continue
            chunk_id = str(uuid5(NAMESPACE_URL, f"dh:{identity}:{page_number}:{start}"))
            chunks.append(
                {
                    **metadata.model_dump(),
                    "document_id": identity,
                    "chunk_id": chunk_id,
                    "subject_key": metadata.subject.casefold(),
                    "chapter_key": metadata.chapter.casefold(),
                    "page_start": page_number,
                    "page_end": page_number,
                    "text": excerpt,
                }
            )
    return chunks
