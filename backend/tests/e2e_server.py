"""Isolated browser fixture with HTTP contract doubles; never a deployment entry point."""

import tempfile
from pathlib import Path

import httpx

from app.config import Settings
from app.identity import UserInput
from app.main import create_app
from tests.conftest import TOKEN, FakeLocalStack


def create_e2e_app():
    settings = Settings(
        _env_file=None,
        data_dir=Path(tempfile.mkdtemp(prefix="dh-e2e-")),
        ai_enabled=True,
        require_auth=False,
        auth_cookie_secure=False,
        chat_provider="ollama",
        admin_token=TOKEN,
        ollama_base_url="http://ollama.test",
        qdrant_url="http://qdrant.test",
        kolibri_public_url="http://kolibri.test:8080",
        kolibri_probe_url="http://kolibri.test:8080",
    )
    app = create_app(settings, httpx.AsyncClient(transport=httpx.MockTransport(FakeLocalStack())))
    identity = app.state.identity
    admin = identity.create_user(
        UserInput(
            username="e2e-admin",
            display_name="E2E Administrator",
            password="E2E-Admin-Password-2026!",
            role="admin",
        )
    )
    teacher = identity.create_user(
        UserInput(
            username="e2e-teacher",
            display_name="E2E Teacher",
            password="E2E-Teacher-Password-2026!",
            role="teacher",
        )
    )
    student = identity.create_user(
        UserInput(
            username="e2e-student",
            display_name="E2E Student",
            password="E2E-Student-Password-2026!",
            role="student",
            grade=8,
        )
    )
    with identity.connect() as database:
        database.execute("UPDATE users SET must_change_password = 0")
    classroom = identity.create_class(
        name="E2E Grade 8 A", grade=8, creator_id=admin["id"], teacher_id=teacher["id"]
    )
    identity.enroll_student(classroom["id"], student["id"])
    return app
