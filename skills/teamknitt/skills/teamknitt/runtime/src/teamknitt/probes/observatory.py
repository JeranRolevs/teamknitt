"""Offline HTML and a loopback-only, read-only viewer. No directory serving or API."""
from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
from urllib.parse import urlsplit

from .config import resource


def html(report):
    encoded = json.dumps(report, allow_nan=False).replace("&", "\\u0026").replace("<", "\\u003c").replace(">", "\\u003e")
    return resource("observatory.html").read_text(encoding="utf-8").replace("__REPORT_JSON__", encoded)


def snapshot(report, path: Path):
    # Exclusive creation; no overwriting an earlier snapshot or following a symlink.
    import os
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as stream:
        stream.write(html(report))
    return {"status": "snapshot_saved", "output": str(path.absolute()), "api_calls": 0}


def serve(report, port=8766):
    page = html(report).encode()
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if urlsplit(self.path).path != "/":
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(page)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("Content-Security-Policy", "default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'; frame-ancestors 'self' https:")
            self.end_headers()
            self.wfile.write(page)
        def log_message(self, *_):
            return
    with ThreadingHTTPServer(("127.0.0.1", port), Handler) as server:
        print(f"Teamknitt read-only observatory: http://127.0.0.1:{server.server_address[1]}", flush=True)
        print("Saved observations only; no provider calls. Ctrl-C stops the viewer.", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
    return {"status": "viewer_stopped", "api_calls": 0}
