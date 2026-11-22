import json

import httpx
import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


def ask(client, **overrides):
    return client.post(
        "/api/tutor/chat",
        json={"message": "Explain force in two sentences.", **overrides},
    )


def test_lmstudio_settings_are_blank_by_default_and_read_from_env_file(tmp_path):
    defaults = Settings(_env_file=None, data_dir=tmp_path)
    assert defaults.lmstudio_base_url == ""
    assert defaults.lmstudio_model == ""

    env_file = tmp_path / ".env"
    env_file.write_text(
        "AI_ENABLED=true\n"
        "CHAT_PROVIDER=lmstudio\n"
        "LMSTUDIO_BASE_URL=http://127.0.0.1:1234\n"
        "LMSTUDIO_MODEL=  phi-4-mini-instruct  \n",
        encoding="utf-8",
    )
    loaded = Settings(_env_file=env_file, data_dir=tmp_path)
    assert loaded.chat_provider == "lmstudio"
    assert loaded.lmstudio_base_url == "http://127.0.0.1:1234"
    assert loaded.lmstudio_model == "phi-4-mini-instruct"
    assert loaded.active_chat_model == "phi-4-mini-instruct"


def test_lmstudio_instruct_happy_path_and_services_probe(tmp_path):
    calls = []

    def handler(request):
        calls.append(request)
        if request.method == "GET" and request.url.path == "/api/v1/models":
            return httpx.Response(
                200,
                json={
                    "models": [
                        {
                            "type": "llm",
                            "key": "phi-4-mini-instruct",
                            "loaded_instances": [{"id": "phi-4-mini-instruct"}],
                        },
                        {
                            "type": "embedding",
                            "key": "text-embedding-nomic-embed-text-v1.5",
                        },
                    ]
                },
            )
        if request.method == "POST" and request.url.path == "/api/v1/chat":
            return httpx.Response(
                200,
                json={
                    "model_instance_id": "phi-4-mini-instruct",
                    "output": [{"type": "message", "content": "\n\nA force is a push or pull.  "}],
                },
            )
        return httpx.Response(404)

    settings = Settings(
        _env_file=None,
        data_dir=tmp_path,
        ai_enabled=True,
        chat_provider="lmstudio",
        lmstudio_base_url="http://lmstudio.test",
        lmstudio_model="phi-4-mini-instruct",
        ollama_base_url="",
        qdrant_url="",
    )
    upstream = httpx.AsyncClient(transport=httpx.MockTransport(handler), trust_env=False)

    with TestClient(create_app(settings, upstream)) as client:
        services = client.get("/api/services").json()
        response = ask(client)

    assert services["tutor"]["status"] == "ready"
    assert services["dependencies"]["chat_model"] == "ready"
    assert services["dependencies"]["embeddings"] == "unconfigured"
    assert services["dependencies"]["vectors"] == "unconfigured"
    assert services["evaluation_config"]["chat_provider"] == "lmstudio"
    assert services["evaluation_config"]["chat_model"] == "phi-4-mini-instruct"

    assert response.status_code == 200, response.text
    assert response.json()["answer"] == "A force is a push or pull."
    assert response.json()["grounding"] == "general"
    assert response.json()["sources"] == []
    assert response.json()["model"] == "phi-4-mini-instruct"

    chat_requests = [req for req in calls if req.url.path == "/api/v1/chat"]
    assert len(chat_requests) == 1
    payload = json.loads(chat_requests[0].content)
    assert payload["model"] == "phi-4-mini-instruct"
    assert payload["system_prompt"]
    assert json.loads(payload["input"])["question"] == "Explain force in two sentences."
    assert payload["max_output_tokens"] == settings.lmstudio_max_output_tokens
    assert payload["store"] is False


def test_lmstudio_strips_reasoning_output_and_serializes_history(tmp_path):
    captured = []

    def handler(request):
        captured.append(json.loads(request.content))
        return httpx.Response(
            200,
            json={
                "output": [
                    {"type": "reasoning", "content": "Internal scratchpad that must not leak."},
                    {"type": "message", "content": "Doubling mass requires double the force."},
                ]
            },
        )

    settings = Settings(
        _env_file=None,
        data_dir=tmp_path,
        ai_enabled=True,
        chat_provider="lmstudio",
        lmstudio_base_url="http://lmstudio.test",
        lmstudio_model="custom/reasoning-model",
        qdrant_url="",
    )
    upstream = httpx.AsyncClient(transport=httpx.MockTransport(handler), trust_env=False)

    with TestClient(create_app(settings, upstream)) as client:
        response = ask(
            client,
            message="What happens if mass doubles?",
            history=[
                {"role": "user", "content": "What is force?"},
                {"role": "assistant", "content": "Force equals mass times acceleration."},
            ],
        )

    assert response.status_code == 200, response.text
    assert response.json()["answer"] == "Doubling mass requires double the force."
    assert "Internal scratchpad" not in response.json()["answer"]
    assert len(captured) == 1
    assert "system_prompt" in captured[0]
    assert "Untrusted previous conversation:" in captured[0]["input"]
    assert "User: What is force?" in captured[0]["input"]
    assert "Assistant: Force equals mass times acceleration." in captured[0]["input"]
    assert "What happens if mass doubles?" in captured[0]["input"]


