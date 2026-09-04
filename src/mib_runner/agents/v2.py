"""Reference Agents for generated Scenarios (MIB v0.2).

None of these reads an Oracle.  ``StructuredMemoryAgent`` keeps perfect
structured memory by parsing the generated surface language with the same
grammar the generator uses (a B3-like fixture); ``WindowMemoryAgent`` is the
same Agent limited to its last *k* observations, so its retention curve decays
on the ladder; ``RecencyAgent`` treats every mention as a fact and lets the
last one win (the naive associative memory the interrogation lane detects);
``NoMemoryAgent`` ignores the past entirely.
"""

from __future__ import annotations

import re
from typing import Any

from .. import __version__
from ..generate.pools import ATTRIBUTES, NAMES
from ..generate.surface import parse, parse_prompt
from ..types import ActStep, AgentOutput, Observation
from ..worldmodel import Assertion, Source, WorldModel

_COMMITMENT = re.compile(
    r"^(?:when|next time) (?P<name>[A-Z][a-z]+) joins (?:the|a) call, (?:please )?remind me (?:to ask )?about the (?P<topic>.+?)\.$",
    re.IGNORECASE,
)
_TRIGGER = re.compile(r"^(?P<name>[A-Z][a-z]+) (?:has just )?joined the call\.$", re.IGNORECASE)
_LIMITATION = re.compile(r"you (?:are not allowed to|must never) restart", re.IGNORECASE)
_WORKSPACE = re.compile(r"'(?P<ws>[a-z]+)' workspace", re.IGNORECASE)
_NAME_IDS = {n.lower(): n for n in NAMES}


def _describe(name: str, memory: bool) -> dict[str, Any]:
    return {
        "protocol": "mib-agent/0.1",
        "implementation": {"name": name, "version": __version__, "vendor": "MIB"},
        "track_support": ["integrated_agent"],
        "capabilities": {
            "observe": True, "respond": True, "act": True, "spontaneous_emissions": memory,
            "maintenance": memory, "runner_managed_tools": True, "structured_output": True,
            "virtual_time": True, "seedable": True,
        },
        "state": {"run_isolation": "hard", "observe_visibility": "read_after_write", "request_idempotency": True},
    }


