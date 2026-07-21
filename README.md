# Sistema de Reservas de Entradas en Kubernetes Multi-Nodo

Este repositorio deja listo un sistema de reservas de entradas sobre Kubernetes para la práctica de Sistemas Distribuidos. La validación operativa está pensada para el clúster K3s de `pc-persona1` como `server/control-plane` y `pc-persona2-336714b0` como `worker`, unidos por Tailscale.

## Contexto y arquitectura

- `Persona 1`: Windows + Ubuntu WSL2, nodo `pc-persona1`, K3s server/control-plane, Tailscale `100.81.223.82`.
- `Persona 2`: Windows + Ubuntu WSL2, nodo `pc-persona2-336714b0`, K3s agent/worker, Tailscale `100.93.117.85`.
- `Persona 2` no crea otro clúster. Solo se une al clúster existente de `Persona 1`.
- Namespace de trabajo: `ticket-system`.
- Despliegue principal: `kubectl apply -f k8s/`.

Comando de unión de `Persona 2` con placeholder de token:

```bash
curl -sfL https://get.k3s.io | K3S_URL=https://100.81.223.82:6443 K3S_TOKEN='PEGAR_TOKEN_AQUI' INSTALL_K3S_EXEC="agent --node-name pc-persona2 --with-node-id --node-ip $(tailscale ip -4) --flannel-iface tailscale0" sh -
```

Con `--with-node-id`, el nombre visible del worker puede quedar como `pc-persona2-<id>`, por ejemplo `pc-persona2-336714b0`.

## Componentes obligatorios

Los seis componentes exigidos están implementados y desplegados como servicios separados:

1. `API Gateway`: [apps/api-gateway/app.py](apps/api-gateway/app.py)
2. `Servicio de Reservas/Core`: [apps/reservas/app.py](apps/reservas/app.py)
3. `Servicio de Inventario`: [apps/inventario/app.py](apps/inventario/app.py)
4. `Servicio de Pagos externo/simulado`: [apps/pagos/app.py](apps/pagos/app.py)
5. `Servicio de Notificaciones`: [apps/notificaciones/app.py](apps/notificaciones/app.py)
6. `Base de Datos con persistencia`: [apps/database/app.py](apps/database/app.py)

Adicionalmente existe un `frontend` de demo en [apps/frontend/app.py](apps/frontend/app.py).

## Cómo desplegar

Aplicación completa:

```bash
kubectl apply -f k8s/
kubectl wait --for=condition=available deployment --all -n ticket-system --timeout=240s
```

Validaciones base:

```bash
kubectl get nodes -o wide
kubectl get pods -n ticket-system -o wide
kubectl get svc -n ticket-system
kubectl get pvc -n ticket-system
kubectl get endpoints -n ticket-system
```

Puertos de demo:

- `Frontend`: `http://100.81.223.82:30080`
- `API Gateway`: `http://100.81.223.82:30081`

Si prefieres `port-forward`:

```bash
kubectl port-forward -n ticket-system svc/api-gateway 8081:8080
kubectl port-forward -n ticket-system svc/frontend 8080:8080
```

Compra normal:

```bash
curl -X POST http://100.81.223.82:30081/api/comprar \
  -H "Content-Type: application/json" \
  -d '{"cliente":"demo","evento":"concierto-kubernetes","cantidad":1}'
```

## Resiliencia implementada de verdad

### 1. Inventario Fantasma

- Mecanismo de defensa: manejo controlado de error en `reservas`.
- Implementación: [apps/reservas/app.py](apps/reservas/app.py)
- Flujo: si `inventario` no responde, `reservas` corta el flujo, no llama a `pagos` y devuelve:
  - `ok=false`
  - `fase=inventario`
  - `error=inventario_no_disponible`
  - `accion=error_controlado_sin_cobro`
- Inyección: [chaos/01-inventario-fantasma.sh](chaos/01-inventario-fantasma.sh)

### 2. Pasarela Lenta

- Mecanismo de defensa:
  - timeout real hacia `pagos`;
  - reintento con backoff simple;
  - compensación liberando inventario;
  - circuit breaker simple de pagos, abierto tras 3 fallos consecutivos y con reapertura después de 30 segundos.
- Implementación: [apps/reservas/app.py](apps/reservas/app.py)
- Inyección: [chaos/02-pagos-lento.sh](chaos/02-pagos-lento.sh)

