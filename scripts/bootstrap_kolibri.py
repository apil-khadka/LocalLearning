"""Provision the bundled Kolibri demo facility once for local development."""

from __future__ import annotations

import os
import stat
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PASSWORD_FILE = ROOT / "private-local" / "kolibri-admin-password"
COMPOSE_EXEC = ["docker", "compose", "exec", "-T", "kolibri"]
FACILITY_STATUS_SCRIPT = (
    "from kolibri.core.auth.models import Facility; "
    "print('DH_KOLIBRI_PROVISIONED=' + str(Facility.objects.exists()))"
)
PROVISION_SCRIPT = """
import sys
from django.core.management import call_command
from kolibri.core.auth.models import Facility

if Facility.objects.exists():
    print("Kolibri already has a facility; leaving existing data unchanged.")
else:
    password = sys.stdin.readline().rstrip("\\r\\n")
    if len(password) < 16:
        raise RuntimeError("The local Kolibri admin password must be at least 16 characters.")
    call_command(
        "provisiondevice",
        facility="Digital Himalaya Dev School",
        superusername="devadmin",
        superuserpassword=password,
        preset="formal",
        language_id="en",
        interactive=False,
    )
    print("Created the Digital Himalaya Dev School facility and devadmin account.")
"""


def compose(
    *args: str, input_text: str | None = None
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [*COMPOSE_EXEC, *args],
        check=False,
        capture_output=True,
        text=True,
        timeout=20,
        input=input_text,
    )


def wait_for_kolibri() -> None:
    probe = (
        "from urllib.request import urlopen; "
        "urlopen('http://127.0.0.1:8080/en/setup/', timeout=3)"
    )
    deadline = time.monotonic() + 90
    while time.monotonic() < deadline:
        result = compose("python", "-c", probe)
        if result.returncode == 0:
            return
        time.sleep(2)
    raise SystemExit("Kolibri did not become ready within 90 seconds.")


def facility_exists() -> bool:
    result = compose("kolibri", "manage", "shell", "-c", FACILITY_STATUS_SCRIPT)
    if result.returncode:
        raise SystemExit(
            result.stderr or "Could not inspect the Kolibri facility state."
        )
    for line in result.stdout.splitlines():
        if line.strip() == "DH_KOLIBRI_PROVISIONED=True":
            return True
        if line.strip() == "DH_KOLIBRI_PROVISIONED=False":
            return False
    raise SystemExit("Kolibri did not report its facility state.")


def read_dev_password() -> str:
    if not PASSWORD_FILE.is_file():
        raise SystemExit(
            "Kolibri is unconfigured. Create the ignored local file "
            "private-local/kolibri-admin-password with your dev admin password, "
            "then rerun `make education-up`. See docs/KOLIBRI_GUIDE.md."
        )

    if os.name == "posix" and stat.S_IMODE(PASSWORD_FILE.stat().st_mode) & 0o077:
        raise SystemExit("Set private-local/kolibri-admin-password permissions to 600.")

    password = PASSWORD_FILE.read_text(encoding="utf-8").rstrip("\r\n")
    if "\n" in password or "\r" in password or len(password) < 16:
        raise SystemExit(
            "The local Kolibri admin password must be one line and 16+ characters."
        )
    return password


def main() -> int:
    wait_for_kolibri()
    if facility_exists():
        print("Kolibri is already provisioned; no existing data was changed.")
        return 0

    password = read_dev_password()
    result = compose(
        "kolibri",
        "manage",
        "shell",
        "-c",
        PROVISION_SCRIPT,
        input_text=f"{password}\n",
    )
    if result.returncode:
        print(
            "Kolibri provisioning failed. Review `docker compose logs kolibri` "
            "for details; the password was not printed.",
            file=sys.stderr,
        )
        return result.returncode
    print(result.stdout.strip())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
