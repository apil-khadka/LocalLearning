"""Built-in SQLite FTS5 full-text search across local ready textbooks."""

from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING
from uuid import NAMESPACE_URL, uuid5

from pypdf import PdfReader

from app.documents import InvalidDocument, _unlock_empty_password

if TYPE_CHECKING:
    from app.store import Store

SUBJECT_FAMILIES: tuple[frozenset[str], ...] = (
    frozenset({"science", "science and technology"}),
    frozenset({"math", "maths", "mathematics"}),
    frozenset({"social", "social studies"}),
    frozenset({"computer", "computer science"}),
    frozenset({"health", "health and physical education"}),
)

_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")
_PREETI_MARKERS = re.compile(r"[A-Za-z][|\\;~`^\[\]{}]|[|\\;~`^\[\]{}][A-Za-z]")
_CAMEL_NOISE = re.compile(r"[a-z]{2,}[A-Z][a-z]+")
_EN_STOPWORDS = re.compile(
    r"\b(?:the|and|of|to|in|is|are|for|with|that|this|from|by|on|as|at|or|be|"
    r"have|can|we|not|it|an|was|were|will|which|unit|chapter|lesson|grade|class)\b"
)
_TOC_ENTRY = re.compile(r"\b\d{1,3}\s+[A-Za-z]")
_TOKEN_PATTERN = re.compile(r"[A-Za-z0-9\u0900-\u097f]{2,}")

_QUERY_STOPWORDS = frozenset(
    {
        "about",
        "all",
        "an",
        "and",
        "any",
        "are",
        "as",
        "at",
        "be",
        "between",
        "by",
        "can",
        "chapter",
        "class",
        "compare",
        "could",
        "define",
        "definition",
        "describe",
        "did",
        "different",
        "difference",
        "do",
        "does",
        "example",
        "examples",
        "explain",
        "for",
        "from",
        "give",
        "grade",
        "have",
        "help",
        "how",
        "in",
        "into",
        "is",
        "it",
        "its",
        "learn",
        "lesson",
        "me",
        "mean",
        "meaning",
        "more",
        "not",
        "of",
        "on",
        "or",
        "please",
        "question",
        "short",
        "tell",
        "than",
        "that",
        "the",
        "their",
        "them",
        "they",
        "this",
        "to",
        "understand",
        "unit",
        "us",
        "use",
        "was",
        "we",
        "were",
        "what",
        "when",
        "where",
        "which",
        "who",
        "why",
        "will",
        "with",
        "would",
        "you",
        "your",
    }
)


def canonical_subject_keys(subject: str) -> set[str]:
    """Return normalized subject keys including known curriculum naming variants."""
    key = subject.strip().casefold()
    if not key:
        return set()
    keys = {key}
    for family in SUBJECT_FAMILIES:
        if key in family:
            keys.update(family)
    return keys


def subject_matches(doc_subject: str, requested_subject: str) -> bool:
    """Return True when two subject names belong to the same subject family."""
    doc_key = doc_subject.strip().casefold()
    return bool(doc_key and doc_key in canonical_subject_keys(requested_subject))


def clean_page_text(raw: str) -> str:
    """Normalize PDF/text page output by stripping control chars and extra spaces."""
    cleaned = _CONTROL_CHARS.sub(" ", raw)
    return re.sub(r"\s+", " ", cleaned).strip()


def is_readable_text(text: str) -> bool:
    """Return True if extracted page text is real readable text rather than mojibake."""
    compact = re.sub(r"\s+", "", text)
    if len(compact) < 40:
        return False

    non_ascii_letters = sum(1 for char in compact if ord(char) > 127 and char.isalpha())
    if non_ascii_letters >= len(compact) * 0.12:
        return True

    alpha_count = sum(1 for char in compact if char.isalpha())
    if alpha_count < len(compact) * 0.45:
        return False

    preeti_hits = len(_PREETI_MARKERS.findall(text))
    camel_noise = len(_CAMEL_NOISE.findall(text))
    en_stopwords = len(_EN_STOPWORDS.findall(text.lower()))
    return not ((preeti_hits >= 4 or camel_noise >= 6) and en_stopwords < 3)


