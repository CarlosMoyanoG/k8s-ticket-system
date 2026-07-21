# Checklist para la Validación Final del Miércoles 22 de Julio de 2026

## Red y clúster

1. Abrir WSL de `Persona 1`.
2. Ejecutar `tailscale status`.
3. Confirmar que `Persona 2` aparece en la red Tailscale.
4. Si no aparece `Ready`, unir `Persona 2` con el comando documentado en el README.
5. Ejecutar:
   ```bash
   kubectl get nodes -o wide
   ```

## Despliegue

6. Aplicar manifests:
   ```bash
   kubectl apply -f k8s/
   kubectl wait --for=condition=available deployment --all -n ticket-system --timeout=240s
   ```
7. Verificar PVC:
   ```bash
   kubectl get pvc -n ticket-system
   ```
8. Verificar pods distribuidos:
   ```bash
   kubectl get pods -n ticket-system -o wide
   ```
9. Confirmar que `reservas` e `inventario` estén en nodos distintos.

## Validación funcional

10. Ejecutar compra normal:
    ```bash
    curl -X POST http://100.81.223.82:30081/api/comprar -H "Content-Type: application/json" -d '{"cliente":"validacion-manana","evento":"concierto-kubernetes","cantidad":1}'
    ```
11. Ejecutar:
    ```bash
    bash chaos/01-inventario-fantasma.sh
    bash chaos/02-pagos-lento.sh
    bash chaos/03-correo-perdido.sh
    bash chaos/04-diluvio-peticiones.sh 30 10
    ```
12. Capturar:
    - `kubectl get nodes -o wide`
    - `kubectl get pods -n ticket-system -o wide`
    - `kubectl get pvc -n ticket-system`
    - respuestas JSON de compra normal y chaos
    - logs de `reservas`

## Criterio honesto de cierre

- Si el `worker` sigue sin `Ready`, no afirmar validación multi-nodo completa.
- Si `podAntiAffinity` deja pods `Pending` con un solo nodo, mostrarlo como evidencia de que la prueba final depende de `Persona 2`.
