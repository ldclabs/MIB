from __future__ import annotations

import copy
import json
import math
import random
import statistics as stats
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from .experimental.transfer_fixtures import OverTransferAgent
from .benchmark import build_instance_aggregate, validate_causal_pairs
from .calibration_baselines import BASELINE_FACTORIES
from .materialize import materialize
from .runner import run_scenario
from .scoring import mean as _mean, percentile  # noqa: F401
from .util import utc_now  # noqa: F401
from .experimental.transfer import POSITIVE_RELATIONS, parse_transfer_support
from .experimental.transfer_diagnostics import transfer_relation_aggregates
from .experimental.transfer_matrix import run_transfer_matrix
from .validation import validate_scenario


DEFAULT_THRESHOLDS = {
    "full_context_min": 0.80,
    "no_memory_max": 0.60,
    "mdi_min": 0.25,
    "baseline_span_min": 0.20,
    "irrelevant_stability_min": 0.90,
    "causal_memory_benefit_min": 0.20,
}


def mean(xs: list[float]) -> float:
    """Re-exported from ``scoring`` so calibration and pack aggregation agree."""
    return _mean(xs)


def bootstrap_ci(values: list[float], *, resamples: int, seed: str | int, level: float = 0.95) -> dict[str, Any] | None:
    """Flat percentile bootstrap over independent observations."""
    if not values:
        return None
    rng = random.Random(str(seed))
    n_resamples = max(1, resamples)
    samples = []
    for _ in range(n_resamples):
        draw = [rng.choice(values) for _ in values]
        samples.append(mean(draw))
    alpha = 1.0 - level
    return {
        "level": level,
        "lower": percentile(samples, alpha / 2),
        "upper": percentile(samples, 1 - alpha / 2),
        "method": "instance_bootstrap_percentile",
        "resamples": n_resamples,
        "seed": seed,
    }


def hierarchical_bootstrap_ci(
    groups: list[list[float]], *, resamples: int, seed: str | int, level: float = 0.95
) -> dict[str, Any] | None:
    """Percentile bootstrap that resamples Instances, then Repetitions within them.

    Repetitions of one Scenario Instance are not independent observations: under
    the harness's own decoding lock (temperature 0, or a paired per-call seed)
    they are deterministic clones.  Treating them as independent rows shrinks
    every interval by roughly the repetition factor, so the resampling hierarchy
    must mirror the design: Instance -> Repetition, exactly as the pack-level
    bootstrap in ``benchmark.hierarchical_bootstrap`` does.
    """
    groups = [g for g in groups if g]
    if not groups:
        return None
    rng = random.Random(str(seed))
    n_resamples = max(1, resamples)
    samples = []
    for _ in range(n_resamples):
        picked = [rng.choice(groups) for _ in groups]
        draw = [mean([rng.choice(g) for _ in g]) for g in picked]
        samples.append(mean(draw))
    alpha = 1.0 - level
    return {
        "level": level,
        "lower": percentile(samples, alpha / 2),
        "upper": percentile(samples, 1 - alpha / 2),
        "method": "hierarchical_bootstrap_percentile",
        "resamples": n_resamples,
        "seed": seed,
    }


def load_private_templates(pack_root: str | Path) -> list[dict[str, Any]]:
    """Load a Scenario pack.

    The evaluator-only pack nests Templates under ``templates/``; the public dev
    pack stores them directly under Scenario-family directories.  Both layouts
    load, so the same harness can run against either without a second loader.
    """
    root = Path(pack_root)
    search_root = root / "templates" if (root / "templates").is_dir() else root
    files = sorted(f for f in search_root.rglob("MIB-*.json") if ".example-" not in f.name)
    if not files:
        raise ValueError(f"no Templates found under {search_root}")
    return [json.loads(p.read_text(encoding="utf-8")) for p in files]


