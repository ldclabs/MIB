"""Shared scoring primitives and the single implementation of every aggregation formula.

Kept free of Runner/report imports so the single-Scenario report path, the pack
aggregation path, the bootstrap, ``verify-score`` and the calibration harness all
use one implementation of each formula (MIB-Specification §6–§7).
"""

from __future__ import annotations

import math
from collections import defaultdict
from typing import Any

CAUSAL_DIM = "causal_memory_impact"
HMB = "headroom_normalized_memory_benefit"
IMS = "irrelevant_memory_stability"
HRS = "harm_resistance"

# MIB-Specification §7.6 component weights.
CAUSAL_WEIGHTS: dict[str, float] = {HMB: 0.50, IMS: 0.20, HRS: 0.30}
# MIB-Specification §7.2: an ablated condition this close to the ceiling has no headroom.
HEADROOM_EPSILON = 0.02

# Probe outcomes that stay in the denominator (``fail_probe`` execution policy).
SCORED_OUTCOMES = {"scored", "execution_failure"}

CONDITION_BY_ABLATION_KIND = {
    "relevant_memory": "relevant_ablation",
    "irrelevant_memory": "irrelevant_ablation",
    "no_memory": "no_memory",
    "stale_memory": "stale_memory",
    "harmful_memory": "harmful_memory",
    "counterexample": "counterexample",
}


def mean(values: list[float]) -> float:
    # fsum, not sum: aggregation runs over many small weighted terms and every
    # path (report, pack, bootstrap, calibration) must agree to the last bit.
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
    """MIB-Specification §8.2: percentile interval of bootstrap draws."""
    alpha = 1.0 - level
    return {
        "level": level,
        "lower": percentile(values, alpha / 2.0),
        "upper": percentile(values, 1.0 - alpha / 2.0),
        "method": method,
        "resamples": resamples,
        "seed": seed,
    }


def weighted_mean(rows: list[tuple[float, float]]) -> float | None:
    denom = math.fsum(w for _, w in rows)
    if denom <= 0:
        return None
    return math.fsum(s * w for s, w in rows) / denom


def ablation_tolerances(scenario: dict[str, Any]) -> dict[str, float]:
    """Per-ablation tolerance declared by a Scenario, keyed by ablation id."""
    return {
        a["id"]: float(a.get("tolerance") or 0.0)
        for a in (scenario.get("ablations") or [])
        if a.get("id") is not None
    }


def run_tolerances(runs: list[dict[str, Any]]) -> dict[str, float]:
    """Tolerances carried on Run Artifacts, so a report can be re-verified without the Scenario."""
    return {
        str(r["ablation_id"]): float(r.get("ablation_tolerance") or 0.0)
        for r in runs
        if r.get("ablation_id") is not None
    }


def tolerant_stability(delta: float, tolerance: float) -> float:
    """MIB-Specification §7.3: ``IMS_tau = 1 - max(0, |F-I| - tau) / (1 - tau)``, clamped.

    Stochastic wobble below the Scenario-declared tolerance is not interference.
    """
    tolerance = min(max(float(tolerance), 0.0), 0.99)
    excess = max(0.0, abs(float(delta)) - tolerance)
    return max(0.0, min(1.0, 1.0 - excess / (1.0 - tolerance)))


def tolerant_harm_resistance(harm: float, tolerance: float) -> float:
    """MIB-Specification §7.4: ``HRS_tau = 1 - max(0, C-H - tau) / (1 - tau)``, clamped."""
    tolerance = min(max(float(tolerance), 0.0), 0.99)
    excess = max(0.0, float(harm) - tolerance)
    return max(0.0, min(1.0, 1.0 - excess / (1.0 - tolerance)))


def scenario_score_from_probes(probe_results: list[dict[str, Any]]) -> float:
    """MIB-Specification §6.2: weighted mean over scored Probes.

    ``fail_probe`` is the reference execution policy, so an execution failure
    remains a zero-score Probe with its original weight; dropping it would let a
    partially failing Agent average only its successful attempts.
    """
    rows = [
        (float(p.get("score", 0.0)), float(p.get("weight", 1.0)))
        for p in probe_results
        if p.get("outcome") in SCORED_OUTCOMES
    ]
    return weighted_mean(rows) or 0.0


