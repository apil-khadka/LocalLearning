"""Isolated browser fixture with HTTP contract doubles; never a deployment entry point."""

import tempfile
from pathlib import Path

import httpx

from app.config import Settings
from app.main import create_app
from tests.conftest import TOKEN, FakeLocalStack


def create_e2e_app():
    settings = Settings(
        _env_file=None,
        data_dir=Path(tempfile.mkdtemp(prefix="dh-e2e-")),
        ai_enabled=True,
        chat_provider="ollama",
        admin_token=TOKEN,
        ollama_base_url="http://ollama.test",
        qdrant_url="http://qdrant.test",
        kolibri_public_url="http://kolibri.test:8080",
        kolibri_probe_url="http://kolibri.test:8080",
    )
    return create_app(settings, httpx.AsyncClient(transport=httpx.MockTransport(FakeLocalStack())))
