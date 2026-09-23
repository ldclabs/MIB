"""The shared score functional used by execution, comparisons and verification."""
from __future__ import annotations

import copy
import math
from collections import defaultdict
from typing import Any

from .scoring import CAUSAL_DIM, mean

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
    counts: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    for tid, instances in instances_by_template.items():
        per_name: dict[str, list[float]] = defaultdict(list)
        for i in instances:
            for m in i.get("causal_metrics", []):
                per_name[m["name"]].append(float(m["value"]))
                counts[m['name']][0] += int(m.get('eligible_n', 0))
                counts[m['name']][1] += int(m.get('total_n', 0))
        # v0.2: causal metrics are diagnostics.  A Template that carries no causal
        # evidence weight still contributes, with unit weight.
        evidence_w = float(((templates_by_id[tid].get("scoring") or {}).get("dimension_weights") or {}).get(CAUSAL_DIM, 0.0)) or 1.0
        for name, vals in per_name.items():
            template_metric_values[name].append((mean(vals), evidence_w))
    out = []
    unit_map = {
        "memory_benefit": "normalized_delta",
        "memory_harm": "normalized_delta",
        "memory_harm_effect": "normalized_delta",
        "negative_transfer_effect": "normalized_delta",
        "net_memory_gain": "normalized_delta",
        "consolidation_benefit": "normalized_delta",
        "headroom_normalized_memory_benefit": "normalized",
        "irrelevant_memory_stability": "normalized",
        "harm_resistance": "normalized",
        "negative_transfer": "normalized_delta",
        "learning_gain": "normalized_delta",
    }
    for name, rows in sorted(template_metric_values.items()):
        denom = math.fsum(w for _, w in rows)
        value = math.fsum(v * w for v, w in rows) / denom if denom else 0.0
        out.append({
            "name": name,
            "value": value,
            "unit": unit_map.get(name, "normalized"),
            "scope": "benchmark",
            "eligible_n": counts[name][0],
            "total_n": counts[name][1],
            "coverage": counts[name][0] / counts[name][1] if counts[name][1] else 0.0,
        })
        if name in {'content_tracking_rate', 'stale_adoption_rate'}:
            totals = tracking_totals([i for values in instances_by_template.values() for i in values])
            out[-1].update(eligible_n=totals['eligible_n'], total_n=totals['total_n'],
                           coverage=totals['eligible_n'] / totals['total_n'] if totals['total_n'] else 0.0,
                           notes='Program-balanced mean of eligible Instance rates; counts are physical changed-probe pairs.')
    mb = next((m["value"] for m in out if m["name"] == "memory_benefit"), None)
    mh = next((m["value"] for m in out if m["name"] == "memory_harm"), None)
    if mb is not None and mh is not None and not any(m["name"] == "net_memory_gain" for m in out):
        out.append({"name": "net_memory_gain", "value": mb - mh, "unit": "normalized_delta", "scope": "benchmark"})
    return out


def profile_score(dimensions: list[dict[str, Any]]) -> float:
    rows = [(float(d["score"]), float(d["weight"])) for d in dimensions if float(d.get("weight", 0.0)) > 0]
    denom = math.fsum(w for _, w in rows)
    return math.fsum(s * w for s, w in rows) / denom if denom else 0.0


def canonical_instances(instances: list[dict[str, Any]], profile: dict[str, Any]) -> list[dict[str, Any]]:
    rung = profile.get('canonical_rung')
    return [i for i in instances if rung is None or i.get('rung') is None or int(i['rung']) == int(rung)]


def tracking_totals(instances: list[dict[str, Any]]) -> dict[str, int]:
    return {key: sum(int(i.get('counterfactual_counts', {}).get(key, 0)) for i in instances)
            for key in ['eligible_n', 'total_n', 'successes']}


def score_aggregates(instances: list[dict[str, Any]], templates: list[dict[str, Any]], profile: dict[str, Any]) -> dict[str, Any]:
    by_template: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for instance in canonical_instances(instances, profile):
        by_template[instance['template_id']].append(instance)
    template_rows = [build_template_aggregate(t, by_template[t['id']]) for t in templates if by_template[t['id']]]
    dimensions = dimension_aggregates(template_rows, profile, templates)
    metrics = aggregate_benchmark_causal_metrics(by_template, {t['id']: t for t in templates})
    return {'templates': template_rows, 'dimensions': dimensions, 'causal_metrics': metrics, 'score': profile_score(dimensions)}
