import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib import error, request


PORT = int(os.environ.get("PORT", "8080"))
RESERVAS_URL = os.environ.get("RESERVAS_URL", "http://reservas:8080")
INVENTARIO_URL = os.environ.get("INVENTARIO_URL", "http://inventario:8080")
TIMEOUT = float(os.environ.get("RESERVAS_TIMEOUT_SECONDS", "18"))


def send_cors_headers(handler):
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
    handler.send_header("Access-Control-Allow-Headers", "Content-Type")


def send_json(handler, status, payload):
    data = json.dumps(payload, ensure_ascii=True).encode("utf-8")
    handler.send_response(status)
    send_cors_headers(handler)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", str(len(data)))
    handler.end_headers()
    handler.wfile.write(data)


def parse_body(handler):
    length = int(handler.headers.get("Content-Length", "0"))
    raw = handler.rfile.read(length) if length > 0 else b"{}"
    return json.loads(raw.decode("utf-8")) if raw else {}


def proxy_purchase(payload):
    return proxy_json(RESERVAS_URL, "/comprar", method="POST", payload=payload)


def proxy_json(base_url, path, method="GET", payload=None, timeout=TIMEOUT):
    body = None
    headers = {}
    if payload is not None:
        body = json.dumps(payload, ensure_ascii=True).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = request.Request(f"{base_url}{path}", data=body, headers=headers, method=method)
    try:
        with request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
            return resp.status, json.loads(raw) if raw else {}
    except error.HTTPError as exc:
        raw = exc.read().decode("utf-8")
        return exc.code, json.loads(raw) if raw else {}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        return

    def do_OPTIONS(self):
        self.send_response(204)
        send_cors_headers(self)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self):
        if self.path == "/health":
            return send_json(
                self,
                200,
                {"status": "ok", "upstream": {"reservas": RESERVAS_URL, "inventario": INVENTARIO_URL}},
            )
        if self.path.startswith("/api/inventario/"):
            event = self.path.split("/api/inventario/", 1)[1]
            try:
                status, response = proxy_json(INVENTARIO_URL, f"/inventario/{event}")
                return send_json(self, status, response)
            except Exception as exc:
                return send_json(
                    self,
                    503,
                    {
                        "ok": False,
                        "fase": "gateway",
                        "error": "inventario_no_disponible",
                        "detalle": str(exc),
                    },
                )
        return send_json(self, 404, {"ok": False, "error": "ruta_no_encontrada"})

    def do_POST(self):
        body = parse_body(self)
        if self.path == "/api/comprar":
            try:
                status, response = proxy_purchase(body)
                return send_json(self, status, response)
            except Exception as exc:
                return send_json(
                    self,
                    503,
                    {
                        "ok": False,
                        "fase": "gateway",
                        "error": "reservas_no_disponible",
                        "detalle": str(exc),
                    },
                )
        if self.path == "/api/inventario/recargar":
            try:
                status, response = proxy_json(
                    INVENTARIO_URL,
                    "/inventario/recargar",
                    method="POST",
                    payload=body,
                )
                return send_json(self, status, response)
            except Exception as exc:
                return send_json(
                    self,
                    503,
                    {
                        "ok": False,
                        "fase": "gateway",
                        "error": "inventario_no_disponible",
                        "detalle": str(exc),
                    },
                )
        return send_json(self, 404, {"ok": False, "error": "ruta_no_encontrada"})


if __name__ == "__main__":
    server = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    print(f"api-gateway escuchando en {PORT}", flush=True)
    server.serve_forever()
