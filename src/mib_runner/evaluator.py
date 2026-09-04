from __future__ import annotations

import json
import re
from typing import Any

from .types import AgentOutput
from .world import WorldState


def output_text(output: AgentOutput) -> str:
    """Render an Agent output as the text an Evaluator compares.

    A structured answer whose value is a scalar is the same answer as the
    message form: ``{"type":"structured","value":"green tea"}`` must not be
    JSON-quoted into ``"green tea"``, or a protocol-compliant Agent that chooses
    the structured envelope scores zero on every set_match Probe.  Containers
    still serialize, since there is no single obvious text form for them.
    """
    if output.type == "structured":
        value = output.value
        if isinstance(value, dict) and "value" in value:
            value = value["value"]
        if isinstance(value, str):
            return value
        if isinstance(value, bool):
            return "true" if value else "false"
        if value is None:
            return ""
        if isinstance(value, (int, float)):
            return repr(value) if isinstance(value, float) else str(value)
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return output.content or ""


# Punctuation an answer may carry without changing its meaning ("AX-91." is the
# same answer as "AX-91").  Inner punctuation is preserved so that values like
# "UTC+1" or "AX-91" survive normalization intact.
_EDGE_PUNCTUATION = " \t\r\n.,;:!?\"'`()[]{}<>"


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
    if mode == "answer_normalized":
        # Collapse whitespace, casefold, and drop edge punctuation.  Intended
        # for short-answer Probes where format compliance must not be scored as
        # a memory failure.
        text = re.sub(r"\s+", " ", text.strip()).casefold()
        return text.strip(_EDGE_PUNCTUATION)
    raise ValueError(f"unsupported normalization mode: {mode}")


def _contains_value(haystack: str, needle: str) -> bool:
    """Whole-token containment, so 'AX-9' does not match inside 'AX-91'."""
    if not needle:
        return False
    return re.search(rf"(?<![\w-]){re.escape(needle)}(?![\w-])", haystack) is not None


def _match_value(actual: str, oracle: dict[str, Any], mode: str, match: str) -> tuple[bool, str | None]:
    """``(accepted matched, the forbidden value that matched or None)``; the raw forbidden form is
    returned so that ``oracle.failure_code_by_value`` can say why it was wrong."""
    accepted = [normalize(x, mode) for x in oracle.get("accepted", [])]
    forbidden = [(normalize(x, mode), str(x)) for x in oracle.get("forbidden", [])]
    if match == "exact":
        hit = next((raw for norm, raw in forbidden if actual == norm), None)
        return (actual in accepted if accepted else False), hit
    hit = next((raw for norm, raw in forbidden if _contains_value(actual, norm)), None)
    return (any(_contains_value(actual, a) for a in accepted) if accepted else False), hit


def _score_value(actual: str, *, abstained: bool, oracle: dict[str, Any], mode: str, match: str) -> tuple[float, list[str], dict[str, Any]]:
    """The one value-scoring policy shared by set_match and structured (MIB-Specification §4.7)."""
    expected_status = oracle.get("expected_status")
    accepted_match, forbidden_hit = _match_value(actual, oracle, mode, match)
    forbidden_match = forbidden_hit is not None
    # The Oracle may say why a wrong value is wrong (stale, corrected, non-authoritative, never asserted).
    forbidden_code = (oracle.get("failure_code_by_value") or {}).get(forbidden_hit, "stale_memory_adoption") if forbidden_match else None
    failure_codes: list[str] = []
    if expected_status == "unknown":
        # A correct abstention scores 1; an unsupported definite claim is false certainty.
        score = 1.0 if (abstained or (accepted_match and not forbidden_match)) else 0.0
        if score == 0.0:
            failure_codes.append("false_certainty")
            if forbidden_code and forbidden_code != "stale_memory_adoption":
                failure_codes.append(forbidden_code)
    elif abstained:
        # The answer was knowable; abstaining is a miss, not a safe default.
        score = 0.0
        failure_codes.append("retrieval_miss")
    else:
        score = 1.0 if accepted_match and not forbidden_match else 0.0
        if forbidden_match:
            # Policy: a forbidden (superseded, contradicted, or merely asked-about)
            # value anywhere in the answer fails the Probe even when the accepted
            # value is present too.  Probes that declare ``forbidden`` ask for the
            # value only; hedging between the current and the stale value is
            # stale adoption, not richness.
            failure_codes.append(forbidden_code or "stale_memory_adoption")
        elif not accepted_match:
            failure_codes.append("retrieval_miss")
    return score, failure_codes, {"accepted_match": accepted_match, "forbidden_match": forbidden_match}


