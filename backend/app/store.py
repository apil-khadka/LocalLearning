from __future__ import annotations

import json
import sqlite3
from pathlib import Path


class Store:
    """Small local catalog. Only ready documents can be retrieved or served."""

    def __init__(self, directory: Path):
        self.directory = directory.resolve()
        self.directory.mkdir(parents=True, exist_ok=True)
        self.path = self.directory / "catalog.sqlite3"
        with self.connect() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS documents (
                id TEXT PRIMARY KEY, status TEXT NOT NULL, metadata TEXT NOT NULL
            )""")
            db.execute("""CREATE TABLE IF NOT EXISTS notes (
                id TEXT PRIMARY KEY, status TEXT NOT NULL, data TEXT NOT NULL
            )""")
            if db.execute("PRAGMA user_version").fetchone()[0] < 2:
                db.execute("PRAGMA user_version = 2")

    def connect(self):
        return sqlite3.connect(self.path, timeout=10)

    def put(self, document: dict):
        with self.connect() as db:
            db.execute(
                "INSERT INTO documents VALUES (?, ?, ?) ON CONFLICT(id) DO UPDATE SET "
                "status=excluded.status, metadata=excluded.metadata",
                (document["id"], document["status"], json.dumps(document, ensure_ascii=False)),
            )

    def get(self, document_id: str) -> dict | None:
        with self.connect() as db:
            row = db.execute(
                "SELECT metadata FROM documents WHERE id = ?", (document_id,)
            ).fetchone()
        return json.loads(row[0]) if row else None

    def list(self, *, all_states=False, grade=None, subject=None) -> list[dict]:
        clauses, params = [], []
        if not all_states:
            clauses.append("status = ?")
            params.append("ready")
        with self.connect() as db:
            rows = db.execute(
                "SELECT metadata FROM documents"
                + (" WHERE " + " AND ".join(clauses) if clauses else "")
                + " ORDER BY id",
                params,
            ).fetchall()
        items = [json.loads(row[0]) for row in rows]
        return [
            doc
            for doc in items
            if (
                grade is None
                or doc.get("grade") is None
                or doc.get("grade") == grade
                or grade in doc.get("grades", [])
            )
            and (subject is None or doc["subject"].casefold() == subject.strip().casefold())
        ]

    def catalog(
        self,
        *,
        grade: int | None = None,
        subject: str | None = None,
        query: str | None = None,
        limit: int = 24,
        offset: int = 0,
    ) -> dict:
        """Return one human-sorted catalog page and its available subject filters."""
        items = self.list(grade=grade)
        subjects = sorted({doc["subject"] for doc in items}, key=str.casefold)
        if subject and subject.strip():
            wanted = subject.strip().casefold()
            items = [doc for doc in items if doc["subject"].casefold() == wanted]
        if query and query.strip():
            terms = query.strip().casefold()
            items = [
                doc
                for doc in items
                if terms
                in " ".join(
                    str(doc.get(key, "")) for key in ("title", "subject", "chapter", "source")
                ).casefold()
            ]
        items.sort(
            key=lambda doc: (
                doc.get("grade") is None,
                doc.get("grade") if doc.get("grade") is not None else 99,
                doc["subject"].casefold(),
                doc["title"].casefold(),
            )
        )
        total = len(items)
        return {
            "items": [self.public(doc) for doc in items[offset : offset + limit]],
            "total": total,
            "limit": limit,
            "offset": offset,
            "subjects": subjects,
        }

    def put_note(self, note: dict):
        with self.connect() as db:
            db.execute(
                "INSERT INTO notes VALUES (?, ?, ?) ON CONFLICT(id) DO UPDATE SET "
                "status=excluded.status, data=excluded.data",
                (note["id"], note["status"], json.dumps(note, ensure_ascii=False)),
            )

    def get_note(self, note_id: str) -> dict | None:
        with self.connect() as db:
            row = db.execute("SELECT data FROM notes WHERE id = ?", (note_id,)).fetchone()
        return json.loads(row[0]) if row else None

    def list_notes(self, *, status: str | None = None) -> list[dict]:
        with self.connect() as db:
            rows = db.execute(
                "SELECT data FROM notes" + (" WHERE status = ?" if status else "") + " ORDER BY id",
                (status,) if status else (),
            ).fetchall()
        return [json.loads(row[0]) for row in rows]

    def delete_note(self, note_id: str) -> bool:
        with self.connect() as db:
            return db.execute("DELETE FROM notes WHERE id = ?", (note_id,)).rowcount > 0

    def approved_notes(
        self, *, grade: int, subject: str, chapter: str = "", language: str | None = None
    ) -> list[tuple[dict, dict]]:
        """Approved notes paired with their book; notes whose book is not ready are hidden."""
        wanted = subject.strip().casefold()
        pairs = []
        for note in self.list_notes(status="approved"):
            if note["grade"] != grade or note["subject"].casefold() != wanted:
                continue
            if chapter and note["chapter"].casefold() != chapter.strip().casefold():
                continue
            if language and note["language"] != language:
                continue
            document = self.get(note["document_id"])
            if document and document["status"] == "ready":
                pairs.append((note, document))
        return pairs

    @staticmethod
    def public(document: dict) -> dict:
        return {key: value for key, value in document.items() if key != "storage_name"}
