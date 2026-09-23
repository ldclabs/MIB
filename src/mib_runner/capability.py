from __future__ import annotations

from typing import Any


DISPLAY = {
    "retention_retrieval": "Retention & Retrieval",
    "temporal_memory": "Temporal Memory",
    "epistemic_memory": "Epistemic Memory",
    "experience_memory": "Experience Memory",
    "skill_learning_transfer": "Procedural Memory & Applicability",
    "procedural_memory": "Procedural Memory",
    "selective_forgetting": "Withdrawal Compliance",
    "prospective_self_memory": "Prospective & Self Memory",
    "causal_memory_impact": "Causal Memory Impact",
}


def _metric(report: dict[str, Any], name: str):
    return next((m for m in report.get("causal_metrics", []) if m.get("name") == name), None)


def render_capability_card(report: dict[str, Any]) -> str:
    bench = report["benchmark"]
    score = report["aggregates"]["mib_score"]
    ci = score.get("ci")
    agent = report.get("system", {}).get("agent", {})
    if score.get("official"):
        score_status = "Official Hidden Eval leaderboard score."
    elif score.get("partial"):
        score_status = "Partial profile score — not an official leaderboard score."
    else:
        score_status = "Development profile — not an official Hidden Eval leaderboard score."
    lines = [
        "# MIB Capability Card",
        "",
        "```text",
        "MIB — Memory Intelligence Benchmark",
        "════════════════════════════════════════════",
        "",
        f"Profile   {bench['profile']['id']} {bench['profile']['version']}",
        f"Track     {bench['track']}",
        f"Scale     {bench['scale']}",
        f"Agent     {agent.get('name', 'Unknown')} {agent.get('version', '')}".rstrip(),
    ]
    # Headline (measurement 0.5.0): per-dimension capability, dependence
    # evidence and resources. The composite is a Profile-weighted summary
    # shown with its weight sensitivity; causal quantities are diagnostics.
    lines += ["", "Capability"]
    for d in report["aggregates"]["dimensions"]:
        lines.append(f"  {DISPLAY.get(d['dimension'], d['dimension']):28s} {d['score']:5.1f}  coverage {100*d['coverage']:5.1f}%")
    lines += _dependence_lines(report)
    lines += ["", f"Composite MIB Score {score['final_score']:.1f} (Profile weights)"]
    if ci:
        lines.append(f"  95% CI    [{ci['lower']:.1f}, {ci['upper']:.1f}]")
    sensitivity = composite_sensitivity(report["aggregates"]["dimensions"])
    if sensitivity:
        lines.append(f"  Equal weights {sensitivity['equal_weight']:.1f}; leave-one-dimension-out range "
                     f"[{sensitivity['leave_one_out_min']:.1f}, {sensitivity['leave_one_out_max']:.1f}]")
    lines += _resource_lines(report)
    diagnostics = []
    for name, label, fmt in [
        ("memory_benefit", "Memory Benefit", "pp"),
        ("memory_harm_effect", "Signed Harm Effect", "pp"),
        ("memory_harm", "Downside Loss (clipped)", "pp"),
        ("net_memory_gain", "Net Memory Gain", "pp"),
        ("irrelevant_memory_stability", "Irrelevant Stability", "score"),
        ("harm_resistance", "Harm Resistance", "score"),
        ("content_tracking_rate", "Content Tracking", "score"),
        ("stale_adoption_rate", "Stale Adoption", "rate"),
        ("error_recurrence_rate", "Error Recurrence", "rate"),
        ("consolidation_benefit", "Consolidation Benefit", "pp"),
    ]:
        m = _metric(report, name)
        if not m:
            continue
        v = float(m["value"])
        if fmt == "pp":
            diagnostics.append(f"  {label:28s} {100*v:+5.1f} pp")
        elif fmt == "rate":
            diagnostics.append(f"  {label:28s} {100*v:5.1f}%")
        else:
            diagnostics.append(f"  {label:28s} {100*v:5.1f}")
    if diagnostics:
        lines += ["", "Causal Diagnostics (not part of the headline)"] + diagnostics
    lines += _behaviour_lines(report)
    lines += _retention_lines(report)
    lines += _transfer_lines(report)
    lines += [
        "",
        score_status,
        "```",
        "",
    ]
    return "\n".join(lines)


