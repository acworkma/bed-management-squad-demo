#!/usr/bin/env bash
# Smoke test — verify the API is reachable and responding.
# Usage: ./scripts/smoke_test.sh [base_url]

set -euo pipefail

BASE_URL="${1:-http://localhost:8000}"

echo "==> Smoke test: GET ${BASE_URL}/api/state"

HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "${BASE_URL}/api/state")

if [ "$HTTP_CODE" -eq 200 ]; then
  echo "✅  /api/state returned 200 OK"
  exit 0
else
  echo "❌  /api/state returned HTTP ${HTTP_CODE}"
  exit 1
fi
