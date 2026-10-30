from typing import Annotated, Literal

from pydantic import BaseModel, Field, StringConstraints

ShortText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]


class Turn(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=3000)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000, pattern=r"\S")
    grade: int = Field(8, ge=1, le=12)
    subject: ShortText = "Science"
    chapter: Annotated[str, StringConstraints(strip_whitespace=True, max_length=120)] = ""
    language: Literal["en", "ne"] = "en"
    history: list[Turn] = Field(default_factory=list, max_length=8)


class Source(BaseModel):
    document_id: str
    title: str
    page_start: int
    page_end: int
    chunk_id: str


class ChatResponse(BaseModel):
    answer: str
    grounding: Literal["textbook", "general"]
    sources: list[Source]
    model: str


class DocumentInput(BaseModel):
    title: ShortText
    grade: int = Field(ge=1, le=12)
    subject: ShortText
    chapter: ShortText
    license: ShortText
    source: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)]
