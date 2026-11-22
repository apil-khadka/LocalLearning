#!/usr/bin/env python3
"""Prepare a shareable local Phi-4 Mini Instruct demo."""

from __future__ import annotations

import ipaddress
import json
import os
import secrets
import shutil
import socket
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = ROOT / ".env"
ENV_EXAMPLE = ROOT / ".env.example"
ACCESS_FILE = ROOT / "private-local" / "phi4-demo-access.md"

MODEL_KEY = "phi-4-mini-instruct"
MODEL_HUB_ID = "microsoft/phi-4-mini@q4_k_m"
MODEL_IDENTIFIER = "phi-4-mini-instruct"
MODEL_PORT = 1234
PORTAL_PORT = 8090
STAFF_PORT = 8091


class SetupError(Exception):
    """A setup step could not finish safely."""


def run(command: list[str], *, capture_output: bool = False) -> str:
    try:
        result = subprocess.run(
            command,
            cwd=ROOT,
            check=True,
            text=True,
            capture_output=capture_output,
        )
    except FileNotFoundError as exc:
        raise SetupError(f"Required command is missing: {command[0]}") from exc
    except subprocess.CalledProcessError as exc:
        raise SetupError(
            f"Command failed ({exc.returncode}): {' '.join(command)}"
        ) from exc
    return result.stdout if capture_output else ""


def require_prerequisites() -> None:
    for executable, hint in (
        ("docker", "Install and start Docker Desktop or Docker Engine."),
        ("lms", "Install LM Studio, open it once, then run `lms` in a terminal."),
    ):
        if shutil.which(executable) is None:
            raise SetupError(f"{executable} is required. {hint}")
    run(["docker", "compose", "version"], capture_output=True)
    run(["docker", "info"], capture_output=True)


def shared_ipv4() -> str:
    override = os.environ.get("DEMO_BIND_IP", "").strip()
    if override:
        address = override
    else:
        # A UDP connect selects the default route without sending a packet.
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.connect(("192.0.2.1", 9))
                address = sock.getsockname()[0]
        except OSError as exc:
            raise SetupError(
                "Could not find a LAN IPv4 address. Set DEMO_BIND_IP to the server's "
                "reserved LAN address and rerun."
            ) from exc
    try:
        parsed = ipaddress.ip_address(address)
    except ValueError as exc:
        raise SetupError("DEMO_BIND_IP must be a valid IPv4 address.") from exc
    if parsed.version != 4 or parsed.is_loopback or parsed.is_unspecified or parsed.is_multicast:
        raise SetupError("DEMO_BIND_IP must be a usable, non-loopback IPv4 address.")
    return str(parsed)


def installed_phi_model() -> bool:
    output = run(["lms", "ls", "--llm", "--json"], capture_output=True)
    try:
        models = json.loads(output)
    except json.JSONDecodeError as exc:
        raise SetupError("LM Studio returned an unreadable model list.") from exc
    return any(isinstance(model, dict) and model.get("modelKey") == MODEL_KEY for model in models)


def ensure_model(bind_ip: str) -> str:
    if not installed_phi_model():
        print(f"Downloading {MODEL_HUB_ID} (Q4_K_M; about 2.5 GB).")
        run(["lms", "get", MODEL_HUB_ID, "--gguf", "-y"])
        if not installed_phi_model():
            raise SetupError(f"LM Studio did not install the expected {MODEL_KEY} model.")
    print(f"Loading {MODEL_KEY} in LM Studio.")
    run(
        [
            "lms",
            "load",
            MODEL_KEY,
            "--identifier",
            MODEL_IDENTIFIER,
            "--context-length",
            "8192",
            "-y",
        ]
    )

    model_url = f"http://{bind_ip}:{MODEL_PORT}/api/v1/models"
    if not http_ready(model_url, timeout=2):
        # Rebind an existing loopback-only LM Studio server for the Docker API.
        if http_ready(f"http://127.0.0.1:{MODEL_PORT}/api/v1/models", timeout=2):
            print("Rebinding the LM Studio server to the selected LAN interface.")
            run(["lms", "server", "stop"])
        print(f"Starting the LM Studio server on {bind_ip}:{MODEL_PORT}.")
        run(["lms", "server", "start", "--port", str(MODEL_PORT), "--bind", bind_ip])
        if not wait_http(model_url, timeout=90):
            raise SetupError(
                "LM Studio did not answer on the LAN address. Check its server status and "
                "host firewall, then rerun `make phi4-demo`."
            )
    return f"http://{bind_ip}:{MODEL_PORT}"


