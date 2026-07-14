import json
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

DATA_FILE = os.getenv("DATA_FILE", "/data/inventario.json")
INITIAL_SEATS = int(os.getenv("INITIAL_SEATS", "50"))
lock = threading.Lock()

def load_state():
    if not os.path.exists(DATA_FILE):
        return {"evento": "concierto-kubernetes", "disponibles": INITIAL_SEATS, "reservas": []}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_state(state):
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

class Handler(BaseHTTPRequestHandler):
    def send_json(self, status, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/health":
            self.send_json(200, {"service": "inventario", "status": "ok"})
        elif self.path == "/asientos":
            with lock:
                state = load_state()
            self.send_json(200, {"evento": state["evento"], "disponibles": state["disponibles"]})
        else:
            self.send_json(404, {"error": "not_found"})

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length).decode("utf-8") or "{}")

        if self.path == "/reservar":
            cantidad = int(body.get("cantidad", 1))
            reserva_id = body.get("reserva_id")

            with lock:
                state = load_state()
                if state["disponibles"] < cantidad:
                    self.send_json(409, {"ok": False, "error": "sin_asientos_disponibles"})
                    return

                state["disponibles"] -= cantidad
                state["reservas"].append({"reserva_id": reserva_id, "cantidad": cantidad})
                save_state(state)

            self.send_json(200, {"ok": True, "reserva_id": reserva_id, "disponibles": state["disponibles"]})

        elif self.path == "/liberar":
            cantidad = int(body.get("cantidad", 1))
            reserva_id = body.get("reserva_id")

            with lock:
                state = load_state()
                state["disponibles"] += cantidad
                state["reservas"] = [r for r in state["reservas"] if r.get("reserva_id") != reserva_id]
                save_state(state)

            self.send_json(200, {"ok": True, "reserva_id": reserva_id, "disponibles": state["disponibles"]})
        else:
            self.send_json(404, {"error": "not_found"})

if __name__ == "__main__":
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    if not os.path.exists(DATA_FILE):
        save_state({"evento": "concierto-kubernetes", "disponibles": INITIAL_SEATS, "reservas": []})

    port = int(os.getenv("PORT", "8080"))
    print(f"inventario escuchando en puerto {port}", flush=True)
    ThreadingHTTPServer(("", port), Handler).serve_forever()
