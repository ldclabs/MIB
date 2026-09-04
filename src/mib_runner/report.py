from __future__ import annotations

import uuid
from collections import defaultdict
from typing import Any

import jsonschema

from . import __version__
from .scoring import (
    build_instance_aggregate,
    instance_dimension_scores,
    instance_pair_notes,
    mean,
    paired_causal_metrics,
    scenario_score_from_probes,
    full_run_metrics,
    weighted_mean,
)
from .util import utc_now


def pair_warnings(scope: str, notes: list[str]) -> list[dict[str, Any]]:
    """Causal-pair validity is a report warning, never a metric (MIB-Specification §7.7)."""
    return [
        {"code": "causal.pair_invalid", "severity": "warning", "message": note, "scope": scope}
        for note in notes
    ]


def build_basic_report(
    *,
    runs: list[dict[str, Any]],
    scenario: dict[str, Any],
    agent_descriptor: dict[str, Any],
) -> dict[str, Any]:
    """Single-Scenario development report.

    It uses exactly the pack path's Instance aggregation, so ``mib run`` and
    ``mib benchmark`` cannot disagree about one Scenario.
    """
    aggregate = build_instance_aggregate(scenario, runs)
    notes = instance_pair_notes(runs)
    instance = scenario.get("instantiation") or {}
    iid = aggregate["scenario_instance_id"]
    template_id = aggregate["template_id"]
    full_score = float(aggregate["full_score"])
    dim_scores01 = dict(aggregate["dimension_scores"])
    metrics = aggregate["causal_metrics"]

    dim_weights = (scenario.get("scoring") or {}).get("dimension_weights") or {}
    weighted = weighted_mean(
        [(dim_scores01[d], float(w)) for d, w in dim_weights.items() if d in dim_scores01 and float(w) > 0]
    )
    mib_score = 100.0 * (weighted if weighted is not None else full_score)

    scheduled = sum(len(r.get("probe_results", [])) for r in runs)
    failed = sum(
        1 for r in runs for p in r.get("probe_results", [])
        if p.get("outcome") == "execution_failure"
    )
    dim_objs = [
        {
            "dimension": d,
            "score": 100.0 * score01,
            "weight": float(dim_weights.get(d, 0.0)),
            "coverage": 1.0,
            "template_count": 1,
            "eligible_template_count": 1,
        }
        for d, score01 in dim_scores01.items()
    ]
    warnings = [{
        "code": "development.single_scenario_partial_score",
        "severity": "info",
        "message": "This is a single-Scenario development report, not an official MIB-Core-0.1 score.",
        "scope": "report",
    }] + pair_warnings(iid, notes)

    return {
        "mib": "0.1",
        "kind": "MIBReport",
        "report_version": "0.1.0",
        "report_id": f"report_{uuid.uuid4().hex[:16]}",
        "generated_at": utc_now(),
        "scope": "internal",
        "benchmark": {
            "mib_version": "0.1",
            "profile": {"id": "MIB-Core-0.1-Dev-Single", "version": "0.1.0"},
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
            "runner": {"name": "MIB Reference Runner", "version": __version__},
            "world_simulator": {"name": "MIB Reference World Simulator", "version": __version__},
            "evaluator_bundle": {"name": "MIB Reference Evaluator Bundle", "version": __version__},
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
            "scenario_instances": [aggregate],
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
        "causal_metrics": [{**m, "scope": "benchmark"} for m in metrics],
        "coverage": {
            "overall": 1.0,
            "profile_required": 0.0,
            "by_dimension": {d: 1.0 for d in dim_scores01},
            "missing_required_templates": [],
            "unsupported_required_templates": [],
            "partial_score_reason": "Single-Scenario development report; not an official profile score.",
        },
        "statistics": {
            "confidence_level": 0.95,
            "mib_score": {"value": mib_score, "n": 1},
        },
        "warnings": warnings,
        "provenance": {
            "generated_by": "MIB Reference Runner",
            "generator_version": __version__,
            "score_recomputed": True,
            "verification_status": "partially_verified",
        },
    }


def strip_extensions_for_report(run: dict[str, Any]) -> dict[str, Any]:
    """mib-report.schema RunResult is intentionally closed; drop runner-private fields."""
    allowed = {
        "run_id", "scenario_instance_id", "scenario_instance_version", "template_id",
        "template_version", "instance_seed", "condition", "ablation_id", "ablation_method",
        "ablation_tolerance", "repetition", "agent_seed", "status", "started_at", "completed_at",
        "scenario_score", "penalty", "probe_results", "usage", "validity", "trace_ref", "warnings", "task_results",
    }
    result = {k: v for k, v in run.items() if k in allowed and v is not None}
    # ProbeResult is also closed; keep its allowed fields.
    p_allowed = {
        "probe_id", "probe_kind", "condition", "repetition", "outcome", "score", "weight",
        "dimensions", "evaluator_results", "failure_codes", "output_ref", "output_digest",
        "latency_ms", "usage", "counterfactual", "recurrence", "traps",
    }
    result["probe_results"] = [
        {k: v for k, v in p.items() if k in p_allowed and v is not None}
        for p in result.get("probe_results", [])
    ]
    return result


def validate_report(report: dict[str, Any], schema: dict[str, Any]) -> None:
    jsonschema.Draft202012Validator(schema).validate(report)


def verify_score(report: dict[str, Any], tolerance: float = 1e-9) -> dict[str, Any]:
    """Recompute every aggregation layer the report carries (MIB-Specification §9.2).

    With ``results.runs`` present (internal reports) verification is ``full``:
    run scores from Probe results, Instance full/dimension scores and causal
    metrics from the paired runs, then Template, Dimension and MIB Score.  A
    redacted public report carries no runs, so its verification level is
    ``aggregates_only`` and says so.
    """
    errors: list[str] = []
    aggregates = report.get("aggregates", {})
    instance_rows = aggregates.get("scenario_instances", [])
    template_rows = aggregates.get("templates", [])
    dimension_rows = aggregates.get("dimensions", [])
    runs = (report.get("results") or {}).get("runs") or []
    level = "full" if runs else "aggregates_only"

    def close(a: float, b: float) -> bool:
        return abs(a - b) <= tolerance

    run_checks: list[dict[str, Any]] = []
    instance_checks: list[dict[str, Any]] = []
    if runs:
        runs_by_iid: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for r in runs:
            recomputed = scenario_score_from_probes(r.get("probe_results", []))
            stored = float(r.get("scenario_score", 0.0))
            ok = close(recomputed, stored)
            run_checks.append({"run_id": r.get("run_id"), "stored": stored, "recomputed": recomputed, "valid": ok})
            if not ok:
                errors.append(f"run {r.get('run_id')}: stored={stored} recomputed={recomputed}")
            runs_by_iid[r["scenario_instance_id"]].append(r)

        for inst in instance_rows:
            iid = inst["scenario_instance_id"]
            rr = runs_by_iid.get(iid, [])
            full_runs = [r for r in rr if r.get("condition") == "full"]
            if not full_runs:
                errors.append(f"instance {iid}: no full runs in report")
                continue
            recomputed_full = mean([float(r.get("scenario_score", 0.0)) for r in full_runs])
            ok = close(recomputed_full, float(inst["full_score"]))
            if not ok:
                errors.append(f"instance {iid} full_score: stored={inst['full_score']} recomputed={recomputed_full}")
            # Tolerances travel on the Run Artifacts, so no Scenario body is needed.
            metrics = paired_causal_metrics(rr) + full_run_metrics(full_runs)
            recomputed_metrics = {m["name"]: float(m["value"]) for m in metrics}
            metric_ok = True
            for m in inst.get("causal_metrics", []):
                rec = recomputed_metrics.get(m["name"])
                if rec is None or not close(rec, float(m["value"])):
                    metric_ok = False
                    errors.append(f"instance {iid} causal metric {m['name']}: stored={m['value']} recomputed={rec}")
            stored_dims = inst.get("dimension_scores") or {}
            recomputed_dims = instance_dimension_scores(list(stored_dims), full_runs, metrics)
            dims_ok = True
            for d, stored in stored_dims.items():
                rec = recomputed_dims.get(d)
                if rec is None or not close(rec, float(stored)):
                    dims_ok = False
                    errors.append(f"instance {iid} dimension {d}: stored={stored} recomputed={rec}")
            instance_checks.append({
                "scenario_instance_id": iid, "full_score_valid": ok,
                "causal_metrics_valid": metric_ok, "dimension_scores_valid": dims_ok,
            })

    # Template dimension scores must equal the mean of their Scenario Instance dimension scores.
    # Only canonical-rung Instances feed the capability score (MIB-Specification §8.3); the
    # canonical rung travels on the retention block, so a redacted report can still be verified.
    canonical_by_template = {r["template_id"]: r.get("canonical_rung") for r in report.get("retention") or []}
    by_template: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for inst in instance_rows:
        canonical = canonical_by_template.get(inst["template_id"])
        if canonical is not None and inst.get("rung") is not None and int(inst["rung"]) != int(canonical):
            continue
        by_template[inst["template_id"]].append(inst)
    template_checks = []
    for t in template_rows:
        tid = t["template_id"]
        insts = by_template.get(tid, [])
        for d, stored in (t.get("dimension_scores") or {}).items():
            vals = [float(i["dimension_scores"][d]) for i in insts if d in (i.get("dimension_scores") or {})]
            if not vals:
                continue
            recomputed = 100.0 * mean(vals)
            ok = close(recomputed, float(stored))
            template_checks.append({"template_id": tid, "dimension": d, "stored": float(stored), "recomputed": recomputed, "valid": ok})
            if not ok:
                errors.append(f"template {tid} dimension {d}: stored={stored} recomputed={recomputed}")

    # Dimension scores are weighted means of Template dimension scores using Scenario evidence weights.
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
        recomputed = weighted_mean(rows) or 0.0
        stored = float(drow["score"])
        ok = close(recomputed, stored)
        dimension_checks.append({"dimension": d, "stored": stored, "recomputed": recomputed, "valid": ok})
        if not ok:
            errors.append(f"dimension {d}: stored={stored} recomputed={recomputed}")

    weighted = [(float(x["score"]), float(x["weight"])) for x in dimension_rows if float(x.get("weight", 0.0)) > 0]
    recomputed_base = weighted_mean(weighted) or 0.0
    stored_base = float(report["aggregates"]["mib_score"]["base_score"])
    if not close(recomputed_base, stored_base):
        errors.append(f"MIB base score: stored={stored_base} recomputed={recomputed_base}")

    penalty = float(report["aggregates"]["mib_score"].get("global_guardrail_penalty", 0.0))
    recomputed_final = max(0.0, recomputed_base - penalty)
    stored_final = float(report["aggregates"]["mib_score"]["final_score"])
    if not close(recomputed_final, stored_final):
        errors.append(f"MIB final score: stored={stored_final} recomputed={recomputed_final}")

    return {
        "valid": not errors,
        "verification_level": level,
        "stored_base_score": stored_base,
        "recomputed_base_score": recomputed_base,
        "stored_final_score": stored_final,
        "recomputed_final_score": recomputed_final,
        "difference": recomputed_base - stored_base,
        "run_checks": run_checks,
        "instance_checks": instance_checks,
        "template_checks": template_checks,
        "dimension_checks": dimension_checks,
        "errors": errors,
    }
