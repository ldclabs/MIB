from __future__ import annotations

import re
from typing import Any

from ..types import ActStep, AgentOutput, Observation


_TIME = re.compile(r"\b(?:[01]?\d|2[0-3]):[0-5]\d\b")
_UTC = re.compile(r"\bUTC[+-]\d{1,2}\b", re.I)
_CODE = re.compile(r"\b[A-Z]{2,12}-\d{1,4}\b")
_DATE = re.compile(r"\b(?:May|June|April)\s+\d{1,2}\b", re.I)


class ReferenceMemoryAgent:
    """
    Deterministic fixture Agent for Runner self-tests.

    It sees only Agent Adapter observations and Probe input. It never receives
    Oracle, evaluator, Scenario tags, or ablation labels. Its heuristics are
    intentionally small and are NOT a benchmark baseline claim.
    """

    def __init__(self) -> None:
        self.run_id = ""
        self.observations: list[Observation] = []
        self.responses: dict[tuple[str, str], AgentOutput] = {}
        self.act_responses: dict[tuple[str, str], ActStep] = {}
        self.seen_observe_requests: set[tuple[str, str]] = set()
        self.task_states: dict[str, dict[str, Any]] = {}
        self.tool_call_counter = 0

    def describe(self) -> dict[str, Any]:
        return {
            "protocol": "mib-agent/0.1",
            "implementation": {
                "name": "MIB Reference Fixture Agent",
                "version": "0.4.0",
                "vendor": "MIB",
            },
            "track_support": ["integrated_agent"],
            "capabilities": {
                "observe": True,
                "respond": True,
                "act": True,
                "spontaneous_emissions": False,
                "maintenance": False,
                "runner_managed_tools": True,
                "structured_output": False,
                "virtual_time": True,
                "seedable": True,
            },
            "state": {
                "run_isolation": "hard",
                "observe_visibility": "read_after_write",
                "request_idempotency": True,
            },
        }

    def reset(self, *, run_id: str, seed, virtual_time: str | None) -> dict[str, Any]:
        self.run_id = run_id
        self.observations = []
        self.responses = {}
        self.act_responses = {}
        self.seen_observe_requests = set()
        self.task_states = {}
        self.tool_call_counter = 0
        return {"accepted": True}

    def observe(self, *, run_id: str, request_id: str, observation: Observation) -> dict[str, Any]:
        # Request idempotency: one logical observation per run_id + request_id.
        req_key = (run_id, request_id)
        if req_key in self.seen_observe_requests:
            return {"accepted": True, "emissions": []}
        self.seen_observe_requests.add(req_key)
        if not any(o.observation_id == observation.observation_id for o in self.observations):
            self.observations.append(observation)
        return {"accepted": True, "emissions": []}

    def respond(
        self,
        *,
        run_id: str,
        request_id: str,
        interaction_id: str,
        input_data: dict[str, Any],
        virtual_time: str | None,
    ) -> AgentOutput:
        key = (run_id, request_id)
        if key in self.responses:
            return self.responses[key]
        q = (input_data.get("content") or "").strip()
        answer = self._answer(q)
        out = AgentOutput(type="message", content=answer)
        self.responses[key] = out
        return out

    def _next_call(self) -> str:
        self.tool_call_counter += 1
        return f"call_{self.tool_call_counter:04d}"

    def _memory_text(self) -> str:
        return self._all_text().casefold()

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
    ) -> ActStep:
        req_key = (run_id, request_id)
        if req_key in self.act_responses:
            return self.act_responses[req_key]

        state = self.task_states.setdefault(task_id, {
            "goal": goal or "",
            "tools": {t["name"]: t for t in tools},
            "phase": 0,
            "results": [],
        })
        if goal:
            state["goal"] = goal
        if tools:
            state["tools"] = {t["name"]: t for t in tools}

        def emit(step: ActStep) -> ActStep:
            self.act_responses[req_key] = step
            return step

        # Capture tool-result observations delivered since the previous act step.
        seen_results = state.setdefault("seen_result_ids", set())
        for o in self.observations:
            if o.type == "tool_result" and o.observation_id not in seen_results:
                seen_results.add(o.observation_id)
                state["results"].append({"tool": o.tool, "payload": o.payload or {}})

        names = set(state["tools"])
        mem = self._memory_text()
        # Freeze long-term memory evidence at task start so current tool-result feedback
        # cannot retroactively masquerade as a previously learned Skill/Experience.
        if "memory_snapshot" not in state:
            state["memory_snapshot"] = mem
        task_mem = state["memory_snapshot"]
        goal_text = str(state.get("goal") or "").casefold()

        # Deployment domain. A learned failure/recovery episode causes inspect-first behavior.
        if any(n.startswith("deployment.") for n in names):
            learned_inspect = any(k in task_mem for k in [
                "missing_column", "wrong target", "wrong_target",
                "inspect the actual target", "inspected the actual target", "checked the target", "target mismatch"
            ])
            phase = state["phase"]
            last = state["results"][-1] if state["results"] else None

            if learned_inspect:
                if phase == 0:
                    state["phase"] = 1
                    return emit(ActStep(type="tool_call", tool_call_id=self._next_call(), tool="deployment.inspect_target", arguments={}))
                if phase == 1:
                    target = None
                    if last and last["tool"] == "deployment.inspect_target":
                        target = (last["payload"] or {}).get("actual_target")
                    state["target"] = target
                    state["phase"] = 2
                    return emit(ActStep(type="tool_call", tool_call_id=self._next_call(), tool="deployment.select_target", arguments={"target": target}))
                if phase == 2:
                    state["phase"] = 3
                    return emit(ActStep(type="tool_call", tool_call_id=self._next_call(), tool="deployment.run_migration", arguments={}))
                if phase == 3:
                    state["phase"] = 4
                    return emit(ActStep(type="tool_call", tool_call_id=self._next_call(), tool="deployment.restart_service", arguments={}))
                return emit(ActStep(type="final", content="Deployment repaired."))

            # Naive no-memory behavior intentionally skips diagnosis.
            if phase == 0:
                state["phase"] = 1
                return emit(ActStep(type="tool_call", tool_call_id=self._next_call(), tool="deployment.run_migration", arguments={}))
            if phase == 1:
                state["phase"] = 2
                return emit(ActStep(type="tool_call", tool_call_id=self._next_call(), tool="deployment.restart_service", arguments={}))
            return emit(ActStep(type="final", content="Deployment attempt complete."))

        # Workspace domain: learn select-before-save from prior failure.
        if any(n.startswith("workspace.") for n in names):
            learned = any(k in task_mem for k in ["workspace_required", "select the workspace", "selected the workspace", "workspace before saving"])
            phase = state["phase"]
            ws = "primary"
            if learned:
                if phase == 0:
                    state["phase"] = 1
                    return emit(ActStep(type="tool_call", tool_call_id=self._next_call(), tool="workspace.select_workspace", arguments={"workspace": ws}))
                if phase == 1:
                    state["phase"] = 2
                    return emit(ActStep(type="tool_call", tool_call_id=self._next_call(), tool="workspace.edit_record", arguments={"value": "updated"}))
                if phase == 2:
                    state["phase"] = 3
                    return emit(ActStep(type="tool_call", tool_call_id=self._next_call(), tool="workspace.save", arguments={}))
                return emit(ActStep(type="final", content="Record saved."))
            if phase == 0:
                state["phase"] = 1
                return emit(ActStep(type="tool_call", tool_call_id=self._next_call(), tool="workspace.edit_record", arguments={"value": "updated"}))
            if phase == 1:
                state["phase"] = 2
                return emit(ActStep(type="tool_call", tool_call_id=self._next_call(), tool="workspace.save", arguments={}))
            return emit(ActStep(type="final", content="Save attempt complete."))

        # Surface-changed contextual-save domain.
        if any(n.startswith("canvas.") for n in names):
            learned_context = any(k in task_mem for k in ["workspace_required", "select the workspace", "context before commit", "context_required"])
            nonmatching = any(k in task_mem for k in ["global record", "no workspace is required", "no context is required"])
            phase = state["phase"]
            if learned_context and not nonmatching:
                if phase == 0:
                    state["phase"] = 1
                    return emit(ActStep(type="tool_call", tool_call_id=self._next_call(), tool="canvas.activate_context", arguments={"context": "primary"}))
                if phase == 1:
                    state["phase"] = 2
                    return emit(ActStep(type="tool_call", tool_call_id=self._next_call(), tool="canvas.edit_item", arguments={"value": "updated"}))
                if phase == 2:
                    state["phase"] = 3
                    return emit(ActStep(type="tool_call", tool_call_id=self._next_call(), tool="canvas.commit", arguments={}))
                return emit(ActStep(type="final", content="Item committed."))
            if phase == 0:
                state["phase"] = 1
                return emit(ActStep(type="tool_call", tool_call_id=self._next_call(), tool="canvas.edit_item", arguments={"value": "updated"}))
            if phase == 1:
                state["phase"] = 2
                return emit(ActStep(type="tool_call", tool_call_id=self._next_call(), tool="canvas.commit", arguments={}))
            return emit(ActStep(type="final", content="Commit attempt complete."))

        return emit(ActStep(type="abstention", content="No supported benchmark action policy for these tools."))

    def _text_obs(self) -> list[Observation]:
        return [o for o in self.observations if o.content]

    def _all_text(self) -> str:
        parts = []
        for o in self.observations:
            if o.content:
                who = (o.actor or {}).get("display_name") or ""
                parts.append(f"{who}: {o.content}")
            if isinstance(o.payload, dict):
                parts.append(str(o.payload))
        return "\n".join(parts)

    def _answer(self, q: str) -> str:
        ql = q.casefold()
        obs = self._text_obs()

        # Unknown / abstention case.
        if "allergic to shellfish" in ql:
            if not any("shellfish" in (o.content or "").casefold() for o in obs):
                return "unknown"

        # Direct code recall.
        if "access code" in ql:
            for o in reversed(obs):
                if "access code" in (o.content or "").casefold():
                    m = _CODE.search(o.content or "")
                    if m:
                        return m.group(0)

        # Physical fit from remembered opening size.
        if "fits or does_not_fit" in ql:
            item = re.search(r"(\d+(?:\.\d+)?)\s*cm", q, re.I)
            opening = None
            for o in reversed(obs):
                m = re.search(r"opening that is\s+(\d+(?:\.\d+)?)\s*cm", o.content or "", re.I)
                if m:
                    opening = float(m.group(1))
                    break
            if item and opening is not None:
                return "fits" if float(item.group(1)) <= opening else "does_not_fit"

        # Multi-hop synthetic project -> zone -> UTC.
        if "which utc offset" in ql:
            project_m = re.search(r"scheduling a (.+?) call with", q, re.I)
            project = project_m.group(1).strip() if project_m else None
            zone = None
            if project:
                for o in obs:
                    m = re.search(re.escape(project) + r" schedules all member calls using (.+?)\.", o.content or "", re.I)
                    if m:
                        zone = m.group(1).strip()
                        break
            if zone:
                for o in obs:
                    if zone.casefold() in (o.content or "").casefold():
                        m = _UTC.search(o.content or "")
                        if m:
                            return m.group(0).upper()

        # Same-name identity: map organization -> actor id -> actor preference.
        if "what drink should i order" in ql:
            org_m = re.search(r"from (.+?)\?", q, re.I)
            org = org_m.group(1).strip() if org_m else ""
            target_actor = None
            for o in obs:
                if org and org.casefold() in (o.content or "").casefold():
                    m = re.search(r"actor\s+([A-Za-z0-9_:-]+)", o.content or "", re.I)
                    if m:
                        target_actor = m.group(1)
                        break
            if target_actor:
                for o in obs:
                    if (o.actor or {}).get("id") == target_actor and "prefer" in (o.content or "").casefold():
                        m = re.search(r"prefer\s+(.+?)\.", o.content or "", re.I)
                        if m:
                            return m.group(1).strip()

        # Cross-suite preference update/current vs historical.
        if "what drink should you serve me" in ql or "what drink did i originally ask" in ql:
            drinks = []
            for o in obs:
                text = o.content or ""
                m = re.search(r"serve me (.+?) now, not ", text, re.I)
                if m:
                    drinks.append(m.group(1).strip())
                    continue
                m = re.search(r"serve me (.+?)\.", text, re.I)
                if m:
                    drinks.append(m.group(1).strip())
            if drinks:
                if "originally" in ql or "before my preference changed" in ql:
                    return drinks[0]
                return drinks[-1]

        # Historical confirmed Calendar Tool value.
        if "calendar tool originally confirm" in ql:
            for o in self.observations:
                if o.type == "tool_result" and isinstance(o.payload, dict):
                    if o.payload.get("status") == "confirmed" and o.payload.get("start"):
                        return str(o.payload["start"])

        # Birthday correction/current vs original.
        if "birthday" in ql:
            dates = []
            for o in obs:
                if "birthday" in (o.content or "").casefold():
                    m = _DATE.search(o.content or "")
                    if m:
                        dates.append(m.group(0))
            if dates:
                if "originally" in ql or "before correcting" in ql:
                    return dates[0]
                return dates[-1]

        # Device serial correction.
        if "serial" in ql:
            vals = []
            for o in obs:
                if "serial" in (o.content or "").casefold():
                    m = _CODE.search(o.content or "")
                    if m:
                        vals.append(m.group(0))
            if vals:
                if "original" in ql or "before correcting" in ql:
                    return vals[0]
                return vals[-1]

        # Office current/history.
        if "office" in ql:
            offices = []
            for o in obs:
                t = o.content or ""
                m = re.search(r"office is currently (.+?)\.", t, re.I)
                if m:
                    offices.append(m.group(1).strip())
                m = re.search(r"now in (.+?)\.", t, re.I)
                if m:
                    offices.append(m.group(1).strip())
            if offices:
                if "before the move" in ql or "before" in ql:
                    return offices[0]
                return offices[-1]

        # Current/historical timezone.
        if "timezone" in ql:
            zones = []
            for o in obs:
                if "timezone" in (o.content or "").casefold():
                    m = _UTC.search(o.content or "")
                    if m:
                        zones.append(m.group(0).upper())
            if zones:
                if "before" in ql:
                    return zones[0]
                return zones[-1]

        # Planned vs completed city.
        if "where do i live" in ql:
            current = None
            completed = None
            for o in obs:
                t = o.content or ""
                m = re.search(r"currently live in (.+?)\.", t, re.I)
                if m:
                    current = m.group(1).strip()
                m = re.search(r"now live in (.+?)\.", t, re.I)
                if m:
                    completed = m.group(1).strip()
            return completed or current or "unknown"

        # Source disagreement: "what time did NAME state" / personally claim.
        if "what time did" in ql or "personally claim" in ql:
            target_name = None
            for o in obs:
                name = (o.actor or {}).get("display_name")
                if name and name.casefold() in ql:
                    target_name = name
                    break
            if target_name:
                for o in obs:
                    if (o.actor or {}).get("display_name") == target_name:
                        m = _TIME.search(o.content or "")
                        if m:
                            return m.group(0)

        # Contested resolution status.
        if "is the meeting time resolved" in ql:
            times = []
            for o in obs:
                m = _TIME.search(o.content or "")
                if m:
                    times.append(m.group(0))
            return "contested" if len(set(times)) >= 2 else "resolved"

        # Calendar Tool is authoritative for scheduling.
        if "what start time should you use" in ql:
            for o in reversed(self.observations):
                if o.type == "tool_result" and isinstance(o.payload, dict):
                    if o.payload.get("status") == "confirmed" and o.payload.get("start"):
                        return str(o.payload["start"])

        return "unknown"
