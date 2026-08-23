"""M6.2 / M6.3 — Transfer diagnostics.

Decompose a transfer outcome into what was *formed*, what was *routed*, and
whether the Agent could *use* it, and report how far the transfer had to reach.

Two diagnostic modes:

``behavioral``
    Works for any black-box Agent.  It reads the outcome differences that the
    ordinary MIB conditions already produce (full vs relevant-memory ablation)
    and reports them per annotated transfer relation and distance class.

``decomposable_adapter``
    Optional.  Requires a Memory Adapter that can export, route, and inject
    memory artifacts, which lets the evaluator run the AA / AO / OA / OO cells
    and separate Formation from Routing.  It is never required for a Track B
    submission.

Nothing here changes a MIB Score.  The output is carried as the report
extension ``mib.transfer_diagnostics.v1``.
"""

from __future__ import annotations

import hashlib
import hmac
import math
import random
from collections import defaultdict
from typing import Any

from .transfer import (
    DISTANCE_CLASSES,
    DISTANCE_LABEL,
    NEGATIVE_CONTROL_RELATIONS,
    POSITIVE_RELATIONS,
    TRANSFER_DIAGNOSTICS_EXTENSION,
    parse_transfer_support,
    transfer_coverage,
)

#: Minimum oracle headroom ``OO - B`` for a Formation/Routing ratio to be defined.
#: Below it the denominator is noise and the ratio is reported as unknown, never
#: as zero: missing evidence is not negative evidence.
DEFAULT_EPSILON = 0.05

#: Runner condition -> diagnostic cell.  ``B`` is the memory-removed baseline.
#: A relevant-memory Ablation removes exactly the events that support the
#: annotated Ability, so it is the tighter control; ``no_memory`` is the
#: fallback when a Scenario declares no relevant-memory Ablation.
_BASELINE_PREFERENCE = ("relevant_ablation", "no_memory")

_CELLS = ("AA", "AO", "OA", "OO", "B")


def mean(values: list[float]) -> float | None:
    return math.fsum(values) / len(values) if values else None


def _alias(key: str | None, prefix: str, value: str) -> str:
    if key:
        digest = hmac.new(key.encode("utf-8"), str(value).encode("utf-8"), hashlib.sha256).hexdigest()
    else:
        digest = hashlib.sha256(str(value).encode("utf-8")).hexdigest()
    return f"{prefix}-{digest[:12]}"


def _probe_scores(run: dict[str, Any]) -> dict[str, float]:
    return {
        str(p["probe_id"]): float(p.get("score", 0.0))
        for p in run.get("probe_results", [])
        if p.get("outcome") in {"scored", "execution_failure"}
        and float(p.get("weight", 1.0)) > 0
    }


def _probe_usage(run: dict[str, Any]) -> dict[str, tuple[float, float]]:
    """Per-Probe ``(tool_calls, latency_ms)``.

    Usage is read per Probe, not per run: an Ablation may cover only a subset of
    a Scenario's Probes, so run-level totals would compare different workloads.
    """
    out: dict[str, tuple[float, float]] = {}
    for p in run.get("probe_results", []):
        if p.get("outcome") != "scored":
            continue
        # An Ablation executes the whole Probe program but scores only its own
        # declared subset (weight 0 elsewhere).  Cost must cover exactly the
        # Probes whose scores populate the same cell.
        if float(p.get("weight", 1.0)) <= 0:
            continue
        trace = (p.get("extensions") or {}).get("mib.runner.action_trace") or []
        calls = float(sum(1 for step in trace if step.get("kind") == "tool_call"))
        out[str(p["probe_id"])] = (calls, float(p.get("latency_ms") or 0.0))
    return out


