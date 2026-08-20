from __future__ import annotations

from typing import Any

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
        ("negative_transfer", "Negative Transfer", "score"),
    ]:
        m = _metric(report, name)
        if not m:
            continue
        v = float(m["value"])
        if fmt == "pp":
            lines.append(f"  {label:28s} {100*v:+5.1f} pp")
        else:
            lines.append(f"  {label:28s} {100*v:5.1f}")
    lines += [
        "",
        f"Coverage  {100*report['coverage']['overall']:.1f}%",
        f"Execution Failure Rate  {100*report['execution'].get('execution_failure_rate', 0.0):.2f}%",
        "",
        "Development profile — not an official Hidden Eval leaderboard score.",
        "```",
        "",
    ]
    return "\n".join(lines)