def http_ready(url: str, *, timeout: float = 3) -> bool:
    try:
        with urlopen(url, timeout=timeout) as response:
            return 200 <= response.status < 300
    except (HTTPError, URLError, TimeoutError, OSError):
        return False


def wait_http(url: str, *, timeout: int) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if http_ready(url, timeout=2):
            return True
        time.sleep(2)
    return False


def write_env(overrides: dict[str, str]) -> None:
    if ENV_FILE.exists():
        lines = ENV_FILE.read_text(encoding="utf-8").splitlines()
    else:
        lines = ENV_EXAMPLE.read_text(encoding="utf-8").splitlines()
    pending = dict(overrides)
    result: list[str] = []
    for line in lines:
        key, separator, _value = line.partition("=")
        name = key.strip()
        if separator and name in overrides:
            if name in pending:
                result.append(f"{name}={pending.pop(name)}")
        else:
            result.append(line)
    result.extend(f"{key}={value}" for key, value in pending.items())

    ENV_FILE.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(ENV_FILE, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as target:
        target.write("\n".join(result) + "\n")
    try:
        ENV_FILE.chmod(0o600)
    except OSError:
        pass


def request_json(
    url: str,
    *,
    payload: dict | None = None,
    headers: dict[str, str] | None = None,
    timeout: float = 10,
) -> dict:
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    request_headers = dict(headers or {})
    if payload is not None:
        request_headers["Content-Type"] = "application/json"
    request = Request(url, data=body, headers=request_headers)
    try:
        with urlopen(request, timeout=timeout) as response:
            value = json.loads(response.read())
    except HTTPError as exc:
        raise SetupError(f"The local service returned HTTP {exc.code} for {url}.") from exc
    except (URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
        raise SetupError(f"Could not reach the local service at {url}.") from exc
    if not isinstance(value, dict):
        raise SetupError(f"The local service returned an unexpected response for {url}.")
    return value


def write_access_note(bind_ip: str, setup_token: str) -> None:
    ACCESS_FILE.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    try:
        ACCESS_FILE.parent.chmod(0o700)
    except OSError:
        pass
    content = (
        "# Digital Himalaya local Phi-4 demo first-run access\n\n"
        f"Created: {datetime.now(UTC).isoformat(timespec='seconds')}\n\n"
        f"Student portal: http://{bind_ip}:{PORTAL_PORT}\n"
        f"Staff sign-in: http://{bind_ip}:{STAFF_PORT}/login\n"
        f"One-time school setup token: {setup_token}\n\n"
        "At first sign-in, enter this token and create the school's administrator account. "
        "The administrator username and password are chosen in the setup form.\n"
        f"Model: {MODEL_IDENTIFIER}\n"
    )
    descriptor = os.open(ACCESS_FILE, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as target:
        target.write(content)
    try:
        ACCESS_FILE.chmod(0o600)
    except OSError:
        pass


def provision() -> None:
    require_prerequisites()
    bind_ip = shared_ipv4()
    model_base_url = ensure_model(bind_ip)

    setup_token = secrets.token_urlsafe(48)
    write_env(
        {
            "AI_ENABLED": "true",
            "REQUIRE_AUTH": "true",
            "AUTH_COOKIE_SECURE": "false",
            "CHAT_PROVIDER": "lmstudio",
            "LMSTUDIO_BASE_URL": model_base_url,
            "LMSTUDIO_MODEL": MODEL_IDENTIFIER,
            "CHAT_REASONING_EFFORT": "",
            "ADMIN_TOKEN": setup_token,
            "PORTAL_BIND": bind_ip,
            "STAFF_BIND": bind_ip,
        }
    )

    compose_started = False
    first_run_setup_ready = False
    first_run_candidate = False
    portal = f"http://{bind_ip}:{PORTAL_PORT}"
    try:
        print("Building and starting the Digital Himalaya containers.")
        compose_started = True
        run(["docker", "compose", "up", "-d", "--build", "--wait"])

        if not wait_http(f"{portal}/api/health", timeout=180):
            raise SetupError("The portal did not become healthy within 3 minutes.")

        service_status = request_json(f"{portal}/api/services")
        expected_model = service_status.get("evaluation_config", {}).get("chat_model")
        model_status = service_status.get("dependencies", {}).get("chat_model")
        if expected_model != MODEL_IDENTIFIER or model_status != "ready":
            raise SetupError(
                "The app cannot reach the selected Phi-4 Mini Instruct model. "
                "Check LM Studio's LAN binding and the host firewall, then rerun."
            )

        auth_status = request_json(f"{portal}/api/auth/status")
        first_run_candidate = not auth_status.get("users_exist")
        if not first_run_candidate:
            # An existing school must not retain a bootstrap credential.
            write_env({"ADMIN_TOKEN": ""})
            run(["docker", "compose", "up", "-d", "--no-deps", "--force-recreate", "api"])
            ACCESS_FILE.unlink(missing_ok=True)
            if not wait_http(f"{portal}/api/health", timeout=90):
                raise SetupError("The API did not recover after removing the setup token.")
        final_status = request_json(f"{portal}/api/auth/status")
        if first_run_candidate and final_status.get("users_exist"):
            # Another operator may have completed first-run setup while this command ran.
            write_env({"ADMIN_TOKEN": ""})
            run(["docker", "compose", "up", "-d", "--no-deps", "--force-recreate", "api"])
            ACCESS_FILE.unlink(missing_ok=True)
            if not wait_http(f"{portal}/api/health", timeout=90):
                raise SetupError("The API did not recover after removing the setup token.")
            first_run_candidate = False
        elif not first_run_candidate and not final_status.get("users_exist"):
            raise SetupError("The existing school account status changed during setup.")
        first_run_setup_ready = first_run_candidate
    except Exception:
        write_env({"ADMIN_TOKEN": ""})
        if compose_started:
            try:
                run(
                    ["docker", "compose", "up", "-d", "--no-deps", "--force-recreate", "api"]
                )
            except SetupError:
                pass
        raise

    access_note_saved = False
    if first_run_setup_ready:
        try:
            write_access_note(bind_ip, setup_token)
            access_note_saved = True
        except OSError:
            print(
                "Could not save the private access note; the setup token will be printed below.",
                file=sys.stderr,
            )

    print("\nDigital Himalaya Phi-4 demo is ready.")
    print(f"Student portal: http://{bind_ip}:{PORTAL_PORT}")
    print(f"Staff sign-in:  http://{bind_ip}:{STAFF_PORT}/login")
    print(f"AI model:       {MODEL_IDENTIFIER}")
    if first_run_setup_ready:
        print("School setup is waiting for its first administrator.")
        print(f"One-time school setup token: {setup_token}")
        print("Enter this token on the first-run sign-in form, then choose the admin login.")
        if access_note_saved:
            print(f"Saved privately: {ACCESS_FILE.relative_to(ROOT)}")
        print("Share the setup token privately with the person creating the school account.")
    else:
        print("Existing accounts were found; no setup token was retained or displayed.")
    print("The portal and staff sign-in are reachable on this computer's LAN address.")


def main() -> int:
    try:
        provision()
    except SetupError as exc:
        print(f"Phi-4 demo setup failed: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nSetup interrupted. Rerun `make phi4-demo` to continue.", file=sys.stderr)
        return 130
    except OSError as exc:
        print(f"Phi-4 demo setup failed while accessing a local file: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
