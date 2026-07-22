import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib import error, request


PORT = int(os.environ.get("PORT", "8080"))
API_GATEWAY_URL = os.environ.get("API_GATEWAY_URL", "http://api-gateway:8080")

HTML = f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Sistema de Reservas</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: radial-gradient(circle at top, #f6c76e 0%, #eb8f42 24%, #0c3559 70%, #071a2b 100%);
      --card: rgba(247, 241, 230, 0.95);
      --card-strong: #fffaf1;
      --accent: #b83b2f;
      --accent-dark: #7f271f;
      --text: #1f2a33;
      --muted: #5e6a72;
      --success: #1f7a4d;
      --border: rgba(12, 53, 89, 0.14);
    }}
    body {{
      margin: 0;
      min-height: 100vh;
      font-family: Georgia, "Times New Roman", serif;
      background: var(--bg);
      display: flex;
      align-items: center;
      justify-content: center;
      color: var(--text);
      padding: 24px;
    }}
    main {{
      width: min(96vw, 980px);
      background: var(--card);
      padding: 2rem;
      border-radius: 28px;
      box-shadow: 0 24px 70px rgba(0, 0, 0, 0.28);
      border: 1px solid rgba(255, 255, 255, 0.35);
    }}
    h1 {{
      margin: 0;
      font-size: clamp(2rem, 4vw, 3.5rem);
      line-height: 0.95;
    }}
    p {{
      color: var(--muted);
    }}
    .hero {{
      display: grid;
      grid-template-columns: 1.4fr 1fr;
      gap: 1rem;
      align-items: start;
    }}
    .hero-copy {{
      padding-right: 1rem;
    }}
    .hero-badge {{
      display: inline-block;
      padding: 0.35rem 0.7rem;
      border-radius: 999px;
      background: rgba(184, 59, 47, 0.1);
      color: var(--accent-dark);
      font-size: 0.85rem;
      letter-spacing: 0.08em;
      text-transform: uppercase;
    }}
    .status-panel {{
      background: linear-gradient(180deg, rgba(255, 250, 241, 0.96), rgba(245, 234, 214, 0.96));
      border-radius: 22px;
      padding: 1.25rem;
      border: 1px solid rgba(184, 59, 47, 0.12);
    }}
    .status-grid {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 0.8rem;
      margin-top: 1rem;
    }}
    .metric {{
      background: var(--card-strong);
      border-radius: 16px;
      padding: 0.9rem 1rem;
      border: 1px solid var(--border);
    }}
    .metric strong {{
      display: block;
      font-size: 1.6rem;
      margin-top: 0.25rem;
    }}
    .actions {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 1rem;
      margin-top: 1.4rem;
    }}
    .card {{
      background: rgba(255, 255, 255, 0.52);
      border-radius: 22px;
      padding: 1.25rem;
      border: 1px solid var(--border);
    }}
    form {{
      display: grid;
      gap: 0.8rem;
    }}
    input, button {{
      padding: 0.9rem 1rem;
      border-radius: 12px;
      border: 1px solid #c8d4df;
      font: inherit;
    }}
    button {{
      background: var(--accent);
      color: white;
      border: 0;
      cursor: pointer;
      font-weight: 700;
      transition: transform 160ms ease, background 160ms ease;
    }}
    button:hover {{
      transform: translateY(-1px);
      background: var(--accent-dark);
    }}
    button.secondary {{
      background: #18476f;
    }}
    button.secondary:hover {{
      background: #123654;
    }}
    pre {{
      white-space: pre-wrap;
      background: #0f172a;
      color: #e2e8f0;
      padding: 1rem;
      border-radius: 16px;
      min-height: 180px;
      overflow: auto;
    }}
    .inline {{
      display: flex;
      gap: 0.8rem;
    }}
    .inline input {{
      flex: 1;
    }}
    .hint {{
      margin-top: 0.5rem;
      font-size: 0.92rem;
      color: var(--muted);
    }}
    .ok {{
      color: var(--success);
      font-weight: 700;
    }}
    @media (max-width: 820px) {{
      .hero,
      .actions {{
        grid-template-columns: 1fr;
      }}
      .hero-copy {{
        padding-right: 0;
      }}
      .status-grid {{
        grid-template-columns: 1fr 1fr;
      }}
    }}
    @media (max-width: 560px) {{
      body {{
        padding: 14px;
      }}
      main {{
        padding: 1.2rem;
      }}
      .status-grid {{
        grid-template-columns: 1fr;
      }}
      .inline {{
        flex-direction: column;
      }}
    }}
  </style>
