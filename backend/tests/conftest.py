import json

import httpx
import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app

TOKEN = "test-only-staff-token-that-is-not-a-real-secret"


class FakeLocalStack:
    """HTTP contract double. Never used by the running product."""

    def __init__(self):
        self.points = {}
        self.collection = False
        self.score = 0.95
        self.outage = None
        self.calls = []
        self.last_chat = None

    def __call__(self, request):
        path = request.url.path
        self.calls.append((request.method, path))
        if self.outage and self.outage in str(request.url):
            raise httpx.ConnectError("test failure", request=request)
        body = json.loads(request.content) if request.content else {}
        if path == "/api/tags":
            data = {"models": [{"name": "qwen3:4b-instruct"}, {"name": "embeddinggemma:latest"}]}
        elif path == "/api/embed":
            data = {"embeddings": [[1.0, 0.0, 0.0] for _ in body["input"]]}
        elif path == "/api/chat":
            self.last_chat = body
            data = {"message": {"content": "Test model output. What happens when mass doubles?"}}
        elif path == "/collections":
            data = {
                "result": {"collections": [{"name": "dh_curriculum_v1"}] if self.collection else []}
            }
        elif path == "/collections/dh_curriculum_v1" and request.method == "PUT":
            self.collection = True
            data = {"result": True}
        elif path == "/collections/dh_curriculum_v1":
            data = {
                "result": {"config": {"params": {"vectors": {"size": 3, "distance": "Cosine"}}}}
            }
        elif path.endswith("/points"):
            self.points.update({p["id"]: p for p in body["points"]})
            data = {"result": {"status": "completed"}}
        elif path.endswith("/points/query"):
            data = {
                "result": {
                    "points": [
                        {"payload": p["payload"], "score": self.score}
                        for p in self.points.values()
                        if all(
                            p["payload"].get(f["key"]) == f["match"]["value"]
                            for f in body["filter"]["must"]
                        )
                        and self.score >= body["score_threshold"]
                    ][: body["limit"]]
                }
            }
        else:
            return httpx.Response(404)
        return httpx.Response(200, json=data)


@pytest.fixture
def stack():
    return FakeLocalStack()


@pytest.fixture
def settings(tmp_path):
    return Settings(
        _env_file=None,
        data_dir=tmp_path,
        ai_enabled=True,
        ollama_base_url="http://ollama.test",
        qdrant_url="http://qdrant.test",
        admin_token=TOKEN,
    )


@pytest.fixture
def client(settings, stack):
    upstream = httpx.AsyncClient(transport=httpx.MockTransport(stack))
    with TestClient(create_app(settings, upstream)) as test_client:
        yield test_client


@pytest.fixture
def staff():
    return {"Authorization": "Bearer " + TOKEN}


@pytest.fixture
def upload(client, staff):
    def send(content=b"Newton's second law: Force equals mass times acceleration.", **overrides):
        metadata = {
            "title": "Force and motion",
            "grade": "8",
            "subject": "Science",
            "chapter": "Force and Motion",
            "license": "CC0-1.0",
            "source": "Original test note",
        }
        metadata.update(overrides)
        return client.post(
            "/api/admin/documents",
            headers=staff,
            data=metadata,
            files={"file": ("chapter.txt", content, "text/plain")},
        )

    return send
