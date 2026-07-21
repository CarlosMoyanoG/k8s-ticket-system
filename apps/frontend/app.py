import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


PORT = int(os.environ.get("PORT", "8080"))
GATEWAY_NODEPORT = os.environ.get("GATEWAY_NODEPORT", "30081")

HTML = f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Sistema de Reservas</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: linear-gradient(135deg, #081f3f, #0e4d92 60%, #7ec8e3);
      --card: rgba(255, 255, 255, 0.94);
      --accent: #d64545;
      --text: #132238;
    }}
    body {{
      margin: 0;
      min-height: 100vh;
      font-family: Georgia, "Times New Roman", serif;
      background: var(--bg);
      display: grid;
      place-items: center;
      color: var(--text);
    }}
    main {{
      width: min(92vw, 720px);
      background: var(--card);
      padding: 2rem;
      border-radius: 24px;
      box-shadow: 0 20px 60px rgba(0, 0, 0, 0.25);
    }}
    h1 {{ margin-top: 0; }}
    form {{
      display: grid;
      gap: 0.8rem;
      margin-top: 1rem;
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
    }}
    pre {{
      white-space: pre-wrap;
      background: #0f172a;
      color: #e2e8f0;
      padding: 1rem;
      border-radius: 16px;
      min-height: 140px;
    }}
  </style>
</head>
<body>
  <main>
    <h1>Sistema de Reservas de Entradas</h1>
    <p>Frontend de demostracion para Kubernetes multi-nodo. El API Gateway expuesto usa el puerto {GATEWAY_NODEPORT}.</p>
    <form id="buy-form">
      <input id="cliente" name="cliente" placeholder="Cliente" value="demo-web" required />
      <input id="evento" name="evento" placeholder="Evento" value="concierto-kubernetes" required />
      <input id="cantidad" name="cantidad" placeholder="Cantidad" type="number" min="1" value="1" required />
      <button type="submit">Comprar</button>
    </form>
    <pre id="output">Esperando solicitud...</pre>
  </main>
  <script>
    const form = document.getElementById('buy-form');
    const output = document.getElementById('output');
    form.addEventListener('submit', async (event) => {{
      event.preventDefault();
      const payload = {{
        cliente: document.getElementById('cliente').value,
        evento: document.getElementById('evento').value,
        cantidad: Number(document.getElementById('cantidad').value)
      }};
      const base = window.location.hostname || '127.0.0.1';
      output.textContent = 'Procesando compra...';
      try {{
        const response = await fetch(`http://${{base}}:{GATEWAY_NODEPORT}/api/comprar`, {{
          method: 'POST',
          headers: {{ 'Content-Type': 'application/json' }},
          body: JSON.stringify(payload)
        }});
        const data = await response.json();
        output.textContent = JSON.stringify(data, null, 2);
      }} catch (error) {{
        output.textContent = JSON.stringify({{ ok: false, error: String(error) }}, null, 2);
      }}
    }});
  </script>
</body>
</html>
"""


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        return

    def do_GET(self):
        if self.path == "/health":
            data = json.dumps({"status": "ok"}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return
        if self.path == "/" or self.path == "/index.html":
            data = HTML.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return
        self.send_response(404)
        self.end_headers()


if __name__ == "__main__":
    server = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    print(f"frontend escuchando en {PORT}", flush=True)
    server.serve_forever()
