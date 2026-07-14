import json
import os
import random
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

FAIL_RATE = float(os.getenv("NOTIFICATION_FAIL_RATE", "0"))

class Handler(BaseHTTPRequestHandler):
    def send_json(self, status, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/health":
            self.send_json(200, {"service": "notificaciones", "status": "ok"})
        else:
            self.send_json(404, {"error": "not_found"})

    def do_POST(self):
        if self.path != "/notificar":
            self.send_json(404, {"error": "not_found"})
            return

        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length).decode("utf-8") or "{}")

        if random.random() < FAIL_RATE:
            self.send_json(503, {"ok": False, "error": "servicio_notificaciones_inactivo"})
            return

        print(f"Correo simulado enviado para reserva {body.get('reserva_id')}", flush=True)
        self.send_json(200, {
            "ok": True,
            "estado": "correo_simulado_enviado",
            "reserva_id": body.get("reserva_id")
        })

if __name__ == "__main__":
    port = int(os.getenv("PORT", "8080"))
    print(f"notificaciones escuchando en puerto {port}", flush=True)
    ThreadingHTTPServer(("", port), Handler).serve_forever()
