"""Opt-in checks. No claim of live inference is made when these are skipped."""

import os
from uuid import uuid4

import httpx
import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


@pytest.mark.skipif(
    not os.getenv("LIVE_OLLAMA_URL"), reason="Set LIVE_OLLAMA_URL for real inference"
)
def test_live_model(tmp_path):
    settings = Settings(
        _env_file=None,
        data_dir=tmp_path,
        ai_enabled=True,
        ollama_base_url=os.environ["LIVE_OLLAMA_URL"],
        qdrant_url=os.environ["LIVE_QDRANT_URL"],
        ollama_model=os.environ.get("LIVE_OLLAMA_MODEL", "qwen3:4b-instruct"),
    )
    with TestClient(create_app(settings)) as client:
        response = client.post(
            "/api/tutor/chat", json={"message": "Explain force in two sentences."}
        )
        assert response.status_code == 200, response.text
        assert response.json()["answer"].strip()


@pytest.mark.skipif(
    not os.getenv("QDRANT_TEST_URL"), reason="Set QDRANT_TEST_URL for real vector storage"
)
def test_real_qdrant_ingestion_retrieval_and_retry(tmp_path):
    base_url = os.environ["QDRANT_TEST_URL"]
    collection = "dh_test_" + uuid4().hex
    token = "temporary-test-token-only-for-this-process"

    async def transport(request):
        if request.url.host == "model.test":
            import json

            body = json.loads(request.content)
            if request.url.path == "/api/embed":
                return httpx.Response(200, json={"embeddings": [[1, 0, 0] for _ in body["input"]]})
            return httpx.Response(200, json={"message": {"content": "HTTP adapter test response"}})
        async with httpx.AsyncClient(trust_env=False) as real:
            return await real.send(request)

    settings = Settings(
        _env_file=None,
        data_dir=tmp_path,
        ai_enabled=True,
        ollama_base_url="http://model.test",
        qdrant_url=base_url,
        qdrant_collection=collection,
        admin_token=token,
    )
    try:
        with TestClient(
            create_app(settings, httpx.AsyncClient(transport=httpx.MockTransport(transport)))
        ) as client:

            def upload():
                return client.post(
                    "/api/admin/documents",
                    headers={"Authorization": "Bearer " + token},
                    data={
                        "title": "Force",
                        "grade": 8,
                        "subject": "Science",
                        "chapter": "Motion",
                        "license": "CC0",
                        "source": "Original test",
                    },
                    files={"file": ("force.txt", b"Force equals mass times acceleration.")},
                )

            assert upload().status_code == 201
            assert upload().status_code == 201
            answer = client.post(
                "/api/tutor/chat", json={"message": "Explain force", "chapter": "Motion"}
            )
            assert answer.status_code == 200, answer.text
            assert len(answer.json()["sources"]) == 1
            wrong_grade = client.post(
                "/api/tutor/chat", json={"message": "Explain force", "grade": 9}
            )
            assert wrong_grade.json()["sources"] == []
            info = httpx.get(f"{base_url}/collections/{collection}").json()
            assert info["result"]["points_count"] == 1
    finally:
        httpx.delete(f"{base_url}/collections/{collection}").raise_for_status()