@pytest.mark.parametrize(
    "configured_url",
    [
        "http://lmstudio.test/api/v1",
        "http://lmstudio.test/api/v1/chat",
        "http://lmstudio.test/api/v1/",
    ],
)
def test_lmstudio_base_url_normalization(tmp_path, configured_url):
    paths = []

    def handler(request):
        paths.append((request.method, request.url.path))
        if request.method == "GET":
            return httpx.Response(200, json={"models": [{"type": "llm", "key": "m1"}]})
        return httpx.Response(200, json={"output": [{"type": "message", "content": "Ok"}]})

    settings = Settings(
        _env_file=None,
        data_dir=tmp_path,
        ai_enabled=True,
        chat_provider="lmstudio",
        lmstudio_base_url=configured_url,
        lmstudio_model="m1",
        qdrant_url="",
    )
    upstream = httpx.AsyncClient(transport=httpx.MockTransport(handler), trust_env=False)

    with TestClient(create_app(settings, upstream)) as client:
        assert client.get("/api/services").json()["tutor"]["status"] == "ready"
        assert ask(client).status_code == 200

    assert ("GET", "/api/v1/models") in paths
    assert ("POST", "/api/v1/chat") in paths


def test_lmstudio_api_key_sent_and_not_leaked_on_error(tmp_path):
    api_key = "lmstudio-secret-token-never-leak"
    seen_headers = []

    def handler(request):
        seen_headers.append(request.headers.get("authorization"))
        return httpx.Response(500, text=f"upstream failure {api_key}")

    settings = Settings(
        _env_file=None,
        data_dir=tmp_path,
        ai_enabled=True,
        chat_provider="lmstudio",
        lmstudio_base_url="http://lmstudio.test",
        lmstudio_model="phi-4-mini-instruct",
        lmstudio_api_key=api_key,
        qdrant_url="",
    )
    upstream = httpx.AsyncClient(transport=httpx.MockTransport(handler), trust_env=False)

    with TestClient(create_app(settings, upstream)) as client:
        response = ask(client)

    assert seen_headers == [f"Bearer {api_key}"]
    assert response.status_code == 503
    assert response.json()["detail"] == "A required local service is unavailable."
    assert api_key not in response.text


@pytest.mark.parametrize(
    ("base_url", "model"),
    [
        ("", "phi-4-mini-instruct"),
        ("http://lmstudio.test", ""),
        ("http://lmstudio.test", "   "),
    ],
)
def test_lmstudio_unconfigured_url_or_model_reports_unconfigured_without_requests(
    tmp_path, base_url, model
):
    calls = []
    settings = Settings(
        _env_file=None,
        data_dir=tmp_path,
        ai_enabled=True,
        chat_provider="lmstudio",
        lmstudio_base_url=base_url,
        lmstudio_model=model,
        qdrant_url="",
    )
    upstream = httpx.AsyncClient(
        transport=httpx.MockTransport(lambda req: calls.append(req)),
        trust_env=False,
    )

    with TestClient(create_app(settings, upstream)) as client:
        services = client.get("/api/services").json()
        response = ask(client)

    assert services["tutor"]["status"] == "unconfigured"
    assert services["dependencies"]["chat_model"] == "unconfigured"
    assert response.status_code == 503
    assert response.json()["detail"] == "The AI provider is not configured."
    assert calls == []


def test_lmstudio_missing_model_ignores_embeddings_and_reports_missing_model(tmp_path):
    def handler(request):
        return httpx.Response(
            200,
            json={
                "models": [
                    {"type": "embedding", "key": "phi-4-mini-instruct"},
                    {"type": "llm", "key": "other-model"},
                ]
            },
        )

    settings = Settings(
        _env_file=None,
        data_dir=tmp_path,
        ai_enabled=True,
        chat_provider="lmstudio",
        lmstudio_base_url="http://lmstudio.test",
        lmstudio_model="phi-4-mini-instruct",
        qdrant_url="",
    )
    upstream = httpx.AsyncClient(transport=httpx.MockTransport(handler), trust_env=False)

    with TestClient(create_app(settings, upstream)) as client:
        services = client.get("/api/services").json()

    assert services["tutor"]["status"] == "missing_model"
    assert services["dependencies"]["chat_model"] == "missing_model"


def test_lmstudio_outage_reports_unavailable_and_safe_503(tmp_path):
    def handler(request):
        raise httpx.ConnectError("connection refused", request=request)

    settings = Settings(
        _env_file=None,
        data_dir=tmp_path,
        ai_enabled=True,
        chat_provider="lmstudio",
        lmstudio_base_url="http://lmstudio.test",
        lmstudio_model="phi-4-mini-instruct",
        qdrant_url="",
    )
    upstream = httpx.AsyncClient(transport=httpx.MockTransport(handler), trust_env=False)

    with TestClient(create_app(settings, upstream)) as client:
        services = client.get("/api/services").json()
        response = ask(client)

    assert services["tutor"]["status"] == "unavailable"
    assert services["dependencies"]["chat_model"] == "unavailable"
    assert response.status_code == 503
    assert "lmstudio.test" not in response.text


@pytest.mark.parametrize(
    "output",
    [
        [{"type": "reasoning", "content": "Only thought, no final message."}],
        [{"type": "message", "content": "   "}],
        [],
    ],
)
def test_lmstudio_reasoning_only_or_blank_message_returns_safe_503(tmp_path, output):
    def handler(request):
        return httpx.Response(200, json={"output": output})

    settings = Settings(
        _env_file=None,
        data_dir=tmp_path,
        ai_enabled=True,
        chat_provider="lmstudio",
        lmstudio_base_url="http://lmstudio.test",
        lmstudio_model="phi-4-mini-instruct",
        qdrant_url="",
    )
    upstream = httpx.AsyncClient(transport=httpx.MockTransport(handler), trust_env=False)

    with TestClient(create_app(settings, upstream)) as client:
        response = ask(client)

    assert response.status_code == 503
    assert response.json()["detail"] == "The model did not return a readable answer."