class _CellTable:
    """Per-Template ``cell -> instance -> probe -> [scores]`` observations.

    Aggregation is Template-first throughout: mean within a repetition set,
    then within a Scenario Instance, then across Instances.  A Template with
    many generated Instances never becomes more semantically important.
    """

    def __init__(self) -> None:
        self.scores: dict[str, dict[str, dict[str, list[float]]]] = {
            cell: defaultdict(lambda: defaultdict(list)) for cell in _CELLS
        }
        self.tool_calls: dict[str, dict[str, dict[str, list[float]]]] = {
            cell: defaultdict(lambda: defaultdict(list)) for cell in _CELLS
        }
        self.latency: dict[str, dict[str, dict[str, list[float]]]] = {
            cell: defaultdict(lambda: defaultdict(list)) for cell in _CELLS
        }

    def add(self, cell: str, run: dict[str, Any]) -> None:
        instance = str(run["scenario_instance_id"])
        for probe_id, score in _probe_scores(run).items():
            self.scores[cell][instance][probe_id].append(score)
        for probe_id, (calls, latency) in _probe_usage(run).items():
            self.tool_calls[cell][instance][probe_id].append(calls)
            self.latency[cell][instance][probe_id].append(latency)

    def clear(self, cell: str) -> None:
        self.scores[cell] = defaultdict(lambda: defaultdict(list))
        self.tool_calls[cell] = defaultdict(lambda: defaultdict(list))
        self.latency[cell] = defaultdict(lambda: defaultdict(list))

    @staticmethod
    def _nested(table: dict[str, dict[str, list[float]]], probe_id: str) -> list[float]:
        out = []
        for probes in table.values():
            reps = probes.get(probe_id)
            if reps:
                out.append(math.fsum(reps) / len(reps))
        return out

    def instances(self, cell: str, probe_id: str) -> list[float]:
        return self._nested(self.scores[cell], probe_id)

    def value(self, cell: str, probe_id: str) -> float | None:
        return mean(self.instances(cell, probe_id))

    def usage(self, kind: str, cell: str, probe_id: str) -> float | None:
        table = self.tool_calls if kind == "tool_calls" else self.latency
        return mean(self._nested(table[cell], probe_id))


def _collect(templates: list[dict[str, Any]], runs: list[dict[str, Any]]) -> dict[str, _CellTable]:
    tables: dict[str, _CellTable] = {t["id"]: _CellTable() for t in templates}
    baseline_condition: dict[str, str] = {}
    for run in runs:
        tid = str(run.get("template_id"))
        if tid not in tables:
            continue
        condition = run.get("condition")
        if condition in _BASELINE_PREFERENCE:
            current = baseline_condition.get(tid)
            if current is None or _BASELINE_PREFERENCE.index(condition) < _BASELINE_PREFERENCE.index(current):
                baseline_condition[tid] = condition
    for run in runs:
        tid = str(run.get("template_id"))
        table = tables.get(tid)
        if table is None:
            continue
        condition = run.get("condition")
        if condition == "full":
            table.add("AA", run)
        elif condition == baseline_condition.get(tid):
            table.add("B", run)
        elif condition in {"transfer_ao", "transfer_oa", "transfer_oo"}:
            table.add(condition.split("_")[1].upper(), run)

    # A diagnostic-only baseline covers every annotated Probe, including the
    # negative controls a core Ablation deliberately does not target.  When it
    # is present it replaces the core-derived baseline rather than mixing with it.
    diagnostic_baselines: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for run in runs:
        if run.get("condition") == "transfer_b" and str(run.get("template_id")) in tables:
            diagnostic_baselines[str(run["template_id"])].append(run)
    for tid, rows in diagnostic_baselines.items():
        tables[tid].clear("B")
        for run in rows:
            tables[tid].add("B", run)
    return tables


def _ratio(numerator: float | None, denominator: float | None, *, epsilon: float) -> dict[str, Any]:
    """Efficiency ratio with explicit eligibility.

    Raw values below 0 and above 1 are scientifically meaningful and are kept;
    only the display form is clipped.
    """
    if numerator is None or denominator is None:
        return {"value": None, "eligible": False, "reason": "missing_cell"}
    if denominator <= epsilon:
        return {
            "value": None,
            "eligible": False,
            "reason": "insufficient_oracle_headroom",
            "numerator": numerator,
            "denominator": denominator,
            "epsilon": epsilon,
        }
    raw = numerator / denominator
    return {
        "value": raw,
        "display": min(1.0, max(0.0, raw)),
        "eligible": True,
        "numerator": numerator,
        "denominator": denominator,
    }


