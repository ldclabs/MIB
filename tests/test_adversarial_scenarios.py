"""Adversarial interrogation-installation lane (MIB-ADV-*).

Evaluates the invariant that asking whether X is true must never install X into
memory. Each Template pairs a clean baseline run against a
``replay_with_injections`` condition containing solely questions — never
assertions — about an unestablished value. Because correct answers are
identical across conditions, any paired performance drop isolates false
installation, as demonstrated by the naive reference memory agent.
"""

from __future__ import annotations

import json

import pytest

from mib_runner.agents import ReferenceMemoryAgent
from mib_runner.benchmark import load_templates, paired_causal_metrics, run_benchmark_pack
from mib_runner.materialize import materialize
from mib_runner.report import validate_report, verify_score
from mib_runner.runner import run_scenario
from mib_runner.validation import validate_scenario

from paths import ADVERSARIAL_PACK, PROFILES, REPORT_SCHEMA_PATH, SCENARIO_SCHEMA_PATH

SCHEMA = json.loads(SCENARIO_SCHEMA_PATH.read_text())
REPORT_SCHEMA = json.loads(REPORT_SCHEMA_PATH.read_text())
PROFILE = json.loads((PROFILES / "MIB-Adversarial-0.1-Dev.json").read_text())

# The never-established value each Template interrogates about, by ground-truth key.
NEVER_KEY = {
    "MIB-ADV-001": "never_established",
    "MIB-ADV-002": "never_asserted",
    "MIB-ADV-003": "never_required",
}


def adversarial_files():
    return sorted(ADVERSARIAL_PACK.glob("MIB-ADV-*.json"))


def test_adversarial_templates_validate_and_materialize():
    files = adversarial_files()
    assert len(files) == 3
    for p in files:
        template = json.loads(p.read_text())
        v = validate_scenario(template, SCHEMA)
        assert v.valid, (p, v.errors)
        inst = materialize(template, 101)
        v2 = validate_scenario(inst, SCHEMA)
        assert v2.valid, (p, v2.errors)


def test_interrogated_value_appears_only_inside_questions():
    """Injection-surface hygiene: the never-established value must not appear in
    any base timeline event — only in the harmful Ablation's injected questions
    (and in Probe wording, which is constant across conditions)."""
    for p in adversarial_files():
        inst = materialize(json.loads(p.read_text()), 101)
        fake = str(inst["world"]["hidden_ground_truth"][NEVER_KEY[inst["id"]]]).casefold()
        for event in inst["timeline"]:
            text = (event.get("content") or "") + json.dumps(event.get("payload") or {}, ensure_ascii=False)
            assert fake not in text.casefold(), (inst["id"], event["id"])
        harmful = next(a for a in inst["ablations"] if a["kind"] == "harmful_memory")
        assert any(fake in (i.get("content") or "").casefold() for i in harmful["injections"]), inst["id"]


def test_full_conditions_pass():
    for p in adversarial_files():
        s = materialize(json.loads(p.read_text()), 101)
        runs = run_scenario(scenario=s, agent_factory=ReferenceMemoryAgent, include_ablations=False, agent_seed=101)
        assert runs[0]["status"] == "succeeded"
        assert runs[0]["scenario_score"] == 1.0, p


def test_interrogation_installs_on_naive_memory_and_is_measured():
    for p in adversarial_files():
        s = materialize(json.loads(p.read_text()), 101)
        runs = run_scenario(scenario=s, agent_factory=ReferenceMemoryAgent, include_ablations=True, repetition=0, agent_seed=101)
        by_condition = {r["condition"]: r for r in runs}
        full = by_condition["full"]
        assert full["scenario_score"] == 1.0, p
        # The naive fixture lets questions become memory; the paired condition
        # sees it.  Nothing but the questions differs between the two runs.
        assert by_condition["harmful_memory"]["scenario_score"] < 1.0, p
        assert by_condition["relevant_ablation"]["scenario_score"] < 1.0, p
        assert by_condition["irrelevant_ablation"]["scenario_score"] == 1.0, p

        metrics = {m["name"]: m["value"] for m in paired_causal_metrics(runs)}
        assert metrics["memory_harm"] > 0, p
        assert metrics["harm_resistance"] < 1.0, p
        assert metrics["memory_benefit"] > 0, p
        assert metrics["irrelevant_memory_stability"] == pytest.approx(1.0), p


def test_adversarial_pack_aggregates_and_reports():
    templates = load_templates(ADVERSARIAL_PACK)
    assert len(templates) == 3
    report, summary = run_benchmark_pack(
        templates=templates,
        schema=SCHEMA,
        profile=PROFILE,
        agent_factory=ReferenceMemoryAgent,
        instance_seeds=[101],
        repetitions=1,
        include_ablations=True,
        bootstrap_resamples=20,
        bootstrap_seed=7,
    )
    assert summary["template_count"] == 3
    assert report["coverage"]["overall"] == 1.0
    assert report["aggregates"]["mib_score"]["official"] is False
    validate_report(report, REPORT_SCHEMA)
    assert verify_score(report)["valid"]
