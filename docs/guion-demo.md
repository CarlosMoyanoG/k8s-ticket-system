# Guion de Demo de 10 a 15 Minutos

## Minuto 0-2

- Quién: `Persona 1`
- Comando:
  ```bash
  kubectl get nodes -o wide
  kubectl get pods -n ticket-system -o wide
  ```
- Qué se espera:
  - ver `pc-persona1` y `pc-persona2-336714b0` o `pc-persona2-<id>` en `Ready`;
  - ver `reservas` e `inventario` distribuidos entre nodos.
- Evidencia a capturar:
  - captura de `kubectl get nodes -o wide`;
  - captura de `kubectl get pods -n ticket-system -o wide`.

## Minuto 2-3

- Quién: `Persona 2`
- Comando:
  ```bash
  tailscale ip -4
  systemctl status k3s-agent --no-pager
  ```
- Qué se espera:
  - confirmar IP Tailscale;
  - confirmar que `k3s-agent` está activo.
- Evidencia a capturar:
  - salida del estado del agente.

## Minuto 3-4

- Quién: `Persona 1`
- Comando:
  ```bash
  kubectl get svc -n ticket-system
  curl -X POST http://100.81.223.82:30081/api/comprar -H "Content-Type: application/json" -d '{"cliente":"demo","evento":"concierto-kubernetes","cantidad":1}'
  ```
- Qué se espera:
  - compra exitosa;
  - `ok=true`.
- Evidencia a capturar:
  - respuesta JSON;
  - si se quiere, `kubectl logs -n ticket-system deployment/reservas --tail=50`.

## Minuto 4-6

- Quién: `Persona 1`
- Comando:
  ```bash
  bash chaos/01-inventario-fantasma.sh
  ```
- Qué se espera:
  - endpoints de inventario vacíos;
  - compra fallida con `fase=inventario`;
  - restauración automática.
- Evidencia a capturar:
  - respuesta JSON del fallo;
  - pods restaurados.

## Minuto 6-8

- Quién: `Persona 1`
- Comando:
  ```bash
  bash chaos/02-pagos-lento.sh
  ```
- Qué se espera:
  - timeout o fallo controlado en `pagos`;
  - compensación de inventario;
  - restauración de `PAYMENT_DELAY_SECONDS=0`.
- Evidencia a capturar:
  - respuesta de la compra;
  - `kubectl describe deployment pagos -n ticket-system | grep -n PAYMENT_DELAY_SECONDS`.

## Minuto 8-10

- Quién: `Persona 1`
- Comando:
  ```bash
  bash chaos/03-correo-perdido.sh
  ```
- Qué se espera:
  - compra sigue `ok=true`;
  - warning de notificación.
- Evidencia a capturar:
  - respuesta JSON;
  - pods restaurados de `notificaciones`.

## Minuto 10-12

- Quién: `Persona 1`
- Comando:
  ```bash
  bash chaos/04-diluvio-peticiones.sh 30 10
  ```
- Qué se espera:
  - mezcla de `ok=true` y rechazos por bulkhead;
  - servicio estable al final.
- Evidencia a capturar:
  - resumen del script;
  - pods de `reservas` después de la carga.

## Minuto 12-15

- Quién: `Persona 1` y `Persona 2`
- Comando:
  ```bash
  kubectl get pvc -n ticket-system
  kubectl get endpoints -n ticket-system
  ```
- Qué se espera:
  - PVC `Bound`;
  - endpoints operativos tras restauración.
- Evidencia a capturar:
  - `kubectl get pvc`;
  - `kubectl get endpoints`.
