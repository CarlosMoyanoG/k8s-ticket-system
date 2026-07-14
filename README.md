# Sistema de Reservas de Entradas Resiliente sobre Kubernetes

## 1. Contexto de la práctica

Este proyecto implementa una arquitectura simplificada de venta de entradas para eventos, desplegada sobre un clúster Kubernetes multi-nodo. El objetivo es provocar fallos controlados sobre infraestructura distribuida y demostrar mecanismos de resiliencia que permitan al sistema recuperarse o degradarse de forma controlada.

La práctica se desarrolló sobre dos computadoras Windows usando Ubuntu WSL2, Tailscale y K3s.

---

## 2. Integrantes y roles

| Integrante | Rol en la infraestructura | Responsabilidades principales |
|---|---|---|
| Persona 1 | Nodo control-plane / servidor K3s | Creación del clúster, despliegue de manifiestos, API Gateway, demo principal |
| Persona 2 | Nodo worker / agente K3s | Unión al clúster, ejecución distribuida de pods, apoyo en pruebas de fallo |

---

## 3. Arquitectura general

El sistema está compuesto por los siguientes servicios:

1. **Frontend**: interfaz HTML para ejecutar compras desde navegador.
2. **API Gateway**: punto de entrada para clientes.
3. **Servicio de Reservas**: coordina el flujo de compra.
4. **Servicio de Inventario**: verifica y descuenta disponibilidad de asientos.
5. **Servicio de Pagos**: simula un proveedor externo de pagos.
6. **Servicio de Notificaciones**: simula envío de correo de confirmación.
7. **Database**: servicio simulado de persistencia de reservas.

Flujo principal:

```text
Usuario
  ↓
Frontend
  ↓
API Gateway
  ↓
Reservas
  ├── Inventario
  ├── Pagos
  ├── Database
  └── Notificaciones
```

---

## 4. Infraestructura Kubernetes

El clúster se ejecuta con K3s sobre dos nodos conectados mediante Tailscale:

```text
pc-persona1
Rol: control-plane
IP Tailscale: 100.81.223.82

pc-persona2
Rol: worker
IP Tailscale: 100.93.117.85
```

Verificación del clúster:

```bash
kubectl get nodes -o wide
```

Resultado esperado:

```text
NAME                  STATUS   ROLES           INTERNAL-IP
pc-persona1           Ready    control-plane   100.81.223.82
pc-persona2-xxxxxxx   Ready    <none>          100.93.117.85
```

---

## 5. Distribución de componentes entre nodos

Los componentes críticos `reservas` e `inventario` se ejecutan con dos réplicas y se distribuyen entre ambos nodos usando reglas de anti-affinity.

Verificación:

```bash
kubectl get pods -n ticket-system -o wide
```

Resultado esperado:

```text
reservas-...      Running   pc-persona1
reservas-...      Running   pc-persona2-xxxxxxx

inventario-...    Running   pc-persona1
inventario-...    Running   pc-persona2-xxxxxxx
```

Esto demuestra que la infraestructura no depende de un único contenedor local, sino de dos nodos Kubernetes reales.

---

## 6. Estructura del repositorio

```text
.
├── apps
│   ├── api-gateway
│   │   └── app.py
│   ├── database
│   │   └── app.py
│   ├── frontend
│   │   └── index.html
│   ├── inventario
│   │   └── app.py
│   ├── notificaciones
│   │   └── app.py
│   ├── pagos
│   │   └── app.py
│   └── reservas
│       └── app.py
│
├── chaos
│   ├── 01-inventario-fantasma.sh
│   ├── 02-pagos-lento.sh
│   ├── 03-correo-perdido.sh
│   └── 04-diluvio-peticiones.sh
│
├── docs
├── k8s
│   ├── 00-namespace.yaml
│   ├── 01-configmaps.yaml
│   ├── 10-frontend.yaml
│   ├── 11-api-gateway.yaml
│   ├── 12-reservas.yaml
│   ├── 13-inventario.yaml
│   ├── 14-pagos.yaml
│   ├── 15-notificaciones.yaml
│   └── 16-database.yaml
│
├── scripts
│   └── load-test.sh
│
└── README.md
```

---

## 7. Despliegue

### 7.1 Crear recursos Kubernetes

Desde la raíz del proyecto:

```bash
kubectl apply -f k8s/
```

Esperar disponibilidad:

```bash
kubectl wait --for=condition=available deployment --all -n ticket-system --timeout=240s
```

Verificar pods:

```bash
kubectl get pods -n ticket-system -o wide
```

Verificar servicios:

```bash
kubectl get svc -n ticket-system
```

---

## 8. Acceso a la aplicación

El frontend se expone mediante `port-forward`:

Terminal 1:

```bash
kubectl port-forward --address 0.0.0.0 -n ticket-system svc/frontend 30080:80
```

Terminal 2:

```bash
kubectl port-forward --address 0.0.0.0 -n ticket-system svc/api-gateway 30081:8080
```

Abrir en navegador:

```text
http://localhost:30080
```

También se puede probar el API Gateway directamente:

```bash
curl -X POST http://100.81.223.82:30081/api/comprar \
  -H "Content-Type: application/json" \
  -d '{"cliente":"demo","evento":"concierto-kubernetes"}'
```

Respuesta esperada:

```json
{
  "ok": true,
  "mensaje": "reserva_creada"
}
```

---

## 9. Catálogo de fallos y mecanismos técnicos

