import json
import os
import random
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

DELAY_SECONDS = float(os.getenv("PAYMENT_DELAY_SECONDS", "0"))
FAIL_RATE = float(os.getenv("PAYMENT_FAIL_RATE", "0"))

class Handler(BaseHTTPRequestHandler):
    def send_json(self, status, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/health":
            self.send_json(200, {"service": "pagos", "status": "ok", "delay_seconds": DELAY_SECONDS})
        else:
            self.send_json(404, {"error": "not_found"})

    def do_POST(self):
        if self.path != "/pagar":
            self.send_json(404, {"error": "not_found"})
            return

        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length).decode("utf-8") or "{}")

        if DELAY_SECONDS > 0:
            time.sleep(DELAY_SECONDS)

        if random.random() < FAIL_RATE:
            self.send_json(503, {"ok": False, "error": "pago_rechazado_o_servicio_externo_fallando"})
            return

        self.send_json(200, {
            "ok": True,
            "reserva_id": body.get("reserva_id"),
            "estado": "pago_aprobado",
            "monto": body.get("monto", 100)
        })

if __name__ == "__main__":
    port = int(os.getenv("PORT", "8080"))
    print(f"pagos escuchando en puerto {port}", flush=True)
    ThreadingHTTPServer(("", port), Handler).serve_forever()
