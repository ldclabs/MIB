from __future__ import annotations

import re
from collections import Counter
from typing import Any, Iterable

from .agents.reference_memory import ReferenceMemoryAgent
from . import __version__
from .experimental.transfer import RECALL_PREFIX
from .types import ActStep, AgentOutput, Observation

_RECALL_MARKER = RECALL_PREFIX.casefold()

WORD_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_+.-]*")
CODE_RE = re.compile(r"\b[A-Z][A-Z0-9]{1,15}-\d{1,5}\b")
TIME_RE = re.compile(r"\b(?:[01]?\d|2[0-3]):[0-5]\d\b")
UTC_RE = re.compile(r"\bUTC[+-]\d{1,2}\b", re.I)
DATE_RE = re.compile(
    r"\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2}\b",
    re.I,
)
ISO_DATE_RE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")

STOP = {
    "the", "a", "an", "is", "are", "was", "were", "be", "to", "for", "of", "in", "on", "at",
    "and", "or", "with", "what", "which", "who", "should", "use", "used", "now", "current", "currently",
    "answer", "exactly", "only", "did", "does", "do", "my", "me", "i", "it", "this", "that", "before",
    "after", "under", "from", "has", "have", "had", "into", "its", "we", "our", "you", "your",
}


def _split_routed(text: str) -> tuple[str, str]:
    """Split remembered text into situation evidence and routed procedures."""
    situation, routed = [], []
    for line in text.splitlines():
        (routed if _RECALL_MARKER in line else situation).append(line)
    return "\n".join(situation), "\n".join(routed)


def _tokens(text: str) -> list[str]:
    return [x.casefold() for x in WORD_RE.findall(text) if x.casefold() not in STOP]


def _obs_text(o: Observation) -> str:
    parts = []
    if o.actor:
        parts.extend([str(o.actor.get("display_name") or ""), str(o.actor.get("id") or "")])
    if o.content:
        parts.append(o.content)
    if isinstance(o.payload, dict):
        parts.extend(f"{k} {v}" for k, v in o.payload.items())
    return " ".join(parts)


def _extract_codes(text: str) -> list[str]:
    return CODE_RE.findall(text or "")


def _payload_values(observations: Iterable[Observation], keys: set[str]) -> list[tuple[int, str, Observation]]:
    out = []
    for idx, o in enumerate(observations):
        if isinstance(o.payload, dict):
            for k, v in o.payload.items():
                if k.casefold() in keys and isinstance(v, (str, int, float)):
                    out.append((idx, str(v), o))
    return out