def _relation_row(
    *,
    table: _CellTable,
    probe_id: str,
    relation: Any,
    epsilon: float,
) -> dict[str, Any]:
    aa = table.value("AA", probe_id)
    b = table.value("B", probe_id)
    ao = table.value("AO", probe_id)
    oa = table.value("OA", probe_id)
    oo = table.value("OO", probe_id)

    row: dict[str, Any] = {
        "probe_id": probe_id,
        "relation": relation.relation,
        "support_expected": relation.support_expected,
        "expected_behaviour": relation.expected_behaviour,
        "natural_score": aa,
        "baseline_score": b,
        "instance_count": len(table.instances("AA", probe_id)),
    }
    if relation.support_expected and relation.distance_class:
        row["distance_class"] = relation.distance_class
        row["distance_normalized"] = relation.distance_normalized

    if aa is not None and b is not None:
        # Signed on purpose. A negative Natural Transfer Gain is harmful
        # evolution, not a smaller positive number.
        row["natural_transfer_gain"] = {"value": aa - b}
        if relation.relation in NEGATIVE_CONTROL_RELATIONS:
            # Prior experience made the negative control worse: over-generalization.
            row["memory_induced_harm"] = {"value": max(0.0, b - aa)}
        if relation.relation == "unsupported_novel":
            row["unsupported_memory_delta"] = {"value": aa - b}
            row["unsupported_memory_neutrality"] = {"value": max(0.0, 1.0 - abs(aa - b))}

    if oo is not None and relation.support_expected:
        # The uptake ceiling is only a ceiling where transfer is expected.  On a
        # negative control the OO cell force-routes the very procedure that must
        # be withheld, so a correctly resisting system scores low there; folding
        # that into the ceiling would report boundary respect as uptake failure.
        row["oracle_routed_score"] = {"value": oo}
        if b is not None:
            row["oracle_routed_gain"] = {"value": oo - b}
    if ao is not None:
        row["oracle_routed_automatic_content_score"] = {"value": ao}
    if oa is not None:
        row["automatic_routing_oracle_content_score"] = {"value": oa}

    headroom = (oo - b) if (oo is not None and b is not None) else None
    if ao is not None or oa is not None or oo is not None:
        row["formation_efficiency"] = _ratio(
            (ao - b) if (ao is not None and b is not None) else None, headroom, epsilon=epsilon
        )
        row["routing_efficiency"] = _ratio(
            (oa - b) if (oa is not None and b is not None) else None, headroom, epsilon=epsilon
        )
        row["natural_transfer_efficiency"] = _ratio(
            (aa - b) if (aa is not None and b is not None) else None, headroom, epsilon=epsilon
        )
        losses: dict[str, Any] = {}
        if oo is not None and ao is not None:
            losses["formation_loss"] = oo - ao
        if oo is not None and oa is not None:
            losses["routing_loss"] = oo - oa
        if oo is not None and aa is not None:
            losses["deployment_gap"] = oo - aa
        if {"formation_loss", "routing_loss", "deployment_gap"} <= set(losses):
            # Formation and Routing interact; the decomposition is not additive.
            losses["interaction_residual"] = losses["deployment_gap"] - (
                losses["formation_loss"] + losses["routing_loss"]
            )
        if losses:
            row["loss_decomposition"] = losses
    return row


def _efficiency_block(table: _CellTable, probe_ids: list[str]) -> dict[str, Any] | None:
    """Cost of having a past, paired per annotated Probe.

    Reported, never scored: prior experience changing task cost is a finding,
    not a MIB Score input.
    """
    tool_deltas: list[float] = []
    latency_deltas: list[float] = []
    for probe_id in probe_ids:
        aa_tools = table.usage("tool_calls", "AA", probe_id)
        b_tools = table.usage("tool_calls", "B", probe_id)
        if aa_tools is not None and b_tools is not None:
            tool_deltas.append(aa_tools - b_tools)
        aa_latency = table.usage("latency", "AA", probe_id)
        b_latency = table.usage("latency", "B", probe_id)
        if aa_latency is not None and b_latency is not None:
            latency_deltas.append(aa_latency - b_latency)
    out: dict[str, Any] = {}
    if tool_deltas:
        out["tool_call_delta"] = math.fsum(tool_deltas) / len(tool_deltas)
    if latency_deltas:
        out["latency_ms_delta"] = math.fsum(latency_deltas) / len(latency_deltas)
    return out or None


