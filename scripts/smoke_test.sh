#!/usr/bin/env bash
# Smoke test — verify the API is reachable and responding.
# Usage: ./scripts/smoke_test.sh [base_url]

set -euo pipefail

BASE_URL="${1:-http://localhost:8000}"
FAILED=0

check_endpoint() {
  local path="$1"
  local url="${BASE_URL}${path}"
  echo "==> GET ${url}"
  HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 "${url}")
  if [ "$HTTP_CODE" -eq 200 ]; then
    echo "    ✅ ${path} returned 200 OK"
  else
    echo "    ❌ ${path} returned HTTP ${HTTP_CODE}"
    FAILED=1
  fi
}

check_endpoint "/health"
check_endpoint "/api/state"
check_endpoint "/api/events"

if [ "$FAILED" -ne 0 ]; then
  echo ""
  echo "❌ Smoke test FAILED — one or more endpoints did not return 200."
  exit 1
fi

echo ""
echo "✅ All smoke tests passed."
exit 0
