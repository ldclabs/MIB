from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import jsonschema


@dataclass(slots=True)
class ValidationResult:
    valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def load_json(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def validate_scenario(scenario: dict[str, Any], schema: dict[str, Any]) -> ValidationResult:
    errors: list[str] = []
    warnings: list[str] = []

    validator = jsonschema.Draft202012Validator(schema)
    for err in sorted(validator.iter_errors(scenario), key=lambda e: list(e.path)):
        where = "/".join(str(x) for x in err.path)
        errors.append(f"schema:{where or '$'}: {err.message}")

    timeline = scenario.get("timeline", [])
    probes = scenario.get("probes", [])
    evaluators = scenario.get("evaluators", [])
    ablations = scenario.get("ablations", [])
    actors = scenario.get("actors", [])

    def ids(xs: list[dict[str, Any]]) -> list[str]:
        return [str(x.get("id")) for x in xs if x.get("id") is not None]

    groups = {"timeline": ids(timeline), "probe": ids(probes), "evaluator": ids(evaluators), "ablation": ids(ablations), "actor": ids(actors)}
    for label, vals in groups.items():
        if len(vals) != len(set(vals)):
            errors.append(f"semantic: duplicate {label} id")

    timeline_ids, probe_ids, evaluator_ids, actor_ids = map(set, [groups["timeline"], groups["probe"], groups["evaluator"], groups["actor"]])

    tool_names: set[str] = set()
    for tool in (scenario.get("world") or {}).get("tools", []):
        tid = tool.get("id")
        for op in tool.get("operations", []):
            tool_names.add(f"{tid}.{op.get('name')}")

    for event in timeline:
        if event.get("actor") and event["actor"] not in actor_ids:
            errors.append(f"semantic:{event.get('id')}: unresolved actor {event['actor']}")

    for p in probes:
        trigger = p.get("trigger") or {}
        after = trigger.get("after_event")
        if after and after not in timeline_ids:
            errors.append(f"semantic:{p.get('id')}: unresolved trigger {after}")
        unsupported = set(trigger) - {"after_event"}
        if unsupported:
            warnings.append(f"milestone2:{p.get('id')}: trigger kinds not executable yet: {sorted(unsupported)}")
        for eid in p.get("evaluators", []):
            if eid not in evaluator_ids:
                errors.append(f"semantic:{p.get('id')}: unresolved evaluator {eid}")
        if p.get("delivery") not in {"respond", "act"}:
            warnings.append(f"milestone2:{p.get('id')}: delivery={p.get('delivery')} not executable yet")
        if p.get("delivery") == "act":
            for name in (p.get("input") or {}).get("available_tools", []):
                if name not in tool_names:
                    errors.append(f"semantic:{p.get('id')}: unavailable tool {name}")

    for e in evaluators:
        if e.get("type") == "composite":
            for c in e.get("components", []):
                if c.get("evaluator") not in evaluator_ids:
                    errors.append(f"semantic:{e.get('id')}: unresolved composite evaluator {c.get('evaluator')}")
            total = sum(float(c.get("weight", 0)) for c in e.get("components", []))
            if e.get("components") and abs(total - 1.0) > 1e-6:
                warnings.append(f"semantic:{e.get('id')}: composite weights sum to {total}, Runner will normalize")

    for a in ablations:
        for pid in a.get("probes", []):
            if pid not in probe_ids:
                errors.append(f"semantic:{a.get('id')}: unresolved probe {pid}")
        for eid in (a.get("targets") or {}).get("event_ids", []):
            if eid not in timeline_ids:
                errors.append(f"semantic:{a.get('id')}: unresolved event {eid}")
        if a.get("method") != "replay_excluding_events":
            warnings.append(f"milestone2:{a.get('id')}: ablation method {a.get('method')} not executable yet")

    seqs = [e.get("at", {}).get("sequence") for e in timeline]
    numeric = [s for s in seqs if isinstance(s, int)]
    if len(numeric) == len(seqs) and numeric != sorted(numeric):
        errors.append("semantic: timeline sequence is not monotonic")

    leakage = scenario.get("leakage") or {}
    for key in ("future_probe_visible_during_formation", "oracle_visible_to_agent", "ablation_labels_visible_to_agent", "hidden_world_state_visible_to_agent"):
        if leakage.get(key, False) is not False:
            errors.append(f"semantic: leakage policy {key} must be false")

    weights = (scenario.get("scoring") or {}).get("dimension_weights") or {}
    if weights and abs(sum(float(v) for v in weights.values()) - 1.0) > 1e-6:
        errors.append("semantic: dimension_weights must sum to 1")

    return ValidationResult(not errors, errors, warnings)
