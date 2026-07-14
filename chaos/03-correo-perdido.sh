#!/usr/bin/env bash
set -euo pipefail

NS="ticket-system"

echo "[INFO] Apagando Notificaciones"
kubectl scale deployment/notificaciones -n "$NS" --replicas=0
kubectl wait --for=delete pod -l app=notificaciones -n "$NS" --timeout=120s || true

echo "[INFO] Confirmando endpoints de notificaciones:"
kubectl get endpoints notificaciones -n "$NS"

echo "[INFO] Probando compra sin notificaciones"
curl -X POST http://100.81.223.82:30081/api/comprar \
  -H "Content-Type: application/json" \
  -d '{"cliente":"fallo-correo-perdido","evento":"concierto-kubernetes"}'

echo
echo "[INFO] Restaurando Notificaciones"
kubectl scale deployment/notificaciones -n "$NS" --replicas=1
kubectl wait --for=condition=available deployment/notificaciones -n "$NS" --timeout=180s
