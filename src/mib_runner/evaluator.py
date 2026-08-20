from __future__ import annotations

import json
import re
from typing import Any

from .types import AgentOutput
from .world import WorldState


def output_text(output: AgentOutput) -> str:
    if output.type == "structured":
        return json.dumps(output.value, ensure_ascii=False, sort_keys=True)
    return output.content or ""


def normalize(value: Any, mode: str | None) -> str:
    if isinstance(value, (dict, list)):
        text = json.dumps(value, ensure_ascii=False, sort_keys=True)
    else:
        text = "" if value is None else str(value)
    if mode in (None, "none"):
        return text
    if mode == "casefold_trim":
        return text.strip().casefold()
    if mode == "trim":
        return text.strip()
    if mode == "casefold_trim_collapse_ws":
        return re.sub(r"\s+", " ", text.strip()).casefold()
    raise ValueError(f"unsupported normalization mode: {mode}")


def evaluate_set_match(output: AgentOutput, oracle: dict[str, Any], config: dict[str, Any] | None) -> dict[str, Any]:
    config = config or {}
    mode = config.get("normalization", "casefold_trim")
    actual = normalize(output_text(output), mode)
    accepted = [normalize(x, mode) for x in oracle.get("accepted", [])]
    forbidden = [normalize(x, mode) for x in oracle.get("forbidden", [])]
    accepted_match = actual in accepted if accepted else False
    forbidden_match = actual in forbidden
    score = 1.0 if accepted_match and not forbidden_match else 0.0
    failure_codes: list[str] = []
    if not accepted_match:
        failure_codes.append("retrieval_miss")
    if forbidden_match:
        failure_codes.append("stale_memory_adoption")
    return {
        "score": score,
        "passed": score == 1.0,
        "failure_codes": failure_codes,
        "details": {"actual_normalized": actual, "accepted_count": len(accepted), "forbidden_match": forbidden_match},
    }


def _condition_ok(actual: Any, operator: str, expected: Any = None) -> bool:
    if operator == "eq": return actual == expected
    if operator == "neq": return actual != expected
    if operator == "exists": return actual is not None
    if operator == "not_exists": return actual is None
    if operator == "contains":
        try: return expected in actual
        except TypeError: return False
    if operator == "gte":
        try: return actual >= expected
        except TypeError: return False
    if operator == "lte":
        try: return actual <= expected
        except TypeError: return False
    raise ValueError(operator)


def evaluate_world_state(world: WorldState, oracle: dict[str, Any], config: dict[str, Any] | None) -> dict[str, Any]:
    assertions = list(oracle.get("world_assertions") or [])
    if not assertions:
        return {"score": 0.0, "passed": False, "failure_codes": ["evaluator_error"], "details": {"reason": "no world_assertions"}}
    checks = []
    for a in assertions:
        actual = world.get(a["path"], None)
        ok = _condition_ok(actual, a["operator"], a.get("value"))
        checks.append({"path": a["path"], "operator": a["operator"], "expected": a.get("value"), "actual": actual, "passed": ok})
    score = sum(1.0 for x in checks if x["passed"]) / len(checks)
    failures = [] if score == 1.0 else ["trajectory_collapse"]
    return {"score": score, "passed": score == 1.0, "failure_codes": failures, "details": {"assertions": checks}}


def evaluate_trajectory(trace: list[dict[str, Any]], oracle: dict[str, Any], config: dict[str, Any] | None) -> dict[str, Any]:
    reqs = list(oracle.get("trajectory_requirements") or [])
    if not reqs:
        return {"score": 0.0, "passed": False, "failure_codes": ["evaluator_error"], "details": {"reason": "no trajectory_requirements"}}
    tools = [x.get("tool") for x in trace if x.get("kind") == "tool_call"]
    checks = []
    failures: set[str] = set()
    for r in reqs:
        typ = r["type"]
        ok = False
        if typ == "required_action":
            ok = r.get("action") in tools
        elif typ == "forbidden_action":
            ok = r.get("action") not in tools
            if not ok:
                failures.add("negative_transfer")
        elif typ in {"before", "after"}:
            first, second = r.get("first"), r.get("second")
            try:
                i1, i2 = tools.index(first), tools.index(second)
                ok = i1 < i2 if typ == "before" else i1 > i2
            except ValueError:
                ok = False
        elif typ == "max_occurrences":
            ok = tools.count(r.get("action")) <= int(r.get("count", 0))
        elif typ == "min_occurrences":
            ok = tools.count(r.get("action")) >= int(r.get("count", 0))
        else:
            raise ValueError(f"unsupported trajectory requirement {typ}")
        if not ok:
            failures.add("trajectory_collapse")
        checks.append({"requirement": r, "passed": ok})
    score = sum(1.0 for x in checks if x["passed"]) / len(checks)
    return {"score": score, "passed": score == 1.0, "failure_codes": sorted(failures), "details": {"requirements": checks, "tool_sequence": tools}}


def _eval_one(eid: str, spec: dict[str, Any], output: AgentOutput, probe: dict[str, Any], evaluator_map: dict[str, dict[str, Any]], context: dict[str, Any]) -> dict[str, Any]:
    etype = spec["type"]
    if etype == "set_match":
        r = evaluate_set_match(output, probe["oracle"], spec.get("config"))
    elif etype == "world_state":
        r = evaluate_world_state(context["world"], probe["oracle"], spec.get("config"))
    elif etype == "trajectory":
        r = evaluate_trajectory(context.get("action_trace", []), probe["oracle"], spec.get("config"))
    elif etype == "composite":
        comps = spec.get("components") or []
        if not comps:
            r = {"score": 0.0, "passed": False, "failure_codes": ["evaluator_error"], "details": {"reason": "empty composite"}}
        else:
            rows = []
            total_w = 0.0
            total = 0.0
            failures: set[str] = set()
            for c in comps:
                sub = evaluator_map[c["evaluator"]]
                rr = _eval_one(c["evaluator"], sub, output, probe, evaluator_map, context)
                w = float(c["weight"])
                total_w += w
                total += w * float(rr["score"])
                failures.update(rr.get("failure_codes", []))
                rows.append({"evaluator": c["evaluator"], "weight": w, "score": rr["score"], "passed": rr["passed"]})
            score = total / total_w if total_w else 0.0
            r = {"score": score, "passed": score == 1.0, "failure_codes": sorted(failures), "details": {"components": rows}}
    else:
        raise NotImplementedError(f"Milestone 4 evaluator not implemented: {etype!r}")
    return {"evaluator_id": eid, "evaluator_type": etype, **r}


def evaluate_probe(output: AgentOutput, probe: dict[str, Any], evaluator_map: dict[str, dict[str, Any]], context: dict[str, Any] | None = None) -> tuple[float, list[dict[str, Any]]]:
    context = context or {}
    results = [_eval_one(eid, evaluator_map[eid], output, probe, evaluator_map, context) for eid in probe.get("evaluators", [])]
    score = sum(float(x["score"]) for x in results) / len(results) if results else 0.0
    return score, results
