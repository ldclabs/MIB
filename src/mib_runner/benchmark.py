from __future__ import annotations

import copy
import json
import math
import random
import uuid
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from . import __version__
from .materialize import materialize
from .report import strip_extensions_for_report
from .runner import run_scenario
from .scoring import ablation_tolerances, tolerant_harm_resistance, tolerant_stability
from .transfer_diagnostics import (
    DEFAULT_EPSILON,
    attach_transfer_diagnostics,
    build_transfer_diagnostics,
    transfer_diagnostic_aggregates,
    transfer_distance_aggregates,
    transfer_relation_aggregates,
)
from .transfer_matrix import run_transfer_matrix_pack
from .validation import validate_scenario

CAUSAL_DIM = "causal_memory_impact"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def mean(values: list[float]) -> float:
    return math.fsum(values) / len(values) if values else 0.0


def percentile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    xs = sorted(values)
    if len(xs) == 1:
        return xs[0]
    pos = (len(xs) - 1) * q
    lo = int(math.floor(pos))
    hi = int(math.ceil(pos))
    if lo == hi:
        return xs[lo]
    frac = pos - lo
    return xs[lo] * (1.0 - frac) + xs[hi] * frac


def ci_percentile(values: list[float], level: float, method: str, resamples: int, seed: int | str) -> dict[str, Any]:
    alpha = 1.0 - level
    return {
        "level": level,
        "lower": percentile(values, alpha / 2.0),
        "upper": percentile(values, 1.0 - alpha / 2.0),
        "method": method,
        "resamples": resamples,
        "seed": seed,
    }


def weighted_probe_score(run: dict[str, Any], dimension: str | None = None, probe_ids: set[str] | None = None) -> float | None:
    rows = []
    for p in run.get("probe_results", []):
        if p.get("outcome") not in {"scored", "execution_failure"}:
            continue
        if probe_ids is not None and p["probe_id"] not in probe_ids:
            continue
        if dimension is not None:
            dims = p.get("dimensions") or []
            if dims and dimension not in dims:
                continue
        rows.append((float(p.get("score", 0.0)), float(p.get("weight", 1.0))))
    if not rows:
        return None
    denom = math.fsum(w for _, w in rows)
    if denom <= 0:
        return None
    return math.fsum(s * w for s, w in rows) / denom


def validate_causal_pairs(runs: list[dict[str, Any]]) -> tuple[bool, list[str], list[str]]:
    """Validate that every intervention run has a same-repetition full control."""
    full_by_rep = {int(r["repetition"]): r for r in runs if r.get("condition") == "full"}
    pair_ids: list[str] = []
    notes: list[str] = []
    valid = True
    for r in runs:
        if r.get("condition") == "full":
            continue
        rep = int(r["repetition"])
        full = full_by_rep.get(rep)
        pair_ok = True
        if full is None:
            pair_ok = False
            notes.append(f"missing full control for repetition {rep}")
        else:
            for key in ["scenario_instance_id", "template_id", "instance_seed", "agent_seed"]:
                if full.get(key) != r.get(key):
                    pair_ok = False
                    notes.append(f"pair mismatch {key}: full={full.get(key)!r} variant={r.get(key)!r}")
            full_probe_ids = {p["probe_id"] for p in full.get("probe_results", [])}
            variant_probe_ids = {p["probe_id"] for p in r.get("probe_results", [])}
            if not variant_probe_ids.issubset(full_probe_ids):
                pair_ok = False
                notes.append(f"variant probes not subset of full probes: {sorted(variant_probe_ids - full_probe_ids)}")
            # Late/hidden-late Probe sampling must be identical across causal conditions.
            full_variants = (full.get("extensions") or {}).get("mib.runner.probe_variant_digests", {})
            var_variants = (r.get("extensions") or {}).get("mib.runner.probe_variant_digests", {})
            for pid in variant_probe_ids:
                if full_variants.get(pid) != var_variants.get(pid):
                    pair_ok = False
                    notes.append(f"pair mismatch late Probe variant for {pid}")
        r.setdefault("validity", {})["causal_pair_valid"] = pair_ok
        if not pair_ok:
            valid = False
        else:
            pair_ids.append(f"pair:{r['scenario_instance_id']}:{rep}:{r.get('ablation_id', r['condition'])}")
    return valid, pair_ids, notes