def _run_full_baseline(
    *,
    template: dict[str, Any],
    schema: dict[str, Any],
    baseline_factory: Callable[[], Any],
    seeds: list[int | str],
    repetitions: int,
) -> list[dict[str, Any]]:
    rows = []
    vr = validate_scenario(template, schema)
    if not vr.valid:
        raise ValueError(f"Template {template['id']} invalid: {vr.errors}")
    for seed in seeds:
        instance = materialize(template, seed)
        vr2 = validate_scenario(instance, schema)
        if not vr2.valid:
            raise ValueError(f"Instance {template['id']}:{seed} invalid: {vr2.errors}")
        for rep in range(repetitions):
            runs = run_scenario(
                scenario=instance,
                agent_factory=baseline_factory,
                include_ablations=False,
                repetition=rep,
                agent_seed=f"cal:{seed}:{rep}",
            )
            full = next(r for r in runs if r["condition"] == "full")
            rows.append({
                "template_id": template["id"],
                "seed": seed,
                "repetition": rep,
                "score": float(full.get("scenario_score", 0.0)),
                "probe_scores": {p["probe_id"]: float(p.get("score", 0.0)) for p in full.get("probe_results", [])},
                "status": full.get("status"),
            })
    return rows


def _run_causal_fixture(
    *, template: dict[str, Any], schema: dict[str, Any], baseline_factory: Callable[[], Any],
    seeds: list[int | str], repetitions: int,
) -> list[dict[str, Any]]:
    aggs = []
    for seed in seeds:
        instance = materialize(template, seed)
        vr = validate_scenario(instance, schema)
        if not vr.valid:
            raise ValueError(f"Instance {template['id']}:{seed} invalid: {vr.errors}")
        all_runs = []
        for rep in range(repetitions):
            runs = run_scenario(
                scenario=instance,
                agent_factory=baseline_factory,
                include_ablations=True,
                repetition=rep,
                agent_seed=f"causal:{seed}:{rep}",
            )
            validate_causal_pairs(runs)
            all_runs.extend(runs)
        agg = build_instance_aggregate(instance, all_runs)
        aggs.append(agg)
    return aggs


def _metric(aggs: list[dict[str, Any]], name: str) -> float | None:
    vals = []
    for a in aggs:
        for m in a.get("causal_metrics", []):
            if m.get("name") == name:
                vals.append(float(m["value"]))
    return mean(vals) if vals else None


def _baseline_stat(rows: list[dict[str, Any]], *, bootstrap_resamples: int, bootstrap_seed: str) -> dict[str, Any]:
    vals = [float(r["score"]) for r in rows]
    # Group repetitions under their Scenario Instance seed so the interval
    # reflects the number of independent Instances, not the row count.
    by_instance: dict[Any, list[float]] = defaultdict(list)
    for r in rows:
        by_instance[r.get("seed")].append(float(r["score"]))
    groups = [by_instance[k] for k in sorted(by_instance, key=lambda x: str(x))]
    return {
        "mean": mean(vals),
        # Sample stddev: these rows are a sample of Instances, not a population.
        "stddev": stats.stdev(vals) if len(vals) > 1 else 0.0,
        "n": len(vals),
        "independent_n": len(groups),
        "ci": hierarchical_bootstrap_ci(groups, resamples=bootstrap_resamples, seed=bootstrap_seed),
        "min": min(vals) if vals else 0.0,
        "max": max(vals) if vals else 0.0,
    }


def _recommend(card: dict[str, Any], th: dict[str, float]) -> tuple[str, list[str]]:
    fc = card["metrics"]["full_context"]
    nm = card["metrics"]["no_memory"]
    mdi = card["metrics"]["memory_discriminativeness_index"]
    span = card["metrics"]["baseline_span"]
    reasons = []
    if fc < th["full_context_min"]:
        reasons.append("fixture_full_context_below_target")
    if nm > th["no_memory_max"]:
        reasons.append("no_memory_too_strong")
    if mdi < th["mdi_min"]:
        reasons.append("memory_discriminativeness_below_target")
    if span < th["baseline_span_min"]:
        reasons.append("baseline_separation_too_small")
    if not reasons:
        return "provisional_pass", []
    if nm >= 0.85 or (fc >= 0.8 and mdi < 0.10):
        return "retire_or_redesign_candidate", reasons
    return "revise_or_empirically_review", reasons


