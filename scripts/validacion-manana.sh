#!/usr/bin/env bash
set -euo pipefail

NAMESPACE="${NAMESPACE:-ticket-system}"
GATEWAY_URL="${GATEWAY_URL:-http://100.81.223.82:30081}"

echo "[1/6] Nodes"
kubectl get nodes -o wide

echo "[2/6] Pods"
kubectl get pods -n "$NAMESPACE" -o wide

echo "[3/6] Services"
kubectl get svc -n "$NAMESPACE"

echo "[4/6] PVC"
kubectl get pvc -n "$NAMESPACE"

echo "[5/6] Endpoints"
kubectl get endpoints -n "$NAMESPACE"

echo "[6/6] Compra normal"
curl -sS -X POST "$GATEWAY_URL/api/comprar" \
  -H "Content-Type: application/json" \
  -d '{"cliente":"validacion-manana","evento":"concierto-kubernetes","cantidad":1}'
echo