</head>
<body>
  <main>
    <section class="hero">
      <div class="hero-copy">
        <span class="hero-badge">Demo operativa</span>
        <h1>Reservas listas para correr el flujo y luego romperlo con chaos.</h1>
        <p>Primero validas inventario, recargas stock si hace falta y ejecutas una compra base desde esta misma pantalla. Cuando eso quede estable, corres los chaos uno por uno.</p>
      </div>
      <aside class="status-panel">
        <h2>Estado del inventario</h2>
        <div class="status-grid">
          <div class="metric">
            Evento
            <strong id="metric-evento">concierto-kubernetes</strong>
          </div>
          <div class="metric">
            Disponibles
            <strong id="metric-available">-</strong>
          </div>
          <div class="metric">
            Reservados
            <strong id="metric-reserved">-</strong>
          </div>
          <div class="metric">
            Estado
            <strong id="metric-status">Cargando</strong>
          </div>
        </div>
        <p class="hint">Usa "Actualizar inventario" antes de cada demo para confirmar el punto de partida.</p>
      </aside>
    </section>

    <section class="actions">
      <div class="card">
        <h2>Comprar entrada</h2>
        <form id="buy-form">
          <input id="cliente" name="cliente" placeholder="Cliente" value="demo-web" required />
          <input id="evento" name="evento" placeholder="Evento" value="concierto-kubernetes" required />
          <input id="cantidad" name="cantidad" placeholder="Cantidad" type="number" min="1" value="1" required />
          <button type="submit">Comprar</button>
        </form>
      </div>

      <div class="card">
        <h2>Recargar inventario</h2>
        <form id="restock-form">
          <div class="inline">
            <input id="restock-evento" name="restock-evento" placeholder="Evento" value="concierto-kubernetes" required />
            <input id="restock-cantidad" name="restock-cantidad" placeholder="Cantidad" type="number" min="1" value="10" required />
          </div>
          <button class="secondary" type="submit">Cargar inventario</button>
        </form>
        <p class="hint">La recarga suma unidades disponibles sin tocar la evidencia de reservas ya hechas.</p>
        <button class="secondary" id="refresh-button" type="button">Actualizar inventario</button>
      </div>
    </section>

    <div class="card">
      <h2>Resultado</h2>
      <pre id="output">Esperando solicitud...</pre>
    </div>
  </main>
  <script>
    const defaultEvent = 'concierto-kubernetes';
    const buyForm = document.getElementById('buy-form');
    const restockForm = document.getElementById('restock-form');
    const refreshButton = document.getElementById('refresh-button');
    const output = document.getElementById('output');

    function renderOutput(title, data) {{
      output.textContent = `${{title}}\\n${{JSON.stringify(data, null, 2)}}`;
    }}

    async function fetchJson(url, options = undefined) {{
      const response = await fetch(url, options);
      const data = await response.json();
      return {{ response, data }};
    }}

    async function refreshInventory() {{
      const eventName = document.getElementById('evento').value || defaultEvent;
      document.getElementById('metric-evento').textContent = eventName;
      document.getElementById('metric-status').textContent = 'Consultando';
      try {{
        const {{ response, data }} = await fetchJson(`/api/inventario/${{encodeURIComponent(eventName)}}`);
        if (!response.ok || !data.ok) {{
          document.getElementById('metric-available').textContent = '-';
          document.getElementById('metric-reserved').textContent = '-';
          document.getElementById('metric-status').textContent = 'Error';
          renderOutput('Inventario consultado con error', data);
          return;
        }}
        document.getElementById('metric-available').textContent = data.available;
        document.getElementById('metric-reserved').textContent = data.reserved;
        document.getElementById('metric-status').innerHTML = '<span class="ok">Disponible</span>';
      }} catch (error) {{
        document.getElementById('metric-available').textContent = '-';
        document.getElementById('metric-reserved').textContent = '-';
        document.getElementById('metric-status').textContent = 'Sin conexion';
        renderOutput('Error consultando inventario', {{ ok: false, error: String(error) }});
      }}
    }}

    buyForm.addEventListener('submit', async (event) => {{
      event.preventDefault();
      const payload = {{
        cliente: document.getElementById('cliente').value,
        evento: document.getElementById('evento').value,
        cantidad: Number(document.getElementById('cantidad').value)
      }};
      output.textContent = 'Procesando compra...';
      try {{
        const {{ data }} = await fetchJson('/api/comprar', {{
          method: 'POST',
          headers: {{ 'Content-Type': 'application/json' }},
          body: JSON.stringify(payload)
        }});
        renderOutput('Resultado de compra', data);
      }} catch (error) {{
        renderOutput('Error de compra', {{ ok: false, error: String(error) }});
      }}
      refreshInventory();
    }});

    restockForm.addEventListener('submit', async (event) => {{
      event.preventDefault();
      const payload = {{
        evento: document.getElementById('restock-evento').value,
        cantidad: Number(document.getElementById('restock-cantidad').value)
      }};
      output.textContent = 'Recargando inventario...';
      try {{
        const {{ data }} = await fetchJson('/api/inventario/recargar', {{
          method: 'POST',
          headers: {{ 'Content-Type': 'application/json' }},
          body: JSON.stringify(payload)
        }});
        renderOutput('Resultado de recarga', data);
      }} catch (error) {{
        renderOutput('Error de recarga', {{ ok: false, error: String(error) }});
      }}
      document.getElementById('evento').value = payload.evento;
      await refreshInventory();
    }});

    refreshButton.addEventListener('click', refreshInventory);
    document.getElementById('evento').addEventListener('change', refreshInventory);
    document.getElementById('restock-evento').addEventListener('change', async () => {{
      document.getElementById('evento').value = document.getElementById('restock-evento').value;
      await refreshInventory();
    }});

    refreshInventory();
  </script>
