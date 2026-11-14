"""Read-only Kolibri course-catalog client.

Uses Kolibri's unauthenticated content APIs, which the bundled 0.19.x
service exposes without a session: ``/api/public/info/`` for the server
version and ``/api/content/channel/`` for locally imported channel
metadata. No credentials are sent, and no Kolibri accounts, classes, or
progress records are read or written.

Upstream payloads are untrusted: channel entries are reduced to a fixed
field whitelist, identifiers and URLs are validated before use, and any
structural problem fails closed with ``ValueError`` or ``httpx.HTTPError``
so callers can report the catalog as unavailable instead of serving
partially sanitized data.
"""

from __future__ import annotations

import math
import re
from typing import Any
from urllib.parse import urlsplit

import httpx

_CHANNEL_ID = re.compile(r"[a-f0-9]{32}", re.IGNORECASE)
_VERSION = re.compile(r"[0-9A-Za-z][0-9A-Za-z.+-]{0,31}")
_LANG_CODE = re.compile(r"[A-Za-z]{2,3}(?:-[A-Za-z0-9]{2,8})*")
_CONTROL_CHARS = re.compile(r"[\x00-\x1f\x7f-\x9f]")
_INVISIBLE_CHARS = re.compile("[\u200b-\u200f\u202a-\u202e\u2066-\u2069\u2060\ufeff]")
_MAX_CHANNELS = 200
_MAX_COUNT = 1_000_000
_MAX_INFO_BYTES = 64 * 1024
_MAX_CHANNEL_BYTES = 5 * 1024 * 1024
_MAX_TIMEOUT_SECONDS = 30.0
_MAX_TEXT_INPUT = 20_000


def _normalized_id(value: Any) -> str | None:
    if not isinstance(value, str) or not _CHANNEL_ID.fullmatch(value):
        return None
    return value.lower()


def _safe_base_url(value: Any) -> str:
    """Return a credential-free HTTP(S) base URL or raise ``ValueError``.

    Rejects whitespace/control characters, backslashes, credentials,
    queries, fragments, dot segments, and missing hosts so a configured
    or upstream-influenced value can never become a ``javascript:``,
    protocol-relative, or credential-bearing URL.
    """
    if not isinstance(value, str) or not value.strip():
        raise ValueError("Kolibri is not configured.")
    candidate = value.strip()
    if (
        "\\" in candidate
        or any(char.isspace() for char in candidate)
        or any(ord(char) < 32 or ord(char) == 127 for char in candidate)
    ):
        raise ValueError("Invalid Kolibri URL.")
    try:
        parsed = urlsplit(candidate)
        # Accessing .port validates range/format and raises ValueError.
        _ = parsed.port
    except ValueError as exc:
        raise ValueError("Invalid Kolibri URL.") from exc
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or "//" in parsed.path
        or any(segment in {".", ".."} for segment in parsed.path.split("/"))
    ):
        raise ValueError("Invalid Kolibri URL.")
    return candidate.rstrip("/")


def learn_url(public_url: str, root_id: str) -> str:
    """Deep link to a channel's Learn page from a validated root node id.

    Raises ``ValueError`` when either input cannot form a safe HTTP(S)
    URL; callers that cannot produce a safe link must omit it.
    """
    root = _normalized_id(root_id)
    if root is None:
        raise ValueError("Invalid Kolibri channel root id.")
    base = _safe_base_url(public_url)
    return f"{base}/en/learn/#/topics/c/{root}"


def _text(value: Any, limit: int) -> str:
    if not isinstance(value, str):
        return ""
    bounded = value[:_MAX_TEXT_INPUT]
    cleaned = _CONTROL_CHARS.sub(" ", _INVISIBLE_CHARS.sub("", bounded))
    return " ".join(cleaned.split())[:limit]


def _count(value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return 0
    return min(value, _MAX_COUNT)


def _lang_code(value: Any) -> str:
    code = _text(value, 16)
    return code if _LANG_CODE.fullmatch(code) else ""


def public_channel(entry: Any, public_url: str) -> dict | None:
    """Sanitize one Kolibri channel entry; return None when unusable."""
    if not isinstance(entry, dict):
        return None
    identity = _normalized_id(entry.get("id"))
    root = _normalized_id(entry.get("root"))
    name = _text(entry.get("name"), 200)
    if identity is None or root is None or not name:
        return None
    total_resources = _count(entry.get("total_resource_count"))
    available = entry.get("available") is True and total_resources > 0
    try:
        url = learn_url(public_url, root) if available else None
    except ValueError:
        return None
    return {
        "id": identity,
        "name": name,
        "description": _text(entry.get("description"), 2000),
        "version": _count(entry.get("version")),
        "lang_code": _lang_code(entry.get("lang_code")),
        "lang_name": _text(entry.get("lang_name"), 64),
        "total_resources": total_resources,
        "available": available,
        "learn_url": url,
    }


def public_version(payload: Any) -> str | None:
    """Extract a safe Kolibri version string from /api/public/info/."""
    if not isinstance(payload, dict):
        return None
    version = payload.get("kolibri_version")
    if not isinstance(version, str):
        return None
    version = version.strip()
    return version if _VERSION.fullmatch(version) else None


def _validated_timeout(value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ValueError("Invalid Kolibri timeout.")
    timeout = float(value)
    if not math.isfinite(timeout) or timeout <= 0:
        raise ValueError("Invalid Kolibri timeout.")
    return min(timeout, _MAX_TIMEOUT_SECONDS)


async def _get_json(client: httpx.AsyncClient, url: str, timeout: float, max_bytes: int) -> Any:
    response = await client.get(url, timeout=timeout, follow_redirects=False)
    if response.status_code != 200:
        # Raises httpx.HTTPStatusError (an HTTPError) for error statuses;
        # the explicit ValueError covers any other non-200 status.
        response.raise_for_status()
        raise ValueError(f"Kolibri returned HTTP {response.status_code}.")
    if len(response.content) > max_bytes:
        raise ValueError("Kolibri response is too large.")
    try:
        return response.json()
    except ValueError as exc:
        raise ValueError("Kolibri returned invalid JSON.") from exc


async def fetch_catalog(
    client: httpx.AsyncClient, probe_url: str, public_url: str, timeout: float
) -> tuple[str | None, list[dict]]:
    """Fetch (version, channels) through the server-reachable Kolibri address.

    Deep links are built from the browser-reachable public URL. Raises
    httpx.HTTPError or ValueError when Kolibri does not answer with usable
    JSON; callers decide how to report that failure.
    """
    probe_base = _safe_base_url(probe_url)
    public_base = _safe_base_url(public_url)
    bounded_timeout = _validated_timeout(timeout)
    info_payload = await _get_json(
        client, f"{probe_base}/api/public/info/", bounded_timeout, _MAX_INFO_BYTES
    )
    version = public_version(info_payload)
    entries = await _get_json(
        client, f"{probe_base}/api/content/channel/", bounded_timeout, _MAX_CHANNEL_BYTES
    )
    if not isinstance(entries, list):
        raise ValueError("Kolibri returned an invalid channel list.")
    channels: list[dict] = []
    seen: set[str] = set()
    for entry in entries[:_MAX_CHANNELS]:
        channel = public_channel(entry, public_base)
        if channel is None or channel["id"] in seen:
            continue
        seen.add(channel["id"])
        channels.append(channel)
    channels.sort(key=lambda item: item["name"].casefold())
    return version, channels