class CalibrationReasonerAgent(ReferenceMemoryAgent):
    """Deterministic evaluator-side task solver used only by calibration fixtures.

    It receives only Agent-visible observations and Probe/tool inputs.  It never
    receives Scenario Oracle/evaluator/ablation metadata.  The implementation is
    intentionally transparent and synthetic: it is useful for calibration-harness
    mechanics, but is not an empirical LLM baseline claim.
    """

    baseline_id = "fixture"
    baseline_name = "Calibration Fixture"
    baseline_role = "fixture"
    release_calibration_eligible = False

    def describe(self) -> dict[str, Any]:
        d = super().describe()
        d["implementation"] = {
            "name": self.baseline_name,
            "version": __version__,
            "vendor": "MIB",
        }
        d.setdefault("extensions", {})["mib.calibration"] = {
            "baseline_id": self.baseline_id,
            "role": self.baseline_role,
            "release_calibration_eligible": self.release_calibration_eligible,
        }
        return d

    def _latest_current_mode(self, obs: list[Observation]) -> str | None:
        mode = None
        for o in obs:
            t = _obs_text(o).casefold()
            # Strong current/specific applicability cues should override generic old skills.
            if any(k in t for k in [
                "this item is global", "global item", "global items", "global record", "global records",
                "record class is global", "export record", "no context activation", "without context activation",
                "context_required is false", "no required context", "requires no context", "skip context activation",
                "directly after edit", "edit and commit directly", "do not require context",
            ]):
                mode = "global"
            if any(k in t for k in [
                "current item is contextual", "future item is contextual", "this future object is contextual",
                "this contextual item", "contextual record", "contextual items", "requires an active context",
                "require active context", "context_required is true", "required operational context",
            ]):
                # Old generic statements can be superseded by a later explicit global cue.
                if any(k in t for k in ["current", "future", "next", "this", "requires"]):
                    mode = "contextual"
                elif mode is None:
                    mode = "contextual"
        return mode

    def act(self, **kwargs) -> ActStep:
        # Reuse the Runner fixture state/idempotency mechanics, but improve the
        # policy classifier so official calibration scenarios are supported.
        run_id = kwargs["run_id"]
        request_id = kwargs["request_id"]
        task_id = kwargs["task_id"]
        goal = kwargs.get("goal")
        tools = kwargs.get("tools") or []

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

        seen_results = state.setdefault("seen_result_ids", set())
        for o in self.observations:
            if o.type == "tool_result" and o.observation_id.startswith("obs_tool_") and o.observation_id not in seen_results:
                seen_results.add(o.observation_id)
                state["results"].append({"tool": o.tool, "payload": o.payload or {}})

        names = set(state["tools"])
        if "memory_snapshot_observations" not in state:
            state["memory_snapshot_observations"] = list(self.observations)
        mem_obs: list[Observation] = state["memory_snapshot_observations"]
        mem = "\n".join(_obs_text(o) for o in mem_obs).casefold()
        # A routed memory artifact carries procedural content, not a fact about
        # the current situation.  Without routing both halves are the whole
        # memory, so ordinary calibration runs are unchanged.
        situation_mem, routed_mem = _split_routed(mem)
        phase = int(state["phase"])

        if any(n.startswith("deployment.") for n in names):
            learned_inspect = ("inspect" in routed_mem and "target" in routed_mem) or any(k in situation_mem for k in [
                "missing_column", "wrong target", "wrong_target", "target mismatch", "target alignment",
                "inspect actual target", "inspect the actual target", "inspected the actual target",
                "verify the actual target", "unverified target", "inspect and select", "diagnosed the target",
                "inspecting the actual target", "inspected the target", "inspect the actual deployment target",
                "target alignment before migration",
                "selected it, migrated", "selected the actual target",
            ])
            last = state["results"][-1] if state["results"] else None
            if learned_inspect:
                if phase == 0:
                    state["phase"] = 1
                    return emit(ActStep(type="tool_call", tool_call_id=self._next_call(), tool="deployment.inspect_target", arguments={}))
                if phase == 1:
                    target = (last or {}).get("payload", {}).get("actual_target")
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
            # B0/B2 may have no useful prior lesson: deliberately naive.
            if phase == 0:
                state["phase"] = 1
                return emit(ActStep(type="tool_call", tool_call_id=self._next_call(), tool="deployment.run_migration", arguments={}))
            if phase == 1:
                state["phase"] = 2
                return emit(ActStep(type="tool_call", tool_call_id=self._next_call(), tool="deployment.restart_service", arguments={}))
            return emit(ActStep(type="final", content="Deployment attempt complete."))

        if any(n.startswith("workspace.") for n in names):
            learned = ("workspace" in routed_mem) or any(k in situation_mem for k in [
                "workspace_required", "select the workspace", "selected the workspace", "workspace before",
                "workspace first", "operational context before committing",
            ])
            if learned:
                if phase == 0:
                    state["phase"] = 1
                    return emit(ActStep(type="tool_call", tool_call_id=self._next_call(), tool="workspace.select_workspace", arguments={"workspace": "primary"}))
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

        if any(n.startswith("canvas.") for n in names):
            mode = self._latest_current_mode([o for o in mem_obs if _RECALL_MARKER not in _obs_text(o).casefold()])
            goal_l = str(state.get("goal") or "").casefold()
            if "contextual" in goal_l:
                mode = "contextual"
            elif "global" in goal_l or "export record" in goal_l:
                mode = "global"
            learned_context = ("context" in routed_mem or "scope" in routed_mem) or any(k in situation_mem for k in [
                "context_required", "activate context", "context activation", "context first",
                "required operational context", "context before", "contextual",
            ])
            use_context = mode == "contextual" or (mode is None and learned_context)
            if use_context:
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

        return emit(ActStep(type="abstention", content="No calibration policy for the provided tools."))

    def _answer(self, q: str) -> str:
        # Preserve all public-dev fixture behavior first.
        base = super()._answer(q)
        if base != "unknown":
            return base

        ql = q.casefold()
        obs = list(self.observations)
        texts = [_obs_text(o) for o in obs]
        lower = [t.casefold() for t in texts]

        # Evidence independence / source multiplicity.
        if "independent evidence roots" in ql or ("one independent source or multiple" in ql):
            roots = 0
            for t in lower:
                if any(x in t for x in ["source report", "independent source", "signed ledger", "signed registry"]):
                    if "derived" not in t and "copies" not in t and "repeats" not in t:
                        roots += 1
            if any("one source" in t or "not independently corroborated" in t for t in lower):
                return "one"
            return "multiple" if roots >= 2 else "one"
        if "independently corroborated" in ql:
            if any("not independently corroborated" in t or "not independent evidence" in t or "no new source" in t for t in lower):
                return "single_source"
            return "corroborated"
        if "analyst summary add an independent source" in ql:
            return "no" if any("derived only" in t or "derived exclusively" in t for t in lower) else "yes"

        # Uncertainty / conflict before a later authoritative source arrives.
        if "status of the review room" in ql:
            return "uncertain" if any("not sure" in t or "i think" in t for t in lower) else "known"
        if "before the signed ledger arrives" in ql and "resolved" in ql:
            vals = []
            for o in obs:
                if o.type == "tool_result" and isinstance(o.payload, dict) and o.payload.get("status") == "verified":
                    continue
                vals.extend(_extract_codes(_obs_text(o)))
            return "contested" if len(set(vals)) >= 2 else "resolved"

        # Tool-authoritative values.
        if "treated as confirmed" in ql:
            vals = _payload_values(obs, {"room"})
            confirmed = [(i, v) for i, v, o in vals if isinstance(o.payload, dict) and o.payload.get("status") in {"confirmed", "verified"}]
            if confirmed:
                return confirmed[-1][1]
        if "release channel should be used" in ql or "under the stated authority policy" in ql:
            vals = _payload_values(obs, {"channel"})
            verified = [(i, v) for i, v, o in vals if isinstance(o.payload, dict) and o.payload.get("status") in {"confirmed", "verified"}]
            if verified:
                return verified[-1][1]
        if "operational key is authoritative" in ql:
            vals = _payload_values(obs, {"key"})
            verified = [(i, v) for i, v, o in vals if isinstance(o.payload, dict) and o.payload.get("status") in {"confirmed", "verified"}]
            if verified:
                return verified[-1][1]
        if "package code should be used now" in ql:
            vals = _payload_values(obs, {"package_code"})
            verified = [(i, v) for i, v, o in vals if isinstance(o.payload, dict) and o.payload.get("status") in {"confirmed", "verified"}]
            if verified:
                return verified[-1][1]

        # Source-attributed personal claim.
        if "personally claim" in ql:
            for o in obs:
                name = (o.actor or {}).get("display_name") or ""
                if name and name.casefold() in ql:
                    # channel values often contain hyphens but no digits.
                    m = re.search(r"(?:channel is|is)\s+([A-Za-z0-9_-]+)", o.content or "", re.I)
                    if m:
                        return m.group(1)
                    tm = TIME_RE.search(o.content or "")
                    if tm:
                        return tm.group(0)
        if "who issued the correction" in ql:
            for o in obs:
                if "correction" in (o.content or "").casefold():
                    name = (o.actor or {}).get("display_name")
                    if name:
                        return str(name)

        if "which key was valid on" in ql:
            qdate = ISO_DATE_RE.search(q)
            if qdate:
                for o in obs:
                    t = _obs_text(o)
                    if qdate.group(0) in t:
                        codes = _extract_codes(t)
                        if codes:
                            return codes[-1]

        # Generic code/reference/token questions.
        if any(k in ql for k in ["recovery token", "token associated", "deployment ticket", "active ticket", "ticket identifier", "approval key", "shipment reference", "operational key", "package code", "backup contact code"]):
            candidates: list[tuple[int, str, str]] = []
            for idx, o in enumerate(obs):
                for code in _extract_codes(_obs_text(o)):
                    candidates.append((idx, code, _obs_text(o).casefold()))
                if isinstance(o.payload, dict):
                    for k in ["key", "package_code"]:
                        if o.payload.get(k):
                            candidates.append((idx, str(o.payload[k]), _obs_text(o).casefold()))
            # Prefer explicit verified/current/correction evidence for current questions.
            if "original" in ql or "2026-04-01" in ql:
                if candidates:
                    return candidates[0][1]
            if "approval date" not in ql:
                preferred = [c for c in candidates if any(x in c[2] for x in ["verified", "correction", "should be", "active", "critical constraint", "one-time recovery", "backup contact"])]
                if preferred:
                    return preferred[-1][1]
                # Query entity overlap ranking.
                qt = set(_tokens(q))
                ranked = sorted(candidates, key=lambda c: (len(qt & set(_tokens(c[2]))), c[0]), reverse=True)
                if ranked:
                    return ranked[0][1]

        # Approval date.
        if "approval date" in ql:
            qt = set(_tokens(q))
            rows = []
            for idx, t in enumerate(texts):
                m = DATE_RE.search(t)
                if m:
                    rows.append((len(qt & set(_tokens(t))), idx, m.group(0)))
            if rows:
                return sorted(rows, reverse=True)[0][2]

        # Routing/zone/region/ring/channel temporal state.
        if any(k in ql for k in ["routing zone", "region", "deployment ring", "service channel"]) or ("channel" in ql and "temporary switch" in ql):
            vals: list[tuple[int, str, str]] = []
            patterns = [
                r"routing zone is(?: now)?\s+([A-Za-z0-9_-]+)",
                r"use\s+(Zone-[A-Za-z0-9_-]+)\s+from now on",
                r"region is\s+([A-Za-z0-9_-]+)",
                r"moved(?: again)? to\s+([A-Za-z0-9_-]+)",
                r"deployment ring was\s+([A-Za-z0-9_-]+)",
                r"deployment ring\s+([A-Za-z0-9_-]+)\s+is current",
                r"service channel is(?: now)?\s+([A-Za-z0-9_-]+)",
                r"back to\s+([A-Za-z0-9_-]+)",
            ]
            for idx, t in enumerate(texts):
                for pat in patterns:
                    m = re.search(pat, t, re.I)
                    if m:
                        vals.append((idx, m.group(1).rstrip(".;,"), t.casefold()))
            if vals:
                # When the Probe names a synthetic account/entity, keep only that entity's state chain.
                query_tokens = set(_tokens(q))
                entity_vals = [v for v in vals if any(tok in v[2].split() for tok in query_tokens if tok.startswith("acct-") or tok.startswith("project"))]
                if entity_vals:
                    vals = entity_vals
                # Specific historical-date request.
                dateq = ISO_DATE_RE.search(q)
                if dateq:
                    d = dateq.group(0)
                    on_date = [v for v in vals if d in v[2]]
                    if on_date:
                        return on_date[-1][1]
                    # Current date after a valid_from/current event: prefer explicit current.
                    current = [v for v in vals if ("current" in v[2] or "onward" in v[2]) and "not the current" not in v[2]]
                    if current:
                        return current[-1][1]
                if any(k in ql for k in ["immediately before", "preceded the current"]):
                    return vals[-2][1] if len(vals) >= 2 else vals[0][1]
                if "state first" in ql or "did i state first" in ql:
                    return vals[0][1]
                if "temporary switch" in ql:
                    temp = [v for v in vals if "temporary" in v[2]]
                    active_temp = [v for v in temp if "ended" not in v[2]]
                    return (active_temp[0][1] if active_temp else (temp[0][1] if temp else (vals[1][1] if len(vals) > 1 else vals[0][1])))
                return vals[-1][1]

        # Temporary validity interval.
        if "active or expired" in ql or ("validity status" in ql and "expired" in ql):
            qdate = ISO_DATE_RE.search(q)
            for t in texts:
                dates = ISO_DATE_RE.findall(t)
                if "valid from" in t.casefold() and len(dates) >= 2 and qdate:
                    qd = qdate.group(0)
                    return "active" if dates[0] <= qd <= dates[1] else "expired"

        # Routes / owner / multi-hop relations.
        if "which destination" in ql or ("emergency route" in ql and "destination" in ql):
            protocol = None
            cls = None
            for t in texts:
                m = re.search(r"protocol\s+(.+?),\s+emergency actions use route class\s+([A-Za-z0-9_-]+)", t, re.I)
                if m and (m.group(1).casefold() in ql or ("protocol " + m.group(1)).casefold() in ql):
                    protocol, cls = m.group(1), m.group(2)
                    break
            if cls:
                for t in texts:
                    m = re.search(re.escape(cls) + r"\s+maps to destination\s+([A-Za-z0-9_-]+)", t, re.I)
                    if m:
                        return m.group(1)
        if "escalation route" in ql or ("escalate" in ql and "channel" in ql):
            for t in texts:
                m = re.search(r"escalation (?:channel|route)\s*=\s*([A-Za-z0-9 _-]+?)(?:\.|$)", t, re.I)
                if m:
                    return m.group(1).strip()
        if "which route reaches me" in ql:
            for t in texts:
                m = re.search(r"use\s+(.+?);\s+ordinary", t, re.I)
                if m:
                    return m.group(1).strip()
        if "route reaches its primary owner" in ql or ("urgent-contact route" in ql and "primary owner" in ql):
            owner_org = None
            for t in texts:
                if "primary owner is" in t.casefold():
                    m = re.search(r"primary owner is .+? from ([A-Za-z0-9_-]+)", t, re.I)
                    if m:
                        owner_org = m.group(1)
                        break
            target_actor = None
            if owner_org:
                for o in obs:
                    t = _obs_text(o)
                    if owner_org.casefold() in t.casefold():
                        m = re.search(r"actor\s+([A-Za-z0-9_:-]+)", t, re.I)
                        if m:
                            target_actor = m.group(1)
                            break
            if target_actor:
                for o in obs:
                    if (o.actor or {}).get("id") == target_actor:
                        m = re.search(r"through\s+([A-Za-z0-9_-]+)", o.content or "", re.I)
                        if m:
                            return m.group(1)
            # Some identity-collision holdouts deliberately make display names identical and
            # encode the organization-to-contact binding in adjacent lived observations.
            if owner_org:
                for idx, o in enumerate(obs):
                    if owner_org.casefold() in _obs_text(o).casefold():
                        for later in obs[idx+1:idx+3]:
                            m = re.search(r"through\s+([A-Za-z0-9_-]+)", later.content or "", re.I)
                            if m:
                                return m.group(1)

        # Shipment/reference current/original with correction.
        if "shipment reference" in ql:
            vals = []
            for idx, o in enumerate(obs):
                codes = _extract_codes(_obs_text(o))
                if codes:
                    vals.append((idx, codes[-1], _obs_text(o).casefold()))
            if vals:
                return vals[0][1] if "original" in ql else vals[-1][1]

        # Historical workflow rules / procedure versions.
        if "before the workflow update" in ql and "context activation required" in ql:
            historical = [t for t in lower if "historical workflow rule" in t]
            if any(any(k in t for k in ["not required", "without context", "no-context", "context activation was omitted", "commit directly"]) for t in historical):
                return "not_required"
            if any("required" in t for t in historical):
                return "required"
            return "unknown"
        if "procedure v1 require" in ql:
            return "context" if any("v1 required activating context" in t for t in lower) else "no_context"
        if "context name did v2 require" in ql:
            for t in texts:
                m = re.search(r"V2 changed the required context name to\s+([A-Za-z0-9_-]+)", t, re.I)
                if m:
                    return m.group(1)

        return "unknown"


