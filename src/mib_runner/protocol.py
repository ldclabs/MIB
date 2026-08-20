from __future__ import annotations

from dataclasses import asdict
from typing import Any, Callable

from .types import ActStep, AgentOutput, Observation

PROTOCOL = "mib-agent/0.1"


def ok_response(request: dict[str, Any], body: Any) -> dict[str, Any]:
    return {
        "mib": "0.1",
        "protocol": PROTOCOL,
        "request_id": request.get("request_id", "describe"),
        "run_id": request.get("run_id", "descriptor"),
        "status": "ok",
        "body": body,
    }


def error_response(request: dict[str, Any], code: str, message: str, retryable: bool = False) -> dict[str, Any]:
    return {
        "mib": "0.1",
        "protocol": PROTOCOL,
        "request_id": request.get("request_id", "unknown"),
        "run_id": request.get("run_id", "unknown"),
        "status": "error",
        "error": {"code": code, "message": message, "retryable": retryable},
    }


class AgentHost:
    """Protocol host that gives every run_id its own Agent instance."""

    def __init__(self, agent_factory: Callable[[], Any]) -> None:
        self.agent_factory = agent_factory
        self.agents: dict[str, Any] = {}
        self.descriptor = agent_factory().describe()

    def dispatch(self, request: dict[str, Any]) -> dict[str, Any]:
        try:
            op = request.get("operation")
            if op == "describe":
                return ok_response(request, self.descriptor)
            run_id = request.get("run_id")
            if not run_id:
                return error_response(request, "invalid_request", "run_id is required")
            body = request.get("body") or {}
            vt = request.get("virtual_time")
            if op == "reset":
                agent = self.agent_factory()
                self.agents[run_id] = agent
                result = agent.reset(run_id=run_id, seed=body.get("seed"), virtual_time=body.get("virtual_time") or vt)
                return ok_response(request, result)
            if op == "close":
                self.agents.pop(run_id, None)
                return ok_response(request, {"closed": True})
            if run_id not in self.agents:
                return error_response(request, "invalid_state", "run_id has not been reset")
            agent = self.agents[run_id]
            rid = request.get("request_id") or "req"
            if op == "observe":
                o = body["observation"]
                obs = Observation(**o)
                return ok_response(request, agent.observe(run_id=run_id, request_id=rid, observation=obs))
            if op == "respond":
                out = agent.respond(
                    run_id=run_id,
                    request_id=rid,
                    interaction_id=body["interaction_id"],
                    input_data=body.get("input") or {},
                    virtual_time=vt,
                )
                return ok_response(request, {"interaction_id": body["interaction_id"], "output": asdict(out)})
            if op == "act":
                step = agent.act(
                    run_id=run_id,
                    request_id=rid,
                    task_id=body["task_id"],
                    goal=body.get("goal"),
                    constraints=list(body.get("constraints") or []),
                    tools=list(body.get("tools") or []),
                    continuation=bool(body.get("continuation", False)),
                    virtual_time=vt,
                )
                return ok_response(request, {"task_id": body["task_id"], "result": asdict(step)})
            return error_response(request, "unsupported_operation", f"unsupported operation: {op}")
        except Exception as exc:
            return error_response(request, "internal_error", repr(exc), retryable=False)
