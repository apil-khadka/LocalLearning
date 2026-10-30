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
            db.execute("PRAGMA user_version = 1")

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

    @staticmethod
    def public(document: dict) -> dict:
        return {key: value for key, value in document.items() if key != "storage_name"}