def calibrate_pack(
    *,
    templates: list[dict[str, Any]],
    schema: dict[str, Any],
    profile: dict[str, Any],
    seeds: list[int | str],
    repetitions: int = 1,
    baseline_ids: list[str] | None = None,
    bootstrap_resamples: int = 2000,
    bootstrap_seed: str | int = "mib-calibration-0.1",
    causal_baseline_id: str = "B3",
    causal_seeds: list[int | str] | None = None,
    causal_repetitions: int = 1,
    thresholds: dict[str, float] | None = None,
    baseline_factories: dict[str, Callable[[], Any]] | None = None,
    transfer_calibration: bool = True,
    transfer_thresholds: dict[str, float] | None = None,
) -> dict[str, Any]:
    factories = dict(BASELINE_FACTORIES)
    if baseline_factories:
        factories.update(baseline_factories)
    baseline_ids = baseline_ids or ["B0", "B1", "B2", "B3"]
    thresholds = {**DEFAULT_THRESHOLDS, **(thresholds or {})}
    causal_seeds = causal_seeds or seeds
    templates_by_id = {t["id"]: t for t in templates}

    unknown = [b for b in baseline_ids if b not in factories]
    if unknown:
        raise ValueError(f"unknown baseline ids: {unknown}")

    raw: dict[str, dict[str, list[dict[str, Any]]]] = defaultdict(dict)
    for bid in baseline_ids:
        factory = factories[bid]
        for t in templates:
            raw[t["id"]][bid] = _run_full_baseline(
                template=t, schema=schema, baseline_factory=factory,
                seeds=seeds, repetitions=repetitions,
            )

    causal: dict[str, list[dict[str, Any]]] = {}
    if causal_baseline_id:
        factory = factories[causal_baseline_id]
        for t in templates:
            causal[t["id"]] = _run_causal_fixture(
                template=t, schema=schema, baseline_factory=factory,
                seeds=causal_seeds, repetitions=causal_repetitions,
            )

    cards = []
    for t in templates:
        tid = t["id"]
        stats_by_b = {
            bid: _baseline_stat(
                raw[tid][bid],
                bootstrap_resamples=bootstrap_resamples,
                bootstrap_seed=f"{bootstrap_seed}:{tid}:{bid}",
            ) for bid in baseline_ids
        }
        b0 = stats_by_b.get("B0", {}).get("mean", 0.0)
        b1 = stats_by_b.get("B1", {}).get("mean", 0.0)
        b2 = stats_by_b.get("B2", {}).get("mean", 0.0)
        b3 = stats_by_b.get("B3", {}).get("mean", 0.0)
        mdi = b1 - b0
        denom = b1 - b0
        mgc_b2 = (b2 - b0) / denom if abs(denom) > 1e-12 else None
        mgc_b3 = (b3 - b0) / denom if abs(denom) > 1e-12 else None
        baseline_means = [stats_by_b[b]["mean"] for b in baseline_ids]
        caggs = causal.get(tid, [])
        cdiag = {
            "memory_benefit": _metric(caggs, "memory_benefit"),
            "headroom_normalized_memory_benefit": _metric(caggs, "headroom_normalized_memory_benefit"),
            "irrelevant_memory_stability": _metric(caggs, "irrelevant_memory_stability"),
            "memory_harm": _metric(caggs, "memory_harm"),
            "harm_resistance": _metric(caggs, "harm_resistance"),
            "net_memory_gain": _metric(caggs, "net_memory_gain"),
        }
        card = {
            "template_id": tid,
            "title": t.get("title"),
            "suite": t.get("suite"),
            "visibility": (t.get("metadata") or {}).get("visibility"),
            "dimensions": list(t.get("dimensions") or []),
            "baseline_scores": stats_by_b,
            "metrics": {
                "full_context": b1,
                "no_memory": b0,
                "memory_discriminativeness_index": mdi,
                "simple_retrieval": b2,
                "structured_agentic": b3,
                "memory_gap_closure_b2": mgc_b2,
                "memory_gap_closure_b3": mgc_b3,
                "baseline_span": max(baseline_means) - min(baseline_means),
                "structured_over_retrieval": b3 - b2,
            },
            "causal_diagnostics": cdiag,
            "gates": {
                "full_context": b1 >= thresholds["full_context_min"],
                "no_memory": b0 <= thresholds["no_memory_max"],
                "mdi": mdi >= thresholds["mdi_min"],
                "baseline_span": (max(baseline_means) - min(baseline_means)) >= thresholds["baseline_span_min"],
                "irrelevant_stability": (cdiag["irrelevant_memory_stability"] is None or cdiag["irrelevant_memory_stability"] >= thresholds["irrelevant_stability_min"]),
                "causal_sensitivity": (cdiag["memory_benefit"] is None or cdiag["memory_benefit"] >= thresholds["causal_memory_benefit_min"]),
            },
        }
        rec, reasons = _recommend(card, thresholds)
        causal_risks = []
        if cdiag["memory_benefit"] is not None and cdiag["memory_benefit"] < thresholds["causal_memory_benefit_min"]:
            causal_risks.append("relevant_ablation_low_effect")
        if cdiag["irrelevant_memory_stability"] is not None and cdiag["irrelevant_memory_stability"] < thresholds["irrelevant_stability_min"]:
            causal_risks.append("irrelevant_ablation_unstable")
        card["recommendation"] = rec
        card["reasons"] = reasons
        card["causal_risks"] = causal_risks
        cards.append(card)

    transfer_block = calibrate_transfer(
        templates=templates, schema=schema, seeds=causal_seeds,
        repetitions=causal_repetitions, baseline_id=causal_baseline_id or "B3",
        baseline_factories=baseline_factories, thresholds=transfer_thresholds,
    ) if transfer_calibration else None

    # Dimension-level baseline score surfaces: Template-first, using declared dimension evidence weights.
    dimension_matrix = []
    for d, spec in (profile.get("dimensions") or {}).items():
        row = {"dimension": d, "weight": float(spec["weight"]), "baselines": {}}
        for bid in baseline_ids:
            vals = []
            for card in cards:
                t = templates_by_id[card["template_id"]]
                w = float(((t.get("scoring") or {}).get("dimension_weights") or {}).get(d, 0.0))
                if w <= 0:
                    continue
                vals.append((float(card["baseline_scores"][bid]["mean"]), w))
            den = sum(w for _, w in vals)
            row["baselines"][bid] = sum(v*w for v,w in vals)/den if den else 0.0
        dimension_matrix.append(row)

    rec_counts: dict[str, int] = defaultdict(int)
    gate_counts: dict[str, int] = defaultdict(int)
    causal_risk_counts: dict[str, int] = defaultdict(int)
    for c in cards:
        rec_counts[c["recommendation"]] += 1
        for g, ok in c["gates"].items():
            if ok:
                gate_counts[g] += 1
        for risk in c.get("causal_risks", []):
            causal_risk_counts[risk] += 1

    # Pairwise ordering diagnostics; not used as an admission gate.  Only pairs
    # whose two baselines were actually executed are reported, so a partial
    # --baselines run stays valid instead of raising KeyError.
    def _ordering(hi: str, lo: str) -> int | None:
        if hi not in baseline_ids or lo not in baseline_ids:
            return None
        return sum(1 for c in cards if c["baseline_scores"][hi]["mean"] + 1e-12 >= c["baseline_scores"][lo]["mean"])

    ordering = {
        "B1_ge_B3": _ordering("B1", "B3"),
        "B3_ge_B2": _ordering("B3", "B2"),
        "B2_ge_B0": _ordering("B2", "B0"),
        "template_count": len(cards),
        "baselines_executed": list(baseline_ids),
    }

    actual_baselines = []
    for bid in baseline_ids:
        a = factories[bid]()
        d = a.describe()
        ext = (d.get("extensions") or {}).get("mib.calibration") or {}
        actual_baselines.append({
            "id": bid,
            "name": (d.get("implementation") or {}).get("name", bid),
            "role": ext.get("role", bid),
            "release_calibration_eligible": bool(ext.get("release_calibration_eligible", False)),
        })
    # Release eligibility requires the B0/B1 anchors to have actually run.  An
    # `all()` over an empty selection would otherwise mark a partial run eligible.
    anchor_rows = [x for x in actual_baselines if x["id"] in {"B0", "B1"}]
    release_eligible = (
        len(anchor_rows) == 2
        and all(x.get("release_calibration_eligible") for x in anchor_rows)
    )
    return {
        "mib": "0.1",
        "kind": "MIBCalibrationReport",
        "report_version": "0.1.0",
        "generated_at": utc_now(),
        "profile": {"id": profile["id"], "version": profile["version"]},
        "scenario_pack": copy.deepcopy(profile.get("scenario_pack") or {}),
        "calibration_mode": "reference_fixture",
        "release_calibration_eligible": release_eligible,
        "release_note": (
            "Reference B0-B3 are deterministic calibration fixtures. They validate scenario discrimination mechanics, "
            "but B1 is not a fixed external base-model Full Context run; official release calibration remains pending."
        ),
        "configuration": {
            "instance_seeds": list(seeds),
            "repetitions": repetitions,
            "baseline_ids": baseline_ids,
            "bootstrap_resamples": bootstrap_resamples,
            "causal_baseline_id": causal_baseline_id,
            "causal_instance_seeds": list(causal_seeds),
            "causal_repetitions": causal_repetitions,
            "thresholds": thresholds,
        },
        "baselines": actual_baselines,
        "summary": {
            "template_count": len(cards),
            "recommendations": dict(sorted(rec_counts.items())),
            "gate_pass_counts": {k: gate_counts[k] for k in sorted(gate_counts)},
            "ordering_diagnostics": ordering,
            "causal_risk_counts": dict(sorted(causal_risk_counts.items())),
            "provisional_gate_pass_all_three": sum(1 for c in cards if c["gates"]["full_context"] and c["gates"]["no_memory"] and c["gates"]["mdi"]),
            "provisional_full_gate_including_causal": sum(1 for c in cards if c["gates"]["full_context"] and c["gates"]["no_memory"] and c["gates"]["mdi"] and c["gates"]["causal_sensitivity"] and c["gates"]["irrelevant_stability"]),
        },
        "dimension_matrix": dimension_matrix,
        "templates": sorted(cards, key=lambda x: x["template_id"]),
        # Additional gates for annotated Templates.  FC, NM, MDI, and causal
        # sensitivity above remain the primary structural gates.
        **({"transfer_calibration": transfer_block} if transfer_block else {}),
    }


