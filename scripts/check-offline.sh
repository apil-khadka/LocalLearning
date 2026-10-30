#!/usr/bin/env bash
set -euo pipefail
portal_url="${1:-http://127.0.0.1:8090}"
curl --fail --silent --show-error --max-time 15 "${portal_url}/api/health"
printf '\n'
curl --fail --silent --show-error --max-time 20 "${portal_url}/api/services"
printf '\n'
curl --fail --silent --show-error --max-time 10 "${portal_url}/api/textbooks"
printf '\n'
cat <<'TEXT'
These checks prove HTTP access only, not offline acceptance.
Disconnect WAN and disable cellular data, then follow docs/DEMO_SCRIPT.md.
Verify the actual models, article, lesson, citations and restart on school hardware.
TEXT
