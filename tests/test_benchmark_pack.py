from __future__ import annotations

import json

import pytest

from mib_runner.agents import ReferenceMemoryAgent
from mib_runner.benchmark import (
    dimension_aggregates,
    load_templates,
    paired_causal_metrics,
    run_benchmark_pack,
    run_materialized_pack,
    validate_causal_pairs,
)
from mib_runner.capability import render_capability_card
from mib_runner.materialize import materialize
from mib_runner.report import validate_report, verify_score
from mib_runner.runner import run_scenario
from mib_runner.validation import validate_scenario

from paths import DEV_PACK, PROFILES, REPORT_SCHEMA_PATH, SCENARIO_SCHEMA_PATH

SCHEMA = json.loads(SCENARIO_SCHEMA_PATH.read_text())
REPORT_SCHEMA = json.loads(REPORT_SCHEMA_PATH.read_text())
PROFILE = json.loads((PROFILES / "MIB-Core-0.1-Dev-M3.json").read_text())
PACK = DEV_PACK
CROSS = DEV_PACK / "cross"


def test_complete_public_dev_pack_has_24_valid_templates():
    templates = load_templates(PACK)
    assert len(templates) == 24
    ids = {t["id"] for t in templates}
    assert {"MIB-X-001", "MIB-X-002", "MIB-X-003"}.issubset(ids)
    for t in templates:
        vr = validate_scenario(t, SCHEMA)
        assert vr.valid, (t["id"], vr.errors)
        inst = materialize(t, 101)
        vr2 = validate_scenario(inst, SCHEMA)
        assert vr2.valid, (t["id"], vr2.errors)


def test_cross_suite_full_conditions_and_counterexample_behavior():
    for p in sorted(CROSS.glob("MIB-X-*.json")):
        s = materialize(json.loads(p.read_text()), 101)
        runs = run_scenario(scenario=s, agent_factory=ReferenceMemoryAgent, include_ablations=True, repetition=0, agent_seed=101)
        full = next(r for r in runs if r["condition"] == "full")
        assert full["scenario_score"] == 1.0, p
    s = materialize(json.loads((CROSS / "MIB-X-003.json").read_text()), 101)
    runs = run_scenario(scenario=s, agent_factory=ReferenceMemoryAgent, include_ablations=True, repetition=0, agent_seed=101)
    counter = next(r for r in runs if r["condition"] == "counterexample")
    assert counter["scenario_score"] < 1.0


def test_pack_level_execution_aggregation_bootstrap_and_report():
    templates = load_templates(PACK)
    report, summary = run_benchmark_pack(
        templates=templates,
        schema=SCHEMA,
        # The dev pack carries 3–4 Templates per Dimension; opt into small-sample
        # intervals here only to exercise the bootstrap plumbing.
        profile={**PROFILE, "statistics": {**PROFILE["statistics"], "min_templates_per_dimension": 1}},
        agent_factory=ReferenceMemoryAgent,
        instance_seeds=[101, 202],
        repetitions=2,
        include_ablations=True,
        bootstrap_resamples=50,
        bootstrap_seed=12345,
    )
    assert summary["template_count"] == 24
    assert summary["instance_count"] == 48
    assert summary["run_count"] > 48 * 2
    assert report["coverage"]["overall"] == 1.0
    assert len(report["aggregates"]["templates"]) == 24
    assert len(report["aggregates"]["dimensions"]) == 6
    assert report["aggregates"]["mib_score"]["partial"] is False
    assert report["aggregates"]["mib_score"]["official"] is False
    assert "ci" in report["aggregates"]["mib_score"]
    validate_report(report, REPORT_SCHEMA)
    verification = verify_score(report)
    assert verification["valid"], verification


def test_template_first_dimension_aggregation_ignores_instance_count_as_vote_count():
    profile = {"dimensions": {"retention_retrieval": {"weight": 1.0}}}
    templates = [
        {
            "template_id": "A",
            "instance_count": 1000,
            "dimension_scores": {"retention_retrieval": 100.0},
            "dimension_weights": {"retention_retrieval": 1.0},
        },
        {
            "template_id": "B",
            "instance_count": 1,
            "dimension_scores": {"retention_retrieval": 0.0},
            "dimension_weights": {"retention_retrieval": 1.0},
        },
    ]
    d = dimension_aggregates(templates, profile)[0]
    assert d["score"] == 50.0


def test_causal_pair_validator_detects_mismatch():
    full = {
        "condition": "full", "repetition": 0, "scenario_instance_id": "i", "template_id": "t",
        "instance_seed": 1, "agent_seed": "1:0", "probe_results": [{"probe_id": "p"}], "validity": {}
    }
    variant = {
        "condition": "relevant_ablation", "repetition": 0, "scenario_instance_id": "i", "template_id": "t",
        "instance_seed": 1, "agent_seed": "DIFFERENT", "probe_results": [{"probe_id": "p"}], "validity": {}
    }
    valid, pairs, notes = validate_causal_pairs([full, variant])
    assert not valid
    assert not pairs
    assert notes
    assert variant["validity"]["causal_pair_valid"] is False


def test_relevant_ablation_takes_precedence_over_no_memory_for_benefit():
    def run(condition, score, ablation_id=None):
        row = {
            "condition": condition,
            "repetition": 0,
            "validity": {"causal_pair_valid": True},
            "probe_results": [{
                "probe_id": "p",
                "outcome": "scored",
                "score": score,
                "weight": 1.0,
            }],
        }
        if ablation_id:
            row["ablation_id"] = ablation_id
        return row

    metrics = paired_causal_metrics([
        run("full", 1.0),
        run("relevant_ablation", 0.5, "a-relevant"),
        run("no_memory", 0.0, "a-none"),
    ])
    benefit = next(m for m in metrics if m["name"] == "memory_benefit")
    assert benefit["value"] == pytest.approx(0.5)
    assert benefit["comparison_condition"] == "relevant_ablation"


def test_materialized_pack_rejects_missing_required_templates_before_execution():
    template = json.loads((PACK / "recall" / "MIB-RET-001.json").read_text())
    instance = materialize(template, 101)
    profile = {
        "id": "MIB-Test-Missing",
        "version": "0.1.0",
        "official": True,
        "track": "integrated_agent",
        "scale": "MIB-S",
        "required_coverage": 1.0,
        "required_templates": ["MIB-RET-001", "MIB-RET-999"],
        "dimensions": {"retention_retrieval": {"weight": 1.0}},
    }
    with pytest.raises(ValueError, match="missing Templates.*MIB-RET-999"):
        run_materialized_pack(
            templates=[template],
            instances=[instance],
            schema=SCHEMA,
            profile=profile,
            agent_factory=ReferenceMemoryAgent,
            repetitions=1,
        )


def test_capability_card_uses_the_report_official_status():
    templates = load_templates(PACK)
    report, _ = run_benchmark_pack(
        templates=templates,
        schema=SCHEMA,
        profile=PROFILE,
        agent_factory=ReferenceMemoryAgent,
        instance_seeds=[101],
        repetitions=1,
        include_ablations=False,
    )
    report["aggregates"]["mib_score"].update({"official": True, "partial": False})
    card = render_capability_card(report)
    assert "Official Hidden Eval leaderboard score." in card
    assert "Development profile" not in card
