import asyncio

import httpx
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app import kolibri
from app.config import Settings
from app.main import create_app


@pytest.mark.parametrize(
    "url",
    [
        "http://kolibri.test/../admin",
        "http://kolibri.test//en/learn",
        "http://kolibri.test:invalid",
        "http://user:pass@kolibri.test",
    ],
)
def test_kolibri_public_url_rejects_unsafe_base_urls(url):
    with pytest.raises(ValidationError):
        Settings(_env_file=None, kolibri_public_url=url)


def kolibri_client(tmp_path, stack):
    settings = Settings(
        _env_file=None,
        data_dir=tmp_path,
        kolibri_public_url="http://kolibri.test:8080",
        kolibri_probe_url="http://kolibri.test:8080",
    )
    upstream = httpx.AsyncClient(transport=httpx.MockTransport(stack))
    return TestClient(create_app(settings, upstream))


def test_channels_returns_sanitized_catalog_sorted_by_name(tmp_path, stack):
    with kolibri_client(tmp_path, stack) as client:
        response = client.get("/api/kolibri/channels")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "reachable"
    assert body["url"] == "http://kolibri.test:8080"
    assert body["version"] == "0.19.5"
    names = [item["name"] for item in body["channels"]]
    assert names == ["PhET Interactive Simulations", "Touchable Earth (en)"]
    phet = body["channels"][0]
    assert phet["available"] is True
    assert phet["total_resources"] == 1175
    assert (
        phet["learn_url"]
        == "http://kolibri.test:8080/en/learn/#/topics/c/197934f144305350b5820c7c4dd8e194"
    )
    unavailable = body["channels"][1]
    assert unavailable["available"] is False
    assert unavailable["total_resources"] == 0
    assert unavailable["learn_url"] is None


def test_channels_unconfigured_without_public_url(tmp_path, stack):
    settings = Settings(_env_file=None, data_dir=tmp_path)
    upstream = httpx.AsyncClient(transport=httpx.MockTransport(stack))
    with TestClient(create_app(settings, upstream)) as client:
        response = client.get("/api/kolibri/channels")
    assert response.status_code == 503
    assert "Kolibri" in response.json()["detail"]


def test_services_reports_kolibri_version_and_counts(tmp_path, stack):
    with kolibri_client(tmp_path, stack) as client:
        services = client.get("/api/services").json()
    entry = services["kolibri"]
    assert entry["status"] == "reachable"
    assert entry["url"] == "http://kolibri.test:8080"
    assert entry["version"] == "0.19.5"
    assert entry["channel_count"] == 2
    assert entry["available_count"] == 1
    assert entry["resource_count"] == 1175


def test_public_channel_rejects_invalid_entries():
    assert kolibri.public_channel({"id": "x", "name": "Bad"}, "http://k.test") is None
    assert kolibri.public_channel("not-a-dict", "http://k.test") is None
    assert (
        kolibri.public_channel(
            {
                "id": "197934f144305350b5820c7c4dd8e194",
                "root": "197934f144305350b5820c7c4dd8e194",
                "name": "  ",
            },
            "http://k.test",
        )
        is None
    )


def test_public_version_rejects_invalid_values():
    assert kolibri.public_version({"kolibri_version": "0.19.5"}) == "0.19.5"
    assert kolibri.public_version({}) is None
    assert kolibri.public_version({"kolibri_version": "1.0; rm -rf /"}) is None


CHANNEL_ID = "197934f144305350b5820c7c4dd8e194"
OTHER_ID = "000409f81dbe5d1ba67101cb9fed4530"
PUBLIC_URL = "http://kolibri.test:8080"
PROBE_URL = "http://kolibri.internal:8080"


def _entry(channel_id=CHANNEL_ID, root=None, name="Channel", **overrides):
    entry = {
        "id": channel_id,
        "root": channel_id if root is None else root,
        "name": name,
        "description": "A channel.",
        "version": 2,
        "lang_code": "en",
        "lang_name": "English",
        "total_resource_count": 12,
        "available": True,
    }
    entry.update(overrides)
    return entry


def test_learn_url_preserves_public_base_path():
    assert (
        kolibri.learn_url("https://school.example:8443/kolibri/", CHANNEL_ID)
        == f"https://school.example:8443/kolibri/en/learn/#/topics/c/{CHANNEL_ID}"
    )


