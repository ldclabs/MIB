from __future__ import annotations

from typing import Any

from .experimental.transfer import TRANSFER_DIAGNOSTICS_EXTENSION

DISPLAY = {
    "retention_retrieval": "Retention & Retrieval",
    "temporal_memory": "Temporal Memory",
    "epistemic_memory": "Epistemic Memory",
    "experience_memory": "Experience Memory",
    "skill_learning_transfer": "Skill Learning & Transfer",
    "selective_forgetting": "Selective Forgetting",
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
        "",
        f"MIB Score {score['final_score']:.1f}",
    ]
    if ci:
        lines.append(f"95% CI    [{ci['lower']:.1f}, {ci['upper']:.1f}]")
    lines += ["", "Capability"]
    for d in report["aggregates"]["dimensions"]:
        lines.append(f"  {DISPLAY.get(d['dimension'], d['dimension']):28s} {d['score']:5.1f}  coverage {100*d['coverage']:5.1f}%")
    lines += ["", "Causal Diagnostics"]
    for name, label, fmt in [
        ("memory_benefit", "Memory Benefit", "pp"),
        ("memory_harm", "Memory Harm", "pp"),
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
            lines.append(f"  {label:28s} {100*v:+5.1f} pp")
        elif fmt == "rate":
            lines.append(f"  {label:28s} {100*v:5.1f}%")
        else:
            lines.append(f"  {label:28s} {100*v:5.1f}")
    lines += _behaviour_lines(report)
    lines += _retention_lines(report)
    lines += _dependence_lines(report)
    lines += _transfer_lines(report)
    lines += [
        "",
        f"Coverage  {100*report['coverage']['overall']:.1f}%",
        f"Execution Failure Rate  {100*report['execution'].get('execution_failure_rate', 0.0):.2f}%",
        "",
        score_status,
        "```",
        "",
    ]
    return "\n".join(lines)


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
        ("memory_induced_error_rate", "Memory-Induced Errors", "rate"),
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
    verdict = {True: "earned through memory", False: "BELOW FLOOR — not a memory score", None: "not assessable"}[dep.get("eligible")]
    return [
        "",
        "Memory Dependence",
        f"  {dep.get('metric', 'content_tracking_rate'):28s} {shown}  floor {100*float(dep.get('floor', 0.0)):5.1f}  ({dep.get('eligible_n', 0)}/{dep.get('total_n', 0)} programs with counterfactual pairs)",
        f"  {verdict}",
    ]


def _transfer_lines(report: dict[str, Any]) -> list[str]:
    """Transfer Diagnostics and Transfer Profile, rendered only when present.

    These are supplemental diagnostics.  They do not enter the MIB Score, and
    an absent metric is omitted rather than shown as zero.
    """
    body = (report.get("extensions") or {}).get(TRANSFER_DIAGNOSTICS_EXTENSION)
    if not body:
        return []
    lines: list[str] = []
    aggregate = body.get("aggregate") or {}
    rows = [
        ("natural_transfer_gain", "Natural Transfer Gain", "pp"),
        ("formation_efficiency", "Formation Efficiency", "score"),
        ("routing_efficiency", "Routing Efficiency", "score"),
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