def transfer_relation_aggregates(
    templates: list[dict[str, Any]],
    runs: list[dict[str, Any]],
    *,
    diagnostic_runs: list[dict[str, Any]] | None = None,
    epsilon: float = DEFAULT_EPSILON,
) -> list[dict[str, Any]]:
    """Per-Template rows, each carrying one entry per annotated Probe relation."""
    tables = _collect(templates, list(runs) + list(diagnostic_runs or []))
    out: list[dict[str, Any]] = []
    for template in templates:
        support = parse_transfer_support(template)
        if support is None:
            continue
        table = tables[template["id"]]
        rows = [
            _relation_row(table=table, probe_id=r.probe_id, relation=r, epsilon=epsilon)
            for r in support.probe_relations
        ]
        rows = [r for r in rows if r["natural_score"] is not None]
        if not rows:
            continue
        entry: dict[str, Any] = {
            "template_id": template["id"],
            "template_alias": _alias(None, "xfer", template["id"]),
            "relations": rows,
            # Only an executed AO cell means the evaluator reached into the
            # system's own formed content; an ineligible placeholder does not.
            "diagnostic_mode": (
                "decomposable_adapter"
                if any("oracle_routed_automatic_content_score" in r for r in rows)
                else "behavioral"
            ),
        }
        gains = [r["natural_transfer_gain"]["value"] for r in rows if "natural_transfer_gain" in r]
        if gains:
            entry["natural_transfer_gain"] = {"value": math.fsum(gains) / len(gains)}
        for name in ("formation_efficiency", "routing_efficiency", "natural_transfer_efficiency"):
            values = [r[name]["value"] for r in rows if r.get(name, {}).get("eligible")]
            if values:
                entry[name] = {"value": math.fsum(values) / len(values), "eligible": True}
        oo = [r["oracle_routed_score"]["value"] for r in rows if "oracle_routed_score" in r]
        if oo:
            entry["oracle_routed_score"] = {"value": math.fsum(oo) / len(oo)}
        efficiency = _efficiency_block(table, [r["probe_id"] for r in rows])
        if efficiency:
            entry["efficiency"] = efficiency
        out.append(entry)
    return out


