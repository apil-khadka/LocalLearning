#!/bin/sh
set -eu

public_port=${PORTAL_PUBLIC_PORT:-8090}
staff_port=${PORTAL_STAFF_PORT:-8091}

valid_port() {
  case "$1" in
    ''|*[!0-9]*) return 1 ;;
  esac
  [ "$1" -ge 1 ] && [ "$1" -le 65535 ]
}

if ! valid_port "$public_port" || ! valid_port "$staff_port"; then
  echo "PORTAL_PUBLIC_PORT and PORTAL_STAFF_PORT must be integers from 1 to 65535." >&2
  exit 1
fi

printf 'window.DIGITAL_HIMALAYA_CONFIG = { publicPort: %s, staffPort: %s };\n' \
  "$public_port" "$staff_port" > /usr/share/nginx/html/runtime-config.js
