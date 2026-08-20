from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Any

import jsonschema


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _condition_scores(runs: list[dict[str, Any]]) -> dict[str, float]:
    buckets: dict[str, list[float]] = {}
    for r in runs:
        buckets.setdefault(r["condition"], []).append(float(r.get("scenario_score", 0.0)))
    return {k: sum(v) / len(v) for k, v in buckets.items() if v}


def _probe_map(run: dict[str, Any]) -> dict[str, float]:
    return {
        p["probe_id"]: float(p.get("score", 0.0))
        for p in run.get("probe_results", [])
        if p.get("outcome") == "scored"
    }


def _mean_selected(full_probe_scores: dict[str, float], probe_ids: set[str]) -> float | None:
    vals = [full_probe_scores[p] for p in probe_ids if p in full_probe_scores]
    return sum(vals) / len(vals) if vals else None


def _causal_metrics(runs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Compute paired Milestone 4 causal metrics on each intervention's Probe subset."""
    full_runs = [r for r in runs if r["condition"] == "full"]
    if not full_runs:
        return []
    full_buckets: dict[str, list[float]] = {}
    for fr in full_runs:
        for pid, score in _probe_map(fr).items():
            full_buckets.setdefault(pid, []).append(score)
    full_probe_scores = {k: sum(v) / len(v) for k, v in full_buckets.items()}

    relevant: list[tuple[float, str]] = []
    hmbs: list[float] = []
    irrelevant_stabilities: list[float] = []
    harms: list[float] = []
    harm_resistance: list[float] = []
    negative_transfers: list[float] = []

    for run in runs:
        condition = run["condition"]
        if condition == "full":
            continue
        probe_scores = _probe_map(run)
        probe_ids = set(probe_scores)
        if not probe_ids:
            continue
        full_match = _mean_selected(full_probe_scores, probe_ids)
        variant = sum(probe_scores.values()) / len(probe_scores)
        if full_match is None:
            continue

        if condition in {"relevant_ablation", "no_memory"}:
            delta = full_match - variant
            relevant.append((delta, condition))
            denom = 1.0 - variant
            if denom > 0.02:
                hmbs.append(max(0.0, delta) / denom)
        elif condition == "irrelevant_ablation":
            irrelevant_stabilities.append(max(0.0, min(1.0, 1.0 - abs(full_match - variant))))
        elif condition in {"harmful_memory", "stale_memory"}:
            harm = max(0.0, full_match - variant)
            harms.append(harm)
            harm_resistance.append(1.0 - harm)
        elif condition == "counterexample":
            # Counterexample removal is not the standardized Negative Transfer control.
            pass

    out: list[dict[str, Any]] = []
    if relevant:
        vals = [x[0] for x in relevant]
        refs = {x[1] for x in relevant}
        comparison = next(iter(refs)) if len(refs) == 1 else "custom"
        out.append({
            "name": "memory_benefit", "value": sum(vals) / len(vals), "unit": "percentage_points",
            "scope": "scenario_instance", "reference_condition": "full", "comparison_condition": comparison,
            "eligible_n": len(vals), "total_n": len(vals), "coverage": 1.0,
        })
    if hmbs:
        out.append({
            "name": "headroom_normalized_memory_benefit", "value": sum(hmbs) / len(hmbs), "unit": "normalized",
            "scope": "scenario_instance", "reference_condition": "full", "comparison_condition": "relevant_ablation",
            "eligible_n": len(hmbs), "total_n": len(relevant), "coverage": len(hmbs) / len(relevant) if relevant else 0.0,
        })
    if irrelevant_stabilities:
        out.append({
            "name": "irrelevant_memory_stability", "value": sum(irrelevant_stabilities) / len(irrelevant_stabilities), "unit": "normalized",
            "scope": "scenario_instance", "reference_condition": "full", "comparison_condition": "irrelevant_ablation",
            "eligible_n": len(irrelevant_stabilities), "total_n": len(irrelevant_stabilities), "coverage": 1.0,
        })
    if harms:
        mh = sum(harms) / len(harms)
        out.extend([
            {"name": "memory_harm", "value": mh, "unit": "percentage_points", "scope": "scenario_instance", "reference_condition": "full", "comparison_condition": "harmful_memory", "eligible_n": len(harms), "total_n": len(harms), "coverage": 1.0},
            {"name": "harm_resistance", "value": sum(harm_resistance)/len(harm_resistance), "unit": "normalized", "scope": "scenario_instance", "reference_condition": "full", "comparison_condition": "harmful_memory", "eligible_n": len(harms), "total_n": len(harms), "coverage": 1.0},
        ])
    mb = next((m["value"] for m in out if m["name"] == "memory_benefit"), None)
    mh = next((m["value"] for m in out if m["name"] == "memory_harm"), None)
    if mb is not None and mh is not None:
        out.append({"name": "net_memory_gain", "value": mb-mh, "unit": "percentage_points", "scope": "scenario_instance"})
    return out


def build_basic_report(
    *,
    runs: list[dict[str, Any]],
    scenario: dict[str, Any],
    agent_descriptor: dict[str, Any],
) -> dict[str, Any]:
    full_runs = [r for r in runs if r["condition"] == "full"]
    if not full_runs:
        raise ValueError("at least one full run is required")
    full_score = sum(r["scenario_score"] for r in full_runs) / len(full_runs)
    instance = scenario.get("instantiation") or {}
    iid = full_runs[0]["scenario_instance_id"]
    template_id = instance.get("template_id", scenario["id"])
    metrics = _causal_metrics(runs)
    conditions = _condition_scores(runs)

    dim_scores01: dict[str, float] = {}
    # Milestone 1 uses full Scenario score as evidence for non-causal dimensions.
    for d in scenario.get("dimensions", []):
        if d != "causal_memory_impact":
            dim_scores01[d] = full_score

    hmb_component = next((m for m in metrics if m["name"] == "headroom_normalized_memory_benefit"), None)
    ims_component = next((m for m in metrics if m["name"] == "irrelevant_memory_stability"), None)
    hrs_component = next((m for m in metrics if m["name"] == "harm_resistance"), None)
    if "causal_memory_impact" in scenario.get("dimensions", []):
        available = []
        if hmb_component:
            available.append((0.5, hmb_component["value"]))
        if ims_component:
            available.append((0.2, ims_component["value"]))
        if hrs_component:
            available.append((0.3, hrs_component["value"]))
        if available:
            causal01 = sum(w * v for w, v in available) / sum(w for w, _ in available)
            dim_scores01["causal_memory_impact"] = causal01

    dim_weights = (scenario.get("scoring") or {}).get("dimension_weights") or {}
    available_weights = {d: w for d, w in dim_weights.items() if d in dim_scores01}
    weight_sum = sum(available_weights.values())
    if weight_sum:
        mib_score = 100.0 * sum(dim_scores01[d] * w for d, w in available_weights.items()) / weight_sum
    else:
        mib_score = 100.0 * full_score

    scheduled = sum(len(r.get("probe_results", [])) for r in runs)
    failed = sum(
        1 for r in runs for p in r.get("probe_results", [])
        if p.get("outcome") == "execution_failure"
    )

    dim_objs = []
    for d, score01 in dim_scores01.items():
        weight = float(dim_weights.get(d, 0.0))
        dim_objs.append({
            "dimension": d,
            "score": 100.0 * score01,
            "weight": weight,
            "coverage": 1.0,
            "template_count": 1,
            "eligible_template_count": 1,
        })

    report = {
        "mib": "0.1",
        "kind": "MIBReport",
        "report_version": "0.1.0",
        "report_id": f"report_{uuid.uuid4().hex[:16]}",
        "generated_at": utc_now(),
        "scope": "internal",
        "benchmark": {
            "mib_version": "0.1",
            "profile": {"id": "MIB-Core-0.1-Dev-M2", "version": "0.1.0"},
            "track": "integrated_agent",
            "scale": "MIB-S",
            "scenario_pack": {"id": "single-scenario-dev", "version": "0.1.0"},
            "scoring_spec_version": "0.1-draft",
            "scenario_schema_version": "0.1",
            "agent_adapter_protocol": "mib-agent/0.1",
        },
        "system": {
            "agent": {
                "name": agent_descriptor.get("implementation", {}).get("name", "Unknown Agent"),
                "version": agent_descriptor.get("implementation", {}).get("version", "0.0.0"),
            }
        },
        "adapter": {
            "protocol": agent_descriptor.get("protocol", "mib-agent/0.1"),
            "implementation": {
                "name": agent_descriptor.get("implementation", {}).get("name", "Unknown Adapter"),
                "version": agent_descriptor.get("implementation", {}).get("version", "0.0.0"),
            }
        },
        "environment": {
            "runner": {"name": "MIB Reference Runner", "version": "0.4.0"},
            "world_simulator": {"name": "MIB Milestone 4 World", "version": "0.4.0"},
            "evaluator_bundle": {"name": "MIB M4 Evaluator Bundle", "version": "0.4.0"},
        },
        "execution": {
            "started_at": min(r.get("started_at") for r in runs),
            "completed_at": max(r.get("completed_at") for r in runs),
            "scheduled_runs": len(runs),
            "completed_runs": len(runs),
            "scheduled_probe_attempts": scheduled,
            "execution_failed_probe_attempts": failed,
            "execution_failure_rate": failed / scheduled if scheduled else 0.0,
            "unsupported_required_weight": 0.0,
            "total_required_weight": 1.0,
            "unsupported_rate": 0.0,
        },
        "results": {
            "runs": [strip_extensions_for_report(r) for r in runs],
            "redacted": False,
            "raw_output_policy": "digest_only",
        },
        "aggregates": {
            "scenario_instances": [{
                "scenario_instance_id": iid,
                "template_id": template_id,
                **({"instance_seed": instance.get("seed")} if instance.get("seed") is not None else {}),
                "full_score": full_score,
                "dimension_scores": dim_scores01,
                "condition_scores": conditions,
                "repetitions": 1,
                "causal_metrics": metrics,
            }],
            "templates": [{
                "template_id": template_id,
                "template_version": instance.get("template_version", scenario.get("version")),
                "instance_count": 1,
                "template_weight": 1.0,
                "full_score": 100.0 * full_score,
                "dimension_scores": {d: 100.0 * v for d, v in dim_scores01.items()},
                "dimension_weights": dim_weights,
                "coverage_weight": 1.0,
            }],
            "dimensions": dim_objs,
            "mib_score": {
                "base_score": mib_score,
                "global_guardrail_penalty": 0.0,
                "final_score": mib_score,
                "official": False,
                "partial": True,
                "profile_eligible": False,
                "formula": "weighted_dimension_sum",
            },
            "dimension_weight_sum": min(1.0, sum(float(x.get("weight", 0.0)) for x in dim_objs)),
        },
        "causal_metrics": [
            {**m, "scope": "benchmark"} for m in metrics
        ],
        "coverage": {
            "overall": 1.0,
            "profile_required": 0.0,
            "by_dimension": {d: 1.0 for d in dim_scores01},
            "missing_required_templates": [],
            "unsupported_required_templates": [],
            "partial_score_reason": "Milestone 4 single-scenario development report; not an official profile score.",
        },
        "statistics": {
            "confidence_level": 0.95,
            "mib_score": {"value": mib_score, "n": 1},
        },
        "warnings": [{
            "code": "development.milestone2_partial_score",
            "severity": "info",
            "message": "This is a Milestone 4 development report, not an official MIB-Core-0.1 score.",
            "scope": "report",
        }],
        "provenance": {
            "generated_by": "MIB Reference Runner",
            "generator_version": "0.4.0",
            "score_recomputed": True,
            "verification_status": "partially_verified",
        },
    }
    return report


def strip_extensions_for_report(run: dict[str, Any]) -> dict[str, Any]:
    """mib-report.schema RunResult is intentionally closed; drop runner-private fields."""
    allowed = {
        "run_id", "scenario_instance_id", "scenario_instance_version", "template_id",
        "template_version", "instance_seed", "condition", "ablation_id", "ablation_method",
        "repetition", "agent_seed", "status", "started_at", "completed_at", "scenario_score",
        "penalty", "probe_results", "usage", "validity", "trace_ref", "warnings",
    }
    result = {k: v for k, v in run.items() if k in allowed and v is not None}
    # ProbeResult is also closed; keep its allowed fields.
    p_allowed = {
        "probe_id", "probe_kind", "condition", "repetition", "outcome", "score", "weight",
        "dimensions", "evaluator_results", "failure_codes", "output_ref", "output_digest",
        "latency_ms", "usage",
    }
    result["probe_results"] = [
        {k: v for k, v in p.items() if k in p_allowed and v is not None}
        for p in result.get("probe_results", [])
    ]
    return result


def validate_report(report: dict[str, Any], schema: dict[str, Any]) -> None:
    jsonschema.Draft202012Validator(schema).validate(report)


def verify_score(report: dict[str, Any], tolerance: float = 1e-9) -> dict[str, Any]:
    """Recompute Template, Dimension, and final MIB score from report aggregates."""
    errors: list[str] = []
    instance_rows = report.get("aggregates", {}).get("scenario_instances", [])
    template_rows = report.get("aggregates", {}).get("templates", [])
    dimension_rows = report.get("aggregates", {}).get("dimensions", [])

    # Template dimension scores must equal the mean of their Scenario Instance dimension scores.
    by_template: dict[str, list[dict[str, Any]]] = {}
    for inst in instance_rows:
        by_template.setdefault(inst["template_id"], []).append(inst)
    template_checks = []
    for t in template_rows:
        tid = t["template_id"]
        insts = by_template.get(tid, [])
        for d, stored in (t.get("dimension_scores") or {}).items():
            vals = [float(i.get("dimension_scores", {}).get(d)) for i in insts if d in (i.get("dimension_scores") or {})]
            if not vals:
                continue
            recomputed = 100.0 * sum(vals) / len(vals)
            ok = abs(recomputed - float(stored)) <= tolerance
            template_checks.append({"template_id": tid, "dimension": d, "stored": float(stored), "recomputed": recomputed, "valid": ok})
            if not ok:
                errors.append(f"template {tid} dimension {d}: stored={stored} recomputed={recomputed}")

    # Dimension scores are weighted means of Template dimension scores using Scenario dimension evidence weights.
    dimension_checks = []
    for drow in dimension_rows:
        d = drow["dimension"]
        rows = []
        for t in template_rows:
            if d not in (t.get("dimension_scores") or {}):
                continue
            w = float((t.get("dimension_weights") or {}).get(d, 0.0))
            if w > 0:
                rows.append((float(t["dimension_scores"][d]), w))
        denom = sum(w for _, w in rows)
        recomputed = sum(s*w for s,w in rows)/denom if denom else 0.0
        stored = float(drow["score"])
        ok = abs(recomputed - stored) <= tolerance
        dimension_checks.append({"dimension": d, "stored": stored, "recomputed": recomputed, "valid": ok})
        if not ok:
            errors.append(f"dimension {d}: stored={stored} recomputed={recomputed}")

    weighted = [(float(x["score"]), float(x["weight"])) for x in dimension_rows if float(x.get("weight", 0.0)) > 0]
    denom = sum(w for _, w in weighted)
    recomputed_base = sum(s * w for s, w in weighted) / denom if denom else 0.0
    stored_base = float(report["aggregates"]["mib_score"]["base_score"])
    score_ok = abs(recomputed_base - stored_base) <= tolerance
    if not score_ok:
        errors.append(f"MIB base score: stored={stored_base} recomputed={recomputed_base}")

    penalty = float(report["aggregates"]["mib_score"].get("global_guardrail_penalty", 0.0))
    recomputed_final = max(0.0, recomputed_base - penalty)
    stored_final = float(report["aggregates"]["mib_score"]["final_score"])
    final_ok = abs(recomputed_final - stored_final) <= tolerance
    if not final_ok:
        errors.append(f"MIB final score: stored={stored_final} recomputed={recomputed_final}")

    return {
        "valid": not errors,
        "stored_base_score": stored_base,
        "recomputed_base_score": recomputed_base,
        "stored_final_score": stored_final,
        "recomputed_final_score": recomputed_final,
        "difference": recomputed_base - stored_base,
        "template_checks": template_checks,
        "dimension_checks": dimension_checks,
        "errors": errors,
    }