def write_calibration_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# MIB v0.1 Calibration Report",
        "",
        f"**Profile:** `{report['profile']['id']}`  ",
        f"**Mode:** `{report['calibration_mode']}`  ",
        f"**Release calibration eligible:** `{str(report['release_calibration_eligible']).lower()}`",
        "",
        "> This report uses deterministic reference fixtures to validate benchmark discrimination mechanics. "
        "It is not yet the release-grade fixed-LLM Full Context calibration.",
        "",
        "## Summary",
        "",
        f"- Templates: **{report['summary']['template_count']}**",
        f"- FC/NM/MDI provisional pass: **{report['summary']['provisional_gate_pass_all_three']} / {report['summary']['template_count']}**",
        f"- Full fixture gate including causal sensitivity: **{report['summary']['provisional_full_gate_including_causal']} / {report['summary']['template_count']}**",
    ]
    for k, v in report["summary"]["recommendations"].items():
        lines.append(f"- `{k}`: **{v}**")
    lines += ["", "## Dimension Baseline Matrix", "", "| Dimension | B0 | B1 | B2 | B3 |", "|---|---:|---:|---:|---:|"]
    for row in report["dimension_matrix"]:
        b = row["baselines"]
        lines.append(f"| {row['dimension']} | {100*b.get('B0',0):.1f} | {100*b.get('B1',0):.1f} | {100*b.get('B2',0):.1f} | {100*b.get('B3',0):.1f} |")
    lines += ["", "## Template Calibration Cards", "", "| Template | FC | NM | MDI | B2 | B3 | IMS | Recommendation |", "|---|---:|---:|---:|---:|---:|---:|---|"]
    for c in report["templates"]:
        m = c["metrics"]; cd = c["causal_diagnostics"]
        ims = "—" if cd.get("irrelevant_memory_stability") is None else f"{100*cd['irrelevant_memory_stability']:.0f}"
        lines.append(
            f"| {c['template_id']} | {100*m['full_context']:.0f} | {100*m['no_memory']:.0f} | {100*m['memory_discriminativeness_index']:.0f} | "
            f"{100*m['simple_retrieval']:.0f} | {100*m['structured_agentic']:.0f} | {ims} | `{c['recommendation']}` |"
        )
    lines += [
        "",
        "## Interpretation",
        "",
        "- **FC**: B1 Full Visible History Fixture.",
        "- **NM**: B0 No Memory.",
        "- **MDI**: `FC - NM`.",
        "- **B2**: simple lexical top-k retrieval.",
        "- **B3**: structured/agentic salient-memory retrieval.",
        "- **IMS**: irrelevant-memory stability from B3 causal replay where available.",
        "",
        "A `provisional_pass` means the scenario passes the fixture gate. It does **not** mean the scenario has completed release-grade empirical calibration.",
    ]
    return "\n".join(lines) + "\n"