def paired_causal_metrics(runs: list[dict[str, Any]], tolerances: dict[str, float] | None = None) -> list[dict[str, Any]]:
    """Compute paired causal metrics, preserving repetition pairing and Probe subsets.

    ``tolerances`` maps ablation id to the Scenario-declared tolerance used by
    the tolerant IMS/HRS forms in MIB-Scoring 58 and 62.
    """
    tolerances = tolerances or {}
    full_by_rep = {int(r["repetition"]): r for r in runs if r.get("condition") == "full"}
    benefits: list[tuple[float, str]] = []
    hmb: list[float] = []
    ims: list[float] = []
    harms: list[float] = []
    hrs: list[float] = []
    negative_transfer: list[float] = []

    # Relevant-memory Ablation is the primary causal reference.  No-memory is a
    # fallback only for Probes that have no relevant Ablation in the same paired
    # repetition; averaging both would double-count the same causal unit and
    # change MB/HMB according to how many controls a Scenario happens to declare.
    relevant_probe_ids_by_rep: dict[int, set[str]] = defaultdict(set)
    for variant in runs:
        if variant.get("condition") != "relevant_ablation":
            continue
        if not variant.get("validity", {}).get("causal_pair_valid", True):
            continue
        relevant_probe_ids_by_rep[int(variant["repetition"])].update(
            str(p["probe_id"])
            for p in variant.get("probe_results", [])
            if p.get("outcome") in {"scored", "execution_failure"}
            and float(p.get("weight", 1.0)) > 0
        )

    for variant in runs:
        cond = variant.get("condition")
        if cond == "full" or not variant.get("validity", {}).get("causal_pair_valid", True):
            continue
        full = full_by_rep.get(int(variant["repetition"]))
        if not full:
            continue
        probe_ids = {
            p["probe_id"] for p in variant.get("probe_results", [])
            if p.get("outcome") in {"scored", "execution_failure"}
            and float(p.get("weight", 1.0)) > 0
        }
        if cond == "no_memory":
            probe_ids -= relevant_probe_ids_by_rep.get(int(variant["repetition"]), set())
        if not probe_ids:
            continue
        f = weighted_probe_score(full, probe_ids=probe_ids)
        v = weighted_probe_score(variant, probe_ids=probe_ids)
        if f is None or v is None:
            continue
        if cond in {"relevant_ablation", "no_memory"}:
            delta = f - v
            benefits.append((delta, cond))
            denom = 1.0 - v
            if denom > 0.02:
                hmb.append(max(0.0, delta) / denom)
        elif cond == "irrelevant_ablation":
            tau = tolerances.get(variant.get("ablation_id"), 0.0)
            ims.append(tolerant_stability(f - v, tau))
        elif cond in {"harmful_memory", "stale_memory"}:
            tau = tolerances.get(variant.get("ablation_id"), 0.0)
            harm = max(0.0, f - v)
            harms.append(harm)
            hrs.append(tolerant_harm_resistance(harm, tau))
        elif cond == "counterexample":
            # A generic counterexample ablation demonstrates applicability sensitivity,
            # but it is not the standardized Negative Transfer control from MIB-Scoring.md.
            # Do not mislabel full-vs-counterexample-ablation as raw negative transfer.
            pass

    out: list[dict[str, Any]] = []
    if benefits:
        vals = [v for v, _ in benefits]
        refs = {c for _, c in benefits}
        comparison = next(iter(refs)) if len(refs) == 1 else "custom"
        out.append({
            "name": "memory_benefit", "value": mean(vals), "unit": "percentage_points",
            "scope": "scenario_instance", "reference_condition": "full", "comparison_condition": comparison,
            "eligible_n": len(vals), "total_n": len(vals), "coverage": 1.0,
        })
    if hmb:
        out.append({
            "name": "headroom_normalized_memory_benefit", "value": mean(hmb), "unit": "normalized",
            "scope": "scenario_instance", "reference_condition": "full", "comparison_condition": "relevant_ablation",
            "eligible_n": len(hmb), "total_n": len(benefits), "coverage": len(hmb) / len(benefits) if benefits else 0.0,
        })
    if ims:
        out.append({
            "name": "irrelevant_memory_stability", "value": mean(ims), "unit": "normalized",
            "scope": "scenario_instance", "reference_condition": "full", "comparison_condition": "irrelevant_ablation",
            "eligible_n": len(ims), "total_n": len(ims), "coverage": 1.0,
        })
    if harms:
        out.extend([
            {"name": "memory_harm", "value": mean(harms), "unit": "percentage_points", "scope": "scenario_instance", "reference_condition": "full", "comparison_condition": "harmful_memory", "eligible_n": len(harms), "total_n": len(harms), "coverage": 1.0},
            {"name": "harm_resistance", "value": mean(hrs), "unit": "normalized", "scope": "scenario_instance", "reference_condition": "full", "comparison_condition": "harmful_memory", "eligible_n": len(hrs), "total_n": len(hrs), "coverage": 1.0},
        ])
    mb = next((m["value"] for m in out if m["name"] == "memory_benefit"), None)
    mh = next((m["value"] for m in out if m["name"] == "memory_harm"), None)
    if mb is not None and mh is not None:
        out.append({"name": "net_memory_gain", "value": mb - mh, "unit": "percentage_points", "scope": "scenario_instance"})
    return out


