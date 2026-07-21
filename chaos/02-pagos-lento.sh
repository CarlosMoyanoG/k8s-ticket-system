#!/usr/bin/env bash
set -euo pipefail

NAMESPACE="${NAMESPACE:-ticket-system}"
GATEWAY_URL="${GATEWAY_URL:-http://100.81.223.82:30081}"
ORIGINAL_DELAY="${ORIGINAL_DELAY:-0}"
CHAOS_DELAY="${CHAOS_DELAY:-20}"

cleanup() {
  kubectl set env deployment/pagos -n "$NAMESPACE" PAYMENT_DELAY_SECONDS="$ORIGINAL_DELAY" >/dev/null 2>&1 || true
  kubectl rollout status deployment/pagos -n "$NAMESPACE" --timeout=180s >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "[1/6] Configurando pagos con retardo de $CHAOS_DELAY segundos"
kubectl set env deployment/pagos -n "$NAMESPACE" PAYMENT_DELAY_SECONDS="$CHAOS_DELAY"
kubectl rollout status deployment/pagos -n "$NAMESPACE" --timeout=180s

echo "[1.1/6] Verificando delay efectivo dentro del pod de pagos"
kubectl exec -n "$NAMESPACE" deployment/pagos -- python -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8080/health', timeout=10).read().decode())"

echo "[2/6] Compra de prueba 1 para forzar timeout y compensacion"
response1="$(curl -sS -X POST "$GATEWAY_URL/api/comprar" -H "Content-Type: application/json" -d '{"cliente":"chaos-pagos-1","evento":"concierto-kubernetes","cantidad":1}')"
echo "$response1"

if [[ "$response1" != *'"fase": "pagos"'* ]] || [[ "$response1" != *'"compensacion"'* ]]; then
  if [[ "$response1" == *'"fase": "gateway"'* ]] && [[ "$response1" == *'"error": "reservas_no_disponible"'* ]]; then
    echo "Diagnostico: api-gateway vencio antes de que reservas terminara los retries/compensacion de pagos." >&2
    echo "Revisa RESERVAS_TIMEOUT_SECONDS en api-gateway y reaplica k8s/ antes de repetir este chaos." >&2
  fi
  echo "La respuesta no muestra timeout/compensacion de pagos" >&2
  exit 1
fi

echo "[3/6] Compra de prueba 2 para evidenciar apertura rapida del circuito si aplica"
response2="$(curl -sS -X POST "$GATEWAY_URL/api/comprar" -H "Content-Type: application/json" -d '{"cliente":"chaos-pagos-2","evento":"concierto-kubernetes","cantidad":1}')"
echo "$response2"

echo "[4/6] Restaurando PAYMENT_DELAY_SECONDS=$ORIGINAL_DELAY"
kubectl set env deployment/pagos -n "$NAMESPACE" PAYMENT_DELAY_SECONDS="$ORIGINAL_DELAY"
kubectl rollout status deployment/pagos -n "$NAMESPACE" --timeout=180s

echo "[5/6] Estado del deployment de pagos"
kubectl get pods -n "$NAMESPACE" -l app=pagos -o wide

echo "[6/6] Comando de recuperacion sugerido"
echo "curl -X POST $GATEWAY_URL/api/comprar -H 'Content-Type: application/json' -d '{\"cliente\":\"post-chaos\",\"evento\":\"concierto-kubernetes\",\"cantidad\":1}'"
