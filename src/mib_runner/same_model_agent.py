from __future__ import annotations

import hashlib
import json
import math
import re
import threading
from dataclasses import asdict
from pathlib import Path
from typing import Any

from .model_clients import ModelClient
from .types import ActStep, AgentOutput, Observation

_WORD = re.compile(r"[A-Za-z0-9][A-Za-z0-9_+.-]*")
_STOP = {
    "the", "a", "an", "to", "of", "for", "and", "or", "is", "are", "was", "were",
    "in", "on", "at", "it", "this", "that", "i", "my", "me", "you", "your", "we", "our",
    "what", "which", "who", "when", "where", "how", "with", "be", "as", "now", "current",
}


def _stable_json(x: Any) -> str:
    return json.dumps(x, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha(x: str) -> str:
    return hashlib.sha256(x.encode("utf-8")).hexdigest()


def _tokens(text: str) -> set[str]:
    return {m.group(0).casefold() for m in _WORD.finditer(text) if m.group(0).casefold() not in _STOP}


def observation_text(o: Observation) -> str:
    parts = []
    if o.virtual_time:
        parts.append(f"time={o.virtual_time}")
    if o.actor:
        if o.actor.get("id"):
            parts.append(f"actor_id={o.actor.get('id')}")
        if o.actor.get("display_name"):
            parts.append(f"actor_name={o.actor.get('display_name')}")
    if o.type:
        parts.append(f"type={o.type}")
    if o.content:
        parts.append(o.content)
    if o.payload is not None:
        parts.append(_stable_json(o.payload))
    if o.tool:
        parts.append(f"tool={o.tool}")
    return " | ".join(parts)


class InvocationRecorder:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.rows: list[dict[str, Any]] = []
        self.memory_selection: list[dict[str, Any]] = []

    def record_call(self, row: dict[str, Any]) -> None:
        with self._lock:
            self.rows.append(row)

    def record_memory(self, row: dict[str, Any]) -> None:
        with self._lock:
            self.memory_selection.append(row)

    def summary(self) -> dict[str, Any]:
        with self._lock:
            rows = list(self.rows); sels = list(self.memory_selection)
        usage: dict[str, float] = {}
        for r in rows:
            for k, v in (r.get("usage") or {}).items():
                if isinstance(v, (int, float)):
                    usage[k] = usage.get(k, 0.0) + float(v)
        return {
            "model_calls": len(rows),
            "model_errors": sum(1 for r in rows if r.get("error")),
            "input_chars_total": sum(int(r.get("input_chars", 0)) for r in rows),
            "output_chars_total": sum(int(r.get("output_chars", 0)) for r in rows),
            "usage_totals": usage,
            "memory_selections": len(sels),
            "memory_records_available_total": sum(int(x.get("available", 0)) for x in sels),
            "memory_records_selected_total": sum(int(x.get("selected", 0)) for x in sels),
            "memory_chars_selected_total": sum(int(x.get("selected_chars", 0)) for x in sels),
            "memory_truncations": sum(1 for x in sels if x.get("truncated")),
            "transport_errors": sum(1 for r in rows if r.get("error_kind") == "transport"),
            "parse_errors": sum(1 for r in rows if r.get("error_kind") == "parse"),
            # Distinct fingerprints observed; the fairness audit requires exactly
            # one of each across every condition.
            "model_identities": sorted({json.dumps(r.get("model_identity"), sort_keys=True) for r in rows if r.get("model_identity")}),
            "system_prompt_shas": sorted({r["system_prompt_sha"] for r in rows if r.get("system_prompt_sha")}),
            "reasoning_policy_shas": sorted({r["reasoning_policy_sha"] for r in rows if r.get("reasoning_policy_sha")}),
            "decoding_fingerprints": sorted({r["decoding_fingerprint"] for r in rows if r.get("decoding_fingerprint")}),
            "memory_policy_ids": sorted({r["memory_policy_id"] for r in rows if r.get("memory_policy_id")}),
            "condition_label_visible_calls": sum(1 for r in rows if r.get("condition_label_visible")),
        }


class MemoryPolicy:
    id = "base"
    def select(self, observations: list[Observation], *, query: str, limit_chars: int | None) -> tuple[list[Observation], bool]:
        raise NotImplementedError

    @staticmethod
    def _limit(items: list[Observation], limit_chars: int | None) -> tuple[list[Observation], bool]:
        if not limit_chars or limit_chars <= 0:
            return items, False
        selected: list[Observation] = []
        used = 0
        truncated = False
        for o in reversed(items):
            n = len(observation_text(o))
            if selected and used + n > limit_chars:
                truncated = True
                continue
            if not selected and n > limit_chars:
                # Keep the one observation rather than silently drop all evidence.
                selected.append(o); used += n; truncated = True
                break
            selected.append(o); used += n
        return list(reversed(selected)), truncated


class NoMemoryPolicy(MemoryPolicy):
    id = "B0"
    def select(self, observations: list[Observation], *, query: str, limit_chars: int | None) -> tuple[list[Observation], bool]:
        return [], False


class FullContextPolicy(MemoryPolicy):
    id = "B1"
    def select(self, observations: list[Observation], *, query: str, limit_chars: int | None) -> tuple[list[Observation], bool]:
        return self._limit(list(observations), limit_chars)


class LexicalRetrievalPolicy(MemoryPolicy):
    id = "B2"
    def __init__(self, *, top_k: int = 4) -> None:
        self.top_k = top_k

    def select(self, observations: list[Observation], *, query: str, limit_chars: int | None) -> tuple[list[Observation], bool]:
        qt = _tokens(query)
        scored = []
        for idx, o in enumerate(observations):
            text = observation_text(o)
            ot = _tokens(text)
            overlap = len(qt & ot)
            denom = math.sqrt(max(1, len(qt)) * max(1, len(ot)))
            score = overlap / denom if denom else 0.0
            scored.append((score, idx, o))
        best = sorted(scored, key=lambda x: (x[0], x[1]), reverse=True)[: self.top_k]
        best = sorted(best, key=lambda x: x[1])
        return self._limit([x[2] for x in best], limit_chars)


class StructuredMemoryPolicy(MemoryPolicy):
    id = "B3"
    def __init__(self, *, top_k: int = 10, salient_k: int = 6) -> None:
        self.top_k = top_k
        self.salient_k = salient_k

    @staticmethod
    def _salience(text: str, o: Observation) -> float:
        t = text.casefold()
        score = 0.0
        cues = {
            "correction": 3.0, "corrected": 3.0, "now": 1.5, "current": 1.5,
            "authoritative": 3.0, "confirmed": 2.0, "verified": 2.0, "not sure": 2.0,
            "failed": 2.5, "failure": 2.5, "error": 2.0, "recovery": 3.0, "succeeded": 2.5,
            "must": 1.5, "requires": 2.0, "required": 2.0, "exception": 3.0,
            "class": 1.0, "version": 1.0, "before": 1.0, "after": 1.0,
        }
        for cue, w in cues.items():
            if cue in t:
                score += w
        if o.type in {"feedback", "tool_result", "document"}:
            score += 1.0
        if o.actor:
            score += 0.25
        return score

    def select(self, observations: list[Observation], *, query: str, limit_chars: int | None) -> tuple[list[Observation], bool]:
        qt = _tokens(query)
        ranked = []
        for idx, o in enumerate(observations):
            text = observation_text(o)
            ot = _tokens(text)
            overlap = len(qt & ot) / math.sqrt(max(1, len(qt)) * max(1, len(ot)))
            sal = self._salience(text, o)
            # A little recency, but never enough to erase older source/history evidence.
            recency = idx / max(1, len(observations) - 1) if observations else 0.0
            ranked.append((4.0 * overlap + sal + 0.15 * recency, idx, o))
        primary = sorted(ranked, key=lambda x: (x[0], x[1]), reverse=True)[: self.top_k]
        salient = sorted(ranked, key=lambda x: (self._salience(observation_text(x[2]), x[2]), x[1]), reverse=True)[: self.salient_k]
        merged = {x[1]: x[2] for x in primary + salient}
        items = [merged[i] for i in sorted(merged)]
        return self._limit(items, limit_chars)


POLICIES = {
    "B0": NoMemoryPolicy,
    "B1": FullContextPolicy,
    "B2": LexicalRetrievalPolicy,
    "B3": StructuredMemoryPolicy,
}


class SameModelAgent:
    def __init__(self, *, condition: str, model_client: ModelClient, system_prompt: str,
                 reasoning_policy: str, model_parameters: dict[str, Any], recorder: InvocationRecorder,
                 memory_config: dict[str, Any] | None = None, empirical_eligible: bool = True,
                 seed_policy: str = "fixed", seed_base: str = "mib-same-model") -> None:
        if condition not in POLICIES:
            raise ValueError(f"unknown memory condition: {condition}")
        self.condition = condition
        self.model = model_client
        self.system_prompt = system_prompt
        self.reasoning_policy = reasoning_policy
        self.model_parameters = dict(model_parameters)
        self.recorder = recorder
        self.memory_config = dict(memory_config or {})
        self.empirical_eligible = empirical_eligible
        self.seed_policy = seed_policy
        self.seed_base = seed_base
        # Fingerprints let the fairness audit *verify* that only the memory
        # policy differs between conditions, instead of asserting it.
        self.system_prompt_sha = _sha(system_prompt)
        self.reasoning_policy_sha = _sha(reasoning_policy)
        self.decoding_fingerprint = _sha(
            json.dumps({k: v for k, v in sorted(self.model_parameters.items()) if k != "seed"},
                       sort_keys=True, ensure_ascii=False)
        )
        if condition == "B2":
            self.policy = LexicalRetrievalPolicy(top_k=int(self.memory_config.get("retrieval_top_k", 4)))
        elif condition == "B3":
            self.policy = StructuredMemoryPolicy(
                top_k=int(self.memory_config.get("structured_top_k", 10)),
                salient_k=int(self.memory_config.get("structured_salient_k", 6)),
            )
        else:
            self.policy = POLICIES[condition]()
        self.max_memory_chars = self.memory_config.get("max_memory_chars")
        if self.max_memory_chars is not None:
            self.max_memory_chars = int(self.max_memory_chars)
        self.parse_retries = int(self.memory_config.get("parse_retries", 1))
        self.run_id = ""
        self.seed: int | str | None = None
        self.long_term: list[Observation] = []
        self.transient: list[Observation] = []
        self.active_task: str | None = None
        self.seen_observe: set[tuple[str, str]] = set()
        self.response_cache: dict[tuple[str, str], AgentOutput] = {}
        self.act_cache: dict[tuple[str, str], ActStep] = {}
        self.call_counter = 0

    def describe(self) -> dict[str, Any]:
        return {
            "protocol": "mib-agent/0.1",
            "implementation": {
                "name": f"MIB Same-Model Agent {self.condition}",
                "version": "0.1.0",
                "vendor": "MIB",
            },
            "track_support": ["memory_system"],
            "capabilities": {
                "observe": True, "respond": True, "act": True,
                "runner_managed_tools": True, "virtual_time": True,
                "seedable": True, "structured_output": True,
            },
            "state": {"run_isolation": "hard", "request_idempotency": True},
            "extensions": {
                "mib.calibration": {
                    "role": self.condition,
                    "same_model": True,
                    "memory_policy": self.policy.__class__.__name__,
                    "release_calibration_eligible": bool(self.empirical_eligible),
                }
            },
        }

    def reset(self, *, run_id: str, seed: int | str | None, virtual_time: str | None) -> dict[str, Any]:
        self.run_id = run_id; self.seed = seed
        self.long_term = []; self.transient = []; self.active_task = None
        self.seen_observe = set(); self.response_cache = {}; self.act_cache = {}; self.call_counter = 0
        return {"accepted": True}

    def observe(self, *, run_id: str, request_id: str, observation: Observation) -> dict[str, Any]:
        key = (run_id, request_id)
        if key in self.seen_observe:
            return {"accepted": True, "emissions": []}
        self.seen_observe.add(key)
        # Tool results produced after an ACTION Probe begins are current-task state,
        # not long-term memory. Past timeline tool results arrive before active_task.
        if self.active_task is not None and observation.tool_call_id:
            self.transient.append(observation)
        elif self.condition != "B0":
            self.long_term.append(observation)
        return {"accepted": True, "emissions": []}

    def _memory_context(self, query: str) -> tuple[str, bool, int]:
        selected, truncated = self.policy.select(self.long_term, query=query, limit_chars=self.max_memory_chars)
        lines = []
        for i, o in enumerate(selected, 1):
            lines.append(f"[{i}] {observation_text(o)}")
        text = "\n".join(lines) if lines else "<empty>"
        self.recorder.record_memory({
            "condition": self.condition,
            "available": len(self.long_term),
            "selected": len(selected),
            "selected_chars": len(text),
            "truncated": truncated,
        })
        return text, truncated, len(selected)

    def _transient_context(self) -> str:
        if not self.transient:
            return "<empty>"
        return "\n".join(f"[{i}] {observation_text(o)}" for i, o in enumerate(self.transient, 1))

    def _call(self, *, mode: str, body: dict[str, Any], memory_query: str, seed_key: str) -> dict[str, Any]:
        self.call_counter += 1
        mem, truncated, selected_n = self._memory_context(memory_query)
        user = (
            f"MODE: {mode}\n"
            f"LONG_TERM_MEMORY_CONTEXT:\n{mem}\n\n"
            f"CURRENT_TASK_TRANSIENT_STATE:\n{self._transient_context()}\n\n"
            f"REQUEST:\n{json.dumps(body, ensure_ascii=False, sort_keys=True)}\n"
        )
        messages = [
            {"role": "system", "content": self.system_prompt + "\n\n" + self.reasoning_policy},
            {"role": "user", "content": user},
        ]
        req_base = f"{self.run_id}:{self.call_counter}:{mode}"
        # The prompt actually sent this attempt.  A parse-repair attempt extends
        # it; a transport retry must resend the ORIGINAL prompt unchanged, or the
        # retried call answers a different question than its paired counterpart
        # in the other memory conditions and silently contaminates the pairing.
        attempt_messages = list(messages)
        for attempt in range(self.parse_retries + 1):
            req_id = _sha(req_base + f":{attempt}")[:24]
            last_text = ""
            try:
                parameters = dict(self.model_parameters)
                if self.seed_policy == "paired_per_call":
                    seed_material = f"{self.seed_base}:{self.seed}:{seed_key}:{mode}"
                    parameters["seed"] = int(_sha(seed_material)[:8], 16) & 0x7FFFFFFF
                completion = self.model.complete(messages=attempt_messages, parameters=parameters, request_id=req_id)
                last_text = completion.text.strip()
                parsed = _parse_json_object(last_text)
                self.recorder.record_call({
                    "condition": self.condition, "mode": mode, "request_id": req_id,
                    "input_chars": sum(len(m["content"]) for m in attempt_messages),
                    "output_chars": len(completion.text), "usage": completion.usage,
                    "model_identity": self.model.identity(), "memory_selected": selected_n,
                    "memory_truncated": truncated, "attempt": attempt,
                    **self._audit_fields(attempt_messages),
                })
                return parsed
            except Exception as exc:
                # A parse failure means the model answered but the answer was not
                # a JSON object; anything else (connection reset, timeout, HTTP
                # error) is a transport failure and says nothing about the answer.
                is_parse_failure = last_text != "" and isinstance(exc, (ValueError, KeyError))
                self.recorder.record_call({
                    "condition": self.condition, "mode": mode, "request_id": req_id,
                    "input_chars": sum(len(m["content"]) for m in attempt_messages),
                    "output_chars": len(last_text), "usage": {}, "error": repr(exc),
                    "error_kind": "parse" if is_parse_failure else "transport",
                    "model_identity": self.model.identity(), "memory_selected": selected_n,
                    "memory_truncated": truncated, "attempt": attempt,
                    **self._audit_fields(attempt_messages),
                })
                if attempt >= self.parse_retries:
                    raise
                if is_parse_failure:
                    attempt_messages = attempt_messages + [
                        {"role": "assistant", "content": last_text},
                        {"role": "user", "content": "Return only one valid JSON object matching the required output contract."},
                    ]
                else:
                    # Idempotent resend of the identical prompt.
                    attempt_messages = list(messages)
        raise RuntimeError("unreachable")

    def _audit_fields(self, messages: list[dict[str, str]]) -> dict[str, Any]:
        """Evidence for the fairness audit, captured from the call as sent."""
        rendered = "\n".join(m.get("content", "") for m in messages)
        return {
            "system_prompt_sha": self.system_prompt_sha,
            "reasoning_policy_sha": self.reasoning_policy_sha,
            "decoding_fingerprint": self.decoding_fingerprint,
            "memory_policy_id": getattr(self.policy, "id", self.condition),
            "seed_policy": self.seed_policy,
            # The model must not be able to tell which memory condition it is in.
            "condition_label_visible": self.condition in rendered,
        }

    def respond(self, *, run_id: str, request_id: str, interaction_id: str,
                input_data: dict[str, Any], virtual_time: str | None) -> AgentOutput:
        key = (run_id, request_id)
        if key in self.response_cache:
            return self.response_cache[key]
        self.active_task = None; self.transient = []
        query = str(input_data.get("content") or input_data.get("goal") or "")
        obj = self._call(mode="RESPONSE", body={"input": input_data, "virtual_time": virtual_time}, memory_query=query, seed_key=f"respond:{interaction_id}")
        typ = obj.get("type")
        if typ not in {"message", "structured", "abstention"}:
            raise ValueError(f"invalid response type: {typ!r}")
        out = AgentOutput(type=typ, content=obj.get("content"), value=obj.get("value"))
        self.response_cache[key] = out
        return out

    def act(self, *, run_id: str, request_id: str, task_id: str, goal: str | None,
            constraints: list[str], tools: list[dict[str, Any]], continuation: bool,
            virtual_time: str | None) -> ActStep:
        key = (run_id, request_id)
        if key in self.act_cache:
            return self.act_cache[key]
        if not continuation:
            self.active_task = task_id; self.transient = []
            self._active_goal = goal or ""
            self._active_constraints = list(constraints)
            self._active_tools = list(tools)
            self._active_turn = 0
        query = getattr(self, "_active_goal", "") + " " + " ".join(getattr(self, "_active_constraints", []))
        body = {
            "task_id": task_id,
            "goal": getattr(self, "_active_goal", goal or ""),
            "constraints": getattr(self, "_active_constraints", constraints),
            "tools": getattr(self, "_active_tools", tools),
            "continuation": continuation,
            "virtual_time": virtual_time,
        }
        turn_index = int(getattr(self, "_active_turn", 0))
        try:
            obj = self._call(mode="ACTION", body=body, memory_query=query, seed_key=f"act:{task_id}:{turn_index}")
        except Exception:
            # The Runner records an execution_failure and moves on.  Leaving
            # active_task set would route later timeline tool results into
            # transient state, dropping them from long-term memory for good.
            self.active_task = None
            self.transient = []
            raise
        self._active_turn = turn_index + 1
        typ = obj.get("type")
        if typ == "tool_call":
            out = ActStep(
                type="tool_call",
                tool_call_id=f"sm_{_sha(self.run_id + request_id)[:12]}",
                tool=obj.get("tool"), arguments=obj.get("arguments") or {},
            )
        elif typ in {"final", "abstention"}:
            out = ActStep(type=typ, content=obj.get("content"), value=obj.get("value"))
            self.active_task = None
        else:
            raise ValueError(f"invalid action type: {typ!r}")
        self.act_cache[key] = out
        return out

    def close(self, run_id: str | None = None) -> None:
        # The client factory may return a shared/stateless HTTP client. Closing is
        # therefore intentionally a no-op at Agent level. Harness owns clients.
        return None


def _parse_json_object(text: str) -> dict[str, Any]:
    t = text.strip()
    if t.startswith("```"):
        lines = t.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        t = "\n".join(lines).strip()
    obj = json.loads(t)
    if not isinstance(obj, dict):
        raise ValueError("model output must be a JSON object")
    return obj


def load_prompt(path: str | Path) -> str:
    return Path(path).read_text(encoding="utf-8")
