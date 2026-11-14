"""Local school accounts, signed-in sessions, classes, and tutor history."""

from __future__ import annotations

import hashlib
import hmac
import json
import secrets
import sqlite3
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Literal
from uuid import uuid4

from pydantic import BaseModel, Field, StringConstraints

Username = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True, min_length=3, max_length=48, pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$"
    ),
]
DisplayName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)]
Password = Annotated[str, StringConstraints(min_length=12, max_length=128)]


class LoginInput(BaseModel):
    username: Username
    password: Password


class PasswordChangeInput(BaseModel):
    current_password: Annotated[str, StringConstraints(min_length=1, max_length=128)]
    new_password: Password


class PasswordResetInput(BaseModel):
    temporary_password: Password


class UserStatusInput(BaseModel):
    disabled: bool


class BootstrapInput(BaseModel):
    username: Username
    display_name: DisplayName
    password: Password


class UserInput(BaseModel):
    username: Username
    display_name: DisplayName
    password: Password
    role: Literal["admin", "teacher", "student"]
    grade: int | None = Field(None, ge=1, le=12)


class StudentInput(BaseModel):
    username: Username
    display_name: DisplayName
    password: Password
    grade: int = Field(ge=1, le=12)
    class_id: str | None = Field(None, pattern=r"^[a-f0-9]{32}$")


class ClassInput(BaseModel):
    name: DisplayName
    grade: int = Field(ge=1, le=12)
    teacher_id: str | None = Field(None, pattern=r"^[a-f0-9]{32}$")


class EnrollmentInput(BaseModel):
    student_id: str = Field(pattern=r"^[a-f0-9]{32}$")


def _now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _password_hash(password: str, salt: bytes | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    derived = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1, dklen=32)
    return "scrypt$16384$8$1$" + salt.hex() + "$" + derived.hex()


def _verify_password(password: str, encoded: str) -> bool:
    try:
        scheme, n, r, p, salt_hex, expected_hex = encoded.split("$", 5)
        if scheme != "scrypt":
            return False
        derived = hashlib.scrypt(
            password.encode(),
            salt=bytes.fromhex(salt_hex),
            n=int(n),
            r=int(r),
            p=int(p),
            dklen=32,
        )
        return hmac.compare_digest(derived.hex(), expected_hex)
    except (ValueError, TypeError):
        return False


_DUMMY_PASSWORD_HASH = _password_hash("not-a-real-school-password")


