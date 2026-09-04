from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import jsonschema

from .experimental.transfer import (
    TRANSFER_EXTENSION,
    TransferAnnotationError,
    parse_transfer_support,
    validate_transfer_support,
)


# What the reference Runner can execute.  The schema is deliberately wider (it
# is the format contract); a Scenario that uses anything outside these sets is
# schema-valid but unrunnable, so the validator rejects it here instead of
# letting the Runner crash mid-pack or score every Agent zero in silence.
RUNNER_EVALUATOR_TYPES = {"set_match", "world_state", "trajectory", "composite"}
RUNNER_TRIGGER_KINDS = {"after_event"}
RUNNER_DELIVERY_MODES = {"respond", "act"}
RUNNER_ABLATION_METHODS = {"replay_excluding_events", "replay_with_injections"}
RUNNER_SIMULATOR_BINDINGS = {"mib.deployment.v1", "mib.workspace.v1", "mib.contextual_save.v1"}
RUNNER_EVENT_TYPES = {
    "interaction", "observation", "tool_result", "distractor", "document", "feedback",
    "time_advance", "maintenance_window", "system_event", "custom", "checkpoint", "world_update",
}
RUNNER_NORMALIZATIONS = {"none", "casefold_trim", "trim", "casefold_trim_collapse_ws", "answer_normalized"}
RUNNER_MATCH_MODES = {"exact", "contains"}
RUNNER_WORLD_OPERATORS = {"eq", "neq", "exists", "not_exists", "contains", "gte", "lte"}
RUNNER_TRAJECTORY_TYPES = {"required_action", "forbidden_action", "before", "after", "max_occurrences", "min_occurrences"}


