"""Anthropic Messages API over HTTP.

A thin BaseHTTPRequestHandler that exposes /v1/messages (and /messages),
/v1/models, /health and HEAD. Inference is delegated to generation.py.
"""

import json
import sys
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse

from . import config, metrics
from .config import log
from .generation import generate_response
from .dashboard import DASHBOARD_HTML


def send_json(handler, status, data):
    resp = json.dumps(data).encode()
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", len(resp))
    handler.end_headers()
    handler.wfile.write(resp)


def send_html(handler, status, html):
    resp = html.encode()
    handler.send_response(status)
    handler.send_header("Content-Type", "text/html; charset=utf-8")
    handler.send_header("Content-Length", len(resp))
    handler.end_headers()
    handler.wfile.write(resp)


def get_path(full_path):
    return urlparse(full_path).path


class AnthropicHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def do_HEAD(self):
        log(f"HEAD {self.path}")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()

    def do_POST(self):
        path = get_path(self.path)
        content_length = int(self.headers.get('Content-Length', 0))
        raw = self.rfile.read(content_length) if content_length else b'{}'
        body = json.loads(raw)
        tools_count = len(body.get("tools", []))
        log(f"POST {self.path} model={body.get('model','-')} max_tokens={body.get('max_tokens','-')} tools={tools_count}")

        if path in ("/v1/messages", "/messages"):
            metrics.inc_inflight()
            try:
                result = generate_response(body)
                # Log preview of first content block
                first = result["content"][0]
                if first["type"] == "text":
                    preview = first.get("text", "")[:80]
                    log(f"  ← OK ({result['usage']['output_tokens']} tok) {preview}...")
                elif first["type"] == "tool_use":
                    log(f"  ← OK ({result['usage']['output_tokens']} tok) [tool_use: {first['name']}]")
                send_json(self, 200, result)
            except Exception as e:
                log(f"  ← ERROR: {e}")
                metrics.record_error(e)
                import traceback
                traceback.print_exc(file=sys.stderr)
                send_json(self, 500, {"error": {"type": "server_error", "message": str(e)}})
            finally:
                metrics.dec_inflight()
        else:
            log(f"  Unknown POST: {path}")
            send_json(self, 200, {})

    def do_GET(self):
        path = get_path(self.path)
        log(f"GET {self.path}")

        if path in ("/v1/models", "/models"):
            send_json(self, 200, {
                "object": "list",
                "data": [
                    {"id": "claude-opus-4-6", "object": "model", "created": int(time.time()), "owned_by": "local"},
                    {"id": "claude-sonnet-4-6", "object": "model", "created": int(time.time()), "owned_by": "local"},
                    {"id": "claude-haiku-4-5-20251001", "object": "model", "created": int(time.time()), "owned_by": "local"},
                ]
            })
        elif path == "/health":
            send_json(self, 200, {"status": "ok", "model": config.MODEL_PATH})
        elif path == "/metrics":
            send_json(self, 200, metrics.snapshot())
        elif path in ("/dashboard", "/dashboard/"):
            send_html(self, 200, DASHBOARD_HTML)
        else:
            send_json(self, 200, {})


def make_server():
    """Create the HTTPServer bound to the configured port."""
    return HTTPServer(("127.0.0.1", config.PORT), AnthropicHandler)
