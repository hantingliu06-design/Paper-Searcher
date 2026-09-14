"""A small local demo server, intentionally separate from the research engine."""

from __future__ import annotations

import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import BoundedSemaphore
from urllib.parse import urlsplit

from . import __version__
from .fixtures import DEMO_INPUT
from .providers import ProviderError
from .validation import ValidationError
from .workflow import ResearchAgent

STATIC = Path(__file__).with_name("static")
ASSETS = {"/": ("index.html", "text/html; charset=utf-8"),
          "/index.html": ("index.html", "text/html; charset=utf-8"),
          "/styles.css": ("styles.css", "text/css; charset=utf-8"),
          "/app.js": ("app.js", "text/javascript; charset=utf-8")}
MAX_BODY = 128 * 1024


def make_server(host="127.0.0.1", port=8000, agent: ResearchAgent | None = None) -> ThreadingHTTPServer:
    research = agent or ResearchAgent()
    slots = BoundedSemaphore(2)

    class Handler(BaseHTTPRequestHandler):
        server_version = "ScholarCompass/0.1"

        def setup(self):
            super().setup()
            self.connection.settimeout(10)

        def log_message(self, format, *args):
            # No query strings, bodies, credentials, or provider exception payloads in logs.
            sys.stderr.write(f"{self.command} {urlsplit(self.path).path}\n")

        def respond(self, status, content, content_type="application/json; charset=utf-8"):
            if not isinstance(content, bytes):
                content = json.dumps(content, ensure_ascii=False, allow_nan=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(content)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
            self.end_headers()
            try:
                self.wfile.write(content)
            except (BrokenPipeError, ConnectionResetError):
                pass

        def local_request(self):
            host_header = self.headers.get("Host", "")
            try:
                parsed = urlsplit("http://" + host_header)
                valid_host = parsed.hostname in ("localhost", "127.0.0.1", "::1") and parsed.port == self.server.server_port
            except ValueError:
                valid_host = False
            origin = self.headers.get("Origin")
            if not valid_host or (origin and origin != "http://" + host_header):
                self.respond(403, {"error": "只接受本地同源请求。"})
                return False
            return True

        def do_GET(self):
            if not self.local_request():
                return
            path = urlsplit(self.path).path
            if path in ASSETS:
                name, content_type = ASSETS[path]
                self.respond(200, (STATIC / name).read_bytes(), content_type)
            elif path == "/api/config":
                self.respond(200, {"version": __version__, "demo_input": DEMO_INPUT, "providers": research.settings.public()})
            elif path == "/api/health":
                self.respond(200, {"status": "ok", "version": __version__})
            elif path == "/api/demo":
                self.respond(200, research.run(DEMO_INPUT))
            else:
                self.respond(404, {"error": "页面不存在。"})

        def do_POST(self):
            if not self.local_request():
                return
            path = urlsplit(self.path).path
            if path not in ("/api/plan", "/api/run"):
                self.respond(404, {"error": "接口不存在。"})
                return
            if self.headers.get("Content-Type", "").split(";")[0].strip() != "application/json":
                self.respond(415, {"error": "请发送 application/json。"})
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                length = 0
            if not 0 < length <= MAX_BODY:
                self.respond(413, {"error": "请求为空或超过 128 KB。"})
                return
            if not slots.acquire(blocking=False):
                self.respond(429, {"error": "已有任务运行，请稍后重试。"})
                return
            try:
                data = json.loads(self.rfile.read(length))
                result = research.plan(data) if path == "/api/plan" else research.run(data)
                self.respond(200, result)
            except (ValidationError, ValueError, TypeError, UnicodeDecodeError):
                # Validation messages contain field guidance, but raw JSON/provider data must not leak.
                self.respond(400, {"error": "输入或计划格式错误，请检查题目、背景、年份、权重及阅读计划。"})
            except ProviderError as exc:
                self.respond(502, {"error": str(exc)})
            except (OSError, KeyError, AttributeError):
                self.respond(500, {"error": "服务无法完成请求，请检查本地配置和服务状态。"})
            finally:
                slots.release()

    server = ThreadingHTTPServer((host, port), Handler)
    server.daemon_threads = True
    return server


def serve(host="127.0.0.1", port=8000):
    server = make_server(host, port)
    print(f"Scholar Compass → http://127.0.0.1:{server.server_port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        server.server_close()
