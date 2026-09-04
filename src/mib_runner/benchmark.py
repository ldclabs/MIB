from __future__ import annotations

import copy
import json
import math
import random
import uuid
from collections import defaultdict
from pathlib import Path
from typing import Any, Callable

from . import __version__
from .materialize import materialize
from .report import pair_warnings, strip_extensions_for_report
from .runner import run_scenario
from .scoring import (  # noqa: F401  (re-exported: callers and tests import these from here)
    CAUSAL_DIM,
    HMB,
    HRS,
    IMS,
    ablation_tolerances,
    build_instance_aggregate,
    causal_score01,
    ci_percentile,
    condition_scores,
    instance_dimension_scores,
    mean,
    paired_causal_metrics,
    percentile,
    validate_causal_pairs,
    weighted_mean,
    weighted_probe_score,
)
from .util import utc_now
from .experimental.transfer_diagnostics import (
    DEFAULT_EPSILON,
    attach_transfer_diagnostics,
    build_transfer_diagnostics,
    transfer_diagnostic_aggregates,
    transfer_distance_aggregates,
    transfer_relation_aggregates,
)
from .experimental.transfer_matrix import run_transfer_matrix_pack
from .validation import validate_scenario



def build_template_aggregate(template: dict[str, Any], instances: list[dict[str, Any]]) -> dict[str, Any]:
    dim_names = sorted({d for i in instances for d in (i.get("dimension_scores") or {})})
    dim_scores = {
        d: 100.0 * mean([float(i["dimension_scores"][d]) for i in instances if d in (i.get("dimension_scores") or {})])
        for d in dim_names
    }
    c_metrics: dict[str, list[float]] = defaultdict(list)
    for i in instances:
        for m in i.get("causal_metrics", []):
            c_metrics[m["name"]].append(float(m["value"]))
    cscore = dim_scores.get(CAUSAL_DIM)
    causal_components = None
    if cscore is not None:
        causal_components = {"causal_score": cscore}
        for name in ["headroom_normalized_memory_benefit", "irrelevant_memory_stability", "harm_resistance"]:
            if c_metrics.get(name):
                causal_components[name] = mean(c_metrics[name])
        causal_components["relevant_benefit_coverage"] = 1.0 if c_metrics.get("headroom_normalized_memory_benefit") else 0.0
        causal_components["irrelevant_stability_coverage"] = 1.0 if c_metrics.get("irrelevant_memory_stability") else 0.0
        causal_components["harm_resistance_coverage"] = 1.0 if c_metrics.get("harm_resistance") else 0.0
    out = {
        "template_id": template["id"],
        "template_version": template.get("version"),
        "instance_count": len(instances),
        "template_weight": 1.0,
        "full_score": 100.0 * mean([float(i["full_score"]) for i in instances]),
        "dimension_scores": dim_scores,
        "dimension_weights": copy.deepcopy((template.get("scoring") or {}).get("dimension_weights") or {}),
        "coverage_weight": 1.0,
    }
    if causal_components:
        out["causal_components"] = causal_components
    return out