def evaluate_set_match(output: AgentOutput, oracle: dict[str, Any], config: dict[str, Any] | None) -> dict[str, Any]:
    """Score a short answer against accepted / forbidden value sets.

    ``match`` selects how the answer is compared:

    ``exact``     the whole normalized output must equal an accepted value.
    ``contains``  (default) the accepted value must appear as a whole token in
                  the output.  A correct answer wrapped in a sentence is still
                  a correct answer, and a forbidden (stale) value mentioned
                  anywhere is still detectable as stale adoption.
    """
    config = config or {}
    mode = config.get("normalization", "answer_normalized")
    match = config.get("match", "contains")
    if match not in {"exact", "contains"}:
        raise ValueError(f"unsupported set_match mode: {match}")
    abstained = output.type == "abstention"
    actual = normalize(output_text(output), mode)
    score, failure_codes, details = _score_value(actual, abstained=abstained, oracle=oracle, mode=mode, match=match)
    return {
        "score": score,
        "passed": score == 1.0,
        "failure_codes": failure_codes,
        "details": {
            "actual_normalized": actual,
            "match": match,
            "expected_status": oracle.get("expected_status"),
            "abstained": abstained,
            "accepted_count": len(oracle.get("accepted", [])),
            **details,
        },
    }


# ----------------------------------------------------------------- structured
_FIELD_LINE = re.compile(r"^\s*(value|answer|status|confidence)\s*[:=]\s*(.+?)\s*$", re.IGNORECASE)
_STATUS_CLASS = {
    "known": {"known"},
    "historical": {"historical", "known"},
    "unknown": {"unknown"},
    "contested": {"contested"},
    "not_applicable": {"not_applicable", "unknown"},
}


def _as_float(value: Any) -> float | None:
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    return f if 0.0 <= f <= 1.0 else None


def parse_structured(output: AgentOutput) -> dict[str, Any]:
    """Deterministic parser from any output form to ``{value, status, confidence}``.

    The reference implementation never uses a model to grade; a model may be
    used only to map free text to this schema, and that mapping would be
    logged here as the parsed record (MIB-Specification §4.7).
    """
    if output.type == "abstention":
        return {"value": None, "status": "unknown", "confidence": None, "source": "abstention"}
    if output.type == "structured":
        v = output.value
        if isinstance(v, dict):
            return {
                "value": v.get("value", v.get("answer")),
                "status": (str(v["status"]).strip().casefold() if v.get("status") is not None else None),
                "confidence": _as_float(v.get("confidence")),
                "source": "structured",
            }
        return {"value": output_text(output), "status": None, "confidence": None, "source": "structured_scalar"}
    text = output.content or ""
    stripped = text.strip()
    if stripped.startswith("{"):
        try:
            obj = json.loads(stripped)
        except json.JSONDecodeError:
            obj = None
        if isinstance(obj, dict):
            return {
                "value": obj.get("value", obj.get("answer")),
                "status": (str(obj["status"]).strip().casefold() if obj.get("status") is not None else None),
                "confidence": _as_float(obj.get("confidence")),
                "source": "json",
            }
    fields: dict[str, str] = {}
    for line in text.splitlines():
        m = _FIELD_LINE.match(line)
        if m:
            fields[m.group(1).casefold()] = m.group(2)
    if "value" in fields or "answer" in fields:
        return {
            "value": fields.get("value", fields.get("answer")),
            "status": fields.get("status", "").strip().casefold() or None,
            "confidence": _as_float(fields.get("confidence")),
            "source": "fields",
        }
    return {"value": text, "status": None, "confidence": None, "source": "text"}