@dataclass(slots=True)
class ValidationResult:
    valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def load_json(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def validate_scenario(
    scenario: dict[str, Any],
    schema: dict[str, Any],
    *,
    transfer_schema: dict[str, Any] | None = None,
    require_transfer_annotations: bool = False,
) -> ValidationResult:
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
        if tool.get("simulator_binding") not in RUNNER_SIMULATOR_BINDINGS:
            errors.append(
                f"unsupported:{tid}: simulator_binding {tool.get('simulator_binding')!r} "
                "not implemented by the reference World Simulator"
            )
        for op in tool.get("operations", []):
            tool_names.add(f"{tid}.{op.get('name')}")

    for event in timeline:
        if event.get("actor") and event["actor"] not in actor_ids:
            errors.append(f"semantic:{event.get('id')}: unresolved actor {event['actor']}")
        if event.get("type") not in RUNNER_EVENT_TYPES or event.get("generator"):
            errors.append(
                f"unsupported:{event.get('id')}: event type {event.get('type')!r} with generator="
                f"{'yes' if event.get('generator') else 'no'} is not executable by the reference Runner"
            )

    for p in probes:
        trigger = p.get("trigger") or {}
        after = trigger.get("after_event")
        if after and after not in timeline_ids:
            errors.append(f"semantic:{p.get('id')}: unresolved trigger {after}")
        if not after:
            errors.append(f"unsupported:{p.get('id')}: the reference Runner requires an after_event trigger")
        unsupported = set(trigger) - RUNNER_TRIGGER_KINDS
        if unsupported:
            errors.append(f"unsupported:{p.get('id')}: trigger kinds not executable by the reference Runner: {sorted(unsupported)}")
        for eid in p.get("evaluators", []):
            if eid not in evaluator_ids:
                errors.append(f"semantic:{p.get('id')}: unresolved evaluator {eid}")
        if p.get("delivery") not in RUNNER_DELIVERY_MODES:
            errors.append(f"unsupported:{p.get('id')}: delivery={p.get('delivery')} not executable by the reference Runner")
        oracle = p.get("oracle") or {}
        for assertion in oracle.get("world_assertions") or []:
            if assertion.get("operator") not in RUNNER_WORLD_OPERATORS:
                errors.append(f"unsupported:{p.get('id')}: world assertion operator {assertion.get('operator')!r}")
        for requirement in oracle.get("trajectory_requirements") or []:
            if requirement.get("type") not in RUNNER_TRAJECTORY_TYPES:
                errors.append(f"unsupported:{p.get('id')}: trajectory requirement {requirement.get('type')!r}")
        if p.get("delivery") == "act":
            for name in (p.get("input") or {}).get("available_tools", []):
                if name not in tool_names:
                    errors.append(f"semantic:{p.get('id')}: unavailable tool {name}")

    for e in evaluators:
        if e.get("type") not in RUNNER_EVALUATOR_TYPES:
            errors.append(f"unsupported:{e.get('id')}: evaluator type {e.get('type')!r} not implemented by the reference Runner")
        cfg = e.get("config") or {}
        if e.get("type") == "set_match":
            if cfg.get("normalization", "answer_normalized") not in RUNNER_NORMALIZATIONS:
                errors.append(f"unsupported:{e.get('id')}: normalization {cfg.get('normalization')!r}")
            if cfg.get("match", "contains") not in RUNNER_MATCH_MODES:
                errors.append(f"unsupported:{e.get('id')}: match mode {cfg.get('match')!r}")
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
        if a.get("method") not in RUNNER_ABLATION_METHODS:
            errors.append(f"unsupported:{a.get('id')}: ablation method {a.get('method')} not executable by the reference Runner")
        injection_ids: set[str] = set()
        for injection in a.get("injections", []):
            iid = str(injection.get("id"))
            if iid in timeline_ids or iid in injection_ids:
                errors.append(f"semantic:{a.get('id')}: duplicate injection event id {iid}")
            injection_ids.add(iid)
            if injection.get("actor") and injection["actor"] not in actor_ids:
                errors.append(f"semantic:{a.get('id')}: injection {iid} has unresolved actor {injection['actor']}")
            anchor = (injection.get("at") or {}).get("after_event")
            if anchor and anchor not in timeline_ids:
                errors.append(f"semantic:{a.get('id')}: injection {iid} has unresolved anchor {anchor}")
            if injection.get("world_updates"):
                errors.append(
                    f"semantic:{a.get('id')}: injection {iid} may not mutate world state; "
                    "memory must remain the treatment variable"
                )

    # A relevant_memory Ablation is only meaningful if removing its target events
    # actually removes the answer.  When the Oracle value still appears verbatim
    # in a surviving event, the paired comparison measures nothing and silently
    # dilutes memory_benefit, so surface it at authoring time.
    probes_by_id = {p.get("id"): p for p in probes}
    event_text: dict[str, str] = {}
    for event in timeline:
        parts = [str(event.get("content") or "")]
        payload = event.get("payload")
        if payload is not None:
            parts.append(json.dumps(payload, ensure_ascii=False))
        event_text[str(event.get("id"))] = " ".join(parts)

    for a in ablations:
        if a.get("kind") != "relevant_memory":
            continue
        if a.get("oracle_value_survives_by_design"):
            continue
        removed = {str(x) for x in (a.get("targets") or {}).get("event_ids", [])}
        if not removed:
            continue
        surviving = {eid: text for eid, text in event_text.items() if eid not in removed}
        for pid in a.get("probes", []):
            probe = probes_by_id.get(pid)
            if not probe:
                continue
            for value in (probe.get("oracle") or {}).get("accepted", []):
                needle = str(value).strip()
                if not needle or needle.startswith("${"):
                    continue
                leaked = [eid for eid, text in surviving.items() if needle.casefold() in text.casefold()]
                if leaked:
                    warnings.append(
                        f"ablation:{a.get('id')}: Probe {pid} accepted value {needle!r} still appears in "
                        f"surviving event(s) {sorted(leaked)}; the relevant_memory Ablation may not degrade"
                    )

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

    # Transfer Support Annotation.  A Scenario that carries none is validated
    # exactly as before: legacy v0.1 content must not acquire new findings just
    # because the diagnostic extension exists.
    _validate_transfer_extension(
        scenario,
        errors,
        warnings,
        transfer_schema=transfer_schema,
        require_transfer_annotations=require_transfer_annotations,
    )

    return ValidationResult(not errors, errors, warnings)


def _validate_transfer_extension(
    scenario: dict[str, Any],
    errors: list[str],
    warnings: list[str],
    *,
    transfer_schema: dict[str, Any] | None,
    require_transfer_annotations: bool,
) -> None:
    try:
        support = parse_transfer_support(scenario)
    except TransferAnnotationError as exc:
        errors.append(f"transfer:{TRANSFER_EXTENSION}: {exc}")
        return

    if support is None:
        if require_transfer_annotations:
            errors.append(
                f"transfer: profile requires a {TRANSFER_EXTENSION} annotation, but the Scenario declares none"
            )
        return

    if transfer_schema is not None:
        validator = jsonschema.Draft202012Validator(transfer_schema)
        for err in sorted(validator.iter_errors(support.raw), key=lambda e: list(e.path)):
            where = "/".join(str(x) for x in err.path)
            errors.append(f"transfer-schema:{where or '$'}: {err.message}")

    for finding in validate_transfer_support(scenario, support):
        line = f"transfer:{finding['code']}: {finding['message']}"
        (errors if finding["severity"] == "error" else warnings).append(line)
