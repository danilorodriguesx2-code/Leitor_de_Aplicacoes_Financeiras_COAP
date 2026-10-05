#!/usr/bin/env bash
set -euo pipefail

URL="${1:-http://127.0.0.1:8520/}"
EXPECTED="${EXPECTED_STATUS:-200}"

status=$(curl --silent --show-error --max-time "${TIMEOUT_SECONDS:-10}" \
  --output /dev/null --write-out '%{http_code}' "$URL")

if [[ "$status" != "$EXPECTED" ]]; then
  printf 'Health check failed: %s returned HTTP %s, expected %s\n' "$URL" "$status" "$EXPECTED" >&2
  exit 1
fi

printf 'Health check OK: %s returned HTTP %s\n' "$URL" "$status"