def causal_score01(metrics: list[dict[str, Any]]) -> tuple[float | None, dict[str, float]]:
    by = {m["name"]: float(m["value"]) for m in metrics}
    components: list[tuple[str, float, float]] = []
    if "headroom_normalized_memory_benefit" in by:
        components.append(("headroom_normalized_memory_benefit", 0.50, by["headroom_normalized_memory_benefit"]))
    if "irrelevant_memory_stability" in by:
        components.append(("irrelevant_memory_stability", 0.20, by["irrelevant_memory_stability"]))
    if "harm_resistance" in by:
        components.append(("harm_resistance", 0.30, by["harm_resistance"]))
    if not components:
        return None, {}
    denom = math.fsum(w for _, w, _ in components)
    score = math.fsum(w * v for _, w, v in components) / denom
    return score, {name: value for name, _, value in components}


def condition_scores(runs: list[dict[str, Any]]) -> dict[str, float]:
    buckets: dict[str, list[float]] = defaultdict(list)
    for r in runs:
        buckets[r["condition"]].append(float(r.get("scenario_score", 0.0)))
    return {k: mean(v) for k, v in buckets.items()}


def build_instance_aggregate(scenario: dict[str, Any], runs: list[dict[str, Any]]) -> dict[str, Any]:
    full_runs = [r for r in runs if r.get("condition") == "full"]
    if not full_runs:
        raise ValueError("Scenario Instance requires at least one full run")
    valid, pair_ids, notes = validate_causal_pairs(runs)
    metrics = paired_causal_metrics(runs, ablation_tolerances(scenario))
    dimensions: dict[str, float] = {}
    for d in scenario.get("dimensions", []):
        if d == CAUSAL_DIM:
            continue
        vals = []
        for fr in full_runs:
            x = weighted_probe_score(fr, dimension=d)
            if x is None:
                x = float(fr.get("scenario_score", 0.0))
            vals.append(x)
        dimensions[d] = mean(vals)
    if CAUSAL_DIM in scenario.get("dimensions", []):
        cscore, _ = causal_score01(metrics)
        if cscore is not None:
            dimensions[CAUSAL_DIM] = cscore
    iid = full_runs[0]["scenario_instance_id"]
    result = {
        "scenario_instance_id": iid,
        "template_id": full_runs[0]["template_id"],
        "instance_seed": full_runs[0].get("instance_seed"),
        "full_score": mean([float(r.get("scenario_score", 0.0)) for r in full_runs]),
        "dimension_scores": dimensions,
        "condition_scores": condition_scores(runs),
        "repetitions": len(full_runs),
        "causal_pair_ids": pair_ids,
        "causal_metrics": metrics,
    }
    if not valid:
        result.setdefault("causal_metrics", []).append({
            "name": "causal_memory_impact", "value": 0.0, "unit": "normalized", "scope": "scenario_instance",
            "eligible_n": 0, "total_n": max(0, len(runs) - len(full_runs)), "coverage": 0.0,
            "notes": "; ".join(notes),
        })
    return result


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


def dimension_aggregates(template_aggs: list[dict[str, Any]], profile: dict[str, Any]) -> list[dict[str, Any]]:
    out = []
    profile_dims = profile.get("dimensions") or {}
    for d, spec in profile_dims.items():
        rows = []
        expected = 0.0
        evaluated = 0.0
        for t in template_aggs:
            evidence_w = float((t.get("dimension_weights") or {}).get(d, 0.0))
            if evidence_w <= 0:
                continue
            expected += evidence_w
            if d in (t.get("dimension_scores") or {}):
                rows.append((float(t["dimension_scores"][d]), evidence_w))
                evaluated += evidence_w
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


