from typing import Annotated, Literal

from pydantic import BaseModel, Field, StringConstraints, model_validator

ShortText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]


class Turn(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=3000)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000, pattern=r"\S")
    session_id: str | None = Field(None, pattern=r"^[a-f0-9]{32}$")
    grade: int = Field(8, ge=1, le=12)
    subject: ShortText = "Science"
    chapter: Annotated[str, StringConstraints(strip_whitespace=True, max_length=120)] = ""
    language: Literal["en", "ne"] = "en"
    history: list[Turn] = Field(default_factory=list, max_length=8)
    mode: Literal["explain", "hint", "debug"] = "explain"
    # The learner's own working, required for debug mode. Treated as untrusted data.
    attempt: Annotated[str, StringConstraints(strip_whitespace=True, max_length=2000)] = ""
    # Zero-based hint step used by the progressive hint flow.
    hint_level: int = Field(0, ge=0, le=4)

    @model_validator(mode="after")
    def debug_needs_attempt(self):
        if self.mode == "debug" and not self.attempt:
            raise ValueError("Debug mode needs the learner's attempt.")
        return self


class Source(BaseModel):
    document_id: str
    title: str
    page_start: int
    page_end: int
    chunk_id: str
    kind: Literal["passage", "note"] = "passage"
    note_id: str | None = None


class ChatResponse(BaseModel):
    answer: str
    grounding: Literal["textbook", "note", "general"]
    sources: list[Source]
    model: str
    mode: Literal["explain", "hint", "debug"] = "explain"
    session_id: str | None = None


class DocumentInput(BaseModel):
    title: ShortText
    grade: int | None = Field(None, ge=0, le=12)
    subject: ShortText
    chapter: ShortText
    license: ShortText
    source: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)]


class IndexBookRequest(BaseModel):
    document_id: str = Field(pattern=r"^[a-f0-9]{32}$")
