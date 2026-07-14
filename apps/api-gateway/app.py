import json
import os
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

RESERVAS_URL = os.getenv("RESERVAS_URL", "http://reservas:8080")

def request_json(method, url, payload=None, timeout=5):
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
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_json(200, {"ok": True})

    def do_GET(self):
        if self.path == "/health":
            self.send_json(200, {"service": "api-gateway", "status": "ok"})
        elif self.path == "/api/status":
            try:
                status, payload = request_json("GET", f"{RESERVAS_URL}/status")
                self.send_json(status, payload)
            except Exception as exc:
                self.send_json(503, {"ok": False, "error": "reservas_no_disponible", "detail": str(exc)})
        else:
            self.send_json(404, {"error": "not_found"})

    def do_POST(self):
        if self.path != "/api/comprar":
            self.send_json(404, {"error": "not_found"})
            return

        length = int(self.headers.get("Content-Length", 0))
        payload = json.loads(self.rfile.read(length).decode("utf-8") or "{}")

        try:
            status, result = request_json("POST", f"{RESERVAS_URL}/reservar", payload, timeout=8)
            self.send_json(status, result)
        except Exception as exc:
            self.send_json(503, {
                "ok": False,
                "error": "servicio_reservas_no_responde",
                "detail": str(exc)
            })

if __name__ == "__main__":
    port = int(os.getenv("PORT", "8080"))
    print(f"api-gateway escuchando en puerto {port}", flush=True)
    ThreadingHTTPServer(("", port), Handler).serve_forever()