### 3. Correo Perdido

- Mecanismo de defensa: degradación no crítica; la compra puede quedar `ok=true` aunque falle la notificación.
- Implementación: [apps/reservas/app.py](apps/reservas/app.py)
- Inyección: [chaos/03-correo-perdido.sh](chaos/03-correo-perdido.sh)

### 4. Diluvio de Peticiones

- Mecanismo de defensa: bulkhead simple con `threading.BoundedSemaphore`.
- Implementación: [apps/reservas/app.py](apps/reservas/app.py)
- Comportamiento: cuando se supera el límite concurrente devuelve `429` con `fase=bulkhead`.
- Inyección: [chaos/04-diluvio-peticiones.sh](chaos/04-diluvio-peticiones.sh)

## Fallos analizados pero no implementados como chaos

### 5. Base de Datos Intermitente

- Estado: análisis técnico documentado.
- Documento: [docs/informe-tecnico-fallos-restantes.md](docs/informe-tecnico-fallos-restantes.md)
- Limitación actual: si falla el registro final de booking, `reservas` expone `persistencia.estado=pendiente` o `no_guardado`; no se oculta el problema.

### 6. Condición de Carrera

- Estado: análisis técnico documentado.
- Documento: [docs/informe-tecnico-fallos-restantes.md](docs/informe-tecnico-fallos-restantes.md)
- Nota: la disponibilidad de asientos sí se centralizó en `database` con lock y PVC, lo que mejora consistencia para el inventario replicado. Aun así, el análisis de carrera documenta cómo se endurecería esto en producción.

## Tabla de seis fallos

| Fallo | Estado | Defensa principal | Script / Documento |
|---|---|---|---|
| Inventario Fantasma | Implementado | Error controlado sin cobro | `chaos/01-inventario-fantasma.sh` |
| Pasarela Lenta | Implementado | Timeout + retry + compensación + circuit breaker | `chaos/02-pagos-lento.sh` |
| Diluvio de Peticiones | Implementado | Bulkhead con semaphore | `chaos/04-diluvio-peticiones.sh` |
| Correo Perdido | Implementado | Degradación no crítica | `chaos/03-correo-perdido.sh` |
| Base de Datos Intermitente | Analizado | Persistencia pendiente/no_guardado | `docs/informe-tecnico-fallos-restantes.md` |
| Condición de Carrera | Analizado | Centralización + endurecimiento transaccional futuro | `docs/informe-tecnico-fallos-restantes.md` |

## Archivos Kubernetes principales

- Namespace: [k8s/00-namespace.yaml](k8s/00-namespace.yaml)
- ConfigMaps con código montado: [k8s/01-configmaps.yaml](k8s/01-configmaps.yaml)
- PVC de base de datos: [k8s/08-database-pvc.yaml](k8s/08-database-pvc.yaml)
- API Gateway: [k8s/10-api-gateway.yaml](k8s/10-api-gateway.yaml)
- Frontend: [k8s/11-frontend.yaml](k8s/11-frontend.yaml)
- Reservas: [k8s/12-reservas.yaml](k8s/12-reservas.yaml)
- Inventario: [k8s/13-inventario.yaml](k8s/13-inventario.yaml)
- Pagos: [k8s/14-pagos.yaml](k8s/14-pagos.yaml)
- Notificaciones: [k8s/15-notificaciones.yaml](k8s/15-notificaciones.yaml)
- Database: [k8s/16-database.yaml](k8s/16-database.yaml)

## Scripts de chaos y soporte

- [chaos/01-inventario-fantasma.sh](chaos/01-inventario-fantasma.sh)
- [chaos/02-pagos-lento.sh](chaos/02-pagos-lento.sh)
- [chaos/03-correo-perdido.sh](chaos/03-correo-perdido.sh)
- [chaos/04-diluvio-peticiones.sh](chaos/04-diluvio-peticiones.sh)

## Resultado esperado de cada fallo implementado

- `Inventario Fantasma`: compra rechazada sin cobro.
- `Pasarela Lenta`: compra cancelada con compensación; inventario liberado.
- `Correo Perdido`: compra completada con `warning=notificacion_fallida_no_critica`.
- `Diluvio de Peticiones`: parte del tráfico recibe `429` o error controlado por bulkhead.
