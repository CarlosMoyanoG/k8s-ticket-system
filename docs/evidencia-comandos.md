# Comandos de Evidencia

## Estado base

```bash
kubectl get nodes -o wide
kubectl get pods -n ticket-system -o wide
kubectl get svc -n ticket-system
kubectl get pvc -n ticket-system
kubectl get endpoints -n ticket-system
kubectl logs -n ticket-system deployment/reservas --tail=100
kubectl logs -n ticket-system deployment/inventario --tail=100
```

## Compra normal

```bash
curl -X POST http://100.81.223.82:30081/api/comprar \
  -H "Content-Type: application/json" \
  -d '{"cliente":"evidencia","evento":"concierto-kubernetes","cantidad":1}'
```

Capturar:

- JSON completo de respuesta.
- `kubectl get pods -n ticket-system -o wide`.

## Chaos 1: Inventario Fantasma

```bash
bash chaos/01-inventario-fantasma.sh
kubectl get endpoints inventario -n ticket-system
```

Capturar:

- endpoints de inventario durante el fallo;
- respuesta con `fase=inventario`;
- pods restaurados.

## Chaos 2: Pagos Lento

```bash
bash chaos/02-pagos-lento.sh
kubectl logs -n ticket-system deployment/reservas --tail=100
```

Capturar:

- respuesta con compensación;
- variable `PAYMENT_DELAY_SECONDS=20` durante la prueba;
- restauración posterior.

## Chaos 3: Correo Perdido

```bash
bash chaos/03-correo-perdido.sh
kubectl get endpoints notificaciones -n ticket-system
```

Capturar:

- endpoints vacíos;
- `ok=true` con warning.

## Chaos 4: Diluvio de Peticiones

```bash
bash chaos/04-diluvio-peticiones.sh 30 10
kubectl get pods -n ticket-system -l app=reservas -o wide
```

Capturar:

- resumen del script;
- cantidad de `429` o rechazos controlados;
- estabilidad final de pods.