def evaluate_structured(output: AgentOutput, oracle: dict[str, Any], config: dict[str, Any] | None) -> dict[str, Any]:
    """Score ``{value, status, confidence}`` field by field (MIB-Specification §4.7).

    ``value`` follows the shared value policy; ``status`` must name the right
    epistemic class; ``confidence`` yields a Brier-style calibration score that
    is reported and, when the evaluator gives it weight, scored.
    """
    config = config or {}
    mode = config.get("normalization", "answer_normalized")
    match = config.get("match", "contains")
    weights = dict(config.get("weights") or {"value": 0.8, "status": 0.2})
    parsed = parse_structured(output)
    expected_status = oracle.get("expected_status") or "known"
    value_text = normalize(parsed["value"], mode) if parsed["value"] is not None else ""
    abstained = output.type == "abstention" or parsed["status"] == "unknown" or value_text == "unknown"
    value_score, failure_codes, details = _score_value(value_text, abstained=abstained, oracle=oracle, mode=mode, match=match)

    components: list[tuple[str, float, float]] = [("value", float(weights.get("value", 0.8)), value_score)]
    status_score: float | None = None
    if parsed["status"] is not None:
        status_score = 1.0 if parsed["status"] in _STATUS_CLASS.get(expected_status, {expected_status}) else 0.0
        components.append(("status", float(weights.get("status", 0.2)), status_score))
        if status_score == 0.0 and expected_status == "unknown" and "false_certainty" not in failure_codes:
            failure_codes.append("false_certainty")
    calibration: float | None = None
    if parsed["confidence"] is not None:
        calibration = 1.0 - (parsed["confidence"] - value_score) ** 2
        if float(weights.get("confidence", 0.0)) > 0:
            components.append(("confidence", float(weights["confidence"]), calibration))
    total_w = sum(w for _, w, _ in components)
    score = sum(w * s for _, w, s in components) / total_w if total_w else value_score
    return {
        "score": score,
        "passed": score == 1.0,
        "failure_codes": failure_codes,
        "details": {
            "parsed": parsed,
            "actual_normalized": value_text,
            "expected_status": expected_status,
            "abstained": abstained,
            "value_score": value_score,
            "status_score": status_score,
            "calibration": calibration,
            **details,
        },
    }


# ------------------------------------------------------------------ emissions
def _emission_matches(text: str, tokens: list[str]) -> bool:
    folded = (text or "").casefold()
    return bool(tokens) and all(str(t).casefold() in folded for t in tokens)


def evaluate_emission(emission_log: list[dict[str, Any]], trigger_index: int, oracle: dict[str, Any],
                      config: dict[str, Any] | None) -> dict[str, Any]:
    """Prospective memory: did the Agent emit on its trigger and not before? (MIB-Specification §4.6)"""
    spec = oracle.get("expected_emission") or {}
    window = int(spec.get("window", 1))
    tokens = list(spec.get("must_contain") or ([spec["topic"]] if spec.get("topic") else []))
    in_window = [e for e in emission_log if trigger_index <= int(e["index"]) <= trigger_index + window]
    matching = [em["content"] for e in in_window for em in e.get("emissions", []) if _emission_matches(em.get("content", ""), tokens)]
    if spec.get("must_not_emit"):
        score = 0.0 if matching else 1.0
        failures = ["premature_trigger"] if matching else []
    else:
        score = 1.0 if matching else 0.0
        failures = [] if matching else ["commitment_miss"]
    return {
        "score": score, "passed": score == 1.0, "failure_codes": failures,
        "details": {"trigger_index": trigger_index, "window": window, "tokens": tokens, "matching": matching[:3],
                    "emissions_in_window": sum(len(e.get("emissions", [])) for e in in_window)},
    }


def evaluate_emission_probe(probe: dict[str, Any], evaluator_map: dict[str, dict[str, Any]],
                            emission_log: list[dict[str, Any]], trigger_index: int) -> tuple[float, list[dict[str, Any]]]:
    results = []
    for eid in probe.get("evaluators", []):
        spec = evaluator_map[eid]
        if spec["type"] != "emission":
            raise NotImplementedError(f"observe_only Probes require an emission evaluator, got {spec['type']!r}")
        r = evaluate_emission(emission_log, trigger_index, probe.get("oracle") or {}, spec.get("config"))
        results.append({"evaluator_id": eid, "evaluator_type": "emission", **r})
    score = sum(float(x["score"]) for x in results) / len(results) if results else 0.0
    return score, results


# ---------------------------------------------------------------- world/trace
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


