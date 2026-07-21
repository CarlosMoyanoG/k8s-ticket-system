# Arquitectura Multi-Nodo

## Diagrama

```mermaid
flowchart LR
  subgraph tailscale["Red privada Tailscale"]
    subgraph p1["pc-persona1\nK3s server / control-plane\n100.81.223.82"]
      gw["API Gateway\nNodePort 30081"]
      fe["Frontend\nNodePort 30080"]
      db["Database\nPVC local-path"]
      pay["Pagos"]
      notif["Notificaciones"]
    end

    subgraph p2["pc-persona2-336714b0\nK3s agent / worker\n100.93.117.85"]
      res2["Reservas replica B"]
      inv2["Inventario replica B"]
    end

    res1["Reservas replica A"]
    inv1["Inventario replica A"]
  end

  fe --> gw
  gw --> res1
  gw --> res2
  res1 --> inv1
  res1 --> inv2
  res2 --> inv1
  res2 --> inv2
  res1 --> pay
  res2 --> pay
  res1 --> notif
  res2 --> notif
  inv1 --> db
  inv2 --> db
  res1 --> db
  res2 --> db
```

## Distribución esperada

- `api-gateway`, `frontend`, `pagos`, `notificaciones` y `database` pueden quedar en `pc-persona1`.
- `reservas` tiene `replicas: 2` con `podAntiAffinity` por `kubernetes.io/hostname`.
- `inventario` tiene `replicas: 2` con `podAntiAffinity` por `kubernetes.io/hostname`.
- Con ambos nodos `Ready`, una réplica de `reservas` y una de `inventario` deben caer en cada nodo.
- Con solo un nodo `Ready`, el scheduler dejará una réplica `Pending`, lo cual evidencia que el requisito multi-nodo no fue validado aún.

## Flujo de compra

1. El cliente entra por `frontend` o llama directo al `api-gateway`.
2. `api-gateway` reenvía `POST /api/comprar` a `reservas`.
3. `reservas` intenta reservar stock en `inventario`.
4. `inventario` centraliza disponibilidad en `database`.
5. Si hay stock, `reservas` invoca a `pagos`.
6. Si `pagos` falla o tarda, `reservas` libera inventario y responde error controlado.
7. Si `pagos` responde bien, `reservas` registra booking en `database`.
8. `reservas` intenta `notificaciones`; si falla, deja warning no crítico.

## Persistencia

- `database` usa `PersistentVolumeClaim` `database-pvc`.
- `storageClassName: local-path`.
- Montaje en `/data`.
- Archivo persistido: `/data/ticket-system.json`.
