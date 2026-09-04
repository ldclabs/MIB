"""ScenarioBuilder: turns a program's sampled history into an executable Scenario Instance.

The builder owns the world model, the timeline, the virtual clock and the
probes, and at ``finalize`` derives from the model:

- every Probe Oracle (accepted / forbidden / expected_status) — §4.7
- the relevant-memory ablation of every value Probe from its support set — §4.8
- the counterfactual-content ablation (``swap_parameter``) — §7.2
- a leak proof: withholding the support set makes the answer underivable
"""

from __future__ import annotations

import hashlib
import json
import random
from datetime import datetime, timedelta, timezone
from typing import Any

from .. import __version__
from ..worldmodel import Assertion, QueryResult, Source, WorldModel, oracle_from_result
from . import interference as interf
from .pools import ATTRIBUTES, AttributeSpec
from .surface import prompt as make_prompt
from .surface import realize, tool_payload

MIB_FORMAT = "0.2"


class GenerationError(ValueError):
    pass


def stable_seed(*parts: Any) -> int:
    digest = hashlib.sha256("|".join(str(p) for p in parts).encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big")


class ScenarioBuilder:
    def __init__(
        self,
        *,
        program_id: str,
        program_version: str,
        seed: int | str,
        rung: int,
        interference_count: int,
        title: str,
        suite: str,
        dimensions: list[str],
        dimension_weights: dict[str, float],
        capabilities: list[str],
        start_time: str = "2026-01-01T09:00:00Z",
        instance_index: int = 0,
    ) -> None:
        self.program_id = program_id
        self.program_version = program_version
        self.seed = seed
        self.rung = rung
        self.interference_count = interference_count
        self.rng = random.Random(stable_seed(program_id, program_version, seed))
        self.title = title
        self.suite = suite
        self.dimensions = list(dimensions)
        self.dimension_weights = dict(dimension_weights)
        self.capabilities = list(capabilities)
        self.model = WorldModel()
        self.actors: dict[str, dict[str, Any]] = {}
        self.events: list[dict[str, Any]] = []
        self.probes: list[dict[str, Any]] = []
        self.ablations: list[dict[str, Any]] = []
        self.world_state: dict[str, Any] = {}
        self.tools: list[dict[str, Any]] = []
        self._seq = 0
        self._clock = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
        self._template_index: dict[str, int] = {}
        self._realization: dict[str, dict[str, Any]] = {}
        self._probe_meta: dict[str, dict[str, Any]] = {}
        self.instance_index = instance_index

    # ------------------------------------------------------------ primitives
    def _next(self, stage: str, minutes: tuple[int, int] = (5, 240)) -> tuple[int, str]:
        self._seq += 1
        self._clock += timedelta(minutes=self.rng.randint(*minutes))
        return self._seq, self._clock.isoformat().replace("+00:00", "Z")

    def actor(self, actor_id: str, name: str, kind: str = "person", authority: float = 0.5) -> str:
        self.actors[actor_id] = {"id": actor_id, "kind": kind, "display_name": name}
        self.model.add_source(Source(actor_id, kind, authority, name))
        return actor_id

    def event(self, event_id: str, *, stage: str, etype: str, actor: str | None, content: str | None = None,
              payload: Any = None, visibility: str = "agent", extra: dict[str, Any] | None = None,
              minutes: tuple[int, int] = (5, 240)) -> str:
        seq, at = self._next(stage, minutes)
        row: dict[str, Any] = {"id": event_id, "stage": stage, "type": etype, "at": {"sequence": seq, "time": at}, "visibility": visibility}
        if actor:
            row["actor"] = actor
        if content is not None:
            row["content"] = content
        if payload is not None:
            row["payload"] = payload
        if extra:
            row.update(extra)
        self.events.append(row)
        return event_id

    def say(self, event_id: str, *, source: str, subject: str, attribute: str, value: str | None, kind: str = "state",
            truth_bearing: bool | None = None, supersedes: str | None = None, stage: str = "past",
            subject_name: str | None = None) -> str:
        spec = ATTRIBUTES[attribute]
        first_person = source == subject
        name = subject_name or self.actors.get(subject, {}).get("display_name") or subject
        text, index = realize(spec, kind, value or "", subject_name=name, first_person=first_person, rng=self.rng)
        self.event(event_id, stage=stage, etype="interaction", actor=source, content=text)
        tb = truth_bearing if truth_bearing is not None else (first_person and kind in ("state", "update", "correction"))
        self.model.add(Assertion(event_id, self._seq, source, subject, attribute, value if kind != "retraction" else None, kind, tb, supersedes))
        self._realization[event_id] = {"spec": attribute, "kind": kind, "first_person": first_person, "name": name, "index": index}
        return event_id

    def retract(self, event_id: str, *, source: str, subject: str, attribute: str, of: str, stage: str = "past") -> str:
        """"Forget what I said about X": withdraws assertion ``of`` from the record (§4.2)."""
        return self.say(event_id, source=source, subject=subject, attribute=attribute, value=None, kind="retraction",
                        truth_bearing=False, supersedes=of, stage=stage)

    def observe_tool(self, event_id: str, *, tool_actor: str, tool_name: str, subject: str, attribute: str, value: str,
                     stage: str = "past") -> str:
        payload = tool_payload(tool_name, subject, attribute, value)
        self.event(event_id, stage=stage, etype="tool_result", actor=tool_actor, payload=payload,
                   extra={"tool": tool_name, "tool_call_id": f"call_{event_id}"})
        self.model.add(Assertion(event_id, self._seq, tool_actor, subject, attribute, value, "observation", True))
        self._realization[event_id] = {"tool": tool_name, "subject": subject, "attribute": attribute}
        return event_id

    def neutral(self, event_id: str, actor: str, stage: str = "interference") -> str:
        return self.event(event_id, stage=stage, etype="distractor", actor=actor, content=interf.neutral_sentence(self.rng))

    def interfere(self, *, subject_id: str, attribute: str, exclude_values: set[str], other_actors: list[tuple[str, str]],
                  count: int | None = None, mix: dict[str, float] | None = None, prefix: str = "d") -> list[str]:
        """Plan and emit the rung's interference block."""
        count = self.interference_count if count is None else count
        spec = ATTRIBUTES[attribute]
        subject_name = self.actors[subject_id]["display_name"]
        for actor_id, actor_name in other_actors:
            if actor_id not in self.actors:
                self.actor(actor_id, actor_name)
        planned = interf.plan(self.rng, count, subject_id=subject_id, subject_name=subject_name, spec=spec,
                              exclude_values=exclude_values, other_actors=other_actors, mix=mix)
        ids = []
        for i, item in enumerate(planned, start=1):
            eid = f"{prefix}-{i:04d}"
            self.event(eid, stage="interference", etype="distractor", actor=item.actor, content=item.content, minutes=(2, 90))
            if item.assertion:
                a = item.assertion
                self.model.add(Assertion(eid, self._seq, a["source"], a["subject"], a["attribute"], a["value"], a["kind"], a["truth_bearing"]))
            ids.append(eid)
        return ids

    def checkpoint(self, event_id: str = "cp") -> str:
        return self.event(event_id, stage="pre_probe", etype="checkpoint", actor=None, visibility="harness", minutes=(1, 5))

    def maintenance_window(self, event_id: str, budget: str = "PT1H") -> str:
        return self.event(event_id, stage="consolidation", etype="maintenance_window", actor=None,
                          payload={"budget": budget}, visibility="agent")

    # ---------------------------------------------------------------- probes
    def probe(self, probe_id: str, *, query: dict[str, Any], prompt: str, kind: str, dimensions: list[str],
              asker: str, trigger: str = "cp", weight: float = 1.0, historical: bool = False,
              answer_schema: dict[str, Any] | None = None, other_values_from: tuple[str, str] | None = None,
              swap: bool = True, relevant: bool = True) -> str:
        """A respond Probe.  ``asker`` is the actor the question comes from: a message has
        a sender, and "my timezone" is only well defined given one."""
        spec_id = query.get("attribute") or (query.get("attributes") or [""])[-1]
        asker_name = self.actors.get(asker, {}).get("display_name") or asker
        self.probes.append({
            "id": probe_id, "kind": kind, "trigger": {"after_event": trigger}, "delivery": "respond",
            "input": {"content": prompt, "context": {"actor": asker, "display_name": asker_name},
                      "answer_schema": answer_schema or {"value": True, "status": True, "confidence": True}},
            "query": query, "oracle": {}, "evaluators": ["eval-structured"], "dimensions": list(dimensions), "weight": weight,
        })
        self._probe_meta[probe_id] = {"spec": spec_id, "historical": historical, "other_values_from": other_values_from,
                                      "swap": swap, "relevant": relevant}
        return probe_id

    def task(self, event_id: str, *, actor: str, goal: str, tools: list[str], oracle: dict[str, Any] | None = None,
             constraints: list[str] | None = None, max_agent_turns: int = 12, stage: str = "past") -> str:
        """A lived task (§5.3).  ``oracle`` makes the trial a learning-curve sample (§7.9); it is never a score."""
        body: dict[str, Any] = {"goal": goal, "available_tools": list(tools), "constraints": list(constraints or []),
                                "max_agent_turns": max_agent_turns}
        if oracle:
            body["oracle"] = oracle
            body["evaluators"] = ["eval-action"]
        return self.event(event_id, stage=stage, etype="task", actor=actor, extra={"task": body})

    def raw_probe(self, probe: dict[str, Any]) -> str:
        self.probes.append(probe)
        return probe["id"]

    def ablation(self, ablation: dict[str, Any]) -> None:
        self.ablations.append(ablation)

    # ---------------------------------------------------------------- derive
    def _forms(self, attribute: str):
        spec: AttributeSpec | None = ATTRIBUTES.get(attribute)
        return spec.forms if spec else (lambda v: [str(v)])

    def _oracle(self, model: WorldModel, probe: dict[str, Any]) -> tuple[dict[str, Any], QueryResult]:
        query = probe["query"]
        meta = self._probe_meta[probe["id"]]
        result = model.evaluate(query)
        s, a = meta["other_values_from"] or (query.get("subject"), query.get("attribute"))
        if query.get("op") == "hop":
            attr = query["attributes"][-1]
            others = sorted({x.value for x in model.assertions if x.attribute == attr}, key=str)
            forms = self._forms(attr)
        else:
            others = (model.values_seen(s, a) + model.retracted_values(s, a)) if s and a else []
            forms = self._forms(a or "")
        codes = self._failure_codes(model, s, a, result) if s and a and query.get("op") != "hop" else None
        oracle = oracle_from_result(result, forms=forms, other_values=others, historical=meta["historical"], codes=codes)
        return oracle, result

    @staticmethod
    def _failure_codes(model: WorldModel, subject: str, attribute: str, result: QueryResult) -> dict[Any, str]:
        """Why each wrong value would be wrong (MIB-Specification §4.7 ``failure_code_by_value``).

        A superseded or retracted value is stale adoption; the original of a
        correction is correction loss; a non-authoritative contradiction is
        authority confusion; a value that was only asked about or hypothesized
        is a memory hallucination.  Priority follows that order.
        """
        codes: dict[Any, str] = {}
        rows = sorted(model.assertions, key=lambda x: x.seq)
        corrected = {x.supersedes for x in rows if x.kind == "correction" and x.supersedes}
        retracted = {x.supersedes for x in rows if x.kind == "retraction" and x.supersedes}
        def put(value: Any, code: str) -> None:
            if value is None or (result.kind == "value" and value == result.value):
                return
            codes.setdefault(value, code)
        for x in rows:
            if (x.subject, x.attribute) != (subject, attribute):
                continue
            if x.event_id in retracted:
                put(x.value, "stale_memory_adoption")
            elif x.event_id in corrected:
                put(x.value, "correction_loss")
            elif x.truth_bearing and x.kind in ("state", "update", "observation"):
                put(x.value, "stale_memory_adoption")
        for x in rows:
            if (x.subject, x.attribute) == (subject, attribute) and x.kind == "contradiction":
                put(x.value, "authority_confusion")
        for x in rows:
            if (x.subject, x.attribute) == (subject, attribute) and x.kind in ("question", "hypothetical"):
                put(x.value, "memory_hallucination")
        return codes

    def finalize(self) -> dict[str, Any]:
        # Oracles.
        results: dict[str, QueryResult] = {}
        for p in self.probes:
            if "query" not in p:
                continue
            p["oracle"], results[p["id"]] = self._oracle(self.model, p)

        # Relevant-memory ablations from support sets, with a leak proof.
        for p in self.probes:
            meta = self._probe_meta.get(p["id"])
            if not meta or not meta["relevant"]:
                continue
            support = self.model.support_set(p["query"])
            if support.empty:
                continue
            withheld = support.minimal
            if not self.model.leak_free(p["query"], withheld):
                raise GenerationError(f"{p['id']}: support set does not remove the answer (leak)")
            self.ablations.append({
                "id": f"a-relevant-{p['id']}", "kind": "relevant_memory", "probes": [p["id"]],
                "method": "replay_excluding_events", "targets": {"event_ids": withheld}, "expected_effect": "degrade",
                **({"description": f"redundant causal information set: {support.groups}"} if support.groups else {}),
            })

        # Counterfactual-content ablations.
        for p in self.probes:
            meta = self._probe_meta.get(p["id"])
            if not meta or not meta["swap"] or results[p["id"]].kind != "value":
                continue
            support = self.model.support_set(p["query"])
            if support.empty:
                continue
            pivot = support.minimal[-1]
            realization = self._realization.get(pivot)
            base_assertion = self.model.assertion(pivot)
            if realization is None or base_assertion is None:
                continue
            attribute = base_assertion.attribute
            spec = ATTRIBUTES.get(attribute)
            if spec is None:
                continue
            seen = set(self.model.values_seen(base_assertion.subject, attribute))
            # Prefer a value nothing in the timeline mentioned; at long distances the
            # interference block may have mentioned every pool value, and a mentioned
            # (never asserted) value is still a valid twin: only the pivot changes.
            pool = [v for v in spec.values if v not in seen and v != results[p["id"]].value] \
                or [v for v in spec.values if v != results[p["id"]].value]
            if not pool:
                continue
            alt = self.rng.choice(pool)
            twin = self.model.with_value(pivot, alt)
            changed: dict[str, dict[str, Any]] = {}
            for q in self.probes:
                if "query" not in q:
                    continue
                oracle_cf, res_cf = self._oracle(twin, q)
                if res_cf != results[q["id"]]:
                    # Under the counterfactual the original answer is the stale one: forbid it explicitly.
                    original = results[q["id"]]
                    if original.kind == "value":
                        attr_forms = self._forms(q["query"].get("attribute") or (q["query"].get("attributes") or [""])[-1])
                        forbidden = list(oracle_cf.get("forbidden") or [])
                        for f in attr_forms(original.value):
                            if f not in oracle_cf.get("accepted", []) and f not in forbidden:
                                forbidden.append(f)
                        oracle_cf["forbidden"] = forbidden
                    changed[q["id"]] = oracle_cf
            if p["id"] not in changed:
                continue
            if "tool" in realization:
                replacement: dict[str, Any] = {"payload": tool_payload(realization["tool"], realization["subject"], attribute, alt)}
            else:
                text, _ = realize(spec, realization["kind"], alt, subject_name=realization["name"],
                                  first_person=realization["first_person"], rng=self.rng, template_index=realization["index"])
                replacement = {"content": text}
            self.ablations.append({
                "id": f"a-swap-{p['id']}", "kind": "counterfactual_content", "probes": sorted(changed),
                "method": "swap_parameter", "targets": {"event_ids": [pivot]},
                "counterfactual": {"events": {pivot: replacement}, "oracle": changed},
                "expected_effect": "track",
            })

        # Consolidation: withholding every maintenance window is the paired
        # control for the Agent's own consolidation work (§7.2, consolidation_benefit).
        windows = [e["id"] for e in self.events if e.get("type") == "maintenance_window"]
        if windows and self.probes:
            self.ablations.append({
                "id": "a-no-maintenance", "kind": "no_maintenance", "probes": [p["id"] for p in self.probes],
                "method": "replay_excluding_events", "targets": {"event_ids": windows}, "expected_effect": "informational",
                "description": "Maintenance windows withheld; the paired difference is the value of the Agent's consolidation work.",
            })

        # Distance in three units (§8.1): interference events, whitespace tokens, virtual hours.
        interference = [e for e in self.events if e.get("stage") == "interference"]
        interference_tokens = sum(len(str(e.get("content") or "").split()) for e in interference)
        formation = [e for e in self.events if e.get("stage") in ("seed", "past", "consolidation")]
        checkpoint = next((e for e in self.events if e.get("stage") == "pre_probe"), None)
        distance_hours = 0.0
        if formation and checkpoint:
            t0 = datetime.fromisoformat(formation[-1]["at"]["time"].replace("Z", "+00:00"))
            t1 = datetime.fromisoformat(checkpoint["at"]["time"].replace("Z", "+00:00"))
            distance_hours = round((t1 - t0).total_seconds() / 3600.0, 3)

        digest = hashlib.sha256(json.dumps(
            {"events": self.events, "probes": self.probes}, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()
        template_id = template_id_for(self.program_id)
        instance_id = f"{template_id}"
        scenario = {
            "mib": MIB_FORMAT,
            "kind": "MemoryEpisodeProgram",
            "id": instance_id,
            "version": self.program_version,
            "status": "generated",
            "title": self.title,
            "description": f"Generated by {self.program_id} {self.program_version}; seed {self.seed}; rung {self.rung} ({self.interference_count} interference events).",
            "suite": self.suite,
            "dimensions": self.dimensions,
            "instantiation": {
                "template_id": template_id, "template_version": self.program_version, "seed": self.seed,
                "program": self.program_id, "program_version": self.program_version,
                "rung": self.rung, "interference_count": self.interference_count,
                "interference_tokens": interference_tokens, "distance_hours": distance_hours,
                "parameter_digest": digest, "generator_version": f"mib-generate/{__version__}",
            },
            "requirements": {"black_box_compatible": True, "capabilities": self.capabilities},
            "execution": {"max_agent_turns": 20, "max_tool_calls": 20, "on_agent_error": "fail_probe", "on_timeout": "fail_probe"},
            "leakage": {"probe_sampling": "late", "future_probe_visible_during_formation": False, "oracle_visible_to_agent": False,
                        "ablation_labels_visible_to_agent": False, "hidden_world_state_visible_to_agent": False},
            "actors": list(self.actors.values()),
            "world": {"clock": {"mode": "virtual", "start": self.events[0]["at"]["time"] if self.events else "2026-01-01T09:00:00Z", "timezone": "UTC"},
                      "state": self.world_state, **({"tools": self.tools} if self.tools else {})},
            "timeline": self.events,
            "probes": self.probes,
            "ablations": self.ablations,
            "evaluators": [
                {"id": "eval-structured", "type": "structured", "config": {"normalization": "answer_normalized", "weights": {"value": 0.8, "status": 0.2}}},
                {"id": "eval-world", "type": "world_state"},
                {"id": "eval-trajectory", "type": "trajectory"},
                {"id": "eval-action", "type": "composite", "components": [{"evaluator": "eval-world", "weight": 0.6}, {"evaluator": "eval-trajectory", "weight": 0.4}]},
                {"id": "eval-emission", "type": "emission"},
            ],
            "scoring": {"probe_aggregation": "weighted_mean", "score_range": {"min": 0, "max": 100},
                        "dimension_weights": self.dimension_weights},
        }
        return scenario


def template_id_for(program_id: str) -> str:
    return "MIB-GEN-" + program_id.replace("mib.", "").replace(".", "-").upper()


def probe_prompt(attribute: str, which: str, *, subject_name: str, first_person: bool, source_name: str | None = None) -> str:
    return make_prompt(ATTRIBUTES[attribute], which, subject_name=subject_name, first_person=first_person, source_name=source_name)