</body>
</html>
"""


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        return

    def _send_bytes(self, status, body, content_type="application/json; charset=utf-8"):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _proxy(self, path, method="GET", body=None):
        headers = {}
        if body is not None:
            headers["Content-Type"] = "application/json"
        upstream = request.Request(
            f"{API_GATEWAY_URL}{path}",
            data=body,
            headers=headers,
            method=method,
        )
        try:
            with request.urlopen(upstream, timeout=15) as response:
                return response.status, response.read()
        except error.HTTPError as exc:
            return exc.code, exc.read()
        except Exception as exc:
            return (
                502,
                json.dumps(
                    {"ok": False, "error": "frontend_proxy_error", "detail": str(exc)}
                ).encode("utf-8"),
            )

    def do_GET(self):
        if self.path == "/health":
            data = json.dumps({"status": "ok"}).encode("utf-8")
            self._send_bytes(200, data)
            return
        if self.path == "/" or self.path == "/index.html":
            data = HTML.encode("utf-8")
            self._send_bytes(200, data, "text/html; charset=utf-8")
            return
        if self.path.startswith("/api/"):
            status, response_body = self._proxy(self.path)
            self._send_bytes(status, response_body)
            return
        self.send_response(404)
        self.end_headers()

    def do_POST(self):
        if not self.path.startswith("/api/"):
            self.send_response(404)
            self.end_headers()
            return

        try:
            content_length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            content_length = 0
        body = self.rfile.read(content_length)
        status, response_body = self._proxy(self.path, method="POST", body=body)
        self._send_bytes(status, response_body)


if __name__ == "__main__":
    server = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    print(f"frontend escuchando en {PORT}", flush=True)
    server.serve_forever()