# --- Transfer calibration (M6.3) -------------------------------------------

DEFAULT_TRANSFER_THRESHOLDS = {
    # An oracle Skill under oracle routing must actually solve the future task,
    # or the annotated transfer edge is not empirically supported and must not
    # be used as a positive-transfer benchmark case.
    "oracle_routed_min": 0.80,
    # ... and it must actually improve on the memory-removed baseline.  A
    # curator-labelled Ability is not useful merely because it sounds plausible.
    "oracle_transfer_gain_min": 0.20,
    # Below this, the calibration baseline showed no natural transfer.  That is
    # a finding about the baseline, not a Template defect, so it is reported as
    # a note rather than as an admission gate.
    "natural_transfer_gain_min": 0.10,
    # An unsupported Probe must stay put whether or not a past exists.
    "unsupported_memory_delta_max": 0.10,
    # A near-match trap only measures resistance if an over-transferring system
    # can actually fail it.
    "near_match_trap_min": 0.20,
}


def _transfer_rows(
    *,
    templates: list[dict[str, Any]],
    schema: dict[str, Any],
    factory: Callable[[], Any],
    seeds: list[int | str],
    repetitions: int,
    seed_prefix: str,
) -> dict[str, dict[str, Any]]:
    """Diagnostic rows for annotated Templates, keyed by Template id."""
    runs: list[dict[str, Any]] = []
    diagnostic: list[dict[str, Any]] = []
    for template in templates:
        if parse_transfer_support(template) is None:
            continue
        for seed in seeds:
            instance = materialize(template, seed)
            vr = validate_scenario(instance, schema)
            if not vr.valid:
                raise ValueError(f"Instance {template['id']}:{seed} invalid: {vr.errors}")
            for rep in range(repetitions):
                agent_seed = f"{seed_prefix}:{seed}:{rep}"
                runs.extend(run_scenario(
                    scenario=instance, agent_factory=factory,
                    include_ablations=True, repetition=rep, agent_seed=agent_seed,
                ))
                diagnostic.extend(run_transfer_matrix(
                    scenario=instance, agent_factory=factory,
                    repetition=rep, agent_seed=agent_seed,
                ))
    rows = transfer_relation_aggregates(templates, runs, diagnostic_runs=diagnostic)
    return {row["template_id"]: row for row in rows}


