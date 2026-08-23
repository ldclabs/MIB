from __future__ import annotations

import collections
import json
import select
import subprocess
import threading
import urllib.error
import urllib.request
from dataclasses import asdict
from typing import Any

from .sandbox import SandboxPolicy, SandboxProcess, spawn_sandboxed_stdio
from .types import ActStep, AgentOutput, Observation

# A submission is untrusted: it must not be able to exhaust evaluator memory by
# emitting one unbounded line, and its stderr must be drained continuously or a
# full pipe buffer deadlocks the Runner.
MAX_RESPONSE_CHARS = 8 * 1024 * 1024
MAX_STDERR_TAIL_CHARS = 64 * 1024
MAX_HTTP_RESPONSE_BYTES = 8 * 1024 * 1024


class AgentTransportError(RuntimeError):
    pass


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Refuse redirects so request headers (credentials) reach one host only."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: D102
        raise AgentTransportError(f"Agent endpoint attempted a redirect to {newurl!r}; refusing to follow")


# Correlation fields the Runner actually transmits.  A binding that carries no
# request envelope (the HTTP ``GET /describe`` profile) can only be checked on
# the protocol identity, because the Agent was never told a request_id/run_id.
IDENTITY_FIELDS = ("mib", "protocol", "request_id", "run_id")
PROTOCOL_IDENTITY_FIELDS = ("mib", "protocol")


def _check_response(
    resp: dict[str, Any],
    request: dict[str, Any],
    identity_fields: tuple[str, ...] = IDENTITY_FIELDS,
) -> dict[str, Any]:
    if not isinstance(resp, dict):
        raise AgentTransportError("Agent response must be a JSON object")
    for field in identity_fields:
        if resp.get(field) != request.get(field):
            raise AgentTransportError(
                f"Agent response {field} mismatch: expected {request.get(field)!r}, "
                f"got {resp.get(field)!r}{_reported_error(resp)}"
            )
    if resp.get("status") != "ok":
        err = resp.get("error") or {}
        raise AgentTransportError(f"{err.get('code', 'error')}: {err.get('message', resp)!s}")
    return resp.get("body") or {}


def _reported_error(resp: dict[str, Any]) -> str:
    """Keep the Agent's own error visible when the envelope also fails to correlate.

    An Adapter that could not parse the request answers with ``request_id:
    "unknown"``.  Reporting only the mismatch would hide the error that actually
    explains the failure.
    """
    err = resp.get("error")
    if resp.get("status") == "error" and isinstance(err, dict):
        return f" (Agent reported {err.get('code', 'error')}: {err.get('message')})"
    return ""