def transfer_distance_aggregates(template_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """The Transfer Profile: score and gain per positive-transfer distance class.

    Aggregation is across Templates, so a distance class is a mean of Template
    means, never a mean of Probe attempts.
    """
    per_class_scores: dict[str, list[float]] = defaultdict(list)
    per_class_gains: dict[str, list[float]] = defaultdict(list)
    per_class_templates: dict[str, set[str]] = defaultdict(set)
    for entry in template_rows:
        by_class_scores: dict[str, list[float]] = defaultdict(list)
        by_class_gains: dict[str, list[float]] = defaultdict(list)
        for row in entry["relations"]:
            cls = row.get("distance_class")
            if not cls or not row.get("support_expected"):
                continue
            by_class_scores[cls].append(float(row["natural_score"]))
            if "natural_transfer_gain" in row:
                by_class_gains[cls].append(float(row["natural_transfer_gain"]["value"]))
            per_class_templates[cls].add(entry["template_id"])
        for cls, values in by_class_scores.items():
            per_class_scores[cls].append(math.fsum(values) / len(values))
        for cls, values in by_class_gains.items():
            per_class_gains[cls].append(math.fsum(values) / len(values))

    out = []
    for cls in DISTANCE_CLASSES:
        if cls not in per_class_scores:
            continue
        entry = {
            "class": cls,
            "label": DISTANCE_LABEL[cls],
            "score": math.fsum(per_class_scores[cls]) / len(per_class_scores[cls]),
            "template_count": len(per_class_templates[cls]),
        }
        if per_class_gains.get(cls):
            entry["transfer_gain"] = math.fsum(per_class_gains[cls]) / len(per_class_gains[cls])
        out.append(entry)
    return out


def _relation_class_means(template_rows: list[dict[str, Any]], predicate) -> list[float]:
    """Template-first means over the relation rows matching ``predicate``."""
    out = []
    for entry in template_rows:
        values = [float(r["natural_score"]) for r in entry["relations"] if predicate(r)]
        if values:
            out.append(math.fsum(values) / len(values))
    return out


def transfer_diagnostic_aggregates(template_rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Benchmark-level Transfer Diagnostics, aggregated Template-first."""
    out: dict[str, Any] = {}

    supported = _relation_class_means(template_rows, lambda r: r["relation"] in POSITIVE_RELATIONS)
    if supported:
        out["supported_transfer_success_rate"] = math.fsum(supported) / len(supported)

    composition = _relation_class_means(template_rows, lambda r: r["relation"] == "compositional_transfer")
    if composition:
        out["compositional_transfer_score"] = math.fsum(composition) / len(composition)

    near_match = _relation_class_means(template_rows, lambda r: r["relation"] == "near_match_non_applicable")
    if near_match:
        # Outcome resistance, not "applicability precision": a correct answer is
        # not proof that memory was withheld.
        out["near_match_resistance"] = math.fsum(near_match) / len(near_match)

    neutrality: list[float] = []
    for entry in template_rows:
        values = [
            float(r["unsupported_memory_neutrality"]["value"])
            for r in entry["relations"]
            if "unsupported_memory_neutrality" in r
        ]
        if values:
            neutrality.append(math.fsum(values) / len(values))
    if neutrality:
        out["unsupported_memory_neutrality"] = math.fsum(neutrality) / len(neutrality)

    gains = [float(e["natural_transfer_gain"]["value"]) for e in template_rows if "natural_transfer_gain" in e]
    if gains:
        out["natural_transfer_gain"] = math.fsum(gains) / len(gains)

    # Negative Transfer Rate is deliberately its own name.  It is not the
    # standardized MIB `negative_transfer` causal metric, whose control
    # semantics come from MIB-Scoring.md.  Like every other aggregate here it is
    # Template-first: pooling Probe rows would let one Template with many
    # annotated Probes dominate the benchmark number.
    per_template_rates: list[float] = []
    for entry in template_rows:
        scored = [r for r in entry["relations"] if "natural_transfer_gain" in r]
        if not scored:
            continue
        worse = sum(1 for r in scored if float(r["natural_transfer_gain"]["value"]) < -1e-9)
        per_template_rates.append(worse / len(scored))
    if per_template_rates:
        out["negative_transfer_rate"] = math.fsum(per_template_rates) / len(per_template_rates)

    for name in ("formation_efficiency", "routing_efficiency", "natural_transfer_efficiency"):
        values = [float(e[name]["value"]) for e in template_rows if e.get(name, {}).get("eligible")]
        if values:
            out[name] = math.fsum(values) / len(values)
    oo = [float(e["oracle_routed_score"]["value"]) for e in template_rows if "oracle_routed_score" in e]
    if oo:
        out["oracle_routed_score"] = math.fsum(oo) / len(oo)
    return out


def _bootstrap(
    template_rows: list[dict[str, Any]],
    *,
    resamples: int,
    seed: int | str,
    confidence_level: float,
) -> dict[str, Any]:
    """Template-level bootstrap over the Transfer Profile and aggregates.

    Templates are the resampling unit, matching the hierarchical-bootstrap
    philosophy used by MIB core aggregation.
    """
    rng = random.Random(str(seed))
    n = len(template_rows)
    aggregate_draws: dict[str, list[float]] = defaultdict(list)
    distance_draws: dict[str, list[float]] = defaultdict(list)
    for _ in range(resamples):
        sample = [template_rows[rng.randrange(n)] for _ in range(n)]
        for name, value in transfer_diagnostic_aggregates(sample).items():
            aggregate_draws[name].append(float(value))
        for entry in transfer_distance_aggregates(sample):
            distance_draws[entry["class"]].append(float(entry["score"]))

    alpha = 1.0 - confidence_level

    def ci(values: list[float]) -> dict[str, Any] | None:
        if len(values) < 2:
            return None
        xs = sorted(values)

        def q(p: float) -> float:
            pos = (len(xs) - 1) * p
            lo, hi = int(math.floor(pos)), int(math.ceil(pos))
            return xs[lo] if lo == hi else xs[lo] * (1 - (pos - lo)) + xs[hi] * (pos - lo)

        return {
            "level": confidence_level,
            "lower": q(alpha / 2.0),
            "upper": q(1.0 - alpha / 2.0),
            "method": "template_bootstrap_percentile",
            "resamples": resamples,
            "seed": seed,
        }

    return {
        "aggregate": {k: v for k, v in ((k, ci(v)) for k, v in aggregate_draws.items()) if v},
        "distance_profile": {k: v for k, v in ((k, ci(v)) for k, v in distance_draws.items()) if v},
    }


def build_transfer_diagnostics(
    *,
    templates: list[dict[str, Any]],
    runs: list[dict[str, Any]],
    diagnostic_runs: list[dict[str, Any]] | None = None,
    epsilon: float = DEFAULT_EPSILON,
    bootstrap_resamples: int = 0,
    bootstrap_seed: int | str = 20260819,
    confidence_level: float = 0.95,
) -> dict[str, Any] | None:
    """Build the ``mib.transfer_diagnostics.v1`` extension body, or ``None``.

    Returns ``None`` when no Template in the pack carries a Transfer Support
    Annotation, so an unannotated pack produces a byte-identical report.
    """
    template_rows = transfer_relation_aggregates(
        templates, runs, diagnostic_runs=diagnostic_runs, epsilon=epsilon
    )
    if not template_rows:
        return None

    coverage = transfer_coverage(templates)
    distance_profile = transfer_distance_aggregates(template_rows)
    aggregate = transfer_diagnostic_aggregates(template_rows)
    modes = {e["diagnostic_mode"] for e in template_rows}
    body: dict[str, Any] = {
        "version": "1.0.0",
        "diagnostic_mode": "decomposable_adapter" if "decomposable_adapter" in modes else "behavioral",
        "epsilon": epsilon,
        "coverage": coverage,
        "templates": template_rows,
        "distance_profile": distance_profile,
        "aggregate": aggregate,
    }
    if bootstrap_resamples > 0 and len(template_rows) > 1:
        body["statistics"] = _bootstrap(
            template_rows,
            resamples=bootstrap_resamples,
            seed=bootstrap_seed,
            confidence_level=confidence_level,
        )
    return body


def redact_transfer_diagnostics(
    body: dict[str, Any],
    *,
    aliases: dict[str, str] | None = None,
    redaction_key: str | None = None,
) -> dict[str, Any]:
    """Public projection: aliases and aggregates only.

    A public surface must never let a participant reconstruct which past
    Experience supports which future Probe.  Per-Probe identity, per-Probe
    relation, and the Ability graph stay evaluator-private; repeated
    submissions must not become an oracle-probing channel.
    """
    aliases = aliases or {}
    out: dict[str, Any] = {
        "version": body.get("version", "1.0.0"),
        "diagnostic_mode": body.get("diagnostic_mode"),
        "scope": "public",
        "coverage": {
            "annotated_templates": (body.get("coverage") or {}).get("annotated_templates", 0),
            "annotated_probes": (body.get("coverage") or {}).get("annotated_probes", 0),
        },
        "distance_profile": [dict(x) for x in body.get("distance_profile") or []],
        "aggregate": dict(body.get("aggregate") or {}),
    }
    templates = []
    for entry in body.get("templates") or []:
        tid = entry.get("template_id")
        alias = aliases.get(tid) or _alias(redaction_key, "xfer", str(tid))
        row: dict[str, Any] = {"template_alias": alias, "diagnostic_mode": entry.get("diagnostic_mode")}
        for name in (
            "natural_transfer_gain",
            "formation_efficiency",
            "routing_efficiency",
            "natural_transfer_efficiency",
            "oracle_routed_score",
        ):
            if name in entry:
                row[name] = dict(entry[name])
        templates.append(row)
    out["templates"] = templates
    if body.get("statistics"):
        out["statistics"] = body["statistics"]
    return out


def attach_transfer_diagnostics(report: dict[str, Any], body: dict[str, Any] | None) -> dict[str, Any]:
    if body:
        report.setdefault("extensions", {})[TRANSFER_DIAGNOSTICS_EXTENSION] = body
    return report