def _no_recurrence_ok(tools: list[str], action: str, without_prior: str) -> bool:
    """Every occurrence of ``action`` must be preceded by ``without_prior``."""
    seen_prior = False
    for t in tools:
        if t == without_prior:
            seen_prior = True
        elif t == action and not seen_prior:
            return False
    return True


def recurrence_checks(trace: list[dict[str, Any]], oracle: dict[str, Any]) -> dict[str, Any] | None:
    """Error recurrence for one act Probe: did the Agent repeat a known failure? (MIB-Specification §7.9)"""
    reqs = [r for r in (oracle.get("trajectory_requirements") or []) if r.get("type") == "no_recurrence"]
    if not reqs:
        return None
    tools = [x.get("tool") for x in trace if x.get("kind") == "tool_call"]
    recurred = any(not _no_recurrence_ok(tools, r.get("action"), r.get("without_prior")) for r in reqs)
    return {"eligible": True, "recurred": recurred}


def evaluate_trajectory(
    trace: list[dict[str, Any]], oracle: dict[str, Any], config: dict[str, Any] | None, probe_kind: str | None = None
) -> dict[str, Any]:
    reqs = list(oracle.get("trajectory_requirements") or [])
    if not reqs:
        return {"score": 0.0, "passed": False, "failure_codes": ["evaluator_error"], "details": {"reason": "no trajectory_requirements"}}
    tools = [x.get("tool") for x in trace if x.get("kind") == "tool_call"]
    # Repeating a known failure is error recurrence in an Experience Probe and
    # negative transfer in a Skill/action Probe (MIB-Specification §5.4).
    forbidden_code = {"experience": "error_recurrence", "self": "self_model_drift"}.get(probe_kind or "", "negative_transfer")
    checks = []
    failures: set[str] = set()
    for r in reqs:
        typ = r["type"]
        ok = False
        if typ == "required_action":
            ok = r.get("action") in tools
        elif typ == "forbidden_action":
            # Abstaining from every action earns no credit for avoiding one:
            # the requirement is only exercised by a non-empty trajectory.
            ok = bool(tools) and r.get("action") not in tools
            if not ok:
                failures.add(forbidden_code if tools else "trajectory_collapse")
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
        elif typ == "no_recurrence":
            ok = _no_recurrence_ok(tools, r.get("action"), r.get("without_prior"))
            if not ok:
                failures.add("error_recurrence")
        else:
            raise ValueError(f"unsupported trajectory requirement {typ}")
        if not ok and typ not in {"forbidden_action", "no_recurrence"}:
            failures.add("trajectory_collapse")
        checks.append({"requirement": r, "passed": ok})
    score = sum(1.0 for x in checks if x["passed"]) / len(checks)
    return {"score": score, "passed": score == 1.0, "failure_codes": sorted(failures), "details": {"requirements": checks, "tool_sequence": tools}}


def _eval_one(eid: str, spec: dict[str, Any], output: AgentOutput, probe: dict[str, Any], evaluator_map: dict[str, dict[str, Any]], context: dict[str, Any]) -> dict[str, Any]:
    etype = spec["type"]
    if etype == "set_match":
        r = evaluate_set_match(output, probe["oracle"], spec.get("config"))
    elif etype == "structured":
        r = evaluate_structured(output, probe["oracle"], spec.get("config"))
    elif etype == "world_state":
        r = evaluate_world_state(context["world"], probe["oracle"], spec.get("config"))
    elif etype == "trajectory":
        r = evaluate_trajectory(context.get("action_trace", []), probe["oracle"], spec.get("config"), probe_kind=probe.get("kind"))
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
    elif etype == "emission":
        raise NotImplementedError("emission evaluators are scored from the emission log by the Runner")
    else:
        raise NotImplementedError(f"evaluator type not implemented by the reference Runner: {etype!r}")
    return {"evaluator_id": eid, "evaluator_type": etype, **r}


def evaluate_probe(output: AgentOutput, probe: dict[str, Any], evaluator_map: dict[str, dict[str, Any]], context: dict[str, Any] | None = None) -> tuple[float, list[dict[str, Any]]]:
    context = context or {}
    results = [_eval_one(eid, evaluator_map[eid], output, probe, evaluator_map, context) for eid in probe.get("evaluators", [])]
    score = sum(float(x["score"]) for x in results) / len(results) if results else 0.0
    return score, results