def weighted_probe_score(
    run: dict[str, Any], dimension: str | None = None, probe_ids: set[str] | None = None
) -> float | None:
    rows = []
    for p in run.get("probe_results", []):
        if p.get("outcome") not in SCORED_OUTCOMES:
            continue
        if probe_ids is not None and p["probe_id"] not in probe_ids:
            continue
        if dimension is not None:
            dims = p.get("dimensions") or []
            if dims and dimension not in dims:
                continue
        rows.append((float(p.get("score", 0.0)), float(p.get("weight", 1.0))))
    return weighted_mean(rows) if rows else None


def validate_causal_pairs(runs: list[dict[str, Any]]) -> tuple[bool, list[str], list[str]]:
    """Validate that every intervention run has a same-repetition full control (MIB-Specification §7.7)."""
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


def _scored_probe_ids(run: dict[str, Any]) -> set[str]:
    return {
        str(p["probe_id"]) for p in run.get("probe_results", [])
        if p.get("outcome") in SCORED_OUTCOMES and float(p.get("weight", 1.0)) > 0
    }


def paired_causal_metrics(runs: list[dict[str, Any]], tolerances: dict[str, float] | None = None) -> list[dict[str, Any]]:
    """Compute paired causal metrics, preserving repetition pairing and Probe subsets.

    ``tolerances`` maps ablation id to the Scenario-declared tolerance used by
    the tolerant IMS/HRS forms in MIB-Specification §7.3 and 62.  When omitted, the
    tolerances carried on the Run Artifacts are used, so a published report can
    be re-verified without the Scenario body.
    """
    tolerances = run_tolerances(runs) if tolerances is None else tolerances
    full_by_rep = {int(r["repetition"]): r for r in runs if r.get("condition") == "full"}
    benefits: list[tuple[float, str]] = []
    hmb: list[float] = []
    ims: list[float] = []
    harms: list[float] = []
    hrs: list[float] = []

    # Relevant-memory Ablation is the primary causal reference (MIB-Specification §7.1).
    # No-memory is a fallback only for Probes that have no relevant Ablation in
    # the same paired repetition; averaging both would double-count the same
    # causal unit.
    relevant_probe_ids_by_rep: dict[int, set[str]] = defaultdict(set)
    for variant in runs:
        if variant.get("condition") != "relevant_ablation":
            continue
        if not variant.get("validity", {}).get("causal_pair_valid", True):
            continue
        relevant_probe_ids_by_rep[int(variant["repetition"])].update(_scored_probe_ids(variant))

    for variant in runs:
        cond = variant.get("condition")
        if cond == "full" or not variant.get("validity", {}).get("causal_pair_valid", True):
            continue
        full = full_by_rep.get(int(variant["repetition"]))
        if not full:
            continue
        probe_ids = _scored_probe_ids(variant)
        if cond == "no_memory":
            probe_ids -= relevant_probe_ids_by_rep.get(int(variant["repetition"]), set())
        if not probe_ids:
            continue
        f = weighted_probe_score(full, probe_ids=probe_ids)
        v = weighted_probe_score(variant, probe_ids=probe_ids)
        if f is None or v is None:
            continue
        tau = tolerances.get(str(variant.get("ablation_id")), 0.0)
        if cond in {"relevant_ablation", "no_memory"}:
            delta = f - v
            benefits.append((delta, cond))
            denom = 1.0 - v
            if denom > HEADROOM_EPSILON:
                hmb.append(max(0.0, delta) / denom)
        elif cond == "irrelevant_ablation":
            ims.append(tolerant_stability(f - v, tau))
        elif cond in {"harmful_memory", "stale_memory"}:
            harm = max(0.0, f - v)
            harms.append(harm)
            hrs.append(tolerant_harm_resistance(harm, tau))
        elif cond == "counterexample":
            # A generic counterexample ablation demonstrates applicability
            # sensitivity, but it is not the standardized Negative Transfer
            # control from MIB-Specification §7.8.  Do not mislabel it.
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
            "name": HMB, "value": mean(hmb), "unit": "normalized",
            "scope": "scenario_instance", "reference_condition": "full", "comparison_condition": "relevant_ablation",
            "eligible_n": len(hmb), "total_n": len(benefits), "coverage": len(hmb) / len(benefits) if benefits else 0.0,
        })
    if ims:
        out.append({
            "name": IMS, "value": mean(ims), "unit": "normalized",
            "scope": "scenario_instance", "reference_condition": "full", "comparison_condition": "irrelevant_ablation",
            "eligible_n": len(ims), "total_n": len(ims), "coverage": 1.0,
        })
    if harms:
        out.extend([
            {"name": "memory_harm", "value": mean(harms), "unit": "percentage_points", "scope": "scenario_instance", "reference_condition": "full", "comparison_condition": "harmful_memory", "eligible_n": len(harms), "total_n": len(harms), "coverage": 1.0},
            {"name": HRS, "value": mean(hrs), "unit": "normalized", "scope": "scenario_instance", "reference_condition": "full", "comparison_condition": "harmful_memory", "eligible_n": len(hrs), "total_n": len(hrs), "coverage": 1.0},
        ])
    mb = next((m["value"] for m in out if m["name"] == "memory_benefit"), None)
    mh = next((m["value"] for m in out if m["name"] == "memory_harm"), None)
    if mb is not None and mh is not None:
        out.append({"name": "net_memory_gain", "value": mb - mh, "unit": "percentage_points", "scope": "scenario_instance"})
    return out