class IdentityStore:
    """SQLite-backed local identity and chat history, kept in the content data volume."""

    SESSION_TTL_SECONDS = 7 * 24 * 60 * 60

    def __init__(self, database_path: Path):
        self.path = database_path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    username TEXT NOT NULL COLLATE NOCASE UNIQUE,
                    display_name TEXT NOT NULL,
                    role TEXT NOT NULL CHECK(role IN ('admin', 'teacher', 'student')),
                    grade INTEGER,
                    password_hash TEXT NOT NULL,
                    must_change_password INTEGER NOT NULL DEFAULT 0,
                    disabled INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS auth_sessions (
                    token_hash TEXT PRIMARY KEY,
                    csrf_token TEXT NOT NULL,
                    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    created_at REAL NOT NULL,
                    expires_at REAL NOT NULL,
                    last_seen_at REAL NOT NULL
                );
                CREATE INDEX IF NOT EXISTS auth_sessions_user ON auth_sessions(user_id);
                CREATE TABLE IF NOT EXISTS school_classes (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    grade INTEGER NOT NULL,
                    created_by TEXT NOT NULL REFERENCES users(id),
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS class_teachers (
                    class_id TEXT NOT NULL REFERENCES school_classes(id) ON DELETE CASCADE,
                    teacher_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    PRIMARY KEY(class_id, teacher_id)
                );
                CREATE TABLE IF NOT EXISTS class_students (
                    class_id TEXT NOT NULL REFERENCES school_classes(id) ON DELETE CASCADE,
                    student_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    assigned_at TEXT NOT NULL,
                    PRIMARY KEY(class_id, student_id)
                );
                CREATE INDEX IF NOT EXISTS class_students_student ON class_students(student_id);
                CREATE TABLE IF NOT EXISTS tutor_sessions (
                    id TEXT PRIMARY KEY,
                    student_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    title TEXT NOT NULL,
                    grade INTEGER NOT NULL,
                    subject TEXT NOT NULL,
                    chapter TEXT NOT NULL,
                    language TEXT NOT NULL,
                    mode TEXT NOT NULL,
                    hint_level INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    deleted_at TEXT
                );
                CREATE INDEX IF NOT EXISTS tutor_sessions_student
                    ON tutor_sessions(student_id, updated_at DESC);
                CREATE TABLE IF NOT EXISTS tutor_messages (
                    id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL REFERENCES tutor_sessions(id) ON DELETE CASCADE,
                    role TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
                    content TEXT NOT NULL,
                    attempt TEXT NOT NULL DEFAULT '',
                    mode TEXT,
                    grounding TEXT,
                    sources_json TEXT NOT NULL DEFAULT '[]',
                    created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS tutor_messages_session
                    ON tutor_messages(session_id, created_at);
                CREATE TABLE IF NOT EXISTS transcript_audit (
                    id TEXT PRIMARY KEY,
                    viewer_id TEXT NOT NULL REFERENCES users(id),
                    student_id TEXT NOT NULL REFERENCES users(id),
                    session_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS login_attempts (
                    username_hash TEXT PRIMARY KEY,
                    window_started REAL NOT NULL,
                    failures INTEGER NOT NULL
                );
                """
            )
            columns = {row[1] for row in db.execute("PRAGMA table_info(users)").fetchall()}
            if "must_change_password" not in columns:
                db.execute(
                    "ALTER TABLE users ADD COLUMN must_change_password INTEGER NOT NULL DEFAULT 0"
                )
            session_columns = {
                row[1] for row in db.execute("PRAGMA table_info(tutor_sessions)").fetchall()
            }
            if "hint_level" not in session_columns:
                db.execute(
                    "ALTER TABLE tutor_sessions ADD COLUMN hint_level INTEGER NOT NULL DEFAULT 0"
                )
            message_columns = {
                row[1] for row in db.execute("PRAGMA table_info(tutor_messages)").fetchall()
            }
            if "attempt" not in message_columns:
                db.execute("ALTER TABLE tutor_messages ADD COLUMN attempt TEXT NOT NULL DEFAULT ''")
            version = db.execute("PRAGMA user_version").fetchone()[0]
            if version < 3:
                db.execute("PRAGMA user_version = 3")

    def connect(self) -> sqlite3.Connection:
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys = ON")
        return db

    @staticmethod
    def public_user(row: sqlite3.Row | dict) -> dict:
        return {
            "id": row["id"],
            "username": row["username"],
            "display_name": row["display_name"],
            "role": row["role"],
            "grade": row["grade"],
            "must_change_password": bool(row["must_change_password"]),
            "disabled": bool(row["disabled"]),
        }

    def user_count(self) -> int:
        with self.connect() as db:
            return db.execute("SELECT count(*) FROM users WHERE disabled = 0").fetchone()[0]

    def create_user(self, data: UserInput | BootstrapInput, role: str | None = None) -> dict:
        user_id = uuid4().hex
        user_role = role or getattr(data, "role", "admin")
        with self.connect() as db:
            db.execute(
                "INSERT INTO users(id, username, display_name, role, grade, password_hash, "
                "must_change_password, created_at) VALUES (?, ?, ?, ?, ?, ?, 1, ?)",
                (
                    user_id,
                    data.username,
                    data.display_name,
                    user_role,
                    getattr(data, "grade", None),
                    _password_hash(data.password),
                    _now(),
                ),
            )
            row = db.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        return self.public_user(row)

    def create_bootstrap_admin(self, data: BootstrapInput) -> dict | None:
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            if db.execute("SELECT 1 FROM users WHERE disabled = 0 LIMIT 1").fetchone():
                db.rollback()
                return None
            user_id = uuid4().hex
            db.execute(
                "INSERT INTO users(id, username, display_name, role, grade, password_hash, "
                "must_change_password, created_at) VALUES (?, ?, ?, 'admin', NULL, ?, 0, ?)",
                (user_id, data.username, data.display_name, _password_hash(data.password), _now()),
            )
            row = db.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
            db.commit()
        return self.public_user(row)

    def get_user(self, user_id: str) -> dict | None:
        with self.connect() as db:
            row = db.execute(
                "SELECT * FROM users WHERE id = ? AND disabled = 0", (user_id,)
            ).fetchone()
        return self.public_user(row) if row else None

    def list_users(self, *, role: str | None = None, include_disabled: bool = False) -> list[dict]:
        conditions = [] if include_disabled else ["disabled = 0"]
        params: list[str] = []
        if role:
            conditions.append("role = ?")
            params.append(role)
        clause = " WHERE " + " AND ".join(conditions) if conditions else ""
        with self.connect() as db:
            rows = db.execute(
                "SELECT * FROM users" + clause + " ORDER BY role, username",
                params,
            ).fetchall()
        return [self.public_user(row) for row in rows]

    def set_user_disabled(self, user_id: str, disabled: bool) -> bool:
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = (
                db.execute(
                    "SELECT role FROM users WHERE id = ? AND disabled = 0", (user_id,)
                ).fetchone()
                if disabled
                else db.execute(
                    "SELECT role FROM users WHERE id = ? AND disabled = 1", (user_id,)
                ).fetchone()
            )
            if not row:
                db.rollback()
                return False
            if (
                disabled
                and row[0] == "admin"
                and db.execute(
                    "SELECT count(*) FROM users WHERE role = 'admin' AND disabled = 0"
                ).fetchone()[0]
                <= 1
            ):
                db.rollback()
                return False
            db.execute(
                "UPDATE users SET disabled = ?, must_change_password = "
                "CASE WHEN ? = 0 THEN 1 ELSE must_change_password END WHERE id = ?",
                (int(disabled), int(disabled), user_id),
            )
            if disabled:
                db.execute("DELETE FROM auth_sessions WHERE user_id = ?", (user_id,))
            db.commit()
        return True

    def disable_user(self, user_id: str) -> bool:
        return self.set_user_disabled(user_id, True)

    def reset_password(self, user_id: str, temporary_password: str) -> bool:
        with self.connect() as db:
            row = db.execute(
                "SELECT id FROM users WHERE id = ? AND disabled = 0", (user_id,)
            ).fetchone()
            if not row:
                return False
            db.execute(
                "UPDATE users SET password_hash = ?, must_change_password = 1 WHERE id = ?",
                (_password_hash(temporary_password), user_id),
            )
            db.execute("DELETE FROM auth_sessions WHERE user_id = ?", (user_id,))
        return True

    def authenticate(self, username: str, password: str) -> dict | None:
        normalized = username.strip().casefold()
        name_hash = hashlib.sha256(normalized.encode()).hexdigest()
        now = time.time()
        with self.connect() as db:
            attempt = db.execute(
                "SELECT window_started, failures FROM login_attempts WHERE username_hash = ?",
                (name_hash,),
            ).fetchone()
            if attempt and attempt[1] >= 5 and now - attempt[0] < 900:
                return None
            if attempt and now - attempt[0] >= 900:
                db.execute("DELETE FROM login_attempts WHERE username_hash = ?", (name_hash,))
            row = db.execute(
                "SELECT * FROM users WHERE username = ? COLLATE NOCASE AND disabled = 0",
                (username.strip(),),
            ).fetchone()
        valid = _verify_password(password, row["password_hash"] if row else _DUMMY_PASSWORD_HASH)
        if not row or not valid:
            with self.connect() as db:
                db.execute(
                    "INSERT INTO login_attempts VALUES (?, ?, 1) "
                    "ON CONFLICT(username_hash) DO UPDATE SET "
                    "failures=CASE WHEN ? - window_started >= 900 THEN 1 ELSE failures + 1 END, "
                    "window_started=CASE WHEN ? - window_started >= 900 "
                    "THEN ? ELSE window_started END",
                    (name_hash, now, now, now, now),
                )
            return None
        with self.connect() as db:
            db.execute("DELETE FROM login_attempts WHERE username_hash = ?", (name_hash,))
        return self.public_user(row)

    def create_session(self, user_id: str) -> tuple[str, str]:
        token = secrets.token_urlsafe(32)
        csrf = secrets.token_urlsafe(24)
        now = time.time()
        with self.connect() as db:
            db.execute("DELETE FROM auth_sessions WHERE expires_at < ?", (now,))
            db.execute(
                "INSERT INTO auth_sessions VALUES (?, ?, ?, ?, ?, ?)",
                (
                    hashlib.sha256(token.encode()).hexdigest(),
                    csrf,
                    user_id,
                    now,
                    now + self.SESSION_TTL_SECONDS,
                    now,
                ),
            )
        return token, csrf

    def user_for_session(self, token: str | None) -> tuple[dict, str] | None:
        if not token:
            return None
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        now = time.time()
        with self.connect() as db:
            row = db.execute(
                "SELECT users.*, auth_sessions.csrf_token, auth_sessions.last_seen_at "
                "FROM auth_sessions JOIN users ON users.id = auth_sessions.user_id "
                "WHERE auth_sessions.token_hash = ? AND auth_sessions.expires_at > ? "
                "AND users.disabled = 0",
                (token_hash, now),
            ).fetchone()
            if not row:
                db.execute("DELETE FROM auth_sessions WHERE token_hash = ?", (token_hash,))
                return None
            if now - row["last_seen_at"] > 300:
                db.execute(
                    "UPDATE auth_sessions SET last_seen_at = ? WHERE token_hash = ?",
                    (now, token_hash),
                )
        return self.public_user(row), row["csrf_token"]

    def verify_csrf(self, token: str | None, provided: str | None) -> bool:
        if not token or not provided:
            return False
        session_hash = hashlib.sha256(token.encode()).hexdigest()
        with self.connect() as db:
            row = db.execute(
                "SELECT csrf_token FROM auth_sessions WHERE token_hash = ? AND expires_at > ?",
                (session_hash, time.time()),
            ).fetchone()
        return bool(row and hmac.compare_digest(row[0], provided))

    def delete_session(self, token: str | None) -> None:
        if not token:
            return
        with self.connect() as db:
            db.execute(
                "DELETE FROM auth_sessions WHERE token_hash = ?",
                (hashlib.sha256(token.encode()).hexdigest(),),
            )

    def change_password(self, user_id: str, current: str, new: str) -> bool:
        with self.connect() as db:
            row = db.execute(
                "SELECT password_hash FROM users WHERE id = ? AND disabled = 0", (user_id,)
            ).fetchone()
            if not row or not _verify_password(current, row[0]):
                return False
            db.execute(
                "UPDATE users SET password_hash = ?, must_change_password = 0 WHERE id = ?",
                (_password_hash(new), user_id),
            )
            db.execute("DELETE FROM auth_sessions WHERE user_id = ?", (user_id,))
        return True

    def create_class(self, *, name: str, grade: int, creator_id: str, teacher_id: str) -> dict:
        class_id = uuid4().hex
        with self.connect() as db:
            teacher = db.execute(
                "SELECT role FROM users WHERE id = ? AND disabled = 0", (teacher_id,)
            ).fetchone()
            if not teacher or teacher[0] not in {"teacher", "admin"}:
                raise ValueError("A class must be assigned to an active teacher.")
            db.execute(
                "INSERT INTO school_classes VALUES (?, ?, ?, ?, ?)",
                (class_id, name, grade, creator_id, _now()),
            )
            db.execute("INSERT INTO class_teachers VALUES (?, ?)", (class_id, teacher_id))
        return {"id": class_id, "name": name, "grade": grade, "teacher_id": teacher_id}

    def list_classes(self, user: dict) -> list[dict]:
        with self.connect() as db:
            if user["role"] == "admin":
                rows = db.execute(
                    "SELECT c.*, count(DISTINCT cs.student_id) AS student_count, "
                    "count(DISTINCT ts.id) AS session_count "
                    "FROM school_classes c LEFT JOIN class_students cs ON cs.class_id = c.id "
                    "LEFT JOIN users u ON u.id = cs.student_id "
                    "LEFT JOIN tutor_sessions ts ON ts.student_id = u.id AND ts.deleted_at IS NULL "
                    "GROUP BY c.id ORDER BY c.grade, c.name"
                ).fetchall()
            else:
                rows = db.execute(
                    "SELECT c.*, count(DISTINCT cs.student_id) AS student_count, "
                    "count(DISTINCT ts.id) AS session_count "
                    "FROM school_classes c JOIN class_teachers ct ON ct.class_id = c.id "
                    "LEFT JOIN class_students cs ON cs.class_id = c.id "
                    "LEFT JOIN tutor_sessions ts ON ts.student_id = cs.student_id "
                    "AND ts.deleted_at IS NULL "
                    "WHERE ct.teacher_id = ? GROUP BY c.id ORDER BY c.grade, c.name",
                    (user["id"],),
                ).fetchall()
        return [
            {
                "id": row["id"],
                "name": row["name"],
                "grade": row["grade"],
                "student_count": row["student_count"],
                "session_count": row["session_count"],
            }
            for row in rows
        ]

    def class_allowed(self, user: dict, class_id: str) -> bool:
        if user["role"] == "admin":
            with self.connect() as db:
                return bool(
                    db.execute("SELECT 1 FROM school_classes WHERE id = ?", (class_id,)).fetchone()
                )
        with self.connect() as db:
            return bool(
                db.execute(
                    "SELECT 1 FROM class_teachers WHERE class_id = ? AND teacher_id = ?",
                    (class_id, user["id"]),
                ).fetchone()
            )

    def get_class(self, class_id: str) -> dict | None:
        with self.connect() as db:
            row = db.execute(
                "SELECT id, name, grade FROM school_classes WHERE id = ?", (class_id,)
            ).fetchone()
        return dict(row) if row else None

    def student_in_class(self, class_id: str, student_id: str) -> bool:
        with self.connect() as db:
            return bool(
                db.execute(
                    "SELECT 1 FROM class_students WHERE class_id = ? AND student_id = ?",
                    (class_id, student_id),
                ).fetchone()
            )

    def enroll_student(self, class_id: str, student_id: str) -> bool:
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            student = db.execute(
                "SELECT role, grade FROM users WHERE id = ? AND disabled = 0", (student_id,)
            ).fetchone()
            exists = db.execute(
                "SELECT grade FROM school_classes WHERE id = ?", (class_id,)
            ).fetchone()
            if (
                not student
                or student[0] != "student"
                or not exists
                or (student[1] is not None and student[1] != exists[0])
            ):
                db.rollback()
                return False
            assigned_elsewhere = db.execute(
                "SELECT 1 FROM class_students WHERE student_id = ? AND class_id != ? LIMIT 1",
                (student_id, class_id),
            ).fetchone()
            if assigned_elsewhere:
                db.rollback()
                return False
            db.execute(
                "INSERT OR IGNORE INTO class_students VALUES (?, ?, ?)",
                (class_id, student_id, _now()),
            )
            db.commit()
        return True

    def students_for_class(self, class_id: str) -> list[dict]:
        with self.connect() as db:
            rows = db.execute(
                "SELECT users.*, (SELECT count(*) FROM tutor_sessions s "
                "WHERE s.student_id = users.id AND s.deleted_at IS NULL) AS session_count "
                "FROM class_students JOIN users ON users.id = class_students.student_id "
                "WHERE class_students.class_id = ? AND users.disabled = 0 "
                "ORDER BY users.display_name COLLATE NOCASE",
                (class_id,),
            ).fetchall()
        return [{**self.public_user(row), "session_count": row["session_count"]} for row in rows]

    def student_dashboard(self, user: dict) -> dict:
        with self.connect() as db:
            classes = db.execute(
                "SELECT c.id, c.name, c.grade FROM class_students cs "
                "JOIN school_classes c ON c.id = cs.class_id WHERE cs.student_id = ? "
                "ORDER BY c.grade, c.name",
                (user["id"],),
            ).fetchall()
            count = db.execute(
                "SELECT count(*) FROM tutor_sessions WHERE student_id = ? AND deleted_at IS NULL",
                (user["id"],),
            ).fetchone()[0]
        sessions = self.list_student_sessions(user["id"], limit=8)
        return {
            "user": user,
            "classes": [dict(row) for row in classes],
            "session_count": count,
            "recent_sessions": sessions,
        }

    def list_student_sessions(self, student_id: str, limit: int = 100) -> list[dict]:
        with self.connect() as db:
            rows = db.execute(
                "SELECT s.*, count(m.id) AS message_count FROM tutor_sessions s "
                "LEFT JOIN tutor_messages m ON m.session_id = s.id "
                "WHERE s.student_id = ? AND s.deleted_at IS NULL "
                "GROUP BY s.id ORDER BY s.updated_at DESC LIMIT ?",
                (student_id, min(max(limit, 1), 100)),
            ).fetchall()
        return [dict(row) for row in rows]

    def get_student_session(self, session_id: str, student_id: str) -> dict | None:
        with self.connect() as db:
            row = db.execute(
                "SELECT * FROM tutor_sessions WHERE id = ? AND student_id = ? "
                "AND deleted_at IS NULL",
                (session_id, student_id),
            ).fetchone()
            if not row:
                return None
            messages = db.execute(
                "SELECT role, content, attempt, mode, grounding, sources_json, created_at "
                "FROM tutor_messages WHERE session_id = ? ORDER BY created_at, rowid",
                (session_id,),
            ).fetchall()
        return {**dict(row), "messages": [self._message_json(item) for item in messages]}

    @staticmethod
    def _message_json(row: sqlite3.Row) -> dict:
        item = dict(row)
        item["sources"] = json.loads(item.pop("sources_json"))
        return item

    def append_chat_turn(self, *, user: dict, request, reply: dict) -> str:
        session_id = request.session_id or uuid4().hex
        stamp = _now()
        with self.connect() as db:
            if request.session_id:
                session = db.execute(
                    "SELECT id FROM tutor_sessions WHERE id = ? AND student_id = ? "
                    "AND deleted_at IS NULL",
                    (session_id, user["id"]),
                ).fetchone()
                if not session:
                    raise LookupError("Tutor session not found.")
                db.execute(
                    "UPDATE tutor_sessions SET updated_at = ?, mode = ?, hint_level = ? "
                    "WHERE id = ?",
                    (stamp, request.mode, request.hint_level, session_id),
                )
            else:
                title = " ".join(request.message.split())[:100] or "Tutor session"
                db.execute(
                    "INSERT INTO tutor_sessions(id, student_id, title, grade, subject, chapter, "
                    "language, mode, hint_level, created_at, updated_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        session_id,
                        user["id"],
                        title,
                        request.grade,
                        request.subject,
                        request.chapter,
                        request.language,
                        request.mode,
                        request.hint_level,
                        stamp,
                        stamp,
                    ),
                )
            db.execute(
                "INSERT INTO tutor_messages(id, session_id, role, content, attempt, "
                "mode, created_at) "
                "VALUES (?, ?, 'user', ?, ?, ?, ?)",
                (uuid4().hex, session_id, request.message, request.attempt, request.mode, stamp),
            )
            db.execute(
                "INSERT INTO tutor_messages(id, session_id, role, content, attempt, mode, "
                "grounding, "
                "sources_json, created_at) "
                "VALUES (?, ?, 'assistant', ?, '', ?, ?, ?, ?)",
                (
                    uuid4().hex,
                    session_id,
                    reply["answer"],
                    request.mode,
                    reply["grounding"],
                    json.dumps(reply["sources"], ensure_ascii=False),
                    stamp,
                ),
            )
        return session_id

    def delete_student_session(self, session_id: str, student_id: str) -> bool:
        with self.connect() as db:
            return bool(
                db.execute(
                    "DELETE FROM tutor_sessions WHERE id = ? AND student_id = ?",
                    (session_id, student_id),
                ).rowcount
            )

    def sessions_for_class(self, class_id: str, limit: int = 100) -> list[dict]:
        with self.connect() as db:
            rows = db.execute(
                "SELECT s.id, s.student_id, u.display_name AS student_name, u.username, "
                "s.title, s.grade, s.subject, s.chapter, s.language, s.mode, s.created_at, "
                "s.updated_at, count(m.id) AS message_count FROM class_students cs "
                "JOIN users u ON u.id = cs.student_id JOIN tutor_sessions s ON s.student_id = u.id "
                "LEFT JOIN tutor_messages m ON m.session_id = s.id "
                "WHERE cs.class_id = ? AND s.deleted_at IS NULL AND u.disabled = 0 GROUP BY s.id "
                "ORDER BY s.updated_at DESC LIMIT ?",
                (class_id, min(max(limit, 1), 100)),
            ).fetchall()
        return [dict(row) for row in rows]

    def get_teacher_session(
        self,
        session_id: str,
        class_id: str | None = None,
        *,
        include_disabled: bool = False,
    ) -> dict | None:
        disabled_clause = "" if include_disabled else " AND u.disabled = 0"
        with self.connect() as db:
            if class_id:
                row = db.execute(
                    "SELECT s.*, u.display_name AS student_name, u.username FROM tutor_sessions s "
                    "JOIN class_students cs ON cs.student_id = s.student_id "
                    "JOIN users u ON u.id = s.student_id WHERE s.id = ? AND cs.class_id = ? "
                    "AND s.deleted_at IS NULL" + disabled_clause,
                    (session_id, class_id),
                ).fetchone()
            else:
                row = db.execute(
                    "SELECT s.*, u.display_name AS student_name, u.username FROM tutor_sessions s "
                    "JOIN users u ON u.id = s.student_id WHERE s.id = ? AND s.deleted_at IS NULL"
                    + disabled_clause,
                    (session_id,),
                ).fetchone()
            if not row:
                return None
            messages = db.execute(
                "SELECT role, content, attempt, mode, grounding, sources_json, created_at "
                "FROM tutor_messages WHERE session_id = ? ORDER BY created_at, rowid",
                (session_id,),
            ).fetchall()
        return {**dict(row), "messages": [self._message_json(item) for item in messages]}

    def audit_transcript_view(
        self, viewer_id: str, student_id: str, session_id: str, *, action: str = "view"
    ) -> None:
        with self.connect() as db:
            db.execute(
                "INSERT INTO transcript_audit VALUES (?, ?, ?, ?, ?, ?)",
                (uuid4().hex, viewer_id, student_id, session_id, action, _now()),
            )

    def list_transcript_audit(self, limit: int = 100, offset: int = 0) -> list[dict]:
        with self.connect() as db:
            rows = db.execute(
                "SELECT a.id, a.viewer_id, viewer.display_name AS viewer_name, "
                "a.student_id, student.display_name AS student_name, a.session_id, "
                "a.action, a.created_at FROM transcript_audit a "
                "JOIN users viewer ON viewer.id = a.viewer_id "
                "JOIN users student ON student.id = a.student_id "
                "ORDER BY a.created_at DESC, a.id DESC LIMIT ? OFFSET ?",
                (min(max(limit, 1), 500), max(offset, 0)),
            ).fetchall()
        return [dict(row) for row in rows]