class NoMemoryBaselineAgent(CalibrationReasonerAgent):
    baseline_id = "B0"
    baseline_name = "B0 — No Memory"
    baseline_role = "no_memory"

    def observe(self, *, run_id: str, request_id: str, observation: Observation) -> dict[str, Any]:
        # Keep only tool results produced inside the current future action loop.
        if observation.observation_id.startswith("obs_tool_"):
            return super().observe(run_id=run_id, request_id=request_id, observation=observation)
        self.seen_observe_requests.add((run_id, request_id))
        return {"accepted": True, "emissions": []}

    def act(self, **kwargs) -> ActStep:
        # A No-Memory baseline may use tool results from the task it is currently
        # executing, but nothing may survive the end of that task.  Without this
        # purge B0 carries a previous task's diagnosis into the next one, scores
        # like a memory-enabled agent, and deflates the measured discriminativeness.
        task_id = kwargs["task_id"]
        if task_id != getattr(self, "_current_action_task", None):
            self._current_action_task = task_id
            self.observations = [
                o for o in self.observations if not o.observation_id.startswith("obs_tool_")
            ]
        return super().act(**kwargs)


class FullContextBaselineAgent(CalibrationReasonerAgent):
    baseline_id = "B1"
    baseline_name = "B1 — Full Visible History Fixture"
    baseline_role = "full_context"


