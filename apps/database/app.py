import json
import os
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import unquote, urlparse


PORT = int(os.environ.get("PORT", "8080"))
DATA_DIR = os.environ.get("DATA_DIR", "/data")
DATA_FILE = os.path.join(DATA_DIR, "ticket-system.json")
DEFAULT_EVENT = os.environ.get("DEFAULT_EVENT", "concierto-kubernetes")
DEFAULT_STOCK = int(os.environ.get("DEFAULT_STOCK", "10"))
FAIL_WRITES = os.environ.get("DATABASE_FAIL_WRITES", "false").lower() == "true"

STATE_LOCK = threading.Lock()
STATE = None


def ensure_state():
    global STATE
    os.makedirs(DATA_DIR, exist_ok=True)
    if STATE is not None:
        return STATE
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as fh:
            STATE = json.load(fh)
    else:
        STATE = {
            "events": {
                DEFAULT_EVENT: {
                    "available": DEFAULT_STOCK,
                    "reserved": 0,
                }
            },
            "bookings": [],
        }
        persist_state()
    return STATE


def persist_state():
    if FAIL_WRITES:
        raise RuntimeError("database_write_failure_simulated")
    fd, temp_path = tempfile.mkstemp(dir=DATA_DIR, prefix="ticket-system-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(STATE, fh, ensure_ascii=True, indent=2)
        os.replace(temp_path, DATA_FILE)
    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)


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
    if not raw:
        return {}
    return json.loads(raw.decode("utf-8"))


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        return

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/health":
            ensure_state()
            return send_json(
                self,
                200,
                {
                    "status": "ok",
                    "data_file": DATA_FILE,
                    "events": list(STATE["events"].keys()),
                },
            )
        if parsed.path == "/debug/state":
            ensure_state()
            with STATE_LOCK:
                snapshot = json.loads(json.dumps(STATE))
            return send_json(self, 200, snapshot)
        if parsed.path.startswith("/events/"):
            ensure_state()
            event = unquote(parsed.path.split("/events/", 1)[1])
            with STATE_LOCK:
                event_state = STATE["events"].get(event)
            if not event_state:
                return send_json(self, 404, {"ok": False, "error": "evento_no_encontrado", "evento": event})
            return send_json(self, 200, {"ok": True, "evento": event, **event_state})
        return send_json(self, 404, {"ok": False, "error": "ruta_no_encontrada"})

    def do_POST(self):
        ensure_state()
        if self.path == "/inventory/reserve":
            body = parse_body(self)
            event = body.get("evento", DEFAULT_EVENT)
            cantidad = int(body.get("cantidad", 1))
            with STATE_LOCK:
                event_state = STATE["events"].setdefault(
                    event,
                    {"available": DEFAULT_STOCK, "reserved": 0},
                )
                if event_state["available"] < cantidad:
                    return send_json(
                        self,
                        409,
                        {
                            "ok": False,
                            "error": "sin_stock",
                            "evento": event,
                            "available": event_state["available"],
                        },
                    )
                event_state["available"] -= cantidad
                event_state["reserved"] += cantidad
                persist_state()
                snapshot = dict(event_state)
            return send_json(self, 200, {"ok": True, "evento": event, **snapshot})
        if self.path == "/inventory/release":
            body = parse_body(self)
            event = body.get("evento", DEFAULT_EVENT)
            cantidad = int(body.get("cantidad", 1))
            with STATE_LOCK:
                event_state = STATE["events"].setdefault(
                    event,
                    {"available": DEFAULT_STOCK, "reserved": 0},
                )
                event_state["available"] += cantidad
                event_state["reserved"] = max(0, event_state["reserved"] - cantidad)
                persist_state()
                snapshot = dict(event_state)
            return send_json(self, 200, {"ok": True, "evento": event, **snapshot})
        if self.path == "/bookings/record":
            body = parse_body(self)
            with STATE_LOCK:
                STATE["bookings"].append(body)
                try:
                    persist_state()
                    return send_json(
                        self,
                        201,
                        {
                            "ok": True,
                            "persistencia": "guardado",
                            "reservas_registradas": len(STATE["bookings"]),
                        },
                    )
                except Exception as exc:
                    return send_json(
                        self,
                        503,
                        {
                            "ok": False,
                            "persistencia": "no_guardado",
                            "error": str(exc),
                        },
                    )
        return send_json(self, 404, {"ok": False, "error": "ruta_no_encontrada"})


if __name__ == "__main__":
    ensure_state()
    server = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    print(f"database escuchando en {PORT}", flush=True)
    server.serve_forever()