| # | Fallo | Tipo | Mecanismo de inyección | Estado |
|---|---|---|---|---|
| 1 | Inventario Fantasma | Disponibilidad | Eliminación de pod de `inventario` | Implementado |
| 2 | Pasarela Lenta | Latencia | Variable `PAYMENT_DELAY_SECONDS=20` en `pagos` | Implementado |
| 3 | Diluvio de Peticiones | Sobrecarga | Script de carga concurrente con `curl` y `xargs` | Implementado |
| 4 | Base de Datos Intermitente | Conectividad | Análisis teórico | No implementado |
| 5 | Correo Perdido | Fallo no crítico | Escalado de `notificaciones` a cero réplicas | Implementado |
| 6 | Condición de Carrera | Consistencia | Análisis teórico | No implementado |

---

## 10. Mecanismos de resiliencia implementados

### 10.1 Inventario Fantasma

**Fallo provocado:**  
Se elimina un pod de `inventario` durante la operación del sistema.

**Defensa implementada:**

- Deployment con dos réplicas.
- Kubernetes Service para balancear tráfico.
- Anti-affinity para distribuir réplicas entre nodos.
- Reemplazo automático del pod eliminado por parte del Deployment.

**Código relacionado:**

```text
k8s/13-inventario.yaml
chaos/01-inventario-fantasma.sh
```

**Comando de prueba:**

```bash
./chaos/01-inventario-fantasma.sh
```

**Resultado esperado:**  
El sistema mantiene disponibilidad porque queda una réplica activa de `inventario` en el otro nodo.

---

### 10.2 Pasarela Lenta

**Fallo provocado:**  
El servicio de pagos tarda 20 segundos en responder.

**Defensa implementada:**

- Timeout en el servicio `reservas`.
- Error controlado si pagos no responde.
- Compensación: liberación del inventario si el pago falla o excede el tiempo permitido.

**Código relacionado:**

```text
apps/reservas/app.py
apps/pagos/app.py
chaos/02-pagos-lento.sh
```

Fragmento lógico de defensa:

```text
Reservas intenta reservar inventario.
Reservas llama a Pagos con timeout.
Si Pagos no responde:
    Reservas libera inventario.
    Reservas devuelve error controlado.
```

**Comando de prueba:**

```bash
./chaos/02-pagos-lento.sh
```

**Resultado esperado:**  
La operación no queda colgada indefinidamente. El sistema responde con error controlado y se evita cobrar una reserva incompleta.

---

### 10.3 Correo Perdido

**Fallo provocado:**  
El servicio de notificaciones queda sin pods activos.

**Defensa implementada:**

- El fallo de notificaciones se considera no crítico.
- La reserva y el pago se completan aunque el correo falle.
- El sistema devuelve un warning en la respuesta.

**Código relacionado:**

```text
apps/reservas/app.py
apps/notificaciones/app.py
chaos/03-correo-perdido.sh
```

Respuesta esperada:

```json
{
  "ok": true,
  "mensaje": "reserva_creada",
  "notificacion": {
    "ok": false,
    "warning": "notificacion_fallida_no_critica"
  }
}
```

**Comando de prueba:**

```bash
./chaos/03-correo-perdido.sh
```

**Resultado esperado:**  
La compra se completa exitosamente aunque no se pueda enviar el correo.

---

### 10.4 Diluvio de Peticiones

**Fallo provocado:**  
Se envían múltiples compras concurrentes al API Gateway.

**Defensa implementada:**

- Réplicas distribuidas de `reservas`.
- Réplicas distribuidas de `inventario`.
- Kubernetes Service como balanceador interno.
- Manejo controlado de respuestas desde el API.

**Código relacionado:**

```text
scripts/load-test.sh
chaos/04-diluvio-peticiones.sh
k8s/12-reservas.yaml
k8s/13-inventario.yaml
```

**Comando de prueba:**

```bash
./chaos/04-diluvio-peticiones.sh 30
```

O:

```bash
./scripts/load-test.sh 30
```

**Resultado esperado:**  
El sistema atiende múltiples solicitudes concurrentes sin que los pods colapsen. Si alguna solicitud falla, debe hacerlo con respuesta controlada.

---

## 11. Relación con la rúbrica

### Bloque A — Infraestructura y Experimentación

| Dimensión | Evidencia en el proyecto |
|---|---|
| Despliegue Multi-Nodo y Arquitectura | Clúster K3s con dos nodos, servicios desplegados en Kubernetes, pods distribuidos entre `pc-persona1` y `pc-persona2`. |
| Implementación de Mecanismos de Resiliencia | Código en `apps/reservas/app.py`, manifiestos en `k8s/`, scripts en `chaos/`. |
| Demo en Vivo y Evidencia de Recuperación | Frontend funcional, pruebas por `curl`, scripts de fallos, logs y estado de pods. |

### Bloque B — Análisis Técnico y Documentación

| Dimensión | Evidencia en el proyecto |
|---|---|
| Rigor Teórico de Fallos Analizados | Análisis de Base de Datos Intermitente y Condición de Carrera. |
| Calidad de Solución Propuesta | Pseudocódigo de solución para DB intermitente y condición de carrera. |
| Documentación y Claridad | README, estructura de carpetas, comandos reproducibles y guion de demo. |

## 12. Estado final

El sistema demuestra una arquitectura distribuida y resiliente sobre Kubernetes con:

```text
- Dos nodos reales conectados por Tailscale.
- Componentes desplegados mediante manifiestos Kubernetes.
- Reservas e Inventario replicados entre nodos.
- Frontend operativo.
- Cuatro fallos provocados en vivo.
- Mecanismos de defensa implementados y documentados.
- Dos fallos adicionales analizados teóricamente.
```