def calibrate_transfer(
    *,
    templates: list[dict[str, Any]],
    schema: dict[str, Any],
    seeds: list[int | str],
    repetitions: int = 1,
    baseline_id: str = "B3",
    baseline_factories: dict[str, Callable[[], Any]] | None = None,
    thresholds: dict[str, float] | None = None,
) -> dict[str, Any] | None:
    """Structural gates for Transfer Support Annotations.

    These are additional gates.  They do not replace FC, NM, MDI, or causal
    sensitivity, which remain the primary structural admission gates.

    A curator-labelled Ability is not useful merely because it sounds
    plausible: an annotated edge is only admissible when an oracle Skill under
    oracle routing measurably improves the target Probe.
    """
    annotated = [t for t in templates if parse_transfer_support(t) is not None]
    if not annotated:
        return None
    factories = dict(BASELINE_FACTORIES)
    if baseline_factories:
        factories.update(baseline_factories)
    if baseline_id not in factories:
        raise ValueError(f"unknown baseline id: {baseline_id}")
    thresholds = {**DEFAULT_TRANSFER_THRESHOLDS, **(thresholds or {})}

    baseline_rows = _transfer_rows(
        templates=annotated, schema=schema, factory=factories[baseline_id],
        seeds=seeds, repetitions=repetitions, seed_prefix="xfer",
    )
    # The trap fixture deliberately ignores applicability boundaries.  If it
    # cannot fail a near-match Probe, that Probe is not a trap.
    trap_rows = _transfer_rows(
        templates=annotated, schema=schema, factory=OverTransferAgent,
        seeds=seeds, repetitions=repetitions, seed_prefix="xfer-trap",
    )

    cards = []
    for template in annotated:
        tid = template["id"]
        row = baseline_rows.get(tid) or {"relations": []}
        trap = {r["probe_id"]: r for r in (trap_rows.get(tid) or {"relations": []})["relations"]}
        probes = []
        gates = {
            "oracle_skill_solvable": True,
            "oracle_artifact_declared": True,
            "unsupported_memory_neutral": True,
            "near_match_trap_fires": True,
        }
        risks: list[str] = []
        notes: list[str] = []
        for relation in row["relations"]:
            entry = {
                "probe_id": relation["probe_id"],
                "relation": relation["relation"],
                "distance_class": relation.get("distance_class"),
                "natural_score": relation.get("natural_score"),
                "baseline_score": relation.get("baseline_score"),
                "natural_transfer_gain": (relation.get("natural_transfer_gain") or {}).get("value"),
                "oracle_routed_score": (relation.get("oracle_routed_score") or {}).get("value"),
            }
            if relation["relation"] in POSITIVE_RELATIONS:
                oracle = entry["oracle_routed_score"]
                baseline = entry["baseline_score"]
                entry["oracle_routed_gain"] = (
                    None if oracle is None or baseline is None else float(oracle) - float(baseline)
                )
                if oracle is None:
                    gates["oracle_artifact_declared"] = False
                    risks.append(f"{relation['probe_id']}:no_oracle_artifact")
                elif oracle < thresholds["oracle_routed_min"]:
                    gates["oracle_skill_solvable"] = False
                    risks.append(f"{relation['probe_id']}:oracle_skill_does_not_solve_task")
                elif (
                    entry["oracle_routed_gain"] is not None
                    and entry["oracle_routed_gain"] < thresholds["oracle_transfer_gain_min"]
                ):
                    gates["oracle_skill_solvable"] = False
                    risks.append(f"{relation['probe_id']}:oracle_skill_does_not_improve_task")
                gain = entry["natural_transfer_gain"]
                if gain is not None and gain < thresholds["natural_transfer_gain_min"]:
                    # The oracle edge holds; this baseline simply did not transfer.
                    notes.append(f"{relation['probe_id']}:baseline_shows_no_natural_transfer")
            if relation["relation"] == "unsupported_novel":
                delta = (relation.get("unsupported_memory_delta") or {}).get("value")
                entry["unsupported_memory_delta"] = delta
                if delta is not None and abs(delta) > thresholds["unsupported_memory_delta_max"]:
                    gates["unsupported_memory_neutral"] = False
                    risks.append(f"{relation['probe_id']}:unsupported_task_not_neutral")
            if relation["relation"] == "near_match_non_applicable":
                trap_row = trap.get(relation["probe_id"])
                trap_score = trap_row.get("natural_score") if trap_row else None
                entry["trap_fixture_score"] = trap_score
                entry["near_match_harm"] = (
                    None if trap_score is None or relation.get("natural_score") is None
                    else max(0.0, float(relation["natural_score"]) - float(trap_score))
                )
                if entry["near_match_harm"] is None or entry["near_match_harm"] < thresholds["near_match_trap_min"]:
                    gates["near_match_trap_fires"] = False
                    risks.append(f"{relation['probe_id']}:near_match_trap_does_not_discriminate")
            probes.append(entry)
        cards.append({
            "template_id": tid,
            "suite": template.get("suite"),
            "relations": probes,
            "gates": gates,
            "risks": risks,
            "baseline_notes": notes,
            "recommendation": "provisional_pass" if not risks else "revise_transfer_annotation",
        })

    distance_matrix: dict[str, list[float]] = defaultdict(list)
    for card in cards:
        for entry in card["relations"]:
            cls = entry.get("distance_class")
            if cls and entry.get("natural_score") is not None:
                distance_matrix[cls].append(float(entry["natural_score"]))

    gate_counts: dict[str, int] = defaultdict(int)
    for card in cards:
        for gate, ok in card["gates"].items():
            if ok:
                gate_counts[gate] += 1
    return {
        "enabled": True,
        "baseline_id": baseline_id,
        "trap_fixture": "OverTransferAgent",
        "thresholds": thresholds,
        "annotated_template_count": len(cards),
        "distance_class_baseline": {
            cls: _mean(vals) for cls, vals in sorted(distance_matrix.items())
        },
        "gate_pass_counts": {k: gate_counts[k] for k in sorted(gate_counts)},
        "templates": sorted(cards, key=lambda c: c["template_id"]),
    }
