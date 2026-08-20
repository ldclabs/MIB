from __future__ import annotations

import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Callable

from .protocol import AgentHost, error_response


def serve_stdio(agent_factory: Callable[[], Any]) -> int:
    host = AgentHost(agent_factory)
    for raw in sys.stdin:
        raw = raw.strip()
        if not raw:
            continue
        try:
            req = json.loads(raw)
            resp = host.dispatch(req)
        except Exception as exc:
            resp = error_response({}, "invalid_request", repr(exc))
        sys.stdout.write(json.dumps(resp, separators=(",", ":"), ensure_ascii=False) + "\n")
        sys.stdout.flush()
    return 0


def make_http_handler(agent_factory: Callable[[], Any]):
    host = AgentHost(agent_factory)

    class Handler(BaseHTTPRequestHandler):
        server_version = "MIBAgentHTTP/0.1"

        def log_message(self, fmt: str, *args) -> None:
            # Protocol test servers should not pollute stdout.
            sys.stderr.write((fmt % args) + "\n")

        def _write(self, status: int, payload: dict[str, Any]) -> None:
            body = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _operation(self) -> str:
            return self.path.rstrip("/").split("/")[-1]

        def do_GET(self) -> None:  # noqa: N802
            op = self._operation()
            if op != "describe":
                self._write(404, {"error": "not_found"})
                return
            req = {"mib": "0.1", "protocol": "mib-agent/0.1", "request_id": "describe", "run_id": "descriptor", "operation": "describe", "body": {}}
            self._write(200, host.dispatch(req))

        def do_POST(self) -> None:  # noqa: N802
            length = int(self.headers.get("Content-Length", "0"))
            try:
                req = json.loads(self.rfile.read(length).decode("utf-8")) if length else {}
            except Exception as exc:
                self._write(400, error_response({}, "invalid_request", repr(exc)))
                return
            op = self._operation()
            if req.get("operation") != op:
                self._write(400, error_response(req, "invalid_request", "URL operation does not match request.operation"))
                return
            resp = host.dispatch(req)
            self._write(200 if resp.get("status") == "ok" else 400, resp)

    return Handler


def serve_http(agent_factory: Callable[[], Any], host: str = "127.0.0.1", port: int = 8080) -> None:
    server = ThreadingHTTPServer((host, port), make_http_handler(agent_factory))
    server.serve_forever()
