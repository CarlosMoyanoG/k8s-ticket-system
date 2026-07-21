#!/usr/bin/env bash
set -euo pipefail

NAMESPACE="${NAMESPACE:-ticket-system}"
GATEWAY_URL="${GATEWAY_URL:-http://100.81.223.82:30081}"
RESTORE_REPLICAS="${RESTORE_REPLICAS:-1}"

cleanup() {
  kubectl scale deployment/notificaciones -n "$NAMESPACE" --replicas="$RESTORE_REPLICAS" >/dev/null 2>&1 || true
  kubectl rollout status deployment/notificaciones -n "$NAMESPACE" --timeout=180s >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "[1/7] Pods iniciales de notificaciones"
kubectl get pods -n "$NAMESPACE" -l app=notificaciones -o wide

echo "[2/7] Escalando notificaciones a 0"
kubectl scale deployment/notificaciones -n "$NAMESPACE" --replicas=0

echo "[3/7] Esperando eliminacion de pods"
kubectl wait --for=delete pod -l app=notificaciones -n "$NAMESPACE" --timeout=180s || true

echo "[4/7] Verificando endpoints"
kubectl get endpoints notificaciones -n "$NAMESPACE"

echo "[5/7] Ejecutando compra"
response="$(curl -sS -X POST "$GATEWAY_URL/api/comprar" -H "Content-Type: application/json" -d '{"cliente":"chaos-notificaciones","evento":"concierto-kubernetes","cantidad":1}')"
echo "$response"

if [[ "$response" != *'"ok": true'* ]] || [[ "$response" != *'"warning": "notificacion_fallida_no_critica"'* ]]; then
  echo "La respuesta no muestra degradacion no critica de notificaciones" >&2
  exit 1
fi

echo "[6/7] Restaurando notificaciones"
kubectl scale deployment/notificaciones -n "$NAMESPACE" --replicas="$RESTORE_REPLICAS"
kubectl rollout status deployment/notificaciones -n "$NAMESPACE" --timeout=180s

echo "[7/7] Pods restaurados"
kubectl get pods -n "$NAMESPACE" -l app=notificaciones -o wide
