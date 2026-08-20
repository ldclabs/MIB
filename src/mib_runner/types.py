from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

Json = Any


@dataclass(slots=True)
class Observation:
    observation_id: str
    type: str
    virtual_time: str | None = None
    actor: dict[str, Any] | None = None
    content: str | None = None
    payload: Any = None
    tool_call_id: str | None = None
    tool: str | None = None


@dataclass(slots=True)
class Emission:
    emission_id: str
    type: str
    content: str | None = None
    name: str | None = None
    payload: Any = None


@dataclass(slots=True)
class AgentOutput:
    type: str
    content: str | None = None
    value: Any = None
    attribution: dict[str, Any] | None = None


@dataclass(slots=True)
class ActStep:
    type: str
    tool_call_id: str | None = None
    tool: str | None = None
    arguments: Any = None
    content: str | None = None
    value: Any = None
    attribution: dict[str, Any] | None = None


class AgentAdapter(Protocol):
    """In-process semantics for MIB Agent Adapter v0.1."""

    def describe(self) -> dict[str, Any]: ...

    def reset(
        self,
        *,
        run_id: str,
        seed: int | str | None,
        virtual_time: str | None,
    ) -> dict[str, Any]: ...

    def observe(
        self,
        *,
        run_id: str,
        request_id: str,
        observation: Observation,
    ) -> dict[str, Any]: ...

    def respond(
        self,
        *,
        run_id: str,
        request_id: str,
        interaction_id: str,
        input_data: dict[str, Any],
        virtual_time: str | None,
    ) -> AgentOutput: ...

    def act(
        self,
        *,
        run_id: str,
        request_id: str,
        task_id: str,
        goal: str | None,
        constraints: list[str],
        tools: list[dict[str, Any]],
        continuation: bool,
        virtual_time: str | None,
    ) -> ActStep: ...
