#!/usr/bin/env bash
set -euo pipefail

TOTAL="${1:-30}"
CONCURRENCY="${2:-10}"
NAMESPACE="${NAMESPACE:-ticket-system}"
GATEWAY_URL="${GATEWAY_URL:-http://100.81.223.82:30081}"
WORKDIR="$(mktemp -d)"

cleanup() {
  rm -rf "$WORKDIR"
}
trap cleanup EXIT

run_one() {
  local index="$1"
  local output="$WORKDIR/response-$index.json"
  curl -sS -X POST "$GATEWAY_URL/api/comprar" \
    -H "Content-Type: application/json" \
    -d "{\"cliente\":\"carga-$index\",\"evento\":\"concierto-kubernetes\",\"cantidad\":1}" \
    -o "$output" || echo '{"ok": false, "error": "curl_error"}' > "$output"
}

export -f run_one
export WORKDIR GATEWAY_URL

echo "[1/3] Lanzando $TOTAL solicitudes con concurrencia $CONCURRENCY"
seq "$TOTAL" | xargs -I{} -P "$CONCURRENCY" bash -lc 'run_one "$@"' _ {}

ok_true="$(grep -l '"ok": true' "$WORKDIR"/*.json 2>/dev/null | wc -l | tr -d ' ')"
ok_false="$(grep -l '"ok": false' "$WORKDIR"/*.json 2>/dev/null | wc -l | tr -d ' ')"
bulkhead="$(grep -l 'demasiadas_solicitudes_concurrentes' "$WORKDIR"/*.json 2>/dev/null | wc -l | tr -d ' ')"
otros="$(( TOTAL - ok_true - ok_false ))"

echo "[2/3] Resumen"
echo "total_solicitadas=$TOTAL"
echo "ok_true=$ok_true"
echo "ok_false=$ok_false"
echo "errores_bulkhead_429=$bulkhead"
echo "errores_otros=$otros"

echo "[3/3] Pods despues de la prueba"
kubectl get pods -n "$NAMESPACE" -l app=reservas -o wide
