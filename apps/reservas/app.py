import json
import os
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib import error, request


PORT = int(os.environ.get("PORT", "8080"))
INVENTARIO_URL = os.environ.get("INVENTARIO_URL", "http://inventario:8080")
PAGOS_URL = os.environ.get("PAGOS_URL", "http://pagos:8080")
NOTIFICACIONES_URL = os.environ.get("NOTIFICACIONES_URL", "http://notificaciones:8080")
DATABASE_URL = os.environ.get("DATABASE_URL", "http://database:8080")
INVENTORY_TIMEOUT = float(os.environ.get("INVENTORY_TIMEOUT_SECONDS", "2"))
PAYMENT_TIMEOUT = float(os.environ.get("PAYMENT_TIMEOUT_SECONDS", "5"))
NOTIFICATION_TIMEOUT = float(os.environ.get("NOTIFICATION_TIMEOUT_SECONDS", "2"))
DATABASE_TIMEOUT = float(os.environ.get("DATABASE_TIMEOUT_SECONDS", "2"))
PAYMENT_RETRIES = int(os.environ.get("PAYMENT_RETRIES", "2"))
PAYMENT_BACKOFF_SECONDS = float(os.environ.get("PAYMENT_BACKOFF_SECONDS", "1"))
MAX_CONCURRENT_PURCHASES = int(os.environ.get("MAX_CONCURRENT_PURCHASES", "5"))
CB_FAILURE_THRESHOLD = int(os.environ.get("PAYMENT_CB_FAILURE_THRESHOLD", "3"))
CB_OPEN_SECONDS = int(os.environ.get("PAYMENT_CB_OPEN_SECONDS", "30"))

SEMAPHORE = threading.BoundedSemaphore(MAX_CONCURRENT_PURCHASES)
BREAKER_LOCK = threading.Lock()
BREAKER_STATE = {
    "status": "closed",
    "failures": 0,
    "open_until": 0.0,
    "half_open_in_flight": False,
}


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


def http_json(base_url, path, timeout, method="GET", payload=None):
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
        payload = json.loads(raw) if raw else {}
        return exc.code, payload


def breaker_before_call():
    now = time.time()
    with BREAKER_LOCK:
        if BREAKER_STATE["status"] == "open":
            if now < BREAKER_STATE["open_until"]:
                return False, max(0, int(BREAKER_STATE["open_until"] - now))
            BREAKER_STATE["status"] = "half-open"
            BREAKER_STATE["half_open_in_flight"] = False
        if BREAKER_STATE["status"] == "half-open":
            if BREAKER_STATE["half_open_in_flight"]:
                return False, 0
            BREAKER_STATE["half_open_in_flight"] = True
        return True, 0


def breaker_success():
    with BREAKER_LOCK:
        BREAKER_STATE["status"] = "closed"
        BREAKER_STATE["failures"] = 0
        BREAKER_STATE["open_until"] = 0.0
        BREAKER_STATE["half_open_in_flight"] = False


def breaker_failure():
    now = time.time()
    with BREAKER_LOCK:
        if BREAKER_STATE["status"] == "half-open":
            BREAKER_STATE["status"] = "open"
            BREAKER_STATE["failures"] = CB_FAILURE_THRESHOLD
            BREAKER_STATE["open_until"] = now + CB_OPEN_SECONDS
            BREAKER_STATE["half_open_in_flight"] = False
            return
        BREAKER_STATE["failures"] += 1
        if BREAKER_STATE["failures"] >= CB_FAILURE_THRESHOLD:
            BREAKER_STATE["status"] = "open"
            BREAKER_STATE["open_until"] = now + CB_OPEN_SECONDS
        BREAKER_STATE["half_open_in_flight"] = False


def release_inventory(payload):
    try:
        status, _ = http_json(INVENTARIO_URL, "/inventario/liberar", INVENTORY_TIMEOUT, method="POST", payload=payload)
        return status == 200
    except Exception:
        return False


