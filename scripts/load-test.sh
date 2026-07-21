#!/usr/bin/env bash
set -euo pipefail

TOTAL="${1:-30}"
CONCURRENCY="${2:-10}"
GATEWAY_URL="${GATEWAY_URL:-http://100.81.223.82:30081}"
TMP_DIR="$(mktemp -d)"

cleanup() {
  rm -rf "$TMP_DIR"
}
trap cleanup EXIT

fire_request() {
  local index="$1"
  curl -sS -X POST "$GATEWAY_URL/api/comprar" \
    -H "Content-Type: application/json" \
    -d "{\"cliente\":\"load-$index\",\"evento\":\"concierto-kubernetes\",\"cantidad\":1}" \
    -o "$TMP_DIR/$index.json" || echo '{"ok": false, "error": "curl_error"}' > "$TMP_DIR/$index.json"
}

export -f fire_request
export GATEWAY_URL TMP_DIR

seq "$TOTAL" | xargs -I{} -P "$CONCURRENCY" bash -lc 'fire_request "$@"' _ {}

echo "total=$TOTAL"
echo "ok_true=$(grep -l '\"ok\": true' "$TMP_DIR"/*.json 2>/dev/null | wc -l | tr -d ' ')"
echo "ok_false=$(grep -l '\"ok\": false' "$TMP_DIR"/*.json 2>/dev/null | wc -l | tr -d ' ')"
echo "bulkhead=$(grep -l 'demasiadas_solicitudes_concurrentes' "$TMP_DIR"/*.json 2>/dev/null | wc -l | tr -d ' ')"
