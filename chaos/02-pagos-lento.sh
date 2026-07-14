#!/usr/bin/env bash
set -euo pipefail

NS="ticket-system"

echo "[INFO] Inyectando latencia de 20 segundos en Pagos"
kubectl set env deployment/pagos -n "$NS" PAYMENT_DELAY_SECONDS=20
kubectl rollout status deployment/pagos -n "$NS" --timeout=180s

echo "[INFO] Probando compra con pagos lento"
curl -X POST http://100.81.223.82:30081/api/comprar \
  -H "Content-Type: application/json" \
  -d '{"cliente":"fallo-pagos-lento","evento":"concierto-kubernetes"}'

echo
echo "[INFO] Restaurando Pagos"
kubectl set env deployment/pagos -n "$NS" PAYMENT_DELAY_SECONDS=0
kubectl rollout status deployment/pagos -n "$NS" --timeout=180s