class _ActPolicies:
    """Tool policies shared by the fixtures; learning is decided by the subclass."""

    def _task_state(self, task_id: str, goal: str | None, tools: list[dict[str, Any]]) -> dict[str, Any]:
        state = self.task_states.setdefault(task_id, {"goal": goal or "", "tools": {t["name"] for t in tools}, "plan": None, "step": 0})
        if goal:
            state["goal"] = goal
        if tools:
            state["tools"] = {t["name"] for t in tools}
        return state

    def _call(self, tool: str, arguments: dict[str, Any] | None = None) -> ActStep:
        self.tool_call_counter += 1
        return ActStep(type="tool_call", tool_call_id=f"call_{self.tool_call_counter:04d}", tool=tool, arguments=arguments or {})

    def _last_result(self, task_id: str) -> dict[str, Any] | None:
        rows = [o for o in self.observations if o.type == "tool_result" and (o.observation_id in self.task_results.get(task_id, set()))]
        return rows[-1].payload if rows else None

    def _deployment(self, task_id: str, state: dict[str, Any], learned_inspect: bool, recover: bool, limited: bool = False) -> ActStep:
        plan = state["plan"]
        if plan is None:
            steps = ["inspect", "select", "migrate", "restart"] if learned_inspect else ["migrate", "restart"]
            plan = state["plan"] = [x for x in steps if not (limited and x == "restart")]
            state["limited"] = limited
        last = self._last_result(task_id)
        if last and last.get("success") is False and recover and "recover" not in state:
            # The lived failure: read the error, inspect, select the real target, then retry.
            state["recover"] = True
            state["plan"] = [x for x in ["read_error", "inspect", "select", "migrate", "restart"] if not (state.get("limited") and x == "restart")]
            state["step"] = 0
            plan = state["plan"]
        if state["step"] >= len(plan):
            if state.get("limited"):
                return ActStep(type="final", content="Migration applied. I am not allowed to restart services; handing the restart over.")
            return ActStep(type="final", content="Deployment attempt complete.")
        op = plan[state["step"]]
        state["step"] += 1
        if op == "inspect":
            return self._call("deployment.inspect_target")
        if op == "select":
            target = (last or {}).get("actual_target") if last and last.get("actual_target") else None
            if not target:
                # No inspection result at hand: inspect first, then select.
                state["plan"].insert(state["step"] - 1, "inspect")
                state["step"] -= 1
                return self._call("deployment.inspect_target")
            return self._call("deployment.select_target", {"target": target})
        if op == "migrate":
            return self._call("deployment.run_migration")
        if op == "restart":
            return self._call("deployment.restart_service")
        if op == "read_error":
            return self._call("deployment.read_error")
        return ActStep(type="final", content="Deployment attempt complete.")

    def _canvas(self, task_id: str, state: dict[str, Any], learned_context: bool, recover: bool) -> ActStep:
        goal = state["goal"]
        ws = _WORKSPACE.search(goal)
        is_global = "global record" in goal.lower() or "no context activation" in goal.lower()
        plan = state["plan"]
        if plan is None:
            if is_global:
                plan = ["edit", "commit"]
            elif learned_context and ws:
                plan = ["activate", "edit", "commit"]
            else:
                plan = ["edit", "commit"]
            state["plan"] = plan
        last = self._last_result(task_id)
        if last and last.get("error") == "context_required" and recover and ws and "recover" not in state:
            state["recover"] = True
            state["plan"] = ["activate", "commit"]
            state["step"] = 0
            plan = state["plan"]
        if state["step"] >= len(plan):
            return ActStep(type="final", content="Commit attempt complete.")
        op = plan[state["step"]]
        state["step"] += 1
        if op == "activate":
            return self._call("canvas.activate_context", {"context": ws.group("ws") if ws else "default"})
        if op == "edit":
            return self._call("canvas.edit_item", {"value": "updated"})
        if op == "commit":
            return self._call("canvas.commit")
        return ActStep(type="final", content="Commit attempt complete.")


