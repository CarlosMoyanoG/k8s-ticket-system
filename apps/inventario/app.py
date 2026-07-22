import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib import error, request
from urllib.parse import quote


PORT = int(os.environ.get("PORT", "8080"))
DATABASE_URL = os.environ.get("DATABASE_URL", "http://database:8080")
TIMEOUT = float(os.environ.get("DATABASE_TIMEOUT_SECONDS", "2"))


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


def call_database(path, method="GET", payload=None):
    body = None
    headers = {}
    if payload is not None:
        body = json.dumps(payload, ensure_ascii=True).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = request.Request(f"{DATABASE_URL}{path}", data=body, headers=headers, method=method)
    try:
        with request.urlopen(req, timeout=TIMEOUT) as resp:
            response_body = resp.read().decode("utf-8")
            return resp.status, json.loads(response_body) if response_body else {}
    except error.HTTPError as exc:
        response_body = exc.read().decode("utf-8")
        parsed = json.loads(response_body) if response_body else {}
        return exc.code, parsed


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        return

    def do_GET(self):
        if self.path == "/health":
            try:
                status, payload = call_database("/health")
                return send_json(self, 200 if status == 200 else 503, {"status": "ok", "database": payload})
            except Exception as exc:
                return send_json(self, 503, {"status": "error", "database": "unreachable", "reason": str(exc)})
        if self.path.startswith("/inventario/"):
            event = self.path.split("/inventario/", 1)[1]
            try:
                status, payload = call_database(f"/events/{quote(event)}")
                return send_json(self, status, payload)
            except Exception as exc:
                return send_json(self, 503, {"ok": False, "error": "database_no_disponible", "reason": str(exc)})
        return send_json(self, 404, {"ok": False, "error": "ruta_no_encontrada"})

    def do_POST(self):
        body = parse_body(self)
        try:
            if self.path == "/inventario/reservar":
                status, payload = call_database("/inventory/reserve", method="POST", payload=body)
                return send_json(self, status, payload)
            if self.path == "/inventario/liberar":
                status, payload = call_database("/inventory/release", method="POST", payload=body)
                return send_json(self, status, payload)
            if self.path == "/inventario/recargar":
                status, payload = call_database("/inventory/restock", method="POST", payload=body)
                return send_json(self, status, payload)
        except Exception as exc:
            return send_json(self, 503, {"ok": False, "error": "database_no_disponible", "reason": str(exc)})
        return send_json(self, 404, {"ok": False, "error": "ruta_no_encontrada"})


if __name__ == "__main__":
    server = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    print(f"inventario escuchando en {PORT}", flush=True)
    server.serve_forever()
