import json

import httpx
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


def ask(client):
    return client.post(
        "/api/tutor/chat",
        json={"message": "Explain force in two sentences."},
    )


def test_default_provider_uses_requested_model_and_base_url(tmp_path):
    settings = Settings(_env_file=None, data_dir=tmp_path)

    assert settings.chat_provider == "openai-compatible"
    assert settings.chat_api_base_url == "https://inference.baseten.co/v1"
    assert settings.chat_model == "meta-models/muse-spark-open-1026"


def test_openai_compatible_provider_uses_configured_endpoint_and_model(tmp_path):
    calls = []

    def respond(request):
        calls.append(request)
        return httpx.Response(
            200,
            json={
                "id": "chatcmpl-test",
                "object": "chat.completion",
                "created": 1,
                "model": "meta-models/muse-spark-open-1026",
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": "A force changes motion."},
                        "finish_reason": "stop",
                    }
                ],
            },
        )

    settings = Settings(
        _env_file=None,
        data_dir=tmp_path,
        ai_enabled=True,
        chat_provider="openai-compatible",
        chat_api_base_url="https://inference.test/v1",
        chat_api_key="test-token-that-is-never-a-real-credential",
        chat_model="meta-models/muse-spark-open-1026",
        chat_reasoning_effort="low",
        ollama_base_url="",
        qdrant_url="",
    )
    upstream = httpx.AsyncClient(transport=httpx.MockTransport(respond), trust_env=False)

    with TestClient(create_app(settings, upstream)) as client:
        response = ask(client)
        services = client.get("/api/services").json()

    assert response.status_code == 200, response.text
    assert response.json()["answer"] == "A force changes motion."
    assert response.json()["grounding"] == "general"
    assert response.json()["sources"] == []
    assert response.json()["model"] == "meta-models/muse-spark-open-1026"
    assert len(calls) == 1
    assert calls[0].url == "https://inference.test/v1/chat/completions"
    assert calls[0].headers["authorization"] == "Bearer test-token-that-is-never-a-real-credential"
    payload = json.loads(calls[0].content)
    assert payload["model"] == "meta-models/muse-spark-open-1026"
    assert payload["reasoning_effort"] == "low"
    assert payload["messages"][-1]["role"] == "user"
    assert services["tutor"]["status"] == "configured"
    assert services["dependencies"]["chat_model"] == "configured"
    assert services["dependencies"]["embeddings"] == "unconfigured"
    assert services["dependencies"]["vectors"] == "unconfigured"


def test_openai_compatible_provider_requires_api_key(tmp_path):
    calls = []
    settings = Settings(
        _env_file=None,
        data_dir=tmp_path,
        ai_enabled=True,
        chat_api_base_url="https://inference.test/v1",
        chat_api_key="",
        ollama_base_url="",
        qdrant_url="",
    )
    upstream = httpx.AsyncClient(
        transport=httpx.MockTransport(lambda request: calls.append(request)),
        trust_env=False,
    )

    with TestClient(create_app(settings, upstream)) as client:
        response = ask(client)

    assert response.status_code == 503
    assert response.json()["detail"] == "The AI provider is not configured."
    assert calls == []


def test_openai_compatible_upstream_failure_is_safe(tmp_path):
    api_key = "test-token-that-is-never-a-real-credential"
    settings = Settings(
        _env_file=None,
        data_dir=tmp_path,
        ai_enabled=True,
        chat_api_base_url="https://inference.test/v1",
        chat_api_key=api_key,
        ollama_base_url="",
        qdrant_url="",
    )
    upstream = httpx.AsyncClient(
        transport=httpx.MockTransport(lambda request: httpx.Response(503, text=api_key)),
        trust_env=False,
    )

    with TestClient(create_app(settings, upstream)) as client:
        response = ask(client)

    assert response.status_code == 503
    assert response.json()["detail"] == "The AI provider could not return an answer."
    assert api_key not in response.text