def hierarchical_bootstrap(
    *,
    templates: list[dict[str, Any]],
    runs_by_instance: dict[str, list[dict[str, Any]]],
    profile: dict[str, Any],
    resamples: int,
    seed: int | str,
    confidence_level: float = 0.95,
) -> dict[str, Any]:
    """Fast hierarchical bootstrap over precomputed per-repetition sufficient statistics.

    The resampling hierarchy remains:
      Template -> Instance -> paired Repetition.
    Full/Ablation conditions for a repetition are reduced together before bootstrap,
    so causal pairs cannot be split by resampling.
    """
    rng = random.Random(str(seed))
    templates_by_id = {t["id"]: t for t in templates}

    # Precompute compact repetition summaries once. This makes 10k resamples practical.
    rep_stats: dict[str, list[dict[str, Any]]] = defaultdict(list)
    instance_template: dict[str, str] = {}
    for iid, runs in runs_by_instance.items():
        if not runs:
            continue
        tid = runs[0]["template_id"]
        instance_template[iid] = tid
        reps = sorted({int(r["repetition"]) for r in runs if r.get("condition") == "full"})
        scenario = templates_by_id[tid]
        for rep in reps:
            rr = [r for r in runs if int(r["repetition"]) == rep]
            validate_causal_pairs(rr)
            full = next((r for r in rr if r.get("condition") == "full"), None)
            if full is None:
                continue
            dims: dict[str, float] = {}
            for d in scenario.get("dimensions", []):
                if d == CAUSAL_DIM:
                    continue
                x = weighted_probe_score(full, dimension=d)
                dims[d] = float(full.get("scenario_score", 0.0)) if x is None else x
            metrics = paired_causal_metrics(rr, ablation_tolerances(scenario))
            cscore, _ = causal_score01(metrics)
            if cscore is not None and CAUSAL_DIM in scenario.get("dimensions", []):
                dims[CAUSAL_DIM] = cscore
            rep_stats[iid].append({
                "dimensions": dims,
                "metrics": {m["name"]: float(m["value"]) for m in metrics},
            })

    instance_ids_by_template: dict[str, list[str]] = defaultdict(list)
    for iid, tid in instance_template.items():
        if rep_stats.get(iid):
            instance_ids_by_template[tid].append(iid)

    def sample_instance(iid: str) -> tuple[dict[str, float], dict[str, float]]:
        reps = rep_stats[iid]
        sampled = [rng.choice(reps) for _ in reps]
        dim_names = {d for r in sampled for d in r["dimensions"]}
        metric_names = {m for r in sampled for m in r["metrics"]}
        dims = {d: mean([r["dimensions"][d] for r in sampled if d in r["dimensions"]]) for d in dim_names}
        metrics = {m: mean([r["metrics"][m] for r in sampled if m in r["metrics"]]) for m in metric_names}
        # Recompute causal dimension from the repetition-aggregated causal components.
        crows = [{"name": k, "value": v} for k, v in metrics.items()]
        cscore, _ = causal_score01(crows)
        if cscore is not None:
            dims[CAUSAL_DIM] = cscore
        return dims, metrics

    mib_samples: list[float] = []
    dim_samples: dict[str, list[float]] = defaultdict(list)
    causal_samples: dict[str, list[float]] = defaultdict(list)

    tids = [t["id"] for t in templates if instance_ids_by_template.get(t["id"])]
    for _ in range(resamples):
        # First stage: instance + repetition resampling inside each original Template.
        synthetic: dict[str, dict[str, Any]] = {}
        for tid in tids:
            ids = instance_ids_by_template[tid]
            sampled_ids = [rng.choice(ids) for _ in ids]
            inst_rows = [sample_instance(iid) for iid in sampled_ids]
            dim_names = {d for dims, _ in inst_rows for d in dims}
            metric_names = {m for _, metrics in inst_rows for m in metrics}
            synthetic[tid] = {
                "dimensions": {d: 100.0 * mean([dims[d] for dims, _ in inst_rows if d in dims]) for d in dim_names},
                "metrics": {m: mean([metrics[m] for _, metrics in inst_rows if m in metrics]) for m in metric_names},
                "weights": (templates_by_id[tid].get("scoring") or {}).get("dimension_weights") or {},
            }

        # Second stage: Template resampling independently inside each Dimension.
        boot_dims = []
        for d, spec in (profile.get("dimensions") or {}).items():
            candidates = [tid for tid in tids if d in synthetic[tid]["dimensions"] and float(synthetic[tid]["weights"].get(d, 0.0)) > 0]
            if not candidates:
                score = 0.0
            else:
                selected = [rng.choice(candidates) for _ in candidates]
                rows = [(float(synthetic[tid]["dimensions"][d]), float(synthetic[tid]["weights"][d])) for tid in selected]
                denom = math.fsum(w for _, w in rows)
                score = math.fsum(s * w for s, w in rows) / denom if denom else 0.0
            dim_samples[d].append(score)
            boot_dims.append({"dimension": d, "score": score, "weight": float(spec["weight"]), "coverage": 1.0 if candidates else 0.0})
        mib_samples.append(_profile_score(boot_dims))

        # Causal diagnostics are also Template-first and causal-Template resampled.
        # Sorted: this loop draws from the shared RNG, so iteration order decides
        # which resamples each metric receives. Set order is hash-dependent and
        # varies per process and per Python version, which would make the
        # reported confidence intervals irreproducible.
        names = {m for tid in tids for m in synthetic[tid]["metrics"]}
        for name in sorted(names):
            candidates = [tid for tid in tids if name in synthetic[tid]["metrics"] and float(synthetic[tid]["weights"].get(CAUSAL_DIM, 0.0)) > 0]
            if not candidates:
                continue
            selected = [rng.choice(candidates) for _ in candidates]
            rows = [(float(synthetic[tid]["metrics"][name]), float(synthetic[tid]["weights"][CAUSAL_DIM])) for tid in selected]
            denom = math.fsum(w for _, w in rows)
            causal_samples[name].append(math.fsum(v * w for v, w in rows) / denom if denom else 0.0)

    method = "hierarchical_bootstrap_percentile"
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
        },
        "mib_score": {
            "value": mean(mib_samples),
            "ci": ci_percentile(mib_samples, confidence_level, method, resamples, seed),
            "n": len(mib_samples),
        },
        "dimensions": [
            {"dimension": d, "value": mean(xs), "ci": ci_percentile(xs, confidence_level, method, resamples, seed)}
            for d, xs in sorted(dim_samples.items())
        ],
        "causal_metrics": [
            {"name": name, "value": mean(xs), "ci": ci_percentile(xs, confidence_level, "paired_hierarchical_bootstrap_percentile", resamples, seed)}
            for name, xs in sorted(causal_samples.items())
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
) -> dict[str, Any]:
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
    dims = dimension_aggregates(template_aggs, profile)
    base_score = _profile_score(dims)
    required_coverage = float(profile.get("required_coverage", 1.0))
    by_dim_cov = {d["dimension"]: float(d["coverage"]) for d in dims}
    profile_cov = math.fsum(float(d["weight"]) * float(d["coverage"]) for d in dims)
    profile_eligible = profile_cov + 1e-12 >= required_coverage
    causal = aggregate_benchmark_causal_metrics(instances_by_template, templates_by_id)

    failed_probe_attempts = sum(1 for r in all_runs for p in r.get("probe_results", []) if p.get("outcome") == "execution_failure")
    scheduled_probe_attempts = sum(len(r.get("probe_results", [])) for r in all_runs)
    warnings = []
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
            "unsupported_required_weight": 0.0,
            "total_required_weight": 1.0,
            "unsupported_rate": 0.0,
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
            "unsupported_required_templates": [],
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
    all_instances: list[dict[str, Any]] = []
    all_runs: list[dict[str, Any]] = []
    templates_by_id = {t["id"]: t for t in templates}
    expected_ids = set(profile.get("required_templates") or templates_by_id)
    missing = sorted(expected_ids - set(templates_by_id))
    if missing:
        raise ValueError(f"profile requires missing Templates: {missing}")

    for template in templates:
        vr = validate_scenario(template, schema)
        if not vr.valid:
            raise ValueError(f"Template {template['id']} invalid: {vr.errors}")
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
                validate_causal_pairs(runs)
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
        agent_descriptor=describe_agent_factory(agent_factory),
        statistics=stats,
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
    templates_by_id = {t["id"]: t for t in templates}
    expected_ids = set(profile.get("required_templates") or templates_by_id)
    missing_templates = sorted(expected_ids - set(templates_by_id))
    if missing_templates:
        raise ValueError(f"profile requires missing Templates: {missing_templates}")
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

    all_runs: list[dict[str, Any]] = []
    for instance in instances:
        vr = validate_scenario(instance, schema)
        if not vr.valid:
            raise ValueError(f"Hidden instance {instance.get('id')} invalid: {vr.errors}")
        tid = (instance.get("instantiation") or {}).get("template_id", instance.get("id"))
        if tid not in templates_by_id:
            raise ValueError(f"Hidden instance references unknown Template: {tid}")
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
            validate_causal_pairs(runs)
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
        agent_descriptor=describe_agent_factory(agent_factory),
        statistics=stats,
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