def causal_score01(metrics: list[dict[str, Any]]) -> tuple[float | None, dict[str, float]]:
    """MIB-Specification §7.6: Causal Memory Impact for one paired unit.

    ``CausalScore = HMB · (0.5 + 0.2·IMS + 0.3·HRS) / (0.5 + Σ present weights)``

    Stability and harm-resistance credit is scaled by the demonstrated benefit.
    Without the gate a memory-blind Agent scores IMS = HRS = 1 trivially and
    earns 50–100 on a dimension that asks whether memory made a difference.
    The dimension is undefined (``None``) when no relevant / no-memory pair with
    measurable headroom exists; IMS and HRS remain reported as raw diagnostics.
    """
    by = {m["name"]: float(m["value"]) for m in metrics}
    if HMB not in by:
        return None, {}
    hmb = by[HMB]
    components = {HMB: hmb}
    numer = CAUSAL_WEIGHTS[HMB]
    denom = CAUSAL_WEIGHTS[HMB]
    for name in (IMS, HRS):
        if name in by:
            components[name] = by[name]
            numer += CAUSAL_WEIGHTS[name] * by[name]
            denom += CAUSAL_WEIGHTS[name]
    return max(0.0, min(1.0, hmb * numer / denom)), components


def condition_scores(runs: list[dict[str, Any]]) -> dict[str, float]:
    buckets: dict[str, list[float]] = defaultdict(list)
    for r in runs:
        buckets[r["condition"]].append(float(r.get("scenario_score", 0.0)))
    return {k: mean(v) for k, v in buckets.items()}


def instance_dimension_scores(
    dimensions: list[str], full_runs: list[dict[str, Any]], metrics: list[dict[str, Any]]
) -> dict[str, float]:
    """MIB-Specification §6.3: Probe-tag dimension scores from full runs; causal from paired metrics."""
    out: dict[str, float] = {}
    for d in dimensions:
        if d == CAUSAL_DIM:
            continue
        vals = []
        for fr in full_runs:
            x = weighted_probe_score(fr, dimension=d)
            vals.append(float(fr.get("scenario_score", 0.0)) if x is None else x)
        out[d] = mean(vals)
    if CAUSAL_DIM in dimensions:
        cscore, _ = causal_score01(metrics)
        if cscore is not None:
            out[CAUSAL_DIM] = cscore
    return out


def build_instance_aggregate(scenario: dict[str, Any], runs: list[dict[str, Any]]) -> dict[str, Any]:
    """One Scenario Instance aggregate (MIB-Specification §6.3, §7.6).

    Causal-pair validity is written onto each run's ``validity`` and is reported
    by the caller as a warning; it never masquerades as a metric.
    """
    full_runs = [r for r in runs if r.get("condition") == "full"]
    if not full_runs:
        raise ValueError("Scenario Instance requires at least one full run")
    _, pair_ids, _ = validate_causal_pairs(runs)
    metrics = paired_causal_metrics(runs, ablation_tolerances(scenario))
    dimensions = instance_dimension_scores(list(scenario.get("dimensions", [])), full_runs, metrics)
    seed = full_runs[0].get("instance_seed")
    return {
        "scenario_instance_id": full_runs[0]["scenario_instance_id"],
        "template_id": full_runs[0]["template_id"],
        **({"instance_seed": seed} if seed is not None else {}),
        "full_score": mean([float(r.get("scenario_score", 0.0)) for r in full_runs]),
        "dimension_scores": dimensions,
        "condition_scores": condition_scores(runs),
        "repetitions": len(full_runs),
        "causal_pair_ids": pair_ids,
        "causal_metrics": metrics,
    }


def instance_pair_notes(runs: list[dict[str, Any]]) -> list[str]:
    return validate_causal_pairs(runs)[2]