def composite_sensitivity(dimensions: list[dict[str, Any]]) -> dict[str, float] | None:
    """How much the composite depends on the unvalidated Profile weights."""
    rows = [(float(d["score"]), float(d.get("weight", 0.0))) for d in dimensions if float(d.get("weight", 0.0)) > 0]
    if len(rows) < 2:
        return None
    def weighted(items: list[tuple[float, float]]) -> float:
        total = sum(w for _, w in items)
        return sum(s * w for s, w in items) / total if total else 0.0
    loo = [weighted(rows[:i] + rows[i + 1:]) for i in range(len(rows))]
    return {"equal_weight": sum(s for s, _ in rows) / len(rows), "leave_one_out_min": min(loo), "leave_one_out_max": max(loo)}


def _history_lines(report: dict[str, Any]) -> list[str]:
    """How much history the capability rung shows, and what survived session boundaries.

    A Track B score at a rung whose visible history fits the Agent's context
    does not separate memory from reading the transcript, so the size is part
    of the headline's resource statement rather than a footnote.
    """
    policy = report.get('evaluation_policy', {}).get('profile', {})
    canonical = policy.get('canonical_rung')
    instances = (report.get('aggregates') or {}).get('scenario_instances') or []
    rows = [i for i in instances if i.get('visible_history_chars') is not None
            and (canonical is None or i.get('rung') is None or int(i['rung']) == int(canonical))]
    lines = []
    if rows:
        chars = [int(i['visible_history_chars']) for i in rows]
        lines.append(f"  Visible history at the capability rung: {min(chars):,}\u2013{max(chars):,} characters ({len(rows)} Instances).")
        lines.append("  An integrated Agent whose context holds this much history is in a raw-context regime: the score does not"
                     " separate memory from reading the transcript.")
    isolation = [i['session_isolation'] for i in instances if isinstance(i.get('session_isolation'), dict)]
    if isolation:
        mode = isolation[0].get('mode')
        persisted = max(int(i.get('persisted_bytes', 0)) for i in isolation)
        lines.append(f"  Session isolation: {mode}; persisted state up to {persisted:,} UTF-8 bytes per Instance"
                     + (" (only this record survives a boundary)." if mode == 'persisted_state' else " (boundaries acknowledged, not enforced)."))
    return lines


def _resource_lines(report: dict[str, Any]) -> list[str]:
    lines = ["", "Resources and Boundaries",
             f"  Coverage                     {100*report['coverage']['overall']:5.1f}%",
             f"  Execution Failure Rate       {100*report['execution'].get('execution_failure_rate', 0.0):5.2f}%"]
    regime = report.get('evaluation_policy', {}).get('profile', {}).get('measurement_regime', {})
    if regime:
        lines.append(f"  Regime: {regime.get('kind')}; internal mechanism is not independently identified.")
    lines.extend(_history_lines(report))
    operations = report.get('efficiency', {}).get('runner_measured', {}).get('operations', {})
    if operations:
        lines.append('  Runner operations (all evaluation conditions; UTF-8 bytes, not tokens)')
        for name, row in sorted(operations.items()):
            lines.append(f"    {name:16s} {int(row['calls']):6d} calls; {row['latency_ms']:.1f} ms; "
                         f"{int(row['input_bytes'])} input bytes; {int(row['output_bytes'])} output bytes")
    return lines


def _behaviour_lines(report: dict[str, Any]) -> list[str]:
    """Diagnostics read off full runs and the standardized controls (MIB-Specification §7.8–§7.9)."""
    rows = [
        ("negative_transfer", "Negative Transfer", "pp"),
        ("negative_transfer_rate", "Negative Transfer Rate", "rate"),
        ("learning_gain", "Learning Gain", "pp"),
        ("area_under_learning_curve", "Learning Curve Area", "score"),
        ("historical_fidelity", "Historical Fidelity", "score"),
        ("source_attribution_accuracy", "Source Attribution", "score"),
        ("authority_confusion_rate", "Authority Confusion", "rate"),
        ("self_limitation_continuity", "Self-Rule Continuity", "score"),
        ("memory_related_error_rate", "Memory-Related Error Patterns (descriptive)", "rate"),
    ]
    present = [(n, l, f) for n, l, f in rows if _metric(report, n)]
    if not present:
        return []
    lines = ["", "Behaviour Diagnostics"]
    for name, label, fmt in present:
        v = float(_metric(report, name)["value"])
        if fmt == "pp":
            lines.append(f"  {label:28s} {100*v:+5.1f} pp")
        elif fmt == "rate":
            lines.append(f"  {label:28s} {100*v:5.1f}%")
        else:
            lines.append(f"  {label:28s} {100*v:5.1f}")
    return lines