class StructuredMemoryAgent(_ActPolicies):
    """Perfect structured memory over the generated language, optionally windowed."""

    NAME = "MIB Structured Memory Fixture"
    window: int | None = None
    learns = True
    recovers = True

    def __init__(self, window: int | None = None) -> None:
        if window is not None:
            self.window = window
        self.reset(run_id="", seed=None, virtual_time=None)

    def describe(self) -> dict[str, Any]:
        return _describe(self.NAME + (f" (window {self.window})" if self.window else ""), memory=True)

    def reset(self, *, run_id: str, seed: Any, virtual_time: str | None) -> dict[str, Any]:
        self.run_id = run_id
        self.observations: list[Observation] = []
        self.seen_requests: set[tuple[str, str]] = set()
        self.responses: dict[tuple[str, str], AgentOutput] = {}
        self.act_responses: dict[tuple[str, str], ActStep] = {}
        self.task_states: dict[str, dict[str, Any]] = {}
        self.task_results: dict[str, set[str]] = {}
        self.current_task: str | None = None
        self.tool_call_counter = 0
        self.fired: set[str] = set()
        return {"accepted": True}

    # ------------------------------------------------------------- memory
    def _memory(self) -> list[Observation]:
        return self.observations[-self.window:] if self.window else list(self.observations)

    def _model(self) -> WorldModel:
        model = WorldModel()
        last_by_source: dict[tuple[str, str, str], str] = {}
        for seq, o in enumerate(self._memory(), start=1):
            actor_id = (o.actor or {}).get("id")
            if o.type == "tool_result" and isinstance(o.payload, dict) and o.payload.get("kind") == "lookup":
                tool = str(o.payload.get("tool") or o.tool or "tool")
                if tool not in model.sources:
                    model.add_source(Source(tool, "tool", 1.0, tool))
                model.add(Assertion(o.observation_id, seq, tool, str(o.payload["subject"]), str(o.payload["attribute"]),
                                    o.payload["value"], "observation", True))
                continue
            if not o.content or not actor_id:
                continue
            parsed = parse(o.content)
            if parsed is None:
                continue
            if actor_id not in model.sources:
                model.add_source(Source(actor_id, (o.actor or {}).get("kind") or "person", 0.5, (o.actor or {}).get("display_name")))
            subject = actor_id if parsed.perspective == "first" else str(parsed.subject or "").lower().replace(" ", "")
            if parsed.subject and parsed.perspective == "third" and parsed.attribute == "meeting_start":
                subject = "review"
            if parsed.kind == "retraction":
                # "Forget what I said": withdraw the latest statement by this source on that attribute.
                model.add(Assertion(o.observation_id, seq, actor_id, subject, parsed.attribute, None, "retraction", False,
                                    last_by_source.get((actor_id, subject, parsed.attribute))))
                continue
            truth = self._truth_bearing(parsed.kind, parsed.perspective)
            supersedes = last_by_source.get((actor_id, subject, parsed.attribute)) if parsed.kind == "correction" else None
            model.add(Assertion(o.observation_id, seq, actor_id, subject, parsed.attribute, parsed.value, parsed.kind, truth, supersedes))
            if parsed.kind in ("state", "update", "correction", "contradiction", "observation"):
                last_by_source[(actor_id, subject, parsed.attribute)] = o.observation_id
        return model

    @staticmethod
    def _truth_bearing(kind: str, perspective: str) -> bool:
        if kind in ("question", "hypothetical", "contradiction", "retraction"):
            return False
        return True

    def _limited(self) -> bool:
        """A standing rule about the Agent itself (self memory): no restarts."""
        return any(_LIMITATION.search(o.content or "") for o in self._memory() if o.type != "tool_result")

    def _experience_errors(self) -> set[str]:
        errors = set()
        for o in self._memory():
            if o.type == "tool_result" and isinstance(o.payload, dict) and o.payload.get("success") is False and o.payload.get("error"):
                errors.add(str(o.payload["error"]))
        return errors

    # ------------------------------------------------------------ protocol
    def observe(self, *, run_id: str, request_id: str, observation: Observation) -> dict[str, Any]:
        key = (run_id, request_id)
        if key in self.seen_requests:
            return {"accepted": True, "emissions": []}
        self.seen_requests.add(key)
        if not any(o.observation_id == observation.observation_id for o in self.observations):
            self.observations.append(observation)
        if observation.type == "tool_result" and self.current_task:
            self.task_results.setdefault(self.current_task, set()).add(observation.observation_id)
        return {"accepted": True, "emissions": self._emissions_for(observation)}

    def _emissions_for(self, observation: Observation) -> list[dict[str, Any]]:
        if not observation.content:
            return []
        m = _TRIGGER.match(observation.content.strip())
        if not m:
            return []
        name = m.group("name")
        for o in self._memory():
            if not o.content:
                continue
            c = _COMMITMENT.match(o.content.strip())
            if c and c.group("name").lower() == name.lower() and o.observation_id not in self.fired:
                self.fired.add(o.observation_id)
                return [{"type": "reminder", "content": f"Reminder: ask {name} about the {c.group('topic')}."}]
        return []

    def maintain(self, *, run_id: str, request_id: str, budget: str | None = None, virtual_time: str | None = None) -> dict[str, Any]:
        return {"accepted": True, "consolidated": len(self.observations)}

    def respond(self, *, run_id: str, request_id: str, interaction_id: str, input_data: dict[str, Any], virtual_time: str | None) -> AgentOutput:
        key = (run_id, request_id)
        if key in self.responses:
            return self.responses[key]
        out = self._answer(input_data)
        self.responses[key] = out
        return out

    def _answer(self, input_data: dict[str, Any]) -> AgentOutput:
        prompt = str(input_data.get("content") or "")
        asker = str((input_data.get("context") or {}).get("actor") or "")
        pp = parse_prompt(prompt)
        if pp is None:
            return AgentOutput(type="abstention", content="unknown")
        model = self._model()
        subject = asker if pp.subject is None else pp.subject.lower().replace(" ", "")
        if pp.subject and pp.attribute == "meeting_start":
            subject = "review"
        attr = pp.attribute
        value: Any = None
        status = "known"
        if pp.which == "hop":
            value, _ = model.hop(subject, ["project", "schedule_zone", "utc"])
        elif pp.which == "current":
            value, _ = model.current(subject, attr)
        elif pp.which == "before":
            rows = model.truth_series(subject, attr)
            value = rows[-2][1] if len(rows) >= 2 else None
            status = "historical"
        elif pp.which == "first":
            value = model.first_stated(subject, attr)
            status = "historical"
        elif pp.which == "said_by":
            source = (pp.source or "").lower()
            value = model.said_by(source, subject, attr)
        elif pp.which == "status":
            value = model.status(subject, attr)
            status = "contested" if value == "contested" else "known"
        elif pp.which == "known":
            if model.known(subject, attr):
                value, _ = model.current(subject, attr)
            else:
                value = None
        if value is None:
            return AgentOutput(type="structured", value={"value": "unknown", "status": "unknown", "confidence": 0.9})
        return AgentOutput(type="structured", value={"value": str(value), "status": status, "confidence": 0.95})

    def act(self, *, run_id: str, request_id: str, task_id: str, goal: str | None, constraints: list[str],
            tools: list[dict[str, Any]], continuation: bool, virtual_time: str | None) -> ActStep:
        key = (run_id, request_id)
        if key in self.act_responses:
            return self.act_responses[key]
        self.current_task = task_id
        state = self._task_state(task_id, goal, tools)
        errors = self._experience_errors() if self.learns else set()
        names = state["tools"]
        if any(n.startswith("deployment.") for n in names):
            # A past wrong-target failure teaches inspect-first; the current task's own error is recovery, not learning.
            past_errors = {str(o.payload.get("error")) for o in self._memory()
                           if o.type == "tool_result" and isinstance(o.payload, dict) and o.payload.get("success") is False
                           and o.observation_id not in self.task_results.get(task_id, set())} if self.learns else set()
            step = self._deployment(task_id, state, learned_inspect="wrong_target" in past_errors, recover=self.recovers, limited=self._limited())
        elif any(n.startswith("canvas.") for n in names):
            past_errors = {str(o.payload.get("error")) for o in self._memory()
                           if o.type == "tool_result" and isinstance(o.payload, dict) and o.payload.get("success") is False
                           and o.observation_id not in self.task_results.get(task_id, set())} if self.learns else set()
            step = self._canvas(task_id, state, learned_context="context_required" in past_errors, recover=self.recovers)
        else:
            step = ActStep(type="abstention", content="No policy for these tools.")
        self.act_responses[key] = step
        return step


