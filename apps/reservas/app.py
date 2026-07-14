import json
import os
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

INVENTARIO_URL = os.getenv("INVENTARIO_URL", "http://inventario:8080")
PAGOS_URL = os.getenv("PAGOS_URL", "http://pagos:8080")
NOTIFICACIONES_URL = os.getenv("NOTIFICACIONES_URL", "http://notificaciones:8080")
DATABASE_URL = os.getenv("DATABASE_URL", "http://database:8080")

def request_json(method, url, payload=None, timeout=4):
    data = None
    headers = {"Content-Type": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")

    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.status, json.loads(resp.read().decode("utf-8"))

class Handler(BaseHTTPRequestHandler):
    def send_json(self, status, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/health":
            self.send_json(200, {"service": "reservas", "status": "ok"})
        elif self.path == "/status":
            try:
                _, inv = request_json("GET", f"{INVENTARIO_URL}/asientos", timeout=2)
                self.send_json(200, {"ok": True, "inventario": inv})
            except Exception as exc:
                self.send_json(503, {"ok": False, "error": "inventario_no_disponible", "detail": str(exc)})
        else:
            self.send_json(404, {"error": "not_found"})

    def do_POST(self):
        if self.path != "/reservar":
            self.send_json(404, {"error": "not_found"})
            return

        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length).decode("utf-8") or "{}")
        cliente = body.get("cliente", "anonimo")
        evento = body.get("evento", "evento-demo")
        reserva_id = f"res-{int(time.time() * 1000)}"

        try:
            _, inv = request_json("POST", f"{INVENTARIO_URL}/reservar", {
                "reserva_id": reserva_id,
                "evento": evento,
                "cantidad": 1
            }, timeout=3)
        except Exception as exc:
            self.send_json(503, {
                "ok": False,
                "fase": "inventario",
                "error": "inventario_no_disponible",
                "accion": "error_controlado_sin_cobro",
                "detail": str(exc)
            })
            return

        try:
            _, pago = request_json("POST", f"{PAGOS_URL}/pagar", {
                "reserva_id": reserva_id,
                "cliente": cliente,
                "monto": 100
            }, timeout=5)
        except Exception as exc:
            try:
                request_json("POST", f"{INVENTARIO_URL}/liberar", {
                    "reserva_id": reserva_id,
                    "cantidad": 1
                }, timeout=2)
            except Exception:
                pass

            self.send_json(504, {
                "ok": False,
                "fase": "pagos",
                "error": "pago_lento_o_no_disponible",
                "accion": "inventario_liberado_y_error_controlado",
                "detail": str(exc)
            })
            return

        try:
            request_json("POST", f"{DATABASE_URL}/guardar", {
                "reserva_id": reserva_id,
                "cliente": cliente,
                "evento": evento,
                "pago": pago,
                "inventario": inv
            }, timeout=3)
            db_status = "guardado"
        except Exception as exc:
            db_status = f"no_guardado: {exc}"

        try:
            _, notif = request_json("POST", f"{NOTIFICACIONES_URL}/notificar", {
                "reserva_id": reserva_id,
                "cliente": cliente,
                "evento": evento
            }, timeout=2)
            notif_status = notif
        except Exception as exc:
            notif_status = {
                "ok": False,
                "warning": "notificacion_fallida_no_critica",
                "detail": str(exc)
            }

        self.send_json(201, {
            "ok": True,
            "reserva_id": reserva_id,
            "mensaje": "reserva_creada",
            "inventario": inv,
            "pago": pago,
            "persistencia": db_status,
            "notificacion": notif_status
        })

if __name__ == "__main__":
    port = int(os.getenv("PORT", "8080"))
    print(f"reservas escuchando en puerto {port}", flush=True)
    ThreadingHTTPServer(("", port), Handler).serve_forever()
