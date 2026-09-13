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
    ci_bca,
    ci_percentile,
    condition_scores,
    full_run_metrics,
    instance_dimension_scores,
    instance_key,
    mean,
    memory_dependence,
    aggregate_dependence_evidence,
    paired_causal_metrics,
    percentile,
    retention_block,
    rung_of_key,
    run_tolerances,
    validate_causal_pairs,
    weighted_mean,
    weighted_probe_score,
)
from .generate import generate_pack
from .util import utc_now, runner_source_digest
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



from .aggregation import (build_template_aggregate, dimension_aggregates,
                          aggregate_benchmark_causal_metrics, profile_score as _profile_score,
                          canonical_instances, score_aggregates, tracking_totals)


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
    if profile.get('programs'):
        from .generate import program_descriptor
        required = [program_descriptor(e['id'] if isinstance(e, dict) else e)['id'] for e in profile['programs']]
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
    """Capabilities needed by the Scenario must be explicitly supported."""
    from .adapter_contract import check_descriptor, required_capabilities, AdapterLifecycleError
    try:
        check_descriptor(descriptor, required_capabilities(template))
        return True
    except AdapterLifecycleError:
        return False


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
    # Generated packs: the score is taken at the Profile's canonical rung, and
    # the statistical unit is the Instance (a program is a generator, not a
    # sample), so the threshold counts Instances per Dimension.
    canonical_rung = profile.get("canonical_rung")
    unit_is_instance = bool(profile.get("programs"))

    # Compact per-repetition summaries make 10k resamples practical.
    rep_stats: dict[str, list[dict[str, Any]]] = defaultdict(list)
    instance_template: dict[str, str] = {}
    for iid, runs in runs_by_instance.items():
        if not runs:
            continue
        if canonical_rung is not None and rung_of_key(iid) not in (None, int(canonical_rung)):
            continue
        tid = runs[0]["template_id"]
        instance_template[iid] = tid
        scenario = templates_by_id[tid]
        for rep in sorted({int(r["repetition"]) for r in runs if r.get("condition") == "full"}):
            rr = [r for r in runs if int(r["repetition"]) == rep]
            validate_causal_pairs(rr)
            full = next((r for r in rr if r.get("condition") == "full"), None)
            if full is None:
                continue
            # Run evidence carries the effective tolerance, including when the
            # verifier has only the reduced public Template descriptor. Retain
            # Scenario defaults for legacy artifacts without that field.
            tolerances = {**ablation_tolerances(scenario),
                          **run_tolerances([r for r in rr if 'ablation_tolerance' in r])}
            metrics = paired_causal_metrics(rr, tolerances) + full_run_metrics([full])
            rep_stats[iid].append({
                "dimensions": instance_dimension_scores(list(scenario.get("dimensions", [])), [full], metrics),
                "metrics": {m["name"]: float(m["value"]) for m in metrics},
                "metric_counts": {m['name']: int(m.get('eligible_n', 1)) for m in metrics},
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
        metrics = {m: weighted_mean([(r['metrics'][m], r['metric_counts'].get(m, 1)) for r in sampled if m in r['metrics']]) for m in metric_names}
        metrics = {m: v for m, v in metrics.items() if v is not None}
        if 'memory_benefit' in metrics and 'memory_harm' in metrics:
            metrics['net_memory_gain'] = metrics['memory_benefit'] - metrics['memory_harm']
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
            if not ids_by_tid.get(tid):
                continue   # a jackknife draw may empty a Template
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
                (float(synthetic[tid]["metrics"][name]), weight(tid, CAUSAL_DIM) or 1.0)
                for tid in selected if name in synthetic[tid]["metrics"]
            ]
            value = weighted_mean(rows)
            if value is not None:
                causal_values[name] = value
        return mib, dim_values, causal_values

    point = template_stats(dict(instance_ids_by_template), resample=False)
    point_mib, point_dims, point_causal = reduce(point, tids)
    dim_candidates = {d: [tid for tid in tids if d in point[tid]["dimensions"] and weight(tid, d) > 0] for d, _ in profile_dims}

    def unit_count(candidate_tids: list[str]) -> int:
        if unit_is_instance:
            return sum(len(instance_ids_by_template[tid]) for tid in candidate_tids)
        return len(candidate_tids)

    eligible_dims = {d for d, c in dim_candidates.items() if unit_count(c) >= threshold}
    insufficient = sorted(d for d, _ in profile_dims if d not in eligible_dims)
    causal_candidates = {
        name: [tid for tid in tids if name in point[tid]["metrics"] and (weight(tid, CAUSAL_DIM) > 0 or unit_is_instance)]
        for name in point_causal
    }
    eligible_causal = {name for name, c in causal_candidates.items() if (
        sum(any(name in r['metrics'] for r in rep_stats[iid]) for tid in c for iid in instance_ids_by_template[tid])
        if unit_is_instance else unit_count(c)) >= threshold}

    mib_samples: list[float] = []
    dim_samples: dict[str, list[float]] = defaultdict(list)
    causal_samples: dict[str, list[float]] = defaultdict(list)
    for _ in range(resamples):
        # Stage 1: Instances (and their paired Repetitions) inside each original Template.
        stage1 = {tid: [rng.choice(instance_ids_by_template[tid]) for _ in instance_ids_by_template[tid]] for tid in tids}
        synthetic = template_stats(stage1, resample=True)
        # Stage 2: one Template resample shared by every statistic of this draw.
        # A generated pack has one program per Dimension by design; programs are
        # generators, not samples, so only their Instances are resampled.
        selected = list(tids) if unit_is_instance else [rng.choice(tids) for _ in tids]
        mib, dims, causal = reduce(synthetic, selected)
        if mib is not None:
            mib_samples.append(mib)
        for d, v in dims.items():
            dim_samples[d].append(v)
        for name, v in causal.items():
            causal_samples[name].append(v)

    # Interval method (§8.2): percentile by default; BCa uses leave-one-unit-out jackknife
    # estimates over the same statistic (Instances for generated packs, Templates otherwise).
    interval_method = str((profile.get("statistics") or {}).get("interval_method", "percentile"))
    jack_mib: list[float] = []
    jack_dims: dict[str, list[float]] = defaultdict(list)
    jack_causal: dict[str, list[float]] = defaultdict(list)
    if interval_method == "bca":
        units = ([(tid, iid) for tid in tids for iid in instance_ids_by_template[tid]] if unit_is_instance
                 else [(tid, None) for tid in tids])
        for tid_u, iid_u in units:
            if unit_is_instance:
                ids = {t: [i for i in instance_ids_by_template[t] if i != iid_u] for t in tids}
                selected = [t for t in tids if ids[t]]
                synthetic = template_stats(ids, resample=False)
            else:
                selected = [t for t in tids if t != tid_u]
                synthetic = point
            mib_j, dims_j, causal_j = reduce(synthetic, selected)
            if mib_j is not None:
                jack_mib.append(mib_j)
            for d, v in dims_j.items():
                jack_dims[d].append(v)
            for name, v in causal_j.items():
                jack_causal[name].append(v)

    def interval(samples: list[float], point_value: float, jack: list[float], label: str) -> dict[str, Any]:
        if interval_method == "bca":
            return ci_bca(samples, point_value, jack, confidence_level, resamples, seed)
        return ci_percentile(samples, confidence_level, label, resamples, seed)

    method = "bca" if interval_method == "bca" else "hierarchical_bootstrap_percentile"
    mib_ci_ok = bool(mib_samples) and all(d in eligible_dims for d in weighted_dims)
    return {
        "confidence_level": confidence_level,
        "bootstrap": {
            "method": method,
            "resamples": resamples,
            "seed": seed,
            "template_resampling": not unit_is_instance,
            "instance_resampling": True,
            "repetition_resampling": True,
            "preserve_causal_pairs": True,
            "min_templates_per_dimension": threshold,
            "insufficient_dimensions": insufficient,
        },
        "mib_score": {
            "value": point_mib if point_mib is not None else 0.0,
            "n": len(mib_samples),
            **({"ci": interval(mib_samples, point_mib if point_mib is not None else 0.0, jack_mib, "hierarchical_bootstrap_percentile")} if mib_ci_ok else {}),
        },
        "dimensions": [
            {
                "dimension": d,
                "value": point_dims[d],
                **({"ci": interval(dim_samples[d], point_dims[d], jack_dims.get(d, []), "hierarchical_bootstrap_percentile")}
                   if d in eligible_dims and dim_samples.get(d) else {}),
            }
            for d in sorted(point_dims)
        ],
        "causal_metrics": [
            {
                "name": name,
                "value": point_causal[name],
                **({"ci": interval(causal_samples[name], point_causal[name], jack_causal.get(name, []), "paired_hierarchical_bootstrap_percentile")}
                   if name in eligible_causal and causal_samples.get(name) else {}),
            }
            for name in sorted(point_causal)
        ],
    }


def efficiency_summary(runs: list[dict[str, Any]]) -> dict[str, Any]:
    """Runner-measured cost of the evaluation (§9.1): latency, tool calls, and any participant-reported usage."""
    latencies = sorted(float(p.get("latency_ms", 0.0)) for r in runs for p in r.get("probe_results", []) if p.get("outcome") == "scored")
    tool_calls = sum(1 for r in runs for row in ((r.get("extensions") or {}).get("mib.runner.action_trace") or []) if row.get("kind") == "tool_call")
    measured: dict[str, Any] = {"runs": len(runs), "scored_probes": len(latencies), "tool_calls_total": tool_calls}
    operations: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for run in runs:
        for op, counts in ((run.get('extensions') or {}).get('mib.runner.operation_usage') or {}).items():
            for field, value in counts.items():
                operations[op][field] += value
    if operations:
        measured['operations'] = {k: dict(v) for k, v in operations.items()}
        measured['measurement_unit'] = 'UTF-8 bytes and wall-clock milliseconds; not tokenizer tokens'
    if latencies:
        measured.update({
            "probe_latency_ms_mean": mean(latencies),
            "probe_latency_ms_p50": percentile(latencies, 0.5),
            "probe_latency_ms_max": latencies[-1],
        })
    reported: dict[str, float] = defaultdict(float)
    for r in runs:
        for key, value in (r.get("usage") or {}).items():
            if isinstance(value, (int, float)):
                reported[key] += float(value)
    out: dict[str, Any] = {"runner_measured": measured,
        "participant_reported": {"accounting_complete": False, "total_cost": None,
            "per_run_costs": [{"run_id": r["run_id"], "last_snapshot": r.get("adapter_contract", {}).get("reported_costs_last")}
                              for r in runs]}}
    if reported:
        out["participant_reported"]["known_usage_subtotals"] = dict(reported)
    return out


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
    instance_by_iid = {instance_key(s): s for s in instances}
    runs_by_instance: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in all_runs:
        runs_by_instance[r["scenario_instance_id"]].append(r)

    # Generated packs carry a ladder; the capability score is read at the
    # Profile's canonical rung and every rung feeds the retention curve (§8).
    canonical_rung = profile.get("canonical_rung")
    instance_aggs = []
    instances_by_template: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for iid, runs in sorted(runs_by_instance.items()):
        scenario = instance_by_iid[iid]
        agg = build_instance_aggregate(scenario, runs)
        instance_aggs.append(agg)
        if canonical_rung is None or agg.get("rung") is None or int(agg["rung"]) == int(canonical_rung):
            instances_by_template[agg["template_id"]].append(agg)

    aggregated = score_aggregates(instance_aggs, templates, profile)
    template_aggs, dims, base_score = aggregated['templates'], aggregated['dimensions'], aggregated['score']
    required_coverage = float(profile.get("required_coverage", 1.0))
    by_dim_cov = {d["dimension"]: float(d["coverage"]) for d in dims}
    profile_cov = math.fsum(float(d["weight"]) * float(d["coverage"]) for d in dims)
    profile_eligible = profile_cov + 1e-12 >= required_coverage
    causal = aggregated['causal_metrics']
    retention = retention_block(instance_aggs, int(canonical_rung) if canonical_rung is not None else None)
    evidence = aggregate_dependence_evidence(canonical_instances(instance_aggs, profile))
    dependence = memory_dependence(causal, profile, evidence if profile.get('programs') else None,
                                   tracking_totals(canonical_instances(instance_aggs, profile)) if profile.get('programs') else None)
    dependence_gate = profile.get("memory_dependence") is not None
    dependence_ok = dependence["eligible"] is True if dependence_gate else True
    format_version = "0.2" if str(profile.get("mib", "")) == "0.2" or profile.get("programs") else "0.1"

    failed_probe_attempts = sum(1 for r in all_runs for p in r.get("probe_results", []) if p.get("outcome") == "execution_failure")
    scheduled_probe_attempts = sum(len(r.get("probe_results", [])) for r in all_runs)
    failure_rate = failed_probe_attempts / scheduled_probe_attempts if scheduled_probe_attempts else 0.0
    warnings: list[dict[str, Any]] = list(extra_warnings or [])
    unsupported_templates = sorted(unsupported_templates or [])
    if unsupported_templates:
        warnings.append({
            "code": "coverage.unsupported_templates",
            "severity": "warning",
            "message": f"Not executed: the Agent did not explicitly declare a required capability true for {unsupported_templates}.",
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
    if dependence_gate and not dependence_ok:
        warnings.append({
            "code": "memory_dependence.below_floor",
            "severity": "warning",
            "message": (
                f"Memory dependence not established: {dependence['metric']} = {dependence.get(dependence['metric'])} "
                f"(floor {dependence['floor']}, eligible pairs {dependence['eligible_n']}/{dependence['total_n']}). "
                "The capability score was not shown to be earned through memory."
            ),
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
        "mib": format_version,
        "kind": "MIBReport",
        "report_version": "0.4.0",
        "report_id": f"report_{uuid.uuid4().hex[:16]}",
        "generated_at": utc_now(),
        "scope": "internal",
        "benchmark": {
            "mib_version": format_version,
            "profile": {"id": profile_id, "version": profile["version"]},
            "track": profile.get("track", "integrated_agent"),
            "scale": profile.get("scale", "MIB-S"),
            "scenario_pack": {"id": profile.get("scenario_pack", {}).get("id", "MIB-v0.1-Public-Dev"), "version": profile.get("scenario_pack", {}).get("version", "0.1.0")},
            "scoring_spec_version": f"{format_version}-spec",
            "scenario_schema_version": format_version,
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
                "official": bool(profile.get("official", False)) and profile_eligible and dependence_ok and failure_rate <= float(profile.get('max_execution_failure_rate', 0)),
                "partial": not profile_eligible,
                "profile_eligible": profile_eligible,
                "formula": "weighted_dimension_sum",
            },
            "dimension_weight_sum": math.fsum(float(d["weight"]) for d in dims),
        },
        "causal_metrics": causal,
        **({"retention": retention} if retention else {}),
        "memory_dependence": dependence,
        "evaluation_policy": {
            "version": "1.0.0",
            "runner_source_digest": runner_source_digest(),
            "profile": {k: copy.deepcopy(v) for k, v in profile.items() if k in {
                'id', 'version', 'track', 'scale', 'official', 'required_coverage', 'required_templates', 'dimensions',
                'statistics', 'scenario_pack', 'canonical_rung', 'programs', 'memory_dependence', 'measurement_regime',
                'repetitions', 'max_execution_failure_rate'}},
            "templates": [{'id': t['id'], 'version': t.get('version'), 'dimensions': t.get('dimensions', []),
                           'scoring': {'dimension_weights': copy.deepcopy(t.get('scoring', {}).get('dimension_weights', {}))}}
                          for t in templates],
        },
        "efficiency": efficiency_summary(all_runs),
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
    if statistics:
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
    if profile.get('programs'):
        from .generate.base import template_id_for
        from .generate.registry import resolve_program_config
        configs = [resolve_program_config(e, profile.get('ladder')) for e in profile['programs']]
        by_template = {template_id_for(c['id']): c for c in configs}
        units: dict[tuple[str, Any], set[int]] = defaultdict(set)
        seen = set()
        for instance in instances:
            inst = instance['instantiation']
            config = by_template.get(inst['template_id'])
            rung = inst['rung']
            if (config is None or type(rung) is not int or not 0 <= rung < len(config['ladder'])
                    or inst.get('program') != config['id']
                    or inst.get('program_version') != config['version']
                    or inst.get('interference_count') != config['ladder'][rung]):
                raise ValueError('generated Instance Program/ladder differs from the Profile')
            key = (inst['template_id'], inst['seed'], inst['rung'])
            if key in seen:
                raise ValueError('duplicate generated Instance')
            seen.add(key)
            units[(inst['template_id'], inst['seed'])].add(inst['rung'])
        if any(rungs != set(range(len(by_template[tid]['ladder']))) for (tid, _), rungs in units.items()):
            raise ValueError('generated hidden pack must contain every rung for every seed')
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


def run_generated_pack(
    *,
    profile: dict[str, Any],
    agent_factory: Callable[[], Any],
    schema: dict[str, Any] | None = None,
    seeds: list[int | str] | None = None,
    repetitions: int = 1,
    include_ablations: bool = True,
    bootstrap_resamples: int = 0,
    bootstrap_seed: int | str = 20260819,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Generate and execute a v0.2 pack: every program of the Profile, every seed, every ladder rung."""
    descriptors, instances = generate_pack(profile, seeds)
    descriptor = describe_agent_factory(agent_factory)
    unsupported = [t["id"] for t in descriptors if not agent_supports_template(descriptor, t)]
    warnings: list[dict[str, Any]] = []
    all_runs: list[dict[str, Any]] = []
    executed: list[dict[str, Any]] = []
    for instance in instances:
        if schema is not None:
            vr = validate_scenario(instance, schema)
            if not vr.valid:
                raise ValueError(f"generated instance {instance_key(instance)} invalid: {vr.errors}")
        inst = instance["instantiation"]
        if inst["template_id"] in unsupported:
            continue
        executed.append(instance)
        for rep in range(repetitions):
            agent_seed = f"{inst['seed']}:r{inst['rung']}:{rep}"
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
            templates=descriptors,
            runs_by_instance=runs_by_instance,
            profile=profile,
            resamples=bootstrap_resamples,
            seed=bootstrap_seed,
            confidence_level=float(profile.get("statistics", {}).get("confidence_level", 0.95)),
        )
    report = build_pack_report(
        templates=descriptors,
        instances=executed,
        all_runs=all_runs,
        profile=profile,
        agent_descriptor=descriptor,
        statistics=stats,
        unsupported_templates=unsupported,
        extra_warnings=warnings,
    )
    summary = {
        "profile": profile["id"],
        "programs": [t["template"]["program"]["id"] for t in descriptors],
        "template_count": len(descriptors),
        "instance_count": len(executed),
        "run_count": len(all_runs),
        "repetitions": repetitions,
        "instance_seeds": list(seeds if seeds is not None else profile.get("instance_seeds") or [101, 202]),
        "ladder": list(profile.get("ladder") or []),
        "canonical_rung": profile.get("canonical_rung"),
        "mib_score": report["aggregates"]["mib_score"]["final_score"],
        "coverage": report["coverage"]["overall"],
        "dimensions": {d["dimension"]: d["score"] for d in report["aggregates"]["dimensions"]},
        "causal_metrics": {m["name"]: m["value"] for m in report.get("causal_metrics", [])},
        "retention": {r["template_id"]: [x["full_score"] for x in r["rungs"]] for r in report.get("retention", [])},
        "memory_dependence": report["memory_dependence"],
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
