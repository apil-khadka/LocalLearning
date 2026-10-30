import re
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file="../.env", extra="ignore")

    data_dir: Path = Path("../data")
    ai_enabled: bool = False
    chat_provider: Literal["openai-compatible", "ollama"] = "openai-compatible"
    chat_api_base_url: str = "https://inference.baseten.co/v1"
    chat_api_key: SecretStr = SecretStr("")
    chat_model: str = "meta-models/muse-spark-open-1026"
    ollama_base_url: str = ""
    ollama_model: str = "qwen3:4b-instruct"
    embed_model: str = "embeddinggemma"
    embed_query_prefix: str = "task: search result | query: "
    embed_document_prefix: str = "title: {title} | text: "
    qdrant_url: str = ""
    qdrant_api_key: SecretStr = SecretStr("")
    qdrant_collection: str = "dh_curriculum_v1"
    admin_token: SecretStr = SecretStr("")
    kiwix_public_url: str = ""
    kiwix_probe_url: str = ""
    kolibri_public_url: str = ""
    kolibri_probe_url: str = ""
    model_timeout_seconds: float = Field(120, ge=1, le=600)
    chat_timeout_seconds: float = Field(60, ge=1, le=600)
    dependency_timeout_seconds: float = Field(3, ge=0.1, le=30)
    max_upload_bytes: int = Field(10 * 1024 * 1024, ge=1024, le=50 * 1024 * 1024)
    max_pdf_pages: int = Field(100, ge=1, le=500)
    max_chat_concurrency: int = Field(1, ge=1, le=8)
    retrieval_threshold: float = Field(0.65, ge=0, le=1)
    retrieval_top_k: int = Field(4, ge=1, le=8)

    @field_validator(
        "ollama_base_url",
        "chat_api_base_url",
        "qdrant_url",
        "kiwix_public_url",
        "kolibri_public_url",
        "kiwix_probe_url",
        "kolibri_probe_url",
    )
    @classmethod
    def validate_url(cls, value: str) -> str:
        if not value:
            return value
        parsed = urlsplit(value)
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.hostname
            or parsed.username
            or parsed.password
            or parsed.fragment
            or parsed.query
        ):
            raise ValueError("Use an HTTP(S) URL without credentials, query or fragment")
        return value.rstrip("/")

    @field_validator("qdrant_collection")
    @classmethod
    def isolated_collection(cls, value: str) -> str:
        if not re.fullmatch(r"dh_[a-zA-Z0-9_-]+", value):
            raise ValueError("Use a dedicated collection beginning with dh_")
        return value

    @field_validator("admin_token")
    @classmethod
    def strong_token(cls, value: SecretStr) -> SecretStr:
        if value.get_secret_value() and len(value.get_secret_value()) < 32:
            raise ValueError("ADMIN_TOKEN must be empty (staff disabled) or at least 32 characters")
        return value
