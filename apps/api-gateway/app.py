import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib import error, request


PORT = int(os.environ.get("PORT", "8080"))
RESERVAS_URL = os.environ.get("RESERVAS_URL", "http://reservas:8080")
TIMEOUT = float(os.environ.get("RESERVAS_TIMEOUT_SECONDS", "10"))


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


def proxy_purchase(payload):
    body = json.dumps(payload, ensure_ascii=True).encode("utf-8")
    req = request.Request(
        f"{RESERVAS_URL}/comprar",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=TIMEOUT) as resp:
            raw = resp.read().decode("utf-8")
            return resp.status, json.loads(raw) if raw else {}
    except error.HTTPError as exc:
        raw = exc.read().decode("utf-8")
        return exc.code, json.loads(raw) if raw else {}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        return

    def do_GET(self):
        if self.path == "/health":
            return send_json(self, 200, {"status": "ok", "upstream": RESERVAS_URL})
        return send_json(self, 404, {"ok": False, "error": "ruta_no_encontrada"})

    def do_POST(self):
        if self.path != "/api/comprar":
            return send_json(self, 404, {"ok": False, "error": "ruta_no_encontrada"})
        body = parse_body(self)
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


if __name__ == "__main__":
    server = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    print(f"api-gateway escuchando en {PORT}", flush=True)
    server.serve_forever()