class StdioAgentAdapter:
    """MIB Agent Adapter client over JSON Lines stdio."""

    def __init__(
        self,
        command: list[str],
        *,
        timeout_seconds: float = 30.0,
        sandbox_policy: SandboxPolicy | None = None,
        env: dict[str, str] | None = None,
        stage: list[dict[str, str]] | None = None,
        persistent: bool = False,
    ) -> None:
        self.command = list(command)
        self.timeout_seconds = float(timeout_seconds)
        self.sandbox: SandboxProcess = spawn_sandboxed_stdio(self.command, policy=sandbox_policy, env=env, stage=stage)
        self.proc = self.sandbox.process
        self.persistent = bool(persistent)
        self._reset_request_ids: dict[str, str] = {}
        # Continuously drain stderr into a bounded tail.  Without this a chatty
        # submission fills the pipe buffer and blocks while the Runner blocks on
        # stdout, deadlocking the whole evaluation.
        self._stderr_tail: collections.deque[str] = collections.deque()
        self._stderr_len = 0
        self._stderr_lock = threading.Lock()
        self._stderr_thread: threading.Thread | None = None
        if self.proc.stderr is not None:
            self._stderr_thread = threading.Thread(target=self._drain_stderr, daemon=True)
            self._stderr_thread.start()

    def _drain_stderr(self) -> None:
        stream = self.proc.stderr
        if stream is None:
            return
        try:
            for chunk in iter(lambda: stream.read(4096), ""):
                if not chunk:
                    break
                with self._stderr_lock:
                    self._stderr_tail.append(chunk)
                    self._stderr_len += len(chunk)
                    while self._stderr_len > MAX_STDERR_TAIL_CHARS and self._stderr_tail:
                        self._stderr_len -= len(self._stderr_tail.popleft())
        except Exception:
            return

    def _stderr_snapshot(self) -> str:
        with self._stderr_lock:
            return "".join(self._stderr_tail)[-2000:]

    def _rpc(self, request: dict[str, Any]) -> dict[str, Any]:
        if self.proc.poll() is not None:
            raise AgentTransportError(
                f"stdio Agent exited with code {self.proc.returncode}: {self._stderr_snapshot()}"
            )
        line = json.dumps(request, separators=(",", ":"), ensure_ascii=False)
        assert self.proc.stdin is not None and self.proc.stdout is not None
        self.proc.stdin.write(line + "\n")
        self.proc.stdin.flush()

        if hasattr(self.proc.stdout, "fileno"):
            ready, _, _ = select.select([self.proc.stdout], [], [], self.timeout_seconds)
            if not ready:
                # A response may still arrive after the timeout.  Reusing this
                # JSONL stream would let the next request consume that stale line
                # as its own response, so a timed-out channel is no longer safe.
                self.sandbox.terminate()
                raise TimeoutError(f"stdio Agent timed out after {self.timeout_seconds}s")
        # Bounded read: an untrusted Agent must not be able to OOM the Runner
        # with a single unterminated line.
        response_line = self.proc.stdout.readline(MAX_RESPONSE_CHARS)
        if not response_line:
            raise AgentTransportError(f"stdio Agent closed output: {self._stderr_snapshot()}")
        if not response_line.endswith("\n") and len(response_line) >= MAX_RESPONSE_CHARS:
            raise AgentTransportError(
                f"stdio Agent response exceeded {MAX_RESPONSE_CHARS} characters"
            )
        return json.loads(response_line)

    def describe(self) -> dict[str, Any]:
        req = {"mib": "0.1", "protocol": "mib-agent/0.1", "request_id": "describe", "run_id": "descriptor", "operation": "describe", "body": {}}
        body = _check_response(self._rpc(req), req)
        # Surface sandbox enforcement facts in descriptor diagnostics.
        body = dict(body)
        body.setdefault("extensions", {})["mib.sandbox"] = {
            "transport": "stdio",
            "network_isolated": self.sandbox.network_isolated,
            "filesystem_isolated": self.sandbox.filesystem_isolated,
            "warnings": list(self.sandbox.warnings),
        }
        return body

    def reset(self, *, run_id: str, seed, virtual_time: str | None) -> dict[str, Any]:
        rid = self._reset_request_ids.setdefault(run_id, f"reset:{run_id}")
        req = {"mib": "0.1", "protocol": "mib-agent/0.1", "request_id": rid, "run_id": run_id, "operation": "reset", "virtual_time": virtual_time, "body": {"mode": "fresh", "seed": seed, "virtual_time": virtual_time}}
        return _check_response(self._rpc(req), req)

    def observe(self, *, run_id: str, request_id: str, observation: Observation) -> dict[str, Any]:
        req = {"mib": "0.1", "protocol": "mib-agent/0.1", "request_id": request_id, "run_id": run_id, "operation": "observe", "virtual_time": observation.virtual_time, "body": {"observation": asdict(observation)}}
        return _check_response(self._rpc(req), req)

    def respond(self, *, run_id: str, request_id: str, interaction_id: str, input_data: dict[str, Any], virtual_time: str | None) -> AgentOutput:
        req = {"mib": "0.1", "protocol": "mib-agent/0.1", "request_id": request_id, "run_id": run_id, "operation": "respond", "virtual_time": virtual_time, "body": {"interaction_id": interaction_id, "input": input_data}}
        body = _check_response(self._rpc(req), req)
        return AgentOutput(**body["output"])

    def act(self, *, run_id: str, request_id: str, task_id: str, goal: str | None, constraints: list[str], tools: list[dict[str, Any]], continuation: bool, virtual_time: str | None) -> ActStep:
        req = {"mib": "0.1", "protocol": "mib-agent/0.1", "request_id": request_id, "run_id": run_id, "operation": "act", "virtual_time": virtual_time, "body": {"task_id": task_id, "goal": goal, "constraints": constraints, "tools": tools, "continuation": continuation}}
        body = _check_response(self._rpc(req), req)
        return ActStep(**body["result"])

    def close(self, *, run_id: str | None = None) -> None:
        try:
            if run_id and self.proc.poll() is None:
                req = {"mib": "0.1", "protocol": "mib-agent/0.1", "request_id": f"close:{run_id}", "run_id": run_id, "operation": "close", "body": {"reason": "run_complete"}}
                self._rpc(req)
        except Exception:
            pass
        finally:
            if not self.persistent:
                self.sandbox.terminate()

    def shutdown(self) -> None:
        self.sandbox.terminate()


