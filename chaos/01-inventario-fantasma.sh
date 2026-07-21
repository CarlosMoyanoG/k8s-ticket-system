#!/usr/bin/env bash
set -euo pipefail

NAMESPACE="${NAMESPACE:-ticket-system}"
GATEWAY_URL="${GATEWAY_URL:-http://100.81.223.82:30081}"
RESTORE_REPLICAS="${RESTORE_REPLICAS:-2}"

cleanup() {
  kubectl scale deployment/inventario -n "$NAMESPACE" --replicas="$RESTORE_REPLICAS" >/dev/null 2>&1 || true
  kubectl rollout status deployment/inventario -n "$NAMESPACE" --timeout=180s >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "[1/7] Pods iniciales de inventario"
kubectl get pods -n "$NAMESPACE" -l app=inventario -o wide

echo "[2/7] Escalando inventario a 0"
kubectl scale deployment/inventario -n "$NAMESPACE" --replicas=0

echo "[3/7] Esperando eliminacion de pods de inventario"
kubectl wait --for=delete pod -l app=inventario -n "$NAMESPACE" --timeout=180s || true

echo "[4/7] Verificando endpoints"
kubectl get endpoints inventario -n "$NAMESPACE"

echo "[5/7] Ejecutando compra de prueba"
response="$(curl -sS -X POST "$GATEWAY_URL/api/comprar" -H "Content-Type: application/json" -d '{"cliente":"chaos-inventario","evento":"concierto-kubernetes","cantidad":1}')"
echo "$response"

if [[ "$response" != *'"fase": "inventario"'* ]] || [[ "$response" != *'"accion": "error_controlado_sin_cobro"'* ]]; then
  echo "La respuesta no evidencia el control esperado del fallo de inventario" >&2
  exit 1
fi

echo "[6/7] Restaurando inventario a $RESTORE_REPLICAS replicas"
kubectl scale deployment/inventario -n "$NAMESPACE" --replicas="$RESTORE_REPLICAS"
kubectl rollout status deployment/inventario -n "$NAMESPACE" --timeout=180s

echo "[7/7] Pods restaurados y distribucion actual"
kubectl get pods -n "$NAMESPACE" -l app=inventario -o wide
