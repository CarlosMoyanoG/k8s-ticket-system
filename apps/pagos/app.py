import json
import os
import random
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


PORT = int(os.environ.get("PORT", "8080"))


def payment_delay():
    return float(os.environ.get("PAYMENT_DELAY_SECONDS", "0"))


def fail_rate():
    return float(os.environ.get("PAYMENT_FAIL_RATE", "0"))


def send_json(handler, status, payload):
    data = json.dumps(payload, ensure_ascii=True).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", str(len(data)))
    handler.end_headers()
    handler.wfile.write(data)


def parse_body(handler):
    length = int(handler.headers.get("Content-Length", "0"))
    raw = handler.rfile.read(length) if length > 0 else b"{}"
    return json.loads(raw.decode("utf-8")) if raw else {}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        return

    def do_GET(self):
        if self.path == "/health":
            return send_json(
                self,
                200,
                {
                    "status": "ok",
                    "payment_delay_seconds": payment_delay(),
                    "payment_fail_rate": fail_rate(),
                },
            )
        return send_json(self, 404, {"ok": False, "error": "ruta_no_encontrada"})

    def do_POST(self):
        if self.path != "/pagar":
            return send_json(self, 404, {"ok": False, "error": "ruta_no_encontrada"})
        body = parse_body(self)
        delay = payment_delay()
        if delay > 0:
            time.sleep(delay)
        if random.random() < fail_rate():
            return send_json(
                self,
                503,
                {
                    "ok": False,
                    "error": "pago_rechazado",
                    "evento": body.get("evento"),
                },
            )
        return send_json(
            self,
            200,
            {
                "ok": True,
                "transaccion": f"pay-{int(time.time() * 1000)}",
                "evento": body.get("evento"),
                "cliente": body.get("cliente"),
            },
        )


if __name__ == "__main__":
    server = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    print(f"pagos escuchando en {PORT}", flush=True)
    server.serve_forever()