def attempt_payment(payload):
    last_error = {"error": "pago_no_disponible"}
    for attempt in range(1, PAYMENT_RETRIES + 1):
        allowed, retry_after = breaker_before_call()
        if not allowed:
            last_error = {
                "error": "circuito_pagos_abierto",
                "retry_after_seconds": retry_after,
            }
            break
        try:
            status, response = http_json(PAGOS_URL, "/pagar", PAYMENT_TIMEOUT, method="POST", payload=payload)
            if status == 200 and response.get("ok"):
                breaker_success()
                return True, response
            last_error = response or {"error": "pago_no_disponible"}
        except Exception as exc:
            last_error = {"error": "pago_timeout", "reason": str(exc)}
        breaker_failure()
        if attempt < PAYMENT_RETRIES:
            time.sleep(PAYMENT_BACKOFF_SECONDS * attempt)
    return False, last_error


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
                    "bulkhead_limit": MAX_CONCURRENT_PURCHASES,
                    "payment_breaker": BREAKER_STATE["status"],
                },
            )
        return send_json(self, 404, {"ok": False, "error": "ruta_no_encontrada"})

    def do_POST(self):
        if self.path != "/comprar":
            return send_json(self, 404, {"ok": False, "error": "ruta_no_encontrada"})
        if not SEMAPHORE.acquire(blocking=False):
            return send_json(
                self,
                429,
                {
                    "ok": False,
                    "fase": "bulkhead",
                    "error": "demasiadas_solicitudes_concurrentes",
                    "accion": "rechazo_temporal",
                },
            )
        try:
            body = parse_body(self)
            payload = {
                "cliente": body.get("cliente", "anonimo"),
                "evento": body.get("evento", "concierto-kubernetes"),
                "cantidad": int(body.get("cantidad", 1)),
            }

            try:
                status, inventory_response = http_json(
                    INVENTARIO_URL,
                    "/inventario/reservar",
                    INVENTORY_TIMEOUT,
                    method="POST",
                    payload=payload,
                )
            except Exception as exc:
                return send_json(
                    self,
                    503,
                    {
                        "ok": False,
                        "fase": "inventario",
                        "error": "inventario_no_disponible",
                        "accion": "error_controlado_sin_cobro",
                        "detalle": str(exc),
                    },
                )

            if status != 200 or not inventory_response.get("ok"):
                inventory_error = inventory_response.get("error", "inventario_no_disponible")
                return send_json(
                    self,
                    503 if status >= 500 else status,
                    {
                        "ok": False,
                        "fase": "inventario",
                        "error": inventory_error,
                        "accion": "error_controlado_sin_cobro",
                        "inventario": inventory_response,
                    },
                )

            payment_ok, payment_response = attempt_payment(payload)
            if not payment_ok:
                released = release_inventory(payload)
                return send_json(
                    self,
                    503,
                    {
                        "ok": False,
                        "fase": "pagos",
                        "error": payment_response.get("error", "pago_no_disponible"),
                        "accion": "compra_cancelada_con_compensacion",
                        "compensacion": {
                            "inventario_liberado": released,
                            "accion": "liberacion_intentada",
                        },
                        "pagos": payment_response,
                    },
                )

            persistence = {"estado": "guardado"}
            try:
                status, db_response = http_json(
                    DATABASE_URL,
                    "/bookings/record",
                    DATABASE_TIMEOUT,
                    method="POST",
                    payload={
                        **payload,
                        "pago": payment_response,
                    },
                )
                if status >= 400 or not db_response.get("ok"):
                    persistence = {
                        "estado": "pendiente",
                        "error": db_response.get("persistencia", "no_guardado"),
                    }
            except Exception as exc:
                persistence = {"estado": "pendiente", "error": f"no_guardado:{exc}"}

            notification = {"ok": True}
            warning = None
            try:
                n_status, n_response = http_json(
                    NOTIFICACIONES_URL,
                    "/notificar",
                    NOTIFICATION_TIMEOUT,
                    method="POST",
                    payload=payload,
                )
                notification = n_response
                if n_status >= 400 or not n_response.get("ok"):
                    notification = {"ok": False, "detalle": n_response}
                    warning = "notificacion_fallida_no_critica"
            except Exception as exc:
                notification = {"ok": False, "detalle": str(exc)}
                warning = "notificacion_fallida_no_critica"

            response = {
                "ok": True,
                "fase": "completado",
                "inventario": inventory_response,
                "pago": payment_response,
                "persistencia": persistence,
                "notificacion": notification,
            }
            if warning:
                response["warning"] = warning
            return send_json(self, 200, response)
        finally:
            SEMAPHORE.release()


if __name__ == "__main__":
    server = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    print(f"reservas escuchando en {PORT}", flush=True)
    server.serve_forever()