class RetrievalBaselineAgent(CalibrationReasonerAgent):
    baseline_id = "B2"
    baseline_name = "B2 — Simple Lexical Retrieval"
    baseline_role = "simple_retrieval"

    def __init__(self, top_k: int = 2):
        super().__init__()
        self.top_k = top_k
        self._task_retrieved_ids: dict[str, set[str]] = {}

    def reset(self, *, run_id: str, seed, virtual_time: str | None) -> dict[str, Any]:
        self._task_retrieved_ids = {}
        return super().reset(run_id=run_id, seed=seed, virtual_time=virtual_time)

    def _retrieve(self, query: str, include_tool_results: bool = True) -> list[Observation]:
        qt = Counter(_tokens(query))
        scored = []
        for idx, o in enumerate(self.observations):
            if o.observation_id.startswith("obs_tool_") and include_tool_results:
                scored.append((10_000.0 + idx, o))
                continue
            ot = Counter(_tokens(_obs_text(o)))
            overlap = sum(min(qt[t], ot[t]) for t in qt)
            # tiny recency tie-break only; no source/time semantics.
            score = float(overlap) + idx * 1e-6
            scored.append((score, o))
        selected = [o for score, o in sorted(scored, key=lambda x: x[0], reverse=True) if score > 0][: self.top_k]
        return list(reversed(selected))

    def respond(self, **kwargs) -> AgentOutput:
        key = (kwargs["run_id"], kwargs["request_id"])
        if key in self.responses:
            return self.responses[key]
        q = (kwargs.get("input_data") or {}).get("content") or ""
        original = self.observations
        try:
            self.observations = self._retrieve(q)
            out = AgentOutput(type="message", content=self._answer(q))
            self.responses[key] = out
            return out
        finally:
            self.observations = original

    def act(self, **kwargs) -> ActStep:
        task_id = kwargs["task_id"]
        ids = self._task_retrieved_ids.get(task_id)
        if ids is None:
            query = str(kwargs.get("goal") or "") + " " + " ".join(t.get("name", "") for t in kwargs.get("tools") or [])
            chosen = self._retrieve(query, include_tool_results=False)
            ids = {o.observation_id for o in chosen}
            self._task_retrieved_ids[task_id] = ids
        original = self.observations
        try:
            self.observations = [o for o in original if o.observation_id in ids or o.observation_id.startswith("obs_tool_")]
            return super().act(**kwargs)
        finally:
            self.observations = original


