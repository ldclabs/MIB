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
    "counterfactual_content": "counterfactual_content",
    "no_maintenance": "no_maintenance",
    "negative_transfer": "negative_transfer_control",
}

# Failure codes that attribute a wrong answer or action to memory rather than to reasoning (§7.9).
MEMORY_INDUCED_CODES = frozenset({
    "stale_memory_adoption", "correction_loss", "authority_confusion", "memory_hallucination", "source_confusion",
    "identity_mismatch", "negative_transfer", "error_recurrence", "irrelevant_memory_interference", "premature_trigger",
    "self_model_drift",
})


def instance_key(scenario: dict[str, Any]) -> str:
    """One id per (Scenario, seed, ladder rung): the unit every run is grouped under."""
    inst = scenario.get("instantiation") or {}
    key = f"{scenario['id']}:{inst.get('seed', 'instance')}"
    if inst.get("rung") is not None:
        key += f":r{int(inst['rung'])}"
    return key


def rung_of_key(key: str) -> int | None:
    """The ladder rung encoded in an instance key, or ``None`` for static Scenarios."""
    head, sep, tail = key.rpartition(":r")
    return int(tail) if sep and tail.isdigit() else None


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


def ci_bca(values: list[float], point: float, jackknife: list[float], level: float, resamples: int, seed: int | str) -> dict[str, Any]:
    """MIB-Specification §8.2: bias-corrected and accelerated interval (Efron).

    ``z0`` corrects the median bias of the bootstrap distribution around the
    point estimate; ``a`` (from leave-one-unit-out jackknife estimates) corrects
    for a standard error that changes with the estimate.  Degenerate draws (all
    equal, or the point estimate outside the draws) fall back to the percentile
    interval and say so in ``method``.
    """
    from statistics import NormalDist
    alpha = 1.0 - level
    if not values:
        return {"level": level, "lower": 0.0, "upper": 0.0, "method": "bca", "resamples": resamples, "seed": seed}
    below = sum(1 for v in values if v < point)
    if below == 0 or below == len(values) or len(set(values)) == 1 or len(jackknife) < 2:
        return ci_percentile(values, level, "hierarchical_bootstrap_percentile", resamples, seed)
    nd = NormalDist()
    z0 = nd.inv_cdf(below / len(values))
    jmean = math.fsum(jackknife) / len(jackknife)
    num = math.fsum((jmean - j) ** 3 for j in jackknife)
    den = 6.0 * (math.fsum((jmean - j) ** 2 for j in jackknife) ** 1.5)
    a = num / den if den > 0 else 0.0
    def adjusted(q: float) -> float:
        z = nd.inv_cdf(q)
        t = z0 + (z0 + z) / (1.0 - a * (z0 + z)) if a * (z0 + z) != 1.0 else z0 + z
        return min(max(nd.cdf(t), 0.0), 1.0)
    return {
        "level": level,
        "lower": percentile(values, adjusted(alpha / 2.0)),
        "upper": percentile(values, adjusted(1.0 - alpha / 2.0)),
        "method": "bca",
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
    tracking: list[float] = []
    tracking_total = 0
    stale: list[float] = []
    consolidation: list[float] = []
    nt: list[float] = []
    ntr: list[float] = []
    nt_rate: list[float] = []

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
        elif cond == "counterfactual_content":
            # MIB-Specification §7.2: does the answer *track* a changed event?
            # Only pairs whose full Probe was right are eligible; a wrong answer
            # under both conditions says nothing about tracking.
            full_scores = {p["probe_id"]: float(p.get("score", 0.0)) for p in full.get("probe_results", [])
                           if p.get("outcome") in SCORED_OUTCOMES}
            variant_rows = {p["probe_id"]: p for p in variant.get("probe_results", [])
                            if p.get("outcome") in SCORED_OUTCOMES and float(p.get("weight", 1.0)) > 0}
            for pid in sorted(probe_ids):
                tracking_total += 1
                if full_scores.get(pid, 0.0) < 1.0:
                    continue
                row = variant_rows.get(pid, {})
                tracking.append(1.0 if float(row.get("score", 0.0)) >= 1.0 else 0.0)
                stale.append(1.0 if (row.get("counterfactual") or {}).get("stale") else 0.0)
        elif cond == "no_maintenance":
            consolidation.append(f - v)
        elif cond == "negative_transfer_control":
            # MIB-Specification §7.8: the non-matching task without the skill memory (v)
            # versus with it (f).  Memory that hurts the non-matching task is negative transfer.
            harm = max(0.0, v - f)
            nt.append(harm)
            ntr.append(tolerant_harm_resistance(harm, tau))
            rows = [p for p in full.get("probe_results", [])
                    if p["probe_id"] in probe_ids and p.get("outcome") in SCORED_OUTCOMES]
            if rows:
                nt_rate.append(mean([1.0 if "negative_transfer" in (p.get("failure_codes") or []) else 0.0 for p in rows]))
        elif cond == "counterexample":
            # A generic counterexample ablation demonstrates applicability
            # sensitivity, but it is not the standardized Negative Transfer
            # control from MIB-Specification §7.8.  Do not mislabel it.
            pass

    out: list[dict[str, Any]] = []
    if tracking_total:
        out.append({
            "name": "content_tracking_rate", "value": mean(tracking) if tracking else 0.0, "unit": "normalized",
            "scope": "scenario_instance", "reference_condition": "full", "comparison_condition": "counterfactual_content",
            "eligible_n": len(tracking), "total_n": tracking_total, "coverage": len(tracking) / tracking_total,
        })
        out.append({
            "name": "stale_adoption_rate", "value": mean(stale) if stale else 0.0, "unit": "normalized",
            "scope": "scenario_instance", "reference_condition": "full", "comparison_condition": "counterfactual_content",
            "eligible_n": len(stale), "total_n": tracking_total, "coverage": len(stale) / tracking_total,
        })
    if consolidation:
        out.append({
            "name": "consolidation_benefit", "value": mean(consolidation), "unit": "percentage_points",
            "scope": "scenario_instance", "reference_condition": "full", "comparison_condition": "no_maintenance",
            "eligible_n": len(consolidation), "total_n": len(consolidation), "coverage": 1.0,
        })
    if nt:
        out.append({
            "name": "negative_transfer", "value": mean(nt), "unit": "percentage_points",
            "scope": "scenario_instance", "reference_condition": "full", "comparison_condition": "negative_transfer_control",
            "eligible_n": len(nt), "total_n": len(nt), "coverage": 1.0,
        })
        out.append({
            "name": "negative_transfer_resistance", "value": mean(ntr), "unit": "normalized",
            "scope": "scenario_instance", "reference_condition": "full", "comparison_condition": "negative_transfer_control",
            "eligible_n": len(ntr), "total_n": len(ntr), "coverage": 1.0,
        })
        if nt_rate:
            out.append({
                "name": "negative_transfer_rate", "value": mean(nt_rate), "unit": "normalized",
                "scope": "scenario_instance", "reference_condition": "full", "comparison_condition": "full",
                "eligible_n": len(nt_rate), "total_n": len(nt_rate), "coverage": 1.0,
            })
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


def recurrence_metrics(full_runs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """MIB-Specification §7.9: error recurrence over eligible lived-failure opportunities."""
    rows = [
        1.0 if (p.get("recurrence") or {}).get("recurred") else 0.0
        for r in full_runs for p in r.get("probe_results", [])
        if p.get("outcome") in SCORED_OUTCOMES and (p.get("recurrence") or {}).get("eligible")
    ]
    if not rows:
        return []
    err = mean(rows)
    base = {"unit": "normalized", "scope": "scenario_instance", "reference_condition": "full", "comparison_condition": "full",
            "eligible_n": len(rows), "total_n": len(rows), "coverage": 1.0}
    return [
        {"name": "error_recurrence_rate", "value": err, **base},
        {"name": "error_avoidance_score", "value": 1.0 - err, **base},
    ]


def _scored_full_probes(full_runs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [p for r in full_runs for p in r.get("probe_results", []) if p.get("outcome") in SCORED_OUTCOMES]


def behaviour_metrics(full_runs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """MIB-Specification §7.9: diagnostics read off full runs alone.

    Each is undefined (absent) when no Probe is eligible: eligibility comes
    from the Probe kind (``historical``, ``audit``, ``self``) or from the traps
    the Oracle declared (``authority_confusion``); the memory-induced error
    rate is over every scored Probe.
    """
    probes = _scored_full_probes(full_runs)
    base = {"unit": "normalized", "scope": "scenario_instance", "reference_condition": "full", "comparison_condition": "full"}
    out: list[dict[str, Any]] = []

    def rate(name: str, rows: list[dict[str, Any]], hit) -> None:
        if rows:
            out.append({"name": name, "value": mean([1.0 if hit(p) else 0.0 for p in rows]), **base,
                        "eligible_n": len(rows), "total_n": len(probes), "coverage": len(rows) / len(probes) if probes else 0.0})

    def accuracy(name: str, kind: str) -> None:
        rows = [p for p in probes if p.get("probe_kind") == kind]
        if rows:
            out.append({"name": name, "value": mean([float(p.get("score", 0.0)) for p in rows]), **base,
                        "eligible_n": len(rows), "total_n": len(probes), "coverage": len(rows) / len(probes) if probes else 0.0})

    rate("memory_induced_error_rate", probes, lambda p: bool(MEMORY_INDUCED_CODES & set(p.get("failure_codes") or [])))
    rate("authority_confusion_rate", [p for p in probes if "authority_confusion" in (p.get("traps") or [])],
         lambda p: "authority_confusion" in (p.get("failure_codes") or []))
    accuracy("historical_fidelity", "historical")
    accuracy("source_attribution_accuracy", "audit")
    accuracy("self_limitation_continuity", "self")
    return out


def learning_metrics(full_runs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """MIB-Specification §7.9: learning gain and area under the learning curve from lived trials.

    A run with at least two trial results is one learning curve; the gain is
    last minus first trial score, the area is the mean trial score.  Trials are
    diagnostics: they never enter a capability score.
    """
    gains: list[float] = []
    areas: list[float] = []
    for r in full_runs:
        trials = sorted(r.get("task_results") or [], key=lambda t: int(t.get("index", 0)))
        if len(trials) < 2:
            continue
        scores = [float(t.get("score", 0.0)) for t in trials]
        gains.append(scores[-1] - scores[0])
        areas.append(mean(scores))
    if not gains:
        return []
    base = {"scope": "scenario_instance", "reference_condition": "full", "comparison_condition": "full",
            "eligible_n": len(gains), "total_n": len(full_runs), "coverage": len(gains) / len(full_runs)}
    return [
        {"name": "learning_gain", "value": mean(gains), "unit": "percentage_points", **base},
        {"name": "area_under_learning_curve", "value": mean(areas), "unit": "normalized", **base},
    ]


def full_run_metrics(full_runs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Every diagnostic computed from full runs only (§7.9); recomputable from a report's runs."""
    return recurrence_metrics(full_runs) + behaviour_metrics(full_runs) + learning_metrics(full_runs)


def build_instance_aggregate(scenario: dict[str, Any], runs: list[dict[str, Any]]) -> dict[str, Any]:
    """One Scenario Instance aggregate (MIB-Specification §6.3, §7.6).

    Causal-pair validity is written onto each run's ``validity`` and is reported
    by the caller as a warning; it never masquerades as a metric.
    """
    full_runs = [r for r in runs if r.get("condition") == "full"]
    if not full_runs:
        raise ValueError("Scenario Instance requires at least one full run")
    _, pair_ids, _ = validate_causal_pairs(runs)
    metrics = paired_causal_metrics(runs, ablation_tolerances(scenario)) + full_run_metrics(full_runs)
    dimensions = instance_dimension_scores(list(scenario.get("dimensions", [])), full_runs, metrics)
    seed = full_runs[0].get("instance_seed")
    inst = scenario.get("instantiation") or {}
    return {
        "scenario_instance_id": full_runs[0]["scenario_instance_id"],
        "template_id": full_runs[0]["template_id"],
        **({"instance_seed": seed} if seed is not None else {}),
        **({"rung": int(inst["rung"])} if inst.get("rung") is not None else {}),
        **({"interference_count": int(inst["interference_count"])} if inst.get("interference_count") is not None else {}),
        **({"interference_tokens": int(inst["interference_tokens"])} if inst.get("interference_tokens") is not None else {}),
        **({"distance_hours": float(inst["distance_hours"])} if inst.get("distance_hours") is not None else {}),
        "full_score": mean([float(r.get("scenario_score", 0.0)) for r in full_runs]),
        "dimension_scores": dimensions,
        "condition_scores": condition_scores(runs),
        "repetitions": len(full_runs),
        "causal_pair_ids": pair_ids,
        "causal_metrics": metrics,
    }


def retention_block(instance_aggs: list[dict[str, Any]], canonical_rung: int | None) -> list[dict[str, Any]]:
    """MIB-Specification §8: performance as a function of interference distance, per program."""
    by_template: dict[str, dict[int, list[dict[str, Any]]]] = defaultdict(lambda: defaultdict(list))
    for agg in instance_aggs:
        if agg.get("rung") is None:
            continue
        by_template[agg["template_id"]][int(agg["rung"])].append(agg)
    out = []
    for tid in sorted(by_template):
        rungs = []
        for rung in sorted(by_template[tid]):
            rows = by_template[tid][rung]
            counts = [r["interference_count"] for r in rows if r.get("interference_count") is not None]
            tokens = [int(r["interference_tokens"]) for r in rows if r.get("interference_tokens") is not None]
            hours = [float(r["distance_hours"]) for r in rows if r.get("distance_hours") is not None]
            rungs.append({
                "rung": rung, "interference_count": counts[0] if counts else None,
                **({"interference_tokens": mean(tokens)} if tokens else {}),
                **({"distance_hours": mean(hours)} if hours else {}),
                "full_score": mean([float(r["full_score"]) for r in rows]), "n": len(rows),
            })
        base = rungs[0]["full_score"]
        half: float | None = None
        beyond = True
        if base > 0:
            for prev, cur in zip(rungs, rungs[1:]):
                if cur["full_score"] <= 0.5 * base:
                    # Linear interpolation between the last rung above half and the first at/below it.
                    x0, x1 = prev["interference_count"] or prev["rung"], cur["interference_count"] or cur["rung"]
                    y0, y1 = prev["full_score"], cur["full_score"]
                    target = 0.5 * base
                    half = x0 + (x1 - x0) * ((y0 - target) / (y0 - y1)) if y0 != y1 else float(x1)
                    beyond = False
                    break
        out.append({
            "template_id": tid, "canonical_rung": canonical_rung, "rungs": rungs,
            "retention_index": mean([r["full_score"] for r in rungs]),
            "half_distance": half, "half_distance_beyond_ladder": beyond,
        })
    return out


def memory_dependence(causal_metrics: list[dict[str, Any]], profile: dict[str, Any]) -> dict[str, Any]:
    """MIB-Specification §7.10: is the capability score earned through memory?

    Eligibility uses the benchmark-level content tracking rate: a system whose
    answers do not follow a changed event was answering from priors, and its
    capability score is not a memory score.
    """
    policy = profile.get("memory_dependence") or {}
    metric_name = policy.get("metric", "content_tracking_rate")
    floor = float(policy.get("floor", 0.5))
    by = {m["name"]: m for m in causal_metrics}
    gate = by.get(metric_name)
    value = float(gate["value"]) if gate else None
    eligible: bool | None = None if value is None else value >= floor
    return {
        "content_tracking_rate": float(by["content_tracking_rate"]["value"]) if "content_tracking_rate" in by else None,
        "stale_adoption_rate": float(by["stale_adoption_rate"]["value"]) if "stale_adoption_rate" in by else None,
        "memory_benefit": float(by["memory_benefit"]["value"]) if "memory_benefit" in by else None,
        "headroom_normalized_memory_benefit": float(by[HMB]["value"]) if HMB in by else None,
        "harm_resistance": float(by[HRS]["value"]) if HRS in by else None,
        "consolidation_benefit": float(by["consolidation_benefit"]["value"]) if "consolidation_benefit" in by else None,
        "error_recurrence_rate": float(by["error_recurrence_rate"]["value"]) if "error_recurrence_rate" in by else None,
        "metric": metric_name, "floor": floor, "eligible": eligible,
        "eligible_n": int(gate.get("eligible_n", 0)) if gate else 0,
        "total_n": int(gate.get("total_n", 0)) if gate else 0,
    }


def instance_pair_notes(runs: list[dict[str, Any]]) -> list[str]:
    return validate_causal_pairs(runs)[2]