def is_front_matter(page_number: int, text: str) -> bool:
    """Identify early cover, copyright, preface, or table-of-contents pages."""
    if page_number > 8:
        return False
    lowered = text.lower()
    if any(
        marker in lowered
        for marker in (
            "table of content",
            "contents",
            "preface",
            "all rights reserved",
            "curriculum development centre",
            "publisher:",
        )
    ):
        return True
    return len(_TOC_ENTRY.findall(text)) >= 6


def extract_query_terms(query: str) -> list[str]:
    """Extract distinct meaningful search tokens from a learner question."""
    seen: set[str] = set()
    terms: list[str] = []
    for raw in _TOKEN_PATTERN.findall(query.casefold()):
        if raw in _QUERY_STOPWORDS or raw.isdigit():
            continue
        if raw not in seen:
            seen.add(raw)
            terms.append(raw)
        if len(terms) >= 10:
            break
    return terms


def _term_hits(term: str, doc_tokens: set[str]) -> bool:
    if term in doc_tokens:
        return True
    if len(term) < 4:
        return False
    return any(
        tok.startswith(term) or (len(tok) >= 4 and term.startswith(tok)) for tok in doc_tokens
    )


def _now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


class BookSearchIndex:
    """SQLite FTS5 keyword + BM25 search index for local textbooks."""

    _LOCKS: dict[Path, threading.Lock] = {}
    _LOCKS_GUARD = threading.Lock()

    def __init__(self, store: Store):
        self.store = store
        self._ensure_schema()

    def _lock(self) -> threading.Lock:
        key = self.store.path.resolve()
        with self._LOCKS_GUARD:
            lock = self._LOCKS.get(key)
            if lock is None:
                lock = threading.Lock()
                self._LOCKS[key] = lock
            return lock

    def _connect(self) -> sqlite3.Connection:
        db = sqlite3.connect(self.store.path, timeout=15)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA busy_timeout = 5000")
        return db

    def _ensure_schema(self) -> None:
        with self._lock(), self._connect() as db:
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS book_fts_meta (
                    document_id TEXT PRIMARY KEY,
                    storage_name TEXT NOT NULL,
                    pages_indexed INTEGER NOT NULL,
                    chunks_indexed INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    indexed_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS book_fts_chunks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chunk_id TEXT NOT NULL UNIQUE,
                    document_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    grade INTEGER,
                    subject TEXT NOT NULL,
                    subject_key TEXT NOT NULL,
                    chapter TEXT NOT NULL,
                    chapter_key TEXT NOT NULL,
                    page_start INTEGER NOT NULL,
                    page_end INTEGER NOT NULL,
                    is_front_matter INTEGER NOT NULL DEFAULT 0,
                    text TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_book_fts_chunks_scope
                    ON book_fts_chunks(grade, subject_key, document_id);
                CREATE VIRTUAL TABLE IF NOT EXISTS book_fts_index USING fts5(
                    text,
                    title,
                    chapter,
                    content='book_fts_chunks',
                    content_rowid='id',
                    tokenize='porter unicode61'
                );
                CREATE TRIGGER IF NOT EXISTS book_fts_chunks_ai
                AFTER INSERT ON book_fts_chunks BEGIN
                    INSERT INTO book_fts_index(rowid, text, title, chapter)
                    VALUES (new.id, new.text, new.title, new.chapter);
                END;
                CREATE TRIGGER IF NOT EXISTS book_fts_chunks_ad
                AFTER DELETE ON book_fts_chunks BEGIN
                    INSERT INTO book_fts_index(book_fts_index, rowid, text, title, chapter)
                    VALUES ('delete', old.id, old.text, old.title, old.chapter);
                END;
                CREATE TRIGGER IF NOT EXISTS book_fts_chunks_au
                AFTER UPDATE ON book_fts_chunks BEGIN
                    INSERT INTO book_fts_index(book_fts_index, rowid, text, title, chapter)
                    VALUES ('delete', old.id, old.text, old.title, old.chapter);
                    INSERT INTO book_fts_index(rowid, text, title, chapter)
                    VALUES (new.id, new.text, new.title, new.chapter);
                END;
                """
            )

    def _iter_readable_pages(self, path: Path, max_pages: int):
        suffix = path.suffix.lower()
        if suffix == ".txt":
            text = clean_page_text(path.read_text(encoding="utf-8"))
            if is_readable_text(text):
                yield 1, text
            return
        if suffix != ".pdf":
            return
        reader = PdfReader(path)
        _unlock_empty_password(reader)
        for page_number, page in enumerate(reader.pages[:max_pages], start=1):
            text = clean_page_text(page.extract_text() or "")
            if is_readable_text(text):
                yield page_number, text

    def _index_document_unlocked(
        self, db: sqlite3.Connection, document: dict, max_pages: int
    ) -> int:
        doc_id = document["id"]
        storage_name = document.get("storage_name", "")
        if not storage_name:
            return 0
        path = (self.store.directory / storage_name).resolve()
        if path.parent != self.store.directory or not path.is_file():
            return 0

        rows: list[tuple] = []
        pages_indexed = 0
        title = document["title"]
        grade = document.get("grade")
        subject = document["subject"]
        subject_key = subject.strip().casefold()
        chapter = document["chapter"]
        chapter_key = chapter.strip().casefold()

        try:
            for page_number, page_text in self._iter_readable_pages(path, max_pages):
                pages_indexed += 1
                front = int(is_front_matter(page_number, page_text))
                for start in range(0, len(page_text), 750):
                    excerpt = page_text[start : start + 950].strip()
                    if not excerpt:
                        continue
                    chunk_id = str(uuid5(NAMESPACE_URL, f"dh:{doc_id}:{page_number}:{start}"))
                    rows.append(
                        (
                            chunk_id,
                            doc_id,
                            title,
                            grade,
                            subject,
                            subject_key,
                            chapter,
                            chapter_key,
                            page_number,
                            page_number,
                            front,
                            excerpt,
                        )
                    )
        except (InvalidDocument, OSError, UnicodeDecodeError, ValueError):
            rows = []
            pages_indexed = 0

        db.execute("DELETE FROM book_fts_chunks WHERE document_id = ?", (doc_id,))
        if rows:
            db.executemany(
                "INSERT INTO book_fts_chunks ("
                "chunk_id, document_id, title, grade, subject, subject_key, "
                "chapter, chapter_key, page_start, page_end, is_front_matter, text"
                ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                rows,
            )
        status = "ready" if rows else "unreadable"
        db.execute(
            "INSERT INTO book_fts_meta VALUES (?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(document_id) DO UPDATE SET "
            "storage_name=excluded.storage_name, pages_indexed=excluded.pages_indexed, "
            "chunks_indexed=excluded.chunks_indexed, status=excluded.status, "
            "indexed_at=excluded.indexed_at",
            (doc_id, storage_name, pages_indexed, len(rows), status, _now()),
        )
        return len(rows)

    def index_document(self, document: dict, max_pages: int = 1000) -> int:
        """Index one ready document into SQLite FTS5 without modifying document metadata."""
        if document.get("status") != "ready":
            return 0
        with self._lock(), self._connect() as db:
            return self._index_document_unlocked(db, document, max_pages)

    def ensure_indexed_for(
        self, *, grade: int, subject: str, chapter: str = "", max_pages: int = 1000
    ) -> int:
        """Lazily index ready books matching the learner's grade, subject, and chapter."""
        wanted_chapter = chapter.strip().casefold()
        candidates = [
            doc
            for doc in self.store.list()
            if doc.get("grade") == grade
            and subject_matches(doc["subject"], subject)
            and (not wanted_chapter or doc.get("chapter", "").strip().casefold() == wanted_chapter)
        ]
        if not candidates:
            return 0
        indexed_now = 0
        with self._lock(), self._connect() as db:
            existing = {
                row["document_id"]: row["storage_name"]
                for row in db.execute("SELECT document_id, storage_name FROM book_fts_meta")
            }
            for doc in candidates:
                if existing.get(doc["id"]) == doc.get("storage_name", ""):
                    continue
                if self._index_document_unlocked(db, doc, max_pages) > 0:
                    indexed_now += 1
        return indexed_now

    def index_all_ready(self, max_pages: int = 1000) -> dict[str, int]:
        """Index all unindexed ready documents in the catalog."""
        docs = self.store.list()
        indexed = unreadable = skipped = chunks = 0
        with self._lock(), self._connect() as db:
            existing = {
                row["document_id"]: row["storage_name"]
                for row in db.execute("SELECT document_id, storage_name FROM book_fts_meta")
            }
            for doc in docs:
                if existing.get(doc["id"]) == doc.get("storage_name", ""):
                    skipped += 1
                    continue
                count = self._index_document_unlocked(db, doc, max_pages)
                if count > 0:
                    indexed += 1
                    chunks += count
                else:
                    unreadable += 1
        return {
            "indexed": indexed,
            "unreadable": unreadable,
            "skipped": skipped,
            "chunks": chunks,
        }

    def search(
        self,
        query: str,
        *,
        grade: int,
        subject: str,
        chapter: str = "",
        limit: int = 3,
    ) -> list[dict]:
        """Search indexed textbooks using BM25 + keyword coverage within scope."""
        terms = extract_query_terms(query)
        subject_keys = sorted(canonical_subject_keys(subject))
        if not terms or not subject_keys or limit < 1:
            return []

        fts_query = " OR ".join(f'"{term}"' for term in terms)
        placeholders = ", ".join("?" for _ in subject_keys)
        params: list = [fts_query, grade, *subject_keys]
        chapter_clause = ""
        wanted_chapter = chapter.strip().casefold()
        if wanted_chapter:
            chapter_clause = " AND c.chapter_key = ?"
            params.append(wanted_chapter)

        sql = (
            "SELECT c.chunk_id, c.document_id, c.title, c.grade, c.subject, c.chapter, "
            "c.page_start, c.page_end, c.is_front_matter, c.text, "
            "bm25(book_fts_index) AS rank "
            "FROM book_fts_index "
            "JOIN book_fts_chunks AS c ON c.id = book_fts_index.rowid "
            f"WHERE book_fts_index MATCH ? AND c.grade = ? AND c.subject_key IN ({placeholders})"
            f"{chapter_clause} "
            "ORDER BY rank LIMIT 24"
        )

        with self._connect() as db:
            rows = db.execute(sql, params).fetchall()

        candidates: list[tuple[tuple[int, int, float], sqlite3.Row]] = []
        for row in rows:
            doc = self.store.get(row["document_id"])
            if (
                not doc
                or doc.get("status") != "ready"
                or doc.get("grade") != grade
                or not subject_matches(doc["subject"], subject)
                or (wanted_chapter and doc.get("chapter", "").strip().casefold() != wanted_chapter)
            ):
                continue
            haystack = f"{row['text']} {row['title']} {row['chapter']}".casefold()
            doc_tokens = set(_TOKEN_PATTERN.findall(haystack))
            matched = sum(1 for term in terms if _term_hits(term, doc_tokens))
            if matched < 1:
                continue
            candidates.append(((int(row["is_front_matter"]), -matched, float(row["rank"])), row))

        if not candidates:
            return []

        if any(key[0] == 0 for key, _ in candidates):
            candidates = [item for item in candidates if item[0][0] == 0]

        candidates.sort(key=lambda item: item[0])

        results: list[dict] = []
        seen_pages: set[tuple[str, int]] = set()
        for _, row in candidates:
            page_key = (row["document_id"], int(row["page_start"]))
            if page_key in seen_pages:
                continue
            seen_pages.add(page_key)
            results.append(
                {
                    "document_id": row["document_id"],
                    "title": row["title"],
                    "page_start": int(row["page_start"]),
                    "page_end": int(row["page_end"]),
                    "chunk_id": row["chunk_id"],
                    "text": row["text"],
                }
            )
            if len(results) >= limit:
                break
        return results


def main(argv: list[str] | None = None) -> int:
    from app.store import Store

    parser = argparse.ArgumentParser(description="Build SQLite FTS5 textbook search index.")
    parser.add_argument("--data-dir", type=Path, default=Path(os.getenv("DATA_DIR", "../data")))
    parser.add_argument("--max-pages", type=int, default=1000)
    args = parser.parse_args(argv)
    summary = BookSearchIndex(Store(args.data_dir)).index_all_ready(max_pages=args.max_pages)
    print(json.dumps(summary))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