class StructuredMemoryBaselineAgent(RetrievalBaselineAgent):
    baseline_id = "B3"
    baseline_name = "B3 — Structured / Agentic Memory"
    baseline_role = "structured_agentic"

    def __init__(self):
        super().__init__(top_k=8)

    @staticmethod
    def _salient(o: Observation) -> bool:
        t = _obs_text(o).casefold()
        # Reference packs deliberately mark low-value routine chatter in natural text;
        # this is Agent-visible content, not a hidden relevance label.
        if "routine " in t and " distractor " in t:
            return False
        if o.type in {"tool_result", "feedback", "document"}:
            return True
        markers = [
            "current", "update", "correction", "verified", "confirmed", "authoritative", "policy",
            "historical", "valid", "moved", "changed", "from now", "temporary", "late audit",
            "failed", "failure", "error", "succeeded", "success", "recovery", "lesson", "learned",
            "counterexample", "exception", "contextual", "global", "workspace_required", "missing_column",
            "primary owner", "incident coordinator", "critical constraint", "one source", "independent",
            "urgent incidents", "is actor", "incident roster", "reach me through",
        ]
        return any(m in t for m in markers)

    def _retrieve(self, query: str, include_tool_results: bool = True) -> list[Observation]:
        lexical = super()._retrieve(query, include_tool_results=include_tool_results)
        ids = {o.observation_id for o in lexical}
        # Structured memory keeps compact high-salience facts/Experiences in addition
        # to lexical hits.  It does not receive hidden relevance labels.
        for o in self.observations:
            if self._salient(o):
                ids.add(o.observation_id)
        selected = [o for o in self.observations if o.observation_id in ids]
        # Bound memory exposed to the reasoner while preserving temporal order.
        if len(selected) > 24:
            selected = selected[-24:]
        return selected


BASELINE_FACTORIES = {
    "B0": NoMemoryBaselineAgent,
    "B1": FullContextBaselineAgent,
    "B2": RetrievalBaselineAgent,
    "B3": StructuredMemoryBaselineAgent,
}


def baseline_descriptor_table() -> list[dict[str, Any]]:
    rows = []
    for bid, factory in BASELINE_FACTORIES.items():
        a = factory()
        d = a.describe()
        rows.append({
            "id": bid,
            "name": d["implementation"]["name"],
            "role": d["extensions"]["mib.calibration"]["role"],
            "release_calibration_eligible": d["extensions"]["mib.calibration"]["release_calibration_eligible"],
        })
    return rows
