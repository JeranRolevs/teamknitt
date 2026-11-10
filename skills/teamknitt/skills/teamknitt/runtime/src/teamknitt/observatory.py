"""Local draft builder and read-only live/saved process monitoring. Never runs models.

GET preview is non-mutating. Applying a draft or starting paid execution is a separate,
explicit CLI action. Only allowlisted metadata routes are served, never the filesystem.
"""
from __future__ import annotations

from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
from urllib.parse import urlsplit, parse_qs

from teamknitt.engine.config import ConfigurationError
from .config import resource, compile_plan, load
from .builder import draft_configuration
from .reporting import build_report, plan_report
from .views import with_views, VIEWS, resolve_view


def html(report):
    value = json.dumps(report, allow_nan=False).replace("&", "\\u0026").replace("<", "\\u003c").replace(">", "\\u003e")
    return resource("observatory.html").read_text(encoding="utf-8").replace("__REPORT_JSON__", value).replace("__TEAMKNITT_APP_JS__", resource("app.js").read_text(encoding="utf-8"))


def snapshot(report, path: Path):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as stream:
        # No workspace API or source-text access survives in an offline snapshot.
        stream.write(html({**report, "viewer": {"live": False, "draft_available": False, "selection": "snapshot", **{k: report.get("viewer", {}).get(k) for k in ("initial_group", "initial_section", "view_notice", "multi_team")}}}))
    return {"status": "snapshot_saved", "output": str(path.absolute()), "api_calls": 0}


class ViewerService:
    def __init__(self, report, *, workspace=None, run_directory=None, initial_group=None, initial_section=None, view_notice=None, initial_lens=None, probe_summary=None):
        group, section, notice = resolve_view(initial_group, initial_section, initial_lens)
        self.initial = report
        self.initial_group, self.initial_section = group, section
        self.view_notice = view_notice or notice
        self.probe_summary = probe_summary
        self.workspace = workspace.resolve() if workspace is not None else None
        self.run_directory = run_directory.resolve() if run_directory is not None else None

    def state(self, selection="latest"):
        if selection not in {"latest", "setup"}:
            raise ConfigurationError("Select latest matching execution or setup only.")
        if self.workspace is not None:
            compiled = compile_plan(self.workspace)
            report = plan_report(compiled)
            if selection == "latest" and (self.workspace / "trials").is_dir() and not (self.workspace / "trials").is_symlink():
                candidates = sorted((self.workspace / "trials").iterdir(), key=lambda p: p.name, reverse=True)[:100]
                for path in candidates:
                    if path.is_symlink() or not path.is_dir():
                        continue
                    identity = path / "team-run.json"
                    if not identity.is_file() or identity.is_symlink() or identity.stat().st_size > 100_000:
                        continue
                    try:
                        value = json.loads(identity.read_text())
                        if value.get("configuration_sha256") == compiled["configuration_sha256"]:
                            report = build_report(path)
                            break
                    except (OSError, ValueError, KeyError):
                        continue  # A new checkpoint may still be being created; do not invent observations.
            can_draft = compiled["schema_version"] == 3
        elif self.run_directory is not None:
            report, can_draft = build_report(self.run_directory), False
        else:
            report, can_draft = self.initial, False
        return {**with_views(report, self.probe_summary), "viewer": {"live": True, "draft_available": can_draft, "initial_group": self.initial_group, "initial_section": self.initial_section, "view_notice": self.view_notice,
            "selection": selection if self.workspace is not None else "saved_run", "read_at": datetime.now(timezone.utc).isoformat()}}

    def draft(self, values):
        if self.workspace is None:
            raise ConfigurationError("Drafting requires 'teamknitt view --workspace PATH'; saved runs remain immutable.")
        allowed = {"topology", "members", "communication", "purpose", "max_read_words"}
        if set(values) - allowed or any(len(v) != 1 for v in values.values()):
            raise ConfigurationError("Draft parameters must be single, known team controls.")
        def one(key):
            return values.get(key, [None])[0]
        count = int(one("members")) if one("members") is not None else None
        words = int(one("max_read_words")) if one("max_read_words") is not None else None
        c = draft_configuration(load(self.workspace), topology=one("topology"), count=count,
            communication=one("communication"), purpose=one("purpose"), max_read_words=words)
        report = plan_report(compile_plan(self.workspace, c))
        return {**with_views(report, self.probe_summary), "viewer": {"live": True, "draft_available": True, "initial_group": self.initial_group, "initial_section": self.initial_section, "view_notice": self.view_notice, "selection": "draft_only",
            "notice": "Local preview only. No configuration, task text, model, budget or run was changed."}}


def handler(service):
    class Handler(BaseHTTPRequestHandler):
        def send(self, content, content_type, status=200):
            self.send_response(status)
            for key, value in {"Content-Type": content_type, "Content-Length": str(len(content)),
                "Cache-Control": "no-store", "Referrer-Policy": "no-referrer", "X-Content-Type-Options": "nosniff",
                "Content-Security-Policy": "default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; connect-src 'self'; base-uri 'none'; form-action 'none'; frame-ancestors 'self' https:"}.items():
                self.send_header(key, value)
            self.end_headers()
            self.wfile.write(content)

        def do_GET(self):
            path = urlsplit(self.path)
            if len(self.path) > 4096:
                self.send_error(414)
                return
            try:
                query = parse_qs(path.query, keep_blank_values=True, max_num_fields=10)
                if path.path == "/":
                    self.send(html(service.state()).encode(), "text/html; charset=utf-8")
                elif path.path == "/api/state":
                    if set(query) - {"selection"} or len(query.get("selection", ["latest"])) != 1:
                        raise ConfigurationError("Unknown state selection.")
                    self.send(json.dumps(service.state(query.get("selection", ["latest"])[0]), allow_nan=False).encode(), "application/json")
                elif path.path == "/api/draft":
                    self.send(json.dumps(service.draft(query), allow_nan=False).encode(), "application/json")
                else:
                    self.send_error(404)
            except (ConfigurationError, OSError, ValueError) as error:
                self.send(json.dumps({"error": str(error)}).encode(), "application/json", 400)

        def do_POST(self):
            self.send_error(405, "Read-only service: use the explicit CLI to apply a reviewed draft or start execution.")

        def log_message(self, *_):
            return
    return Handler


def serve(report, port=8766, *, workspace=None, run_directory=None, initial_group=None, initial_section=None, view_notice=None, probe_summary=None):
    service = ViewerService(report, workspace=workspace, run_directory=run_directory, initial_group=initial_group, initial_section=initial_section, view_notice=view_notice, probe_summary=probe_summary)
    with ThreadingHTTPServer(("127.0.0.1", port), handler(service)) as server:
        print(f"teamknitt workspace: http://127.0.0.1:{server.server_address[1]}", flush=True)
        print("Draft previews and metadata monitoring only. No models, configuration writes or run-start API. Ctrl-C stops the viewer.", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
    return {"status": "viewer_stopped", "api_calls": 0}
