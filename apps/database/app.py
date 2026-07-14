import json
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

DATA_FILE = os.getenv("DATA_FILE", "/data/reservas.json")
lock = threading.Lock()

def load_rows():
    if not os.path.exists(DATA_FILE):
        return []
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_rows(rows):
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)

class Handler(BaseHTTPRequestHandler):
    def send_json(self, status, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/health":
            self.send_json(200, {"service": "database", "status": "ok"})
        elif self.path == "/reservas":
            with lock:
                rows = load_rows()
            self.send_json(200, {"ok": True, "total": len(rows), "reservas": rows})
        else:
            self.send_json(404, {"error": "not_found"})

    def do_POST(self):
        if self.path != "/guardar":
            self.send_json(404, {"error": "not_found"})
            return

        length = int(self.headers.get("Content-Length", 0))
        row = json.loads(self.rfile.read(length).decode("utf-8") or "{}")

        with lock:
            rows = load_rows()
            rows.append(row)
            save_rows(rows)

        self.send_json(201, {"ok": True, "guardado": True, "total": len(rows)})

if __name__ == "__main__":
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)

    if not os.path.exists(DATA_FILE):
        save_rows([])

    port = int(os.getenv("PORT", "8080"))
    print(f"database escuchando en puerto {port}", flush=True)
    ThreadingHTTPServer(("", port), Handler).serve_forever()