class HttpAgentAdapter:
    """MIB Agent Adapter client over the reference HTTP profile."""

    def __init__(self, base_url: str, *, timeout_seconds: float = 30.0, headers: dict[str, str] | None = None) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = float(timeout_seconds)
        self.headers = {"Content-Type": "application/json", **(headers or {})}
        self._opener = urllib.request.build_opener(_NoRedirectHandler)

    def _request(self, operation: str, payload: dict[str, Any] | None = None, *, method: str = "POST") -> dict[str, Any]:
        url = f"{self.base_url}/mib-agent/v0.1/{operation}"
        data = None if method == "GET" else json.dumps(payload or {}, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers=self.headers, method=method)
        try:
            with self._opener.open(req, timeout=self.timeout_seconds) as resp:
                raw = resp.read(MAX_HTTP_RESPONSE_BYTES + 1)
            if len(raw) > MAX_HTTP_RESPONSE_BYTES:
                raise AgentTransportError(f"Agent response exceeded {MAX_HTTP_RESPONSE_BYTES} bytes")
            return json.loads(raw.decode("utf-8"))
        except urllib.error.HTTPError as exc:
            body = exc.read(65536).decode("utf-8", "replace")
            raise AgentTransportError(f"HTTP {exc.code}: {body}") from exc

    def describe(self) -> dict[str, Any]:
        # ``GET /describe`` carries no request envelope, so the Agent cannot echo
        # a request_id/run_id it was never sent.
        req = {"mib": "0.1", "protocol": "mib-agent/0.1", "operation": "describe", "body": {}}
        return _check_response(
            self._request("describe", method="GET"), req, PROTOCOL_IDENTITY_FIELDS
        )

    def reset(self, *, run_id: str, seed, virtual_time: str | None) -> dict[str, Any]:
        req = {"mib": "0.1", "protocol": "mib-agent/0.1", "request_id": f"reset:{run_id}", "run_id": run_id, "operation": "reset", "virtual_time": virtual_time, "body": {"mode": "fresh", "seed": seed, "virtual_time": virtual_time}}
        return _check_response(self._request("reset", req), req)

    def observe(self, *, run_id: str, request_id: str, observation: Observation) -> dict[str, Any]:
        req = {"mib": "0.1", "protocol": "mib-agent/0.1", "request_id": request_id, "run_id": run_id, "operation": "observe", "virtual_time": observation.virtual_time, "body": {"observation": asdict(observation)}}
        return _check_response(self._request("observe", req), req)

    def respond(self, *, run_id: str, request_id: str, interaction_id: str, input_data: dict[str, Any], virtual_time: str | None) -> AgentOutput:
        req = {"mib": "0.1", "protocol": "mib-agent/0.1", "request_id": request_id, "run_id": run_id, "operation": "respond", "virtual_time": virtual_time, "body": {"interaction_id": interaction_id, "input": input_data}}
        body = _check_response(self._request("respond", req), req)
        return AgentOutput(**body["output"])

    def act(self, *, run_id: str, request_id: str, task_id: str, goal: str | None, constraints: list[str], tools: list[dict[str, Any]], continuation: bool, virtual_time: str | None) -> ActStep:
        req = {"mib": "0.1", "protocol": "mib-agent/0.1", "request_id": request_id, "run_id": run_id, "operation": "act", "virtual_time": virtual_time, "body": {"task_id": task_id, "goal": goal, "constraints": constraints, "tools": tools, "continuation": continuation}}
        body = _check_response(self._request("act", req), req)
        return ActStep(**body["result"])

    def close(self, *, run_id: str | None = None) -> None:
        if not run_id:
            return
        req = {"mib": "0.1", "protocol": "mib-agent/0.1", "request_id": f"close:{run_id}", "run_id": run_id, "operation": "close", "body": {"reason": "run_complete"}}
        try:
            _check_response(self._request("close", req), req)
        except Exception:
            pass
