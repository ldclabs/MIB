from __future__ import annotations

import json
import select
import subprocess
import time
import urllib.error
import urllib.request
from dataclasses import asdict
from typing import Any

from .sandbox import SandboxPolicy, SandboxProcess, spawn_sandboxed_stdio
from .types import ActStep, AgentOutput, Observation


class AgentTransportError(RuntimeError):
    pass


def _check_response(resp: dict[str, Any]) -> dict[str, Any]:
    if resp.get("status") != "ok":
        err = resp.get("error") or {}
        raise AgentTransportError(f"{err.get('code', 'error')}: {err.get('message', resp)!s}")
    return resp.get("body") or {}


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

    def _rpc(self, request: dict[str, Any]) -> dict[str, Any]:
        if self.proc.poll() is not None:
            stderr = self.proc.stderr.read() if self.proc.stderr else ""
            raise AgentTransportError(f"stdio Agent exited with code {self.proc.returncode}: {stderr[-2000:]}")
        line = json.dumps(request, separators=(",", ":"), ensure_ascii=False)
        assert self.proc.stdin is not None and self.proc.stdout is not None
        self.proc.stdin.write(line + "\n")
        self.proc.stdin.flush()

        if hasattr(self.proc.stdout, "fileno"):
            ready, _, _ = select.select([self.proc.stdout], [], [], self.timeout_seconds)
            if not ready:
                raise TimeoutError(f"stdio Agent timed out after {self.timeout_seconds}s")
        response_line = self.proc.stdout.readline()
        if not response_line:
            stderr = self.proc.stderr.read() if self.proc.stderr else ""
            raise AgentTransportError(f"stdio Agent closed output: {stderr[-2000:]}")
        return json.loads(response_line)

    def describe(self) -> dict[str, Any]:
        req = {"mib": "0.1", "protocol": "mib-agent/0.1", "request_id": "describe", "run_id": "descriptor", "operation": "describe", "body": {}}
        body = _check_response(self._rpc(req))
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
        return _check_response(self._rpc(req))

    def observe(self, *, run_id: str, request_id: str, observation: Observation) -> dict[str, Any]:
        req = {"mib": "0.1", "protocol": "mib-agent/0.1", "request_id": request_id, "run_id": run_id, "operation": "observe", "virtual_time": observation.virtual_time, "body": {"observation": asdict(observation)}}
        return _check_response(self._rpc(req))

    def respond(self, *, run_id: str, request_id: str, interaction_id: str, input_data: dict[str, Any], virtual_time: str | None) -> AgentOutput:
        req = {"mib": "0.1", "protocol": "mib-agent/0.1", "request_id": request_id, "run_id": run_id, "operation": "respond", "virtual_time": virtual_time, "body": {"interaction_id": interaction_id, "input": input_data}}
        body = _check_response(self._rpc(req))
        return AgentOutput(**body["output"])

    def act(self, *, run_id: str, request_id: str, task_id: str, goal: str | None, constraints: list[str], tools: list[dict[str, Any]], continuation: bool, virtual_time: str | None) -> ActStep:
        req = {"mib": "0.1", "protocol": "mib-agent/0.1", "request_id": request_id, "run_id": run_id, "operation": "act", "virtual_time": virtual_time, "body": {"task_id": task_id, "goal": goal, "constraints": constraints, "tools": tools, "continuation": continuation}}
        body = _check_response(self._rpc(req))
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

    def _request(self, operation: str, payload: dict[str, Any] | None = None, *, method: str = "POST") -> dict[str, Any]:
        url = f"{self.base_url}/mib-agent/v0.1/{operation}"
        data = None if method == "GET" else json.dumps(payload or {}, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers=self.headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout_seconds) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", "replace")
            raise AgentTransportError(f"HTTP {exc.code}: {body}") from exc

    def describe(self) -> dict[str, Any]:
        return _check_response(self._request("describe", method="GET"))

    def reset(self, *, run_id: str, seed, virtual_time: str | None) -> dict[str, Any]:
        req = {"mib": "0.1", "protocol": "mib-agent/0.1", "request_id": f"reset:{run_id}", "run_id": run_id, "operation": "reset", "virtual_time": virtual_time, "body": {"mode": "fresh", "seed": seed, "virtual_time": virtual_time}}
        return _check_response(self._request("reset", req))

    def observe(self, *, run_id: str, request_id: str, observation: Observation) -> dict[str, Any]:
        req = {"mib": "0.1", "protocol": "mib-agent/0.1", "request_id": request_id, "run_id": run_id, "operation": "observe", "virtual_time": observation.virtual_time, "body": {"observation": asdict(observation)}}
        return _check_response(self._request("observe", req))

    def respond(self, *, run_id: str, request_id: str, interaction_id: str, input_data: dict[str, Any], virtual_time: str | None) -> AgentOutput:
        req = {"mib": "0.1", "protocol": "mib-agent/0.1", "request_id": request_id, "run_id": run_id, "operation": "respond", "virtual_time": virtual_time, "body": {"interaction_id": interaction_id, "input": input_data}}
        body = _check_response(self._request("respond", req))
        return AgentOutput(**body["output"])

    def act(self, *, run_id: str, request_id: str, task_id: str, goal: str | None, constraints: list[str], tools: list[dict[str, Any]], continuation: bool, virtual_time: str | None) -> ActStep:
        req = {"mib": "0.1", "protocol": "mib-agent/0.1", "request_id": request_id, "run_id": run_id, "operation": "act", "virtual_time": virtual_time, "body": {"task_id": task_id, "goal": goal, "constraints": constraints, "tools": tools, "continuation": continuation}}
        body = _check_response(self._request("act", req))
        return ActStep(**body["result"])

    def close(self, *, run_id: str | None = None) -> None:
        if not run_id:
            return
        req = {"mib": "0.1", "protocol": "mib-agent/0.1", "request_id": f"close:{run_id}", "run_id": run_id, "operation": "close", "body": {"reason": "run_complete"}}
        try:
            _check_response(self._request("close", req))
        except Exception:
            pass
