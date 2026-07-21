# Mapeo de Fallos, Inyección y Resiliencia

| Fallo | Tipo | Mecanismo de inyección | Mecanismo de resiliencia | Archivo / script | Estado |
|---|---|---|---|---|---|
| Inventario Fantasma | Disponibilidad | Escalar `deployment/inventario` a `0` | Error controlado y corte del flujo antes de cobrar | `apps/reservas/app.py`, `chaos/01-inventario-fantasma.sh` | Implementado |
| Pasarela Lenta | Latencia | `PAYMENT_DELAY_SECONDS=20` en `deployment/pagos` | Timeout, retry con backoff, compensación y circuit breaker simple | `apps/reservas/app.py`, `chaos/02-pagos-lento.sh` | Implementado |
| Diluvio de Peticiones | Sobrecarga | `curl` concurrente con `xargs -P` | Bulkhead con `threading.BoundedSemaphore` | `apps/reservas/app.py`, `chaos/04-diluvio-peticiones.sh`, `scripts/load-test.sh` | Implementado |
| Correo Perdido | Dependencia no crítica | Escalar `deployment/notificaciones` a `0` | Degradación no crítica con warning | `apps/reservas/app.py`, `chaos/03-correo-perdido.sh` | Implementado |
| Base de Datos Intermitente | Persistencia / red | No inyectado en vivo | Exposición de `persistencia=pendiente/no_guardado`; análisis técnico | `apps/reservas/app.py`, `docs/informe-tecnico-fallos-restantes.md` | Analizado |
| Condición de Carrera | Concurrencia / consistencia | No inyectado en vivo | Estado centralizado en DB con lock; análisis de solución de producción | `apps/database/app.py`, `docs/informe-tecnico-fallos-restantes.md` | Analizado |
