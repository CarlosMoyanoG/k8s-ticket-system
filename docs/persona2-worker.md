# Persona 2 como Worker Node

`Persona 2` no debe crear otro clúster. Su rol es únicamente actuar como `worker node` del clúster K3s de `Persona 1`.

## Comprobaciones en Persona 2

```bash
tailscale ip -4
ping 100.81.223.82
curl -k https://100.81.223.82:6443/version
systemctl status k3s-agent --no-pager
```

## Comando de unión

```bash
curl -sfL https://get.k3s.io | K3S_URL=https://100.81.223.82:6443 K3S_TOKEN='PEGAR_TOKEN_AQUI' INSTALL_K3S_EXEC="agent --node-name pc-persona2 --with-node-id --node-ip $(tailscale ip -4) --flannel-iface tailscale0" sh -
```

## Qué debe verificar Persona 1

```bash
kubectl get nodes -o wide
kubectl describe node pc-persona2-336714b0
```

Si el nombre no es exactamente `pc-persona2-336714b0`, usar el que devuelva `kubectl get nodes`, porque `--with-node-id` agrega sufijo dinámico.

## Regla operativa

- misma red Tailscale;
- mismo clúster K3s;
- no desplegar otro proyecto en `Persona 2`;
- dejar recursos de esta práctica programables por el scheduler.
