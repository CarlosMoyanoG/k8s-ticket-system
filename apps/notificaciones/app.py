import json
import os
import random
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


PORT = int(os.environ.get("PORT", "8080"))


def fail_rate():
    return float(os.environ.get("NOTIFICATION_FAIL_RATE", "0"))


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
                {"status": "ok", "notification_fail_rate": fail_rate()},
            )
        return send_json(self, 404, {"ok": False, "error": "ruta_no_encontrada"})

    def do_POST(self):
        if self.path != "/notificar":
            return send_json(self, 404, {"ok": False, "error": "ruta_no_encontrada"})
        body = parse_body(self)
        time.sleep(0.1)
        if random.random() < fail_rate():
            return send_json(
                self,
                503,
                {
                    "ok": False,
                    "error": "notificacion_fallida",
                    "cliente": body.get("cliente"),
                },
            )
        return send_json(
            self,
            200,
            {
                "ok": True,
                "mensaje": "notificacion_enviada",
                "cliente": body.get("cliente"),
            },
        )


if __name__ == "__main__":
    server = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    print(f"notificaciones escuchando en {PORT}", flush=True)
    server.serve_forever()