def _retention_lines(report: dict[str, Any]) -> list[str]:
    """Retention curve per Program (MIB-Specification §8.1), rendered only for ladder packs."""
    rows = report.get("retention") or []
    if not rows:
        return []
    lines = ["", "Retention (score by interference distance)"]
    for r in rows:
        curve = "  ".join(f"@{x.get('interference_count', x['rung'])}:{100*float(x['full_score']):5.1f}" for x in r.get("rungs", []))
        half = r.get("half_distance")
        half_text = f"half {half:.0f}" if half is not None else ("half >ladder" if r.get("half_distance_beyond_ladder") else "")
        lines.append(f"  {r['template_id']:28s} {curve}  index {100*float(r['retention_index']):5.1f}  {half_text}".rstrip())
    canonical = next((r.get("canonical_rung") for r in rows if r.get("canonical_rung") is not None), None)
    if canonical is not None:
        lines.append(f"  Capability score read at rung {canonical}.")
    return lines


def _dependence_lines(report: dict[str, Any]) -> list[str]:
    """Memory-dependence gate (MIB-Specification §7.10)."""
    dep = report.get("memory_dependence")
    if not dep:
        return []
    value = dep.get(dep.get("metric", "content_tracking_rate"))
    shown = f"{100*float(value):5.1f}" if value is not None else "  n/a"
    verdict = {True: "meets the declared dependence policy", False: "insufficient evidence or below a policy threshold", None: "not assessable"}[dep.get("eligible")]
    lines = [
        "",
        "Memory Dependence",
        f"  {dep.get('metric', 'content_tracking_rate'):28s} {shown}  floor {100*float(dep.get('floor', 0.0)):5.1f}  ({dep.get('eligible_n', 0)}/{dep.get('total_n', 0)} eligible changed-probe pairs)",
        f"  {verdict}",
    ]
    for row in dep.get('dimensions', []):
        lower = row.get('instance_tracking_lower_bound')
        bound = f'{100*lower:.1f}%' if lower is not None else 'n/a'
        status = {True: 'pass', False: 'below policy', None: 'unassessable'}[row['eligible']]
        lines.append(f"  {DISPLAY.get(row['dimension'], row['dimension']):28s} {row['eligible_instances']} Instances; "
                     f"{row['eligible_n']}/{row['total_n']} pairs; lower bound {bound}; {status}")
    return lines


def _transfer_lines(report: dict[str, Any]) -> list[str]:
    """Transfer Diagnostics and Transfer Profile, rendered only when present.

    These are supplemental diagnostics.  They do not enter the MIB Score, and
    an absent metric is omitted rather than shown as zero.
    """
    from .experimental.transfer import TRANSFER_DIAGNOSTICS_EXTENSION
    body = (report.get("extensions") or {}).get(TRANSFER_DIAGNOSTICS_EXTENSION)
    if not body:
        return []
    lines: list[str] = []
    aggregate = body.get("aggregate") or {}
    rows = [
        ("natural_transfer_gain", "Natural Transfer Gain", "pp"),
        ("formation_efficiency", "Formation Efficiency", "score"),
        ("routing_efficiency", "Historical Artifact Availability", "score"),
        ("natural_transfer_efficiency", "Natural Transfer Efficiency", "score"),
        ("oracle_routed_score", "Oracle-Routed Score", "score"),
        ("supported_transfer_success_rate", "Supported Transfer", "score"),
        ("near_match_resistance", "Near-Match Resistance", "score"),
        ("unsupported_memory_neutrality", "Unsupported Neutrality", "score"),
        ("compositional_transfer_score", "Compositional Transfer", "score"),
        ("negative_transfer_rate", "Negative Transfer Rate", "rate"),
    ]
    present = [(k, label, fmt) for k, label, fmt in rows if aggregate.get(k) is not None]
    if present:
        lines += ["", "Transfer Diagnostics"]
        for key, label, fmt in present:
            v = float(aggregate[key])
            if fmt == "pp":
                lines.append(f"  {label:28s} {100*v:+5.1f} pp")
            elif fmt == "rate":
                lines.append(f"  {label:28s} {100*v:5.1f}%")
            else:
                lines.append(f"  {label:28s} {100*v:5.1f}")

    profile = body.get("distance_profile") or []
    if profile:
        lines += ["", "Transfer Profile"]
        for entry in profile:
            label = f"{entry['class']} {entry.get('label', '')}".strip()
            lines.append(f"  {label:28s} {100*float(entry['score']):5.1f}")
    if lines:
        lines += ["", "  Transfer diagnostics are supplemental; they do not enter the MIB Score."]
    return lines
