# Informe Técnico de Fallos Restantes

## 1. Base de Datos Intermitente

### Por qué ocurre

Una base de datos intermitente aparece cuando la red entre aplicación y almacenamiento entra y sale, o cuando el proceso acepta algunas escrituras y rechaza otras. En un flujo de compra, esto rompe la suposición de que reservar stock, cobrar y registrar el booking son pasos observables y persistentes.

### Relación con CAP, red y consistencia

- Si el enlace al almacenamiento se vuelve inestable, la aplicación enfrenta el clásico dilema entre disponibilidad y consistencia.
- Aceptar compras sin confirmar persistencia sube disponibilidad, pero degrada consistencia observada.
- Rechazar toda compra ante duda protege consistencia, pero empeora disponibilidad.

### Solución de producción

- usar una base de datos con transacciones reales;
- aplicar patrón `outbox` para separar confirmación de compra y efectos secundarios;
- persistir un estado `PENDING` antes de llamar a dependencias externas;
- reintentar con colas y reconciliación.

### Pseudocódigo

```text
begin transaction
  lock inventory row for event
  if stock < requested: rollback
  decrement stock
  insert booking(status="PENDING_PAYMENT")
commit

call payment gateway

begin transaction
  update booking(status="CONFIRMED" or "FAILED")
  if failed: restore stock
  append outbox event
commit
```

### Límite de la implementación actual

La implementación actual usa `database` HTTP simple con archivo JSON y `threading.Lock`. Si falla el registro final del booking, `reservas` responde con `persistencia.estado=pendiente` o `no_guardado`. Eso hace visible el problema, pero no reemplaza una base transaccional.

## 2. Condición de Carrera

### Por qué ocurre

La carrera aparece cuando dos compras compiten por el último asiento y ambas leen disponibilidad válida antes de que una escritura sea visible para la otra. En sistemas distribuidos, una réplica local por pod empeora esto porque cada proceso puede mantener su propio contador.

### Relación con CAP, red y concurrencia

- El problema nace en concurrencia y orden de observación, no solo en caída de nodos.
- Si se replica stock sin coordinación, se sacrifica consistencia por disponibilidad.
- Bajo partición o latencia, dos nodos pueden aceptar la misma unidad de inventario si no existe un punto de serialización.

### Solución de producción

- mantener inventario en un único motor consistente con bloqueo por fila;
- usar `SELECT ... FOR UPDATE`, CAS atómico o `UPDATE ... WHERE stock > 0`;
- asociar compras a claves idempotentes;
- procesar confirmación de pago mediante saga u orquestación transaccional.

### Pseudocódigo

```text
function reserveSeat(eventId, customerId):
  begin transaction
    row = select stock from inventory where event_id = eventId for update
    if row.stock == 0:
      rollback
      return SOLD_OUT
    update inventory set stock = stock - 1 where event_id = eventId
    insert reservation(event_id, customer_id, status="RESERVED")
  commit
  return RESERVED
```

### Límite de la implementación actual

La implementación actual mejora respecto a un contador por réplica porque centraliza stock en `database` y protege escrituras con `threading.Lock`. Eso cubre la demo y reduce la carrera dentro del servicio `database`, pero sigue siendo una aproximación educativa, no un control transaccional de producción.