class WindowMemoryAgent(StructuredMemoryAgent):
    """The structured fixture with a short observation window: retention decays on the ladder."""

    NAME = "MIB Window Memory Fixture"
    window = 12


class RecencyAgent(StructuredMemoryAgent):
    """Every mention is a fact and the last one wins; no source, no correction, no question/fact distinction."""

    NAME = "MIB Recency Fixture"
    learns = False

    @staticmethod
    def _truth_bearing(kind: str, perspective: str) -> bool:
        return True

    def _model(self) -> WorldModel:
        model = super()._model()
        # A recency memory has no notion of withdrawing a fact: retractions are dropped.
        model.assertions = [a for a in model.assertions if a.kind != "retraction"]
        # Flatten everything into last-mention-wins state statements.
        for a in model.assertions:
            a.kind = "state" if a.kind != "observation" else "observation"
            a.truth_bearing = True
            a.supersedes = None
        return model


class ConsolidatingAgent(WindowMemoryAgent):
    """The window fixture with a working ``maintain``: each maintenance window archives everything
    observed so far into long-term memory, so consolidation is load-bearing (consolidation_benefit > 0)."""

    NAME = "MIB Consolidating Window Fixture"

    def reset(self, *, run_id: str, seed: Any, virtual_time: str | None) -> dict[str, Any]:
        out = super().reset(run_id=run_id, seed=seed, virtual_time=virtual_time)
        self.archive: list[Observation] = []
        return out

    def maintain(self, *, run_id: str, request_id: str, budget: str | None = None, virtual_time: str | None = None) -> dict[str, Any]:
        self.archive = list(self.observations)
        return {"accepted": True, "consolidated": len(self.archive)}

    def _memory(self) -> list[Observation]:
        window = super()._memory()
        archived = {o.observation_id for o in self.archive}
        return list(self.archive) + [o for o in window if o.observation_id not in archived]


