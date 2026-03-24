#!/usr/bin/env bash
# Smoke test against a deployed API. Usage:
#   API_URL=https://your-service.onrender.com ./scripts/smoke_prod.sh
set -euo pipefail
API_URL="${API_URL:-}"
if [[ -z "$API_URL" ]]; then
  echo "Set API_URL to your backend base URL (no trailing slash), e.g."
  echo "  API_URL=https://gitlab-rag-api.onrender.com ./scripts/smoke_prod.sh"
  exit 1
fi
API_URL="${API_URL%/}"

echo "GET $API_URL/health"
curl -sfS "$API_URL/health" | head -c 500
echo ""
echo "OK: health passed"