@pytest.mark.parametrize(
    "root_id",
    [
        "",
        "a" * 31,
        "a" * 33,
        "g" * 32,
        "../../admin",
        f"{CHANNEL_ID}#/evil",
        f"{CHANNEL_ID}/extra",
        f"{CHANNEL_ID}\n",
        f" {CHANNEL_ID}",
        None,
        123,
    ],
)
def test_learn_url_rejects_unsafe_root_ids(root_id):
    with pytest.raises(ValueError):
        kolibri.learn_url(PUBLIC_URL, root_id)


@pytest.mark.parametrize(
    "public_url",
    [
        "",
        "kolibri.test",
        "//evil.com",
        "javascript:alert(1)",
        "ftp://kolibri.test",
        "http://user:pass@kolibri.test",
        "http://kolibri.test?x=1",
        "http://kolibri.test#frag",
        "http://kolibri.test:99999",
        "http://kolibri.test/../etc",
        "http://kolibri.test//api",
        "http://kolibri .test",
        None,
    ],
)
def test_learn_url_rejects_unsafe_public_urls(public_url):
    with pytest.raises(ValueError):
        kolibri.learn_url(public_url, CHANNEL_ID)


def test_public_channel_normalizes_uppercase_ids():
    channel = kolibri.public_channel(_entry(CHANNEL_ID.upper()), PUBLIC_URL)
    assert channel is not None
    assert channel["id"] == CHANNEL_ID
    assert channel["learn_url"].endswith(f"/c/{CHANNEL_ID}")


@pytest.mark.parametrize(
    "entry",
    [
        None,
        "not-a-dict",
        [],
        {},
        {"id": CHANNEL_ID, "name": "Missing root"},
        {"id": CHANNEL_ID, "root": "not-an-id", "name": "Bad root"},
        {"id": f" {CHANNEL_ID}", "root": CHANNEL_ID, "name": "Padded id"},
        {"id": CHANNEL_ID, "root": CHANNEL_ID, "name": "   "},
        {"id": CHANNEL_ID, "root": CHANNEL_ID, "name": "\x00\x1b"},
        {"id": "g" * 32, "root": CHANNEL_ID, "name": "Non hex"},
    ],
)
def test_public_channel_rejects_unusable_entries(entry):
    assert kolibri.public_channel(entry, PUBLIC_URL) is None


def test_public_channel_sanitizes_text_and_whitelists_fields():
    channel = kolibri.public_channel(
        _entry(
            name="  PhET\n\tInteractive\x00Simulations ",
            description="line1\nline2\x07end",
            lang_name="Eng\x1blish",
            admin_url="http://evil.example",
        ),
        PUBLIC_URL,
    )
    assert channel is not None
    assert set(channel) == {
        "id",
        "name",
        "description",
        "version",
        "lang_code",
        "lang_name",
        "total_resources",
        "available",
        "learn_url",
    }
    assert channel["name"] == "PhET Interactive Simulations"
    assert channel["description"] == "line1 line2 end"
    assert channel["lang_name"] == "Eng lish"
    for value in channel.values():
        if isinstance(value, str):
            assert not any(ord(char) < 32 or ord(char) == 127 for char in value)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (1175, 1175),
        (0, 0),
        (-1, 0),
        (True, 0),
        (1175.0, 0),
        ("1175", 0),
        (None, 0),
        (10**12, 1_000_000),
    ],
)
def test_public_channel_bounds_counts(raw, expected):
    channel = kolibri.public_channel(_entry(total_resource_count=raw, version=raw), PUBLIC_URL)
    assert channel is not None
    assert channel["total_resources"] == expected
    assert channel["version"] == expected


def test_public_channel_requires_literal_true_and_valid_lang_code():
    assert kolibri.public_channel(_entry(available=1), PUBLIC_URL)["available"] is False
    assert kolibri.public_channel(_entry(available="true"), PUBLIC_URL)["available"] is False
    empty = kolibri.public_channel(_entry(total_resource_count=0), PUBLIC_URL)
    assert empty is not None and empty["learn_url"] is None
    assert kolibri.public_channel(_entry(lang_code='en"><script>'), PUBLIC_URL)["lang_code"] == ""
    assert kolibri.public_channel(_entry(lang_code="en-US"), PUBLIC_URL)["lang_code"] == "en-US"