def dimension_aggregates(
    template_aggs: list[dict[str, Any]],
    profile: dict[str, Any],
    templates: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """MIB-Specification §6.4, §6.5.

    ``templates`` is the complete required pack; when given, the required
    evidence weight counts Templates that were never executed (unsupported by
    the Agent), so coverage cannot be inflated by skipping them.
    """
    out = []
    profile_dims = profile.get("dimensions") or {}
    required_by_dim: dict[str, list[float]] = defaultdict(list)
    for t in templates or []:
        for d, w in (((t.get("scoring") or {}).get("dimension_weights")) or {}).items():
            if float(w) > 0:
                required_by_dim[d].append(float(w))
    for d, spec in profile_dims.items():
        rows = []
        expected_terms: list[float] = []
        evaluated_terms: list[float] = []
        for t in template_aggs:
            evidence_w = float((t.get("dimension_weights") or {}).get(d, 0.0))
            if evidence_w <= 0:
                continue
            expected_terms.append(evidence_w)
            if d in (t.get("dimension_scores") or {}):
                rows.append((float(t["dimension_scores"][d]), evidence_w))
                evaluated_terms.append(evidence_w)
        # fsum on both sides: the same multiset of weights must give coverage exactly 1.
        expected = math.fsum(expected_terms)
        evaluated = math.fsum(evaluated_terms)
        if templates is not None:
            expected = max(expected, math.fsum(required_by_dim.get(d, [])))
        denom = math.fsum(w for _, w in rows)
        score = math.fsum(s * w for s, w in rows) / denom if denom else 0.0
        coverage = evaluated / expected if expected > 0 else 0.0
        out.append({
            "dimension": d,
            "score": score,
            "weight": float(spec["weight"]),
            "coverage": coverage,
            "template_count": len(rows),
            "eligible_template_count": len(rows),
            "required_template_weight": expected,
            "evaluated_template_weight": evaluated,
        })
    return out


def aggregate_benchmark_causal_metrics(instances_by_template: dict[str, list[dict[str, Any]]], templates_by_id: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    template_metric_values: dict[str, list[tuple[float, float]]] = defaultdict(list)
    for tid, instances in instances_by_template.items():
        per_name: dict[str, list[float]] = defaultdict(list)
        for i in instances:
            for m in i.get("causal_metrics", []):
                per_name[m["name"]].append(float(m["value"]))
        evidence_w = float(((templates_by_id[tid].get("scoring") or {}).get("dimension_weights") or {}).get(CAUSAL_DIM, 0.0))
        if evidence_w <= 0:
            continue
        for name, vals in per_name.items():
            template_metric_values[name].append((mean(vals), evidence_w))
    out = []
    unit_map = {
        "memory_benefit": "percentage_points",
        "memory_harm": "percentage_points",
        "net_memory_gain": "percentage_points",
        "headroom_normalized_memory_benefit": "normalized",
        "irrelevant_memory_stability": "normalized",
        "harm_resistance": "normalized",
        "negative_transfer": "normalized",
    }
    for name, rows in sorted(template_metric_values.items()):
        denom = math.fsum(w for _, w in rows)
        value = math.fsum(v * w for v, w in rows) / denom if denom else 0.0
        out.append({
            "name": name,
            "value": value,
            "unit": unit_map.get(name, "normalized"),
            "scope": "benchmark",
            "eligible_n": len(rows),
            "total_n": len(rows),
            "coverage": 1.0,
        })
    mb = next((m["value"] for m in out if m["name"] == "memory_benefit"), None)
    mh = next((m["value"] for m in out if m["name"] == "memory_harm"), None)
    if mb is not None and mh is not None and not any(m["name"] == "net_memory_gain" for m in out):
        out.append({"name": "net_memory_gain", "value": mb - mh, "unit": "percentage_points", "scope": "benchmark"})
    return out


def _profile_score(dimensions: list[dict[str, Any]]) -> float:
    rows = [(float(d["score"]), float(d["weight"])) for d in dimensions if float(d.get("weight", 0.0)) > 0]
    denom = math.fsum(w for _, w in rows)
    return math.fsum(s * w for s, w in rows) / denom if denom else 0.0


def describe_agent_factory(agent_factory: Callable[[], Any]) -> dict[str, Any]:
    agent = agent_factory()
    try:
        return agent.describe()
    finally:
        close = getattr(agent, "close", None)
        if callable(close):
            try:
                close()
            except TypeError:
                pass




def select_profile_templates(templates: list[dict[str, Any]], profile: dict[str, Any]) -> list[dict[str, Any]]:
    """The executed pack is exactly ``profile.required_templates``.

    Extra Templates on disk (another family's pack in the same tree) would
    silently enter the score, and a missing one would silently shrink it.
    """
    required = profile.get("required_templates")
    if not required:
        return list(templates)
    by_id = {t["id"]: t for t in templates}
    missing = sorted(set(required) - set(by_id))
    if missing:
        raise ValueError(f"profile requires missing Templates: {missing}")
    extra = sorted(set(by_id) - set(required))
    if extra:
        raise ValueError(
            f"Templates not listed by profile {profile.get('id')!r}: {extra}; pass only the profile's pack"
        )
    required_set = set(required)
    return [t for t in templates if t["id"] in required_set]


# Scenario ``requirements.capabilities`` names that differ from the Agent descriptor keys.
_CAPABILITY_KEYS = {"tools": "runner_managed_tools"}


def agent_supports_template(descriptor: dict[str, Any], template: dict[str, Any]) -> bool:
    """MIB-Specification §6.6: a Template is unsupported only when the Agent *declares*
    a required capability false.  Absent metadata is not a refusal."""
    caps = (descriptor or {}).get("capabilities") or {}
    for cap in ((template.get("requirements") or {}).get("capabilities") or []):
        key = _CAPABILITY_KEYS.get(cap, cap)
        if key in caps and caps[key] is False:
            return False
    return True


DEFAULT_MIN_TEMPLATES_PER_DIMENSION = 5


def hierarchical_bootstrap(
    *,
    templates: list[dict[str, Any]],
    runs_by_instance: dict[str, list[dict[str, Any]]],
    profile: dict[str, Any],
    resamples: int,
    seed: int | str,
    confidence_level: float = 0.95,
    min_templates_per_dimension: int | None = None,
) -> dict[str, Any]:
    """Hierarchical bootstrap over precomputed per-repetition sufficient statistics.

    Resampling hierarchy (MIB-Specification §8.2): Template -> Instance -> paired
    Repetition.  Full/Ablation conditions of a repetition are reduced together
    before resampling, so causal pairs cannot be split.  One Template resample
    per draw is shared by every Dimension and causal metric, so the MIB Score
    interval keeps the covariance that Cross-Dimension Templates induce.
    A Dimension carried by fewer than ``min_templates_per_dimension`` Templates
    gets no interval: a percentile interval over three Templates is decoration,
    and the MIB Score interval is omitted whenever any weighted Dimension lacks one.
    """
    rng = random.Random(str(seed))
    templates_by_id = {t["id"]: t for t in templates}
    threshold = (
        int((profile.get("statistics") or {}).get("min_templates_per_dimension", DEFAULT_MIN_TEMPLATES_PER_DIMENSION))
        if min_templates_per_dimension is None else int(min_templates_per_dimension)
    )

    # Compact per-repetition summaries make 10k resamples practical.
    rep_stats: dict[str, list[dict[str, Any]]] = defaultdict(list)
    instance_template: dict[str, str] = {}
    for iid, runs in runs_by_instance.items():
        if not runs:
            continue
        tid = runs[0]["template_id"]
        instance_template[iid] = tid
        scenario = templates_by_id[tid]
        tolerances = ablation_tolerances(scenario)
        for rep in sorted({int(r["repetition"]) for r in runs if r.get("condition") == "full"}):
            rr = [r for r in runs if int(r["repetition"]) == rep]
            validate_causal_pairs(rr)
            full = next((r for r in rr if r.get("condition") == "full"), None)
            if full is None:
                continue
            metrics = paired_causal_metrics(rr, tolerances)
            rep_stats[iid].append({
                "dimensions": instance_dimension_scores(list(scenario.get("dimensions", [])), [full], metrics),
                "metrics": {m["name"]: float(m["value"]) for m in metrics},
            })

    instance_ids_by_template: dict[str, list[str]] = defaultdict(list)
    for iid, tid in instance_template.items():
        if rep_stats.get(iid):
            instance_ids_by_template[tid].append(iid)
    tids = [t["id"] for t in templates if instance_ids_by_template.get(t["id"])]
    profile_dims = list((profile.get("dimensions") or {}).items())
    weighted_dims = [d for d, spec in profile_dims if float(spec.get("weight", 0.0)) > 0]

    def weight(tid: str, d: str) -> float:
        return float(((templates_by_id[tid].get("scoring") or {}).get("dimension_weights") or {}).get(d, 0.0))

    def sample_instance(iid: str, resample: bool) -> tuple[dict[str, float], dict[str, float]]:
        reps = rep_stats[iid]
        sampled = [rng.choice(reps) for _ in reps] if resample else reps
        dim_names = {d for r in sampled for d in r["dimensions"]}
        metric_names = {m for r in sampled for m in r["metrics"]}
        dims = {d: mean([r["dimensions"][d] for r in sampled if d in r["dimensions"]]) for d in dim_names}
        metrics = {m: mean([r["metrics"][m] for r in sampled if m in r["metrics"]]) for m in metric_names}
        # The causal dimension is recomputed from repetition-aggregated components.
        cscore, _ = causal_score01([{"name": k, "value": v} for k, v in metrics.items()])
        if cscore is not None and CAUSAL_DIM in templates_by_id[instance_template[iid]].get("dimensions", []):
            dims[CAUSAL_DIM] = cscore
        else:
            dims.pop(CAUSAL_DIM, None)
        return dims, metrics

    def template_stats(ids_by_tid: dict[str, list[str]], resample: bool) -> dict[str, dict[str, Any]]:
        synthetic: dict[str, dict[str, Any]] = {}
        for tid in tids:
            inst_rows = [sample_instance(iid, resample) for iid in ids_by_tid[tid]]
            dim_names = {d for dims, _ in inst_rows for d in dims}
            metric_names = {m for _, metrics in inst_rows for m in metrics}
            synthetic[tid] = {
                "dimensions": {d: 100.0 * mean([dims[d] for dims, _ in inst_rows if d in dims]) for d in dim_names},
                "metrics": {m: mean([metrics[m] for _, metrics in inst_rows if m in metrics]) for m in metric_names},
            }
        return synthetic

    def reduce(synthetic: dict[str, dict[str, Any]], selected: list[str]) -> tuple[float | None, dict[str, float], dict[str, float]]:
        boot_dims = []
        dim_values: dict[str, float] = {}
        for d, spec in profile_dims:
            rows = [
                (float(synthetic[tid]["dimensions"][d]), weight(tid, d))
                for tid in selected if d in synthetic[tid]["dimensions"] and weight(tid, d) > 0
            ]
            score = weighted_mean(rows)
            if score is None:
                continue
            dim_values[d] = score
            boot_dims.append({"dimension": d, "score": score, "weight": float(spec["weight"]), "coverage": 1.0})
        # A draw that lost a whole weighted Dimension cannot use the profile formula.
        mib = _profile_score(boot_dims) if all(d in dim_values for d in weighted_dims) else None
        causal_values: dict[str, float] = {}
        for name in sorted({m for tid in selected for m in synthetic[tid]["metrics"]}):
            rows = [
                (float(synthetic[tid]["metrics"][name]), weight(tid, CAUSAL_DIM))
                for tid in selected if name in synthetic[tid]["metrics"] and weight(tid, CAUSAL_DIM) > 0
            ]
            value = weighted_mean(rows)
            if value is not None:
                causal_values[name] = value
        return mib, dim_values, causal_values

    point = template_stats(dict(instance_ids_by_template), resample=False)
    point_mib, point_dims, point_causal = reduce(point, tids)
    dim_candidates = {d: [tid for tid in tids if d in point[tid]["dimensions"] and weight(tid, d) > 0] for d, _ in profile_dims}
    eligible_dims = {d for d, c in dim_candidates.items() if len(c) >= threshold}
    insufficient = sorted(d for d, _ in profile_dims if d not in eligible_dims)
    causal_candidates = {
        name: [tid for tid in tids if name in point[tid]["metrics"] and weight(tid, CAUSAL_DIM) > 0]
        for name in point_causal
    }
    eligible_causal = {name for name, c in causal_candidates.items() if len(c) >= threshold}

    mib_samples: list[float] = []
    dim_samples: dict[str, list[float]] = defaultdict(list)
    causal_samples: dict[str, list[float]] = defaultdict(list)
    for _ in range(resamples):
        # Stage 1: Instances (and their paired Repetitions) inside each original Template.
        stage1 = {tid: [rng.choice(instance_ids_by_template[tid]) for _ in instance_ids_by_template[tid]] for tid in tids}
        synthetic = template_stats(stage1, resample=True)
        # Stage 2: one Template resample shared by every statistic of this draw.
        selected = [rng.choice(tids) for _ in tids]
        mib, dims, causal = reduce(synthetic, selected)
        if mib is not None:
            mib_samples.append(mib)
        for d, v in dims.items():
            dim_samples[d].append(v)
        for name, v in causal.items():
            causal_samples[name].append(v)

    method = "hierarchical_bootstrap_percentile"
    mib_ci_ok = bool(mib_samples) and all(d in eligible_dims for d in weighted_dims)
    return {
        "confidence_level": confidence_level,
        "bootstrap": {
            "method": method,
            "resamples": resamples,
            "seed": seed,
            "template_resampling": True,
            "instance_resampling": True,
            "repetition_resampling": True,
            "preserve_causal_pairs": True,
            "min_templates_per_dimension": threshold,
            "insufficient_dimensions": insufficient,
        },
        "mib_score": {
            "value": point_mib if point_mib is not None else 0.0,
            "n": len(mib_samples),
            **({"ci": ci_percentile(mib_samples, confidence_level, method, resamples, seed)} if mib_ci_ok else {}),
        },
        "dimensions": [
            {
                "dimension": d,
                "value": point_dims[d],
                **({"ci": ci_percentile(dim_samples[d], confidence_level, method, resamples, seed)}
                   if d in eligible_dims and dim_samples.get(d) else {}),
            }
            for d in sorted(point_dims)
        ],
        "causal_metrics": [
            {
                "name": name,
                "value": point_causal[name],
                **({"ci": ci_percentile(causal_samples[name], confidence_level, "paired_hierarchical_bootstrap_percentile", resamples, seed)}
                   if name in eligible_causal and causal_samples.get(name) else {}),
            }
            for name in sorted(point_causal)
        ],
    }


def build_pack_report(
    *,
    templates: list[dict[str, Any]],
    instances: list[dict[str, Any]],
    all_runs: list[dict[str, Any]],
    profile: dict[str, Any],
    agent_descriptor: dict[str, Any],
    statistics: dict[str, Any] | None = None,
    transfer_diagnostics: dict[str, Any] | None = None,
    unsupported_templates: list[str] | None = None,
    extra_warnings: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    if not all_runs:
        raise ValueError("no runs to report: every required Template was unsupported or skipped")
    templates_by_id = {t["id"]: t for t in templates}
    instance_by_iid = {f"{s['id']}:{(s.get('instantiation') or {}).get('seed', 'instance')}": s for s in instances}
    runs_by_instance: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in all_runs:
        runs_by_instance[r["scenario_instance_id"]].append(r)

    instance_aggs = []
    instances_by_template: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for iid, runs in sorted(runs_by_instance.items()):
        scenario = instance_by_iid[iid]
        agg = build_instance_aggregate(scenario, runs)
        instance_aggs.append(agg)
        instances_by_template[agg["template_id"]].append(agg)

    template_aggs = [
        build_template_aggregate(templates_by_id[tid], instances_by_template[tid])
        for tid in sorted(instances_by_template)
    ]
    dims = dimension_aggregates(template_aggs, profile, templates)
    base_score = _profile_score(dims)
    required_coverage = float(profile.get("required_coverage", 1.0))
    by_dim_cov = {d["dimension"]: float(d["coverage"]) for d in dims}
    profile_cov = math.fsum(float(d["weight"]) * float(d["coverage"]) for d in dims)
    profile_eligible = profile_cov + 1e-12 >= required_coverage
    causal = aggregate_benchmark_causal_metrics(instances_by_template, templates_by_id)

    failed_probe_attempts = sum(1 for r in all_runs for p in r.get("probe_results", []) if p.get("outcome") == "execution_failure")
    scheduled_probe_attempts = sum(len(r.get("probe_results", [])) for r in all_runs)
    warnings: list[dict[str, Any]] = list(extra_warnings or [])
    unsupported_templates = sorted(unsupported_templates or [])
    if unsupported_templates:
        warnings.append({
            "code": "coverage.unsupported_templates",
            "severity": "warning",
            "message": f"Not executed: the Agent declares a required capability false for {unsupported_templates}.",
            "scope": "report",
        })
    if statistics:
        statistics = copy.deepcopy(statistics)
        # One MIB Score per report: the statistics block carries the point estimate, not the bootstrap mean.
        statistics.setdefault("mib_score", {})["value"] = base_score
        insufficient = (statistics.get("bootstrap") or {}).get("insufficient_dimensions") or []
        if insufficient:
            warnings.append({
                "code": "statistics.insufficient_templates",
                "severity": "info",
                "message": (
                    f"No confidence interval: fewer than {statistics['bootstrap'].get('min_templates_per_dimension')} "
                    f"Templates carry {insufficient}."
                ),
                "scope": "report",
            })
    if not profile_eligible:
        warnings.append({
            "code": "coverage.profile_incomplete",
            "severity": "warning",
            "message": f"Profile coverage {profile_cov:.3f} is below required {required_coverage:.3f}.",
            "scope": "report",
        })
    official_profile = bool(profile.get("official", False))
    if official_profile:
        warnings.append({
            "code": "evaluation.hidden_profile",
            "severity": "info",
            "message": "This score was produced from an evaluator-only Hidden/Private pack. Public disclosure may redact Scenario identifiers and seeds.",
            "scope": "report",
        })
    else:
        warnings.append({
            "code": "development.dev_profile",
            "severity": "info",
            "message": "This is a Public Dev Pack score, not an official Hidden Eval leaderboard score.",
            "scope": "report",
        })

    profile_id = profile["id"]
    report = {
        "mib": "0.1",
        "kind": "MIBReport",
        "report_version": "0.1.0",
        "report_id": f"report_{uuid.uuid4().hex[:16]}",
        "generated_at": utc_now(),
        "scope": "internal",
        "benchmark": {
            "mib_version": "0.1",
            "profile": {"id": profile_id, "version": profile["version"]},
            "track": profile.get("track", "integrated_agent"),
            "scale": profile.get("scale", "MIB-S"),
            "scenario_pack": {"id": profile.get("scenario_pack", {}).get("id", "MIB-v0.1-Public-Dev"), "version": profile.get("scenario_pack", {}).get("version", "0.1.0")},
            "scoring_spec_version": "0.1-draft",
            "scenario_schema_version": "0.1",
            "agent_adapter_protocol": agent_descriptor.get("protocol", "mib-agent/0.1"),
        },
        "system": {
            "agent": {
                "name": agent_descriptor.get("implementation", {}).get("name", "Unknown Agent"),
                "version": agent_descriptor.get("implementation", {}).get("version", "0.0.0"),
                "vendor": agent_descriptor.get("implementation", {}).get("vendor", "Unknown"),
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
            **({"platform": {"submission_sandbox": copy.deepcopy((agent_descriptor.get("extensions") or {}).get("mib.sandbox"))}}
               if (agent_descriptor.get("extensions") or {}).get("mib.sandbox") else {}),
        },
        "execution": {
            "started_at": min(r["started_at"] for r in all_runs),
            "completed_at": max(r["completed_at"] for r in all_runs),
            "scheduled_runs": len(all_runs),
            "completed_runs": sum(1 for r in all_runs if r.get("status") in {"succeeded", "failed"}),
            "scheduled_probe_attempts": scheduled_probe_attempts,
            "execution_failed_probe_attempts": failed_probe_attempts,
            "execution_failure_rate": failed_probe_attempts / scheduled_probe_attempts if scheduled_probe_attempts else 0.0,
            "unsupported_required_weight": float(len(unsupported_templates)),
            "total_required_weight": float(len(templates)),
            "unsupported_rate": len(unsupported_templates) / len(templates) if templates else 0.0,
            "repetitions_policy": {"per_instance": int(profile.get("repetitions", 1))},
            "condition_order_policy": "full_then_declared_ablations",
        },
        "results": {
            "runs": [strip_extensions_for_report(r) for r in all_runs],
            "redacted": False,
            "raw_output_policy": "digest_only",
        },
        "aggregates": {
            "scenario_instances": instance_aggs,
            "templates": template_aggs,
            "dimensions": dims,
            "mib_score": {
                "base_score": base_score,
                "global_guardrail_penalty": 0.0,
                "final_score": base_score,
                "official": bool(profile.get("official", False)) and profile_eligible,
                "partial": not profile_eligible,
                "profile_eligible": profile_eligible,
                "formula": "weighted_dimension_sum",
            },
            "dimension_weight_sum": math.fsum(float(d["weight"]) for d in dims),
        },
        "causal_metrics": causal,
        "coverage": {
            "overall": profile_cov,
            "profile_required": required_coverage,
            "by_dimension": by_dim_cov,
            "missing_required_templates": [],
            "unsupported_required_templates": unsupported_templates,
            **({"partial_score_reason": "One or more required development dimensions lack full evidence coverage."} if not profile_eligible else {}),
        },
        "statistics": statistics or {"confidence_level": float(profile.get("statistics", {}).get("confidence_level", 0.95)), "mib_score": {"value": base_score, "n": len(instance_aggs)}},
        "warnings": warnings,
        "provenance": {
            "generated_by": "MIB Reference Runner",
            "generator_version": __version__,
            "score_recomputed": True,
            "verification_status": "verified",
        },
    }
    if statistics and statistics.get("mib_score", {}).get("ci"):
        report["aggregates"]["mib_score"]["ci"] = copy.deepcopy(statistics["mib_score"]["ci"])
        stat_dims = {x["dimension"]: x for x in statistics.get("dimensions", [])}
        for d in report["aggregates"]["dimensions"]:
            if d["dimension"] in stat_dims and stat_dims[d["dimension"]].get("ci"):
                d["ci"] = copy.deepcopy(stat_dims[d["dimension"]]["ci"])
        stat_causal = {x["name"]: x for x in statistics.get("causal_metrics", [])}
        for m in report.get("causal_metrics", []):
            if m["name"] in stat_causal and stat_causal[m["name"]].get("ci"):
                m["ci"] = copy.deepcopy(stat_causal[m["name"]]["ci"])
    # Supplemental diagnostics only.  A pack whose Templates carry no Transfer
    # Support Annotation produces a report with no extension at all, so an
    # unannotated MIB-Core report is byte-identical to the pre-extension one.
    attach_transfer_diagnostics(report, transfer_diagnostics)
    return report


def run_benchmark_pack(
    *,
    templates: list[dict[str, Any]],
    schema: dict[str, Any],
    profile: dict[str, Any],
    agent_factory: Callable[[], Any],
    instance_seeds: list[int | str],
    repetitions: int,
    include_ablations: bool = True,
    bootstrap_resamples: int = 0,
    bootstrap_seed: int | str = 20260819,
    transfer_diagnostics: bool = True,
    transfer_matrix: bool = False,
    transfer_epsilon: float = DEFAULT_EPSILON,
) -> tuple[dict[str, Any], dict[str, Any]]:
    templates = select_profile_templates(templates, profile)
    all_instances: list[dict[str, Any]] = []
    all_runs: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    descriptor = describe_agent_factory(agent_factory)
    unsupported = [t["id"] for t in templates if not agent_supports_template(descriptor, t)]

    for template in templates:
        vr = validate_scenario(template, schema)
        if not vr.valid:
            raise ValueError(f"Template {template['id']} invalid: {vr.errors}")
        if template["id"] in unsupported:
            continue
        for seed in instance_seeds:
            instance = materialize(template, seed)
            vr2 = validate_scenario(instance, schema)
            if not vr2.valid:
                raise ValueError(f"Instance {template['id']} seed={seed} invalid: {vr2.errors}")
            all_instances.append(instance)
            for rep in range(repetitions):
                agent_seed = f"{seed}:{rep}"
                runs = run_scenario(
                    scenario=instance,
                    agent_factory=agent_factory,
                    include_ablations=include_ablations,
                    repetition=rep,
                    agent_seed=agent_seed,
                )
                _, _, notes = validate_causal_pairs(runs)
                warnings.extend(pair_warnings(runs[0]["scenario_instance_id"], notes))
                all_runs.extend(runs)

    runs_by_instance: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in all_runs:
        runs_by_instance[r["scenario_instance_id"]].append(r)

    stats = None
    if bootstrap_resamples > 0:
        stats = hierarchical_bootstrap(
            templates=templates,
            runs_by_instance=runs_by_instance,
            profile=profile,
            resamples=bootstrap_resamples,
            seed=bootstrap_seed,
            confidence_level=float(profile.get("statistics", {}).get("confidence_level", 0.95)),
        )

    # The 2x2 diagnostic cells stay in their own list.  Merging them into
    # all_runs would move condition_scores, causal pair sets, and execution
    # counts, and a supplemental diagnostic must never do that.
    diagnostic_runs = run_transfer_matrix_pack(
        instances=all_instances,
        agent_factory=agent_factory,
        repetitions=repetitions,
    ) if (transfer_diagnostics and transfer_matrix) else []

    report = build_pack_report(
        templates=templates,
        instances=all_instances,
        all_runs=all_runs,
        profile=profile,
        agent_descriptor=descriptor,
        statistics=stats,
        unsupported_templates=unsupported,
        extra_warnings=warnings,
        transfer_diagnostics=build_transfer_diagnostics(
            templates=templates,
            runs=all_runs,
            diagnostic_runs=diagnostic_runs,
            epsilon=transfer_epsilon,
            bootstrap_resamples=bootstrap_resamples,
            bootstrap_seed=bootstrap_seed,
            confidence_level=float(profile.get("statistics", {}).get("confidence_level", 0.95)),
        ) if transfer_diagnostics else None,
    )
    summary = {
        "profile": profile["id"],
        "template_count": len(templates),
        "instance_count": len(all_instances),
        "run_count": len(all_runs),
        "repetitions": repetitions,
        "instance_seeds": list(instance_seeds),
        "mib_score": report["aggregates"]["mib_score"]["final_score"],
        "coverage": report["coverage"]["overall"],
        "dimensions": {d["dimension"]: d["score"] for d in report["aggregates"]["dimensions"]},
        "causal_metrics": {m["name"]: m["value"] for m in report.get("causal_metrics", [])},
        **({"transfer_diagnostic_run_count": len(diagnostic_runs)} if diagnostic_runs else {}),
    }
    return report, summary



def run_materialized_pack(
    *,
    templates: list[dict[str, Any]],
    instances: list[dict[str, Any]],
    schema: dict[str, Any],
    profile: dict[str, Any],
    agent_factory: Callable[[], Any],
    repetitions: int,
    include_ablations: bool = True,
    bootstrap_resamples: int = 0,
    bootstrap_seed: int | str = 20260819,
    transfer_diagnostics: bool = True,
    transfer_matrix: bool = False,
    transfer_epsilon: float = DEFAULT_EPSILON,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Execute evaluator-materialized instances without exposing generation seeds to the submission."""
    templates = select_profile_templates(templates, profile)
    templates_by_id = {t["id"]: t for t in templates}
    expected_ids = set(templates_by_id)
    for t in templates:
        vr = validate_scenario(t, schema)
        if not vr.valid:
            raise ValueError(f"Template {t['id']} invalid: {vr.errors}")
    instance_template_ids = {
        (instance.get("instantiation") or {}).get("template_id", instance.get("id"))
        for instance in instances
    }
    missing_instances = sorted(expected_ids - instance_template_ids)
    if missing_instances:
        raise ValueError(f"profile requires Templates with no materialized Instances: {missing_instances}")
    descriptor = describe_agent_factory(agent_factory)
    unsupported = [t["id"] for t in templates if not agent_supports_template(descriptor, t)]
    warnings: list[dict[str, Any]] = []

    all_runs: list[dict[str, Any]] = []
    for instance in instances:
        vr = validate_scenario(instance, schema)
        if not vr.valid:
            raise ValueError(f"Hidden instance {instance.get('id')} invalid: {vr.errors}")
        tid = (instance.get("instantiation") or {}).get("template_id", instance.get("id"))
        if tid not in templates_by_id:
            raise ValueError(f"Hidden instance references unknown Template: {tid}")
        if tid in unsupported:
            continue
        seed_alias = (instance.get("instantiation") or {}).get("seed", "hidden")
        for rep in range(repetitions):
            # The Agent receives a deterministic opaque seed token.  It is not the
            # evaluator's secret parameter-generation seed.
            agent_seed = f"{seed_alias}:{rep}"
            runs = run_scenario(
                scenario=instance,
                agent_factory=agent_factory,
                include_ablations=include_ablations,
                repetition=rep,
                agent_seed=agent_seed,
            )
            _, _, notes = validate_causal_pairs(runs)
            warnings.extend(pair_warnings(runs[0]["scenario_instance_id"], notes))
            all_runs.extend(runs)

    runs_by_instance: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in all_runs:
        runs_by_instance[r["scenario_instance_id"]].append(r)
    stats = None
    if bootstrap_resamples > 0:
        stats = hierarchical_bootstrap(
            templates=templates,
            runs_by_instance=runs_by_instance,
            profile=profile,
            resamples=bootstrap_resamples,
            seed=bootstrap_seed,
            confidence_level=float(profile.get("statistics", {}).get("confidence_level", 0.95)),
        )
    diagnostic_runs = run_transfer_matrix_pack(
        instances=instances,
        agent_factory=agent_factory,
        repetitions=repetitions,
    ) if (transfer_diagnostics and transfer_matrix) else []

    report = build_pack_report(
        templates=templates,
        instances=instances,
        all_runs=all_runs,
        profile=profile,
        agent_descriptor=descriptor,
        statistics=stats,
        unsupported_templates=unsupported,
        extra_warnings=warnings,
        transfer_diagnostics=build_transfer_diagnostics(
            templates=templates,
            runs=all_runs,
            diagnostic_runs=diagnostic_runs,
            epsilon=transfer_epsilon,
            bootstrap_resamples=bootstrap_resamples,
            bootstrap_seed=bootstrap_seed,
            confidence_level=float(profile.get("statistics", {}).get("confidence_level", 0.95)),
        ) if transfer_diagnostics else None,
    )
    summary = {
        "profile": profile["id"],
        "template_count": len(templates),
        "instance_count": len(instances),
        "run_count": len(all_runs),
        "repetitions": repetitions,
        "mib_score": report["aggregates"]["mib_score"]["final_score"],
        "coverage": report["coverage"]["overall"],
        "dimensions": {d["dimension"]: d["score"] for d in report["aggregates"]["dimensions"]},
        "causal_metrics": {m["name"]: m["value"] for m in report.get("causal_metrics", [])},
        **({"transfer_diagnostic_run_count": len(diagnostic_runs)} if diagnostic_runs else {}),
    }
    return report, summary


def load_templates(root: str | Path) -> list[dict[str, Any]]:
    root = Path(root)
    files = [root] if root.is_file() else sorted(root.rglob("MIB-*.json"))
    out = []
    for p in files:
        if ".example-" in p.name:
            continue
        out.append(json.loads(p.read_text(encoding="utf-8")))
    return out
