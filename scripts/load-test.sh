#!/usr/bin/env bash
set -euo pipefail

URL="http://100.81.223.82:30081/api/comprar"
TOTAL="${1:-30}"

echo "Enviando $TOTAL compras concurrentes contra $URL"

seq 1 "$TOTAL" | xargs -I{} -P 10 sh -c '
  curl -s -X POST "'"$URL"'" \
    -H "Content-Type: application/json" \
    -d "{\"cliente\":\"carga-{}\",\"evento\":\"concierto-kubernetes\"}" \
  | grep -o "\"ok\": *[^,}]*" || true
'
