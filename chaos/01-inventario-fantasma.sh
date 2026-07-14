#!/usr/bin/env bash
set -euo pipefail

NS="ticket-system"

echo "[INFO] Pods de inventario antes del fallo:"
kubectl get pods -n "$NS" -o wide | grep inventario || true

POD_INV=$(kubectl get pods -n "$NS" -o wide | awk '/inventario/ && /pc-persona1/ {print $1; exit}')

if [ -z "$POD_INV" ]; then
  echo "[WARN] No encontré inventario en pc-persona1. Tomaré cualquier pod de inventario."
  POD_INV=$(kubectl get pods -n "$NS" -o wide | awk '/inventario/ {print $1; exit}')
fi

echo "[INFO] Eliminando pod de inventario: $POD_INV"
kubectl delete pod "$POD_INV" -n "$NS"

echo "[INFO] Estado después del fallo:"
kubectl get pods -n "$NS" -o wide | grep inventario || true
