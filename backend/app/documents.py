import hashlib
import io
import json
import re
from uuid import NAMESPACE_URL, uuid5

from pypdf import PdfReader

from app.schemas import DocumentInput


class InvalidDocument(Exception):
    pass


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
            if reader.is_encrypted:
                raise InvalidDocument("Encrypted PDFs are not supported.")
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
