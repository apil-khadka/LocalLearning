"""Teacher-curated structured teaching notes linked to book pages.

A note is staff-authored and only becomes visible to students after review.
Approval records a free-text reviewer label; the portal has no accounts, so
this is a traceability aid and not an identity check.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Annotated, Literal
from uuid import uuid4

from pydantic import BaseModel, Field, StringConstraints, model_validator

from app.kolibri import learn_url

Line = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=600)]
Title = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]
Reviewer = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)]
NoteStatus = Literal["draft", "in_review", "approved"]

_CHANNEL_ID = re.compile(r"[a-f0-9]{32}")
_TOKEN = re.compile(r"[\w]+", re.UNICODE)


class PageRange(BaseModel):
    start: int = Field(ge=1, le=5000)
    end: int = Field(ge=1, le=5000)

    @model_validator(mode="after")
    def ordered(self):
        if self.end < self.start:
            raise ValueError("A page range must end on or after its first page.")
        return self


class Misconception(BaseModel):
    wrong: Line
    correction: Line


class NoteInput(BaseModel):
    title: Title
    grade: int = Field(ge=1, le=12)
    subject: Title
    chapter: Annotated[str, StringConstraints(strip_whitespace=True, max_length=120)] = ""
    language: Literal["en", "ne"] = "en"
    document_id: str = Field(pattern=r"^[a-f0-9]{32}$")
    pages: list[PageRange] = Field(min_length=1, max_length=8)
    key_ideas: list[Line] = Field(min_length=1, max_length=8)
    worked_example: Annotated[str, StringConstraints(strip_whitespace=True, max_length=1500)] = ""
    misconceptions: list[Misconception] = Field(default_factory=list, max_length=6)
    # Hints are ordered from a gentle nudge to the strongest hint; none gives the answer.
    hints: list[Line] = Field(default_factory=list, max_length=5)
    check_question: Annotated[str, StringConstraints(strip_whitespace=True, max_length=500)] = ""
    kolibri_channel_id: str | None = Field(None, pattern=r"^[a-f0-9]{32}$")


class ReviewRequest(BaseModel):
    status: NoteStatus
    reviewer: Annotated[str, StringConstraints(strip_whitespace=True, max_length=80)] = ""


def now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def new_note(data: NoteInput, *, author_id: str = "", author_name: str = "") -> dict:
    stamp = now()
    return {
        **data.model_dump(),
        "id": uuid4().hex,
        "status": "draft",
        "revision": 1,
        "author_id": author_id,
        "author_name": author_name,
        "updated_by": author_id,
        "reviewer": "",
        "reviewer_id": "",
        "reviewed_at": None,
        "created_at": stamp,
        "updated_at": stamp,
    }


def revise_note(
    existing: dict, data: NoteInput, *, editor_id: str = "", editor_name: str = ""
) -> dict:
    """Any content edit invalidates earlier review and returns the note to draft."""
    return {
        **existing,
        **data.model_dump(),
        "status": "draft",
        "revision": existing["revision"] + 1,
        "updated_by": editor_id,
        "author_name": editor_name or existing.get("author_name", ""),
        "reviewer": "",
        "reviewer_id": "",
        "reviewed_at": None,
        "updated_at": now(),
    }


def check_document(data: NoteInput | dict, document: dict | None, *, require_ready: bool) -> str:
    """Return a problem description, or an empty string when the links are valid."""
    get = data.get if isinstance(data, dict) else lambda key: getattr(data, key)
    if document is None:
        return "The linked book does not exist."
    if require_ready and document.get("status") != "ready":
        return "The linked book is not ready."
    grade = get("grade")
    if (
        document.get("grade") is not None
        and document["grade"] != grade
        and grade not in document.get("grades", [])
    ):
        return "The note grade does not match the linked book."
    total = document.get("pages")
    for page in get("pages"):
        end = page["end"] if isinstance(page, dict) else page.end
        if isinstance(total, int) and total > 0 and end > total:
            return f"Page {end} is outside the linked book ({total} pages)."
    return ""


def student_view(note: dict, document: dict, kolibri_public_url: str) -> dict:
    """The fields students may see. Staff review fields beyond status are omitted."""
    view = {
        key: note[key]
        for key in (
            "id",
            "title",
            "grade",
            "subject",
            "chapter",
            "language",
            "document_id",
            "pages",
            "key_ideas",
            "worked_example",
            "misconceptions",
            "hints",
            "check_question",
            "revision",
        )
    }
    view["book_title"] = document["title"]
    channel = note.get("kolibri_channel_id")
    view["kolibri_url"] = (
        learn_url(kolibri_public_url, channel)
        if channel and _CHANNEL_ID.fullmatch(channel) and kolibri_public_url
        else None
    )
    return view


def tokens(text: str) -> set[str]:
    return {word for word in _TOKEN.findall(text.casefold()) if len(word) > 2}


def relevance(note: dict, question: str) -> int:
    """Count words shared by a question and a note's teachable text."""
    haystack = " ".join(
        [
            note["title"],
            note["chapter"],
            *note["key_ideas"],
            note["worked_example"],
            *(m["wrong"] + " " + m["correction"] for m in note["misconceptions"]),
        ]
    )
    return len(tokens(question) & tokens(haystack))