@pytest.mark.parametrize(
    "public_url",
    ["javascript:alert(1)", "//evil.com", "http://user:pass@k.test", "", "ftp://k.test"],
)
def test_public_channel_rejects_unsafe_public_url(public_url):
    assert kolibri.public_channel(_entry(), public_url) is None


def test_public_version_rejects_malformed_payloads():
    assert kolibri.public_version([]) is None
    assert kolibri.public_version("0.19.5") is None
    assert kolibri.public_version(None) is None
    assert kolibri.public_version({"kolibri_version": 19}) is None
    assert kolibri.public_version({"kolibri_version": ""}) is None
    assert kolibri.public_version({"kolibri_version": " 0.19.5 "}) == "0.19.5"
    assert kolibri.public_version({"kolibri_version": "0.19.5\n; rm -rf /"}) is None
    assert kolibri.public_version({"kolibri_version": "1" * 33}) is None


def _upstream(*, info=None, channels=None, calls=None):
    def handler(request):
        if calls is not None:
            calls.append(request.url.path)
        path = request.url.path
        if path == "/api/public/info/":
            payload = {"kolibri_version": "0.19.5"} if info is None else info
            return httpx.Response(200, json=payload)
        if path == "/api/content/channel/":
            return httpx.Response(200, json=[] if channels is None else channels)
        if path == "/":
            return httpx.Response(200, text="Kolibri test service")
        return httpx.Response(404)

    return handler


async def _fetch_async(handler, probe_url=PROBE_URL, public_url=PUBLIC_URL, timeout=3):
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        return await kolibri.fetch_catalog(client, probe_url, public_url, timeout)


def _fetch(handler, **kwargs):
    return asyncio.run(_fetch_async(handler, **kwargs))


def test_fetch_catalog_deduplicates_sorts_and_uses_public_url():
    calls = []
    handler = _upstream(
        calls=calls,
        channels=[
            _entry(OTHER_ID, name="bravo"),
            _entry(CHANNEL_ID.upper(), name="Alpha first"),
            _entry(CHANNEL_ID, name="Alpha duplicate"),
            {"id": "broken", "name": "Broken"},
            _entry("a" * 32, name="charlie"),
        ],
    )
    version, channels = _fetch(handler, public_url="https://school.example/kolibri/")
    assert version == "0.19.5"
    assert [item["name"] for item in channels] == ["Alpha first", "bravo", "charlie"]
    assert channels[0]["id"] == CHANNEL_ID
    assert channels[0]["learn_url"] == (
        f"https://school.example/kolibri/en/learn/#/topics/c/{CHANNEL_ID}"
    )
    assert calls == ["/api/public/info/", "/api/content/channel/"]


def test_fetch_catalog_limits_channel_count():
    entries = [_entry(f"{index:032x}", name=f"Channel {index:03d}") for index in range(205)]
    _, channels = _fetch(_upstream(channels=entries))
    assert len(channels) == 200


def test_fetch_catalog_tolerates_malformed_version():
    version, channels = _fetch(_upstream(info={"kolibri_version": "bad; rm"}, channels=[_entry()]))
    assert version is None
    assert len(channels) == 1
    version, channels = _fetch(_upstream(info=["not-a-dict"], channels=[]))
    assert version is None
    assert channels == []


def test_fetch_catalog_rejects_non_list_channels():
    with pytest.raises(ValueError, match="invalid channel list"):
        _fetch(_upstream(channels={"results": []}))


def test_fetch_catalog_rejects_invalid_json():
    def handler(request):
        if request.url.path == "/api/public/info/":
            return httpx.Response(200, json={"kolibri_version": "0.19.5"})
        return httpx.Response(200, text="{not json", headers={"content-type": "application/json"})

    with pytest.raises(ValueError, match="invalid JSON"):
        _fetch(handler)


def test_fetch_catalog_propagates_upstream_http_errors():
    def info_error(request):
        if request.url.path == "/api/public/info/":
            return httpx.Response(500, text="boom")
        return httpx.Response(200, json=[])

    with pytest.raises(httpx.HTTPError):
        _fetch(info_error)

    def channel_error(request):
        if request.url.path == "/api/public/info/":
            return httpx.Response(200, json={"kolibri_version": "0.19.5"})
        return httpx.Response(503, text="boom")

    with pytest.raises(httpx.HTTPError):
        _fetch(channel_error)

    def redirect(request):
        if request.url.path == "/api/public/info/":
            return httpx.Response(302, headers={"location": "http://127.0.0.1/"})
        return httpx.Response(200, json=[])

    with pytest.raises(httpx.HTTPError):
        _fetch(redirect)