class OvergeneralizingAgent(StructuredMemoryAgent):
    """Learns the skill and applies it everywhere, including where it is a policy violation:
    the fixture that the Negative Transfer control (§7.8) is designed to catch."""

    NAME = "MIB Overgeneralizing Fixture"

    def _canvas(self, task_id: str, state: dict[str, Any], learned_context: bool, recover: bool) -> ActStep:
        if learned_context and state["plan"] is None:
            state["plan"] = ["activate", "edit", "commit"]
        return super()._canvas(task_id, state, learned_context, recover)


class NoMemoryAgent(_ActPolicies):
    """Answers from the present only: abstains on every question, acts naively."""

    NAME = "MIB No-Memory Fixture"

    def __init__(self) -> None:
        self.reset(run_id="", seed=None, virtual_time=None)

    def describe(self) -> dict[str, Any]:
        return _describe(self.NAME, memory=False)

    def reset(self, *, run_id: str, seed: Any, virtual_time: str | None) -> dict[str, Any]:
        self.observations: list[Observation] = []
        self.task_states: dict[str, dict[str, Any]] = {}
        self.task_results: dict[str, set[str]] = {}
        self.current_task: str | None = None
        self.tool_call_counter = 0
        self.act_responses: dict[tuple[str, str], ActStep] = {}
        return {"accepted": True}

    def observe(self, *, run_id: str, request_id: str, observation: Observation) -> dict[str, Any]:
        if observation.type == "tool_result" and self.current_task:
            self.observations.append(observation)
            self.task_results.setdefault(self.current_task, set()).add(observation.observation_id)
        return {"accepted": True, "emissions": []}

    def respond(self, *, run_id: str, request_id: str, interaction_id: str, input_data: dict[str, Any], virtual_time: str | None) -> AgentOutput:
        return AgentOutput(type="abstention", content="unknown")

    def act(self, *, run_id: str, request_id: str, task_id: str, goal: str | None, constraints: list[str],
            tools: list[dict[str, Any]], continuation: bool, virtual_time: str | None) -> ActStep:
        key = (run_id, request_id)
        if key in self.act_responses:
            return self.act_responses[key]
        self.current_task = task_id
        state = self._task_state(task_id, goal, tools)
        names = state["tools"]
        if any(n.startswith("deployment.") for n in names):
            step = self._deployment(task_id, state, learned_inspect=False, recover=False)
        elif any(n.startswith("canvas.") for n in names):
            step = self._canvas(task_id, state, learned_context=False, recover=False)
        else:
            step = ActStep(type="abstention", content="No policy for these tools.")
        self.act_responses[key] = step
        return step
