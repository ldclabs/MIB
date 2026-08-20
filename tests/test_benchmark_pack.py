from __future__ import annotations

import json

from mib_runner.agents import ReferenceMemoryAgent
from mib_runner.benchmark import (
    dimension_aggregates,
    load_templates,
    run_benchmark_pack,
    validate_causal_pairs,
)
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
        profile=PROFILE,
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