def test_fetch_catalog_propagates_timeouts_as_http_errors():
    def handler(request):
        raise httpx.ReadTimeout("slow", request=request)

    with pytest.raises(httpx.HTTPError):
        _fetch(handler)


@pytest.mark.parametrize(
    "probe_url",
    [
        "",
        "kolibri.test",
        "ftp://kolibri.test",
        "javascript:alert(1)",
        "//kolibri.test",
        "http://user:pass@kolibri.test",
        "http://kolibri.test?x=1",
        "http://kolibri.test#frag",
        "http://kolibri.test:99999",
        None,
    ],
)
def test_fetch_catalog_rejects_unsafe_probe_url_without_calling_upstream(probe_url):
    calls = []
    with pytest.raises(ValueError):
        _fetch(_upstream(calls=calls), probe_url=probe_url)
    assert calls == []


@pytest.mark.parametrize(
    "public_url", ["javascript:alert(1)", "//evil.com", "http://user:pass@k.test", ""]
)
def test_fetch_catalog_rejects_unsafe_public_url_without_calling_upstream(public_url):
    calls = []
    with pytest.raises(ValueError):
        _fetch(_upstream(calls=calls), public_url=public_url)
    assert calls == []


@pytest.mark.parametrize("timeout", [0, -1, float("nan"), float("inf"), "3", True, None])
def test_fetch_catalog_rejects_invalid_timeouts_without_calling_upstream(timeout):
    calls = []
    with pytest.raises(ValueError):
        _fetch(_upstream(calls=calls), timeout=timeout)
    assert calls == []


def test_fetch_catalog_bounds_excessive_timeout():
    version, channels = _fetch(_upstream(channels=[]), timeout=10_000)
    assert version == "0.19.5"
    assert channels == []


def test_fetch_catalog_rejects_oversized_payloads():
    def big_channels(request):
        if request.url.path == "/api/public/info/":
            return httpx.Response(200, json={"kolibri_version": "0.19.5"})
        return httpx.Response(200, content=b"x" * (5 * 1024 * 1024 + 1))

    with pytest.raises(ValueError, match="too large"):
        _fetch(big_channels)

    def big_info(request):
        return httpx.Response(200, content=b"x" * (64 * 1024 + 1))

    with pytest.raises(ValueError, match="too large"):
        _fetch(big_info)


def _api_client(tmp_path, handler):
    settings = Settings(
        _env_file=None,
        data_dir=tmp_path,
        kolibri_public_url=PUBLIC_URL,
        kolibri_probe_url=PUBLIC_URL,
    )
    upstream = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return TestClient(create_app(settings, upstream))


def test_channels_api_returns_503_for_invalid_upstream_json(tmp_path):
    def handler(request):
        if request.url.path == "/api/public/info/":
            return httpx.Response(200, json={"kolibri_version": "0.19.5"})
        if request.url.path == "/api/content/channel/":
            return httpx.Response(
                200, text="{not json", headers={"content-type": "application/json"}
            )
        return httpx.Response(200, text="Kolibri test service")

    with _api_client(tmp_path, handler) as client:
        response = client.get("/api/kolibri/channels")
    assert response.status_code == 503
    assert "usable catalog" in response.json()["detail"]


def test_channels_api_returns_503_for_upstream_server_error(tmp_path):
    def handler(request):
        if request.url.path == "/api/public/info/":
            return httpx.Response(500, text="boom")
        if request.url.path == "/api/content/channel/":
            return httpx.Response(200, json=[])
        return httpx.Response(200, text="Kolibri test service")

    with _api_client(tmp_path, handler) as client:
        response = client.get("/api/kolibri/channels")
    assert response.status_code == 503
    assert "usable catalog" in response.json()["detail"]


def test_services_falls_back_to_reachability_when_catalog_invalid(tmp_path):
    handler = _upstream(channels={"results": []})
    with _api_client(tmp_path, handler) as client:
        entry = client.get("/api/services").json()["kolibri"]
    assert entry == {"status": "reachable", "url": PUBLIC_URL}
