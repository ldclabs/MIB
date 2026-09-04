"""MIB v0.2: world model, generated programs, distance ladder, counterfactual content, lived past, prospective memory."""

from __future__ import annotations

import copy
import json
import random

import pytest

from mib_runner.agents import (ConsolidatingAgent, NoMemoryAgent, OvergeneralizingAgent, RecencyAgent, StructuredMemoryAgent,
                               WindowMemoryAgent)
from mib_runner.benchmark import run_generated_pack
from mib_runner.generate import PROGRAMS, generate_instance, generate_pack, program_descriptor
from mib_runner.report import validate_report, verify_score
from mib_runner.runner import run_scenario
from mib_runner.scoring import ci_bca, ci_percentile, full_run_metrics, paired_causal_metrics
from mib_runner.validation import validate_scenario
from mib_runner.worldmodel import Assertion, Source, WorldModel, oracle_from_result

from paths import PROFILES, REPORT_SCHEMA_PATH, SCENARIO_SCHEMA_PATH

SCHEMA = json.loads(SCENARIO_SCHEMA_PATH.read_text())
REPORT_SCHEMA = json.loads(REPORT_SCHEMA_PATH.read_text())
PROFILE = json.loads((PROFILES / "MIB-Core-0.2-Dev.json").read_text())


# ------------------------------------------------------------------ world model
def _model() -> WorldModel:
    m = WorldModel()
    m.add_source(Source("alice", "person", 0.8, "Alice"))
    m.add_source(Source("bob", "person", 0.5, "Bob"))
    m.add_source(Source("calendar", "tool", 1.0, "Calendar"))
    m.add(Assertion("e1", 1, "alice", "alice", "timezone", "UTC+8", "state", True))
    m.add(Assertion("e2", 2, "alice", "alice", "timezone", "UTC+1", "update", True))
    m.add(Assertion("q1", 3, "alice", "alice", "timezone", "UTC+3", "question", False))
    m.add(Assertion("b1", 4, "alice", "alice", "birthday", "May 12", "state", True))
    m.add(Assertion("b2", 5, "alice", "alice", "birthday", "May 21", "correction", True, supersedes="b1"))
    m.add(Assertion("m1", 6, "alice", "review", "meeting_start", "15:00", "state", True))
    m.add(Assertion("m2", 7, "bob", "review", "meeting_start", "16:00", "contradiction", False))
    return m


def test_truth_history_evidence_and_status():
    m = _model()
    assert m.evaluate({"op": "current", "subject": "alice", "attribute": "timezone"}).value == "UTC+1"
    assert m.evaluate({"op": "as_of", "subject": "alice", "attribute": "timezone", "before_event": "e2"}).value == "UTC+8"
    # A correction rewrites truth retroactively but the historical statement survives.
    assert m.evaluate({"op": "current", "subject": "alice", "attribute": "birthday"}).value == "May 21"
    assert m.evaluate({"op": "first_stated", "subject": "alice", "attribute": "birthday"}).value == "May 12"
    # A question asserts nothing; it only becomes a forbidden value.
    assert "UTC+3" in m.values_seen("alice", "timezone")
    assert m.evaluate({"op": "known", "subject": "alice", "attribute": "office"}).kind == "unknown"
    assert m.evaluate({"op": "status", "subject": "review", "attribute": "meeting_start"}).status == "contested"
    m.add(Assertion("c1", 8, "calendar", "review", "meeting_start", "15:00", "observation", True))
    assert m.evaluate({"op": "status", "subject": "review", "attribute": "meeting_start"}).status == "resolved"
    assert m.evaluate({"op": "said_by", "source": "bob", "subject": "review", "attribute": "meeting_start"}).value == "16:00"


def test_support_sets_redundancy_leak_proof_and_counterfactual_twin():
    m = _model()
    m.add(Assertion("c1", 8, "calendar", "review", "meeting_start", "15:00", "observation", True))
    q = {"op": "current", "subject": "review", "attribute": "meeting_start"}
    support = m.support_set(q)
    assert not support.necessary and support.groups == [["m1", "c1"]]
    assert m.leak_free(q, support.minimal)
    q2 = {"op": "current", "subject": "alice", "attribute": "timezone"}
    assert m.support_set(q2).necessary == ["e2"]
    twin = m.with_value("e2", "UTC+9")
    assert twin.evaluate(q2).value == "UTC+9" and m.evaluate(q2).value == "UTC+1"
    oracle = oracle_from_result(m.evaluate(q2), forms=lambda v: [v], other_values=m.values_seen("alice", "timezone"))
    assert oracle["accepted"] == ["UTC+1"] and set(oracle["forbidden"]) == {"UTC+8", "UTC+3"}


# ------------------------------------------------------------------- generation
@pytest.mark.parametrize("program_id", sorted(PROGRAMS))
def test_generated_instances_are_valid_deterministic_and_leak_free(program_id):
    a = generate_instance(program_id, 11, rung=1)
    b = generate_instance(program_id, 11, rung=1)
    assert a == b
    vr = validate_scenario(a, SCHEMA)
    assert vr.valid, vr.errors
    assert a["instantiation"]["program"] == program_id and a["instantiation"]["rung"] == 1
    # Facts are identical across rungs; only the interference block grows.
    r0 = generate_instance(program_id, 11, rung=0)
    facts = lambda s: [(e["id"], e.get("content"), e.get("payload")) for e in s["timeline"] if not e["id"].startswith("d-")]
    assert facts(r0) == facts(a)
    assert sum(e["id"].startswith("d-") for e in a["timeline"]) == 20
    assert sum(e["id"].startswith("d-") for e in r0["timeline"]) == 0
    for ab in a["ablations"]:
        if ab["method"] == "swap_parameter":
            for pid, oracle in ab["counterfactual"]["oracle"].items():
                base = next(p["oracle"] for p in a["probes"] if p["id"] == pid)
                assert oracle["accepted"] != base["accepted"]
                assert base["accepted"][0] in oracle.get("forbidden", [])


def test_interference_never_carries_an_answer_value():
    for pid in ("mib.recall.v1", "mib.temporal.v1", "mib.epistemic.v1"):
        s = generate_instance(pid, 5, rung=2)
        answers = {v for p in s["probes"] for v in p["oracle"].get("accepted", []) if v not in ("unknown", "contested", "resolved")}
        for e in s["timeline"]:
            if e["id"].startswith("d-"):
                for v in answers:
                    assert v not in (e.get("content") or ""), (e, v)


def test_pack_generation_covers_programs_seeds_and_ladder():
    descriptors, instances = generate_pack(PROFILE, seeds=[1, 2])
    assert len(descriptors) == len(PROFILE["programs"])
    assert len(instances) == len(PROFILE["programs"]) * 2 * len(PROFILE["ladder"])
    assert program_descriptor("mib.temporal.v1")["scoring"]["dimension_weights"] == {"temporal_memory": 1.0}


# ------------------------------------------------------------------------ runner
def _score(runs, condition, ablation_id=None):
    return next(r["scenario_score"] for r in runs if r["condition"] == condition and (ablation_id is None or r.get("ablation_id") == ablation_id))


def test_lived_past_is_the_agents_own_experience():
    s = generate_instance("mib.experience.v1", 3, rung=0)
    runs = run_scenario(scenario=s, agent_factory=StructuredMemoryAgent, include_ablations=True)
    full = runs[0]
    assert full["scenario_score"] == 1.0
    assert "t-past" in full["extensions"]["mib.runner.experience_trace"]
    trace = full["extensions"]["mib.runner.experience_trace"]["t-past"]
    assert any(r["result"].get("error") == "wrong_target" for r in trace), "the past task must be lived, including its failure"
    probe = full["probe_results"][0]
    assert probe["recurrence"] == {"eligible": True, "recurred": False}
    # Withholding the lived task removes the lesson: the Agent repeats the failure.
    ablated = next(r for r in runs if r["condition"] == "relevant_ablation")
    assert ablated["scenario_score"] < 1.0
    assert ablated["probe_results"][0]["recurrence"]["recurred"] is True
    naive = run_scenario(scenario=s, agent_factory=NoMemoryAgent, include_ablations=False)[0]
    assert naive["scenario_score"] == 0.0


def test_prospective_emission_fires_on_trigger_and_not_before():
    s = generate_instance("mib.prospective.v1", 9, rung=0)
    runs = run_scenario(scenario=s, agent_factory=StructuredMemoryAgent, include_ablations=True)
    full = runs[0]
    assert full["scenario_score"] == 1.0
    assert full["extensions"]["mib.runner.emissions"]
    assert _score(runs, "relevant_ablation") == 0.0
    blind = run_scenario(scenario=s, agent_factory=NoMemoryAgent, include_ablations=False)[0]
    trigger = next(p for p in blind["probe_results"] if p["probe_id"] == "p-trigger")
    assert trigger["failure_codes"] == ["commitment_miss"]


def test_counterfactual_content_tracking_separates_memory_from_priors():
    s = generate_instance("mib.temporal.v1", 4, rung=0)
    runs = run_scenario(scenario=s, agent_factory=StructuredMemoryAgent, include_ablations=True)
    swap = next(r for r in runs if r["condition"] == "counterfactual_content")
    row = next(p for p in swap["probe_results"] if p["probe_id"] == "p-current")
    assert row["counterfactual"] == {"tracks": True, "stale": False}
    # The replaced event must reach the Agent with the counterfactual value, not the original.
    ab = next(a for a in s["ablations"] if a["method"] == "swap_parameter")
    pivot = ab["targets"]["event_ids"][0]
    assert ab["counterfactual"]["events"][pivot]["content"] != next(e["content"] for e in s["timeline"] if e["id"] == pivot)


def test_structured_answers_and_abstention_are_scored_by_field():
    s = generate_instance("mib.epistemic.v1", 2, rung=0)
    full = run_scenario(scenario=s, agent_factory=StructuredMemoryAgent, include_ablations=False)[0]
    by = {p["probe_id"]: p for p in full["probe_results"]}
    assert by["p-unknown"]["score"] == 1.0
    assert by["p-status"]["score"] == 1.0
    blind = run_scenario(scenario=s, agent_factory=NoMemoryAgent, include_ablations=False)[0]
    b = {p["probe_id"]: p for p in blind["probe_results"]}
    assert b["p-unknown"]["score"] == 1.0
    assert b["p-bday"]["failure_codes"] == ["retrieval_miss"]
    recency = run_scenario(scenario=s, agent_factory=RecencyAgent, include_ablations=False)[0]
    r = {p["probe_id"]: p for p in recency["probe_results"]}
    assert "stale_memory_adoption" in r["p-status"]["failure_codes"] or "stale_memory_adoption" in r["p-use"]["failure_codes"]


def test_maintenance_window_calls_the_agent_hook():
    s = generate_instance("mib.temporal.v1", 6, rung=0)
    # Every program consolidates once before its interference block and pairs it with a no_maintenance control.
    assert [e["id"] for e in s["timeline"] if e["type"] == "maintenance_window"] == ["mw-1"]
    assert any(a["kind"] == "no_maintenance" and a["targets"]["event_ids"] == ["mw-1"] for a in s["ablations"])
    calls = []

    class Hooked(StructuredMemoryAgent):
        def maintain(self, **kw):
            calls.append(kw.get("budget"))
            return {"accepted": True}

    assert validate_scenario(s, SCHEMA).valid
    run_scenario(scenario=s, agent_factory=Hooked, include_ablations=False)
    assert calls == ["PT1H"]


# --------------------------------------------------------------------- the pack
def _pack(agent_factory, seeds=(1, 2), **kw):
    profile = {**PROFILE, "statistics": {**PROFILE["statistics"], "min_templates_per_dimension": 2}}
    return run_generated_pack(profile=profile, schema=SCHEMA, agent_factory=agent_factory, seeds=list(seeds), repetitions=1, **kw)


def test_generated_pack_orders_the_fixtures_and_reports_retention_and_dependence():
    structured, s_sum = _pack(StructuredMemoryAgent)
    window, w_sum = _pack(WindowMemoryAgent)
    blind, b_sum = _pack(NoMemoryAgent)
    assert s_sum["mib_score"] > w_sum["mib_score"] > b_sum["mib_score"]
    assert s_sum["mib_score"] >= 90.0 and b_sum["mib_score"] < 30.0
    # Retention: the window fixture decays along the ladder, the structured fixture does not.
    for tid, curve in w_sum["retention"].items():
        assert curve[0] >= curve[-1], (tid, curve)
    assert any(curve[0] > curve[-1] for curve in w_sum["retention"].values())
    assert all(curve[0] == curve[-1] for curve in s_sum["retention"].values())
    # Memory dependence: earned through memory for the structured fixture, not assessable for the blind one.
    assert structured["memory_dependence"]["eligible"] is True
    assert structured["memory_dependence"]["content_tracking_rate"] == 1.0
    assert blind["memory_dependence"]["eligible"] in (False, None)
    assert any(w["code"] == "memory_dependence.below_floor" for w in blind["warnings"])
    for report in (structured, window, blind):
        validate_report(report, REPORT_SCHEMA)
        v = verify_score(report)
        assert v["valid"] and v["verification_level"] == "full", v["errors"][:3]
    assert structured["mib"] == "0.2" and structured["benchmark"]["mib_version"] == "0.2"
    assert "causal_memory_impact" not in s_sum["dimensions"]
    assert set(s_sum["dimensions"]) == set(PROFILE["dimensions"])


def test_bootstrap_units_are_instances_for_generated_packs():
    report, summary = _pack(StructuredMemoryAgent, seeds=(1, 2, 3), bootstrap_resamples=25)
    assert report["statistics"]["bootstrap"]["min_templates_per_dimension"] == 2
    assert "ci" in report["aggregates"]["mib_score"]
    validate_report(report, REPORT_SCHEMA)


# --------------------------------------------------------- appendix A, implemented
def test_retraction_is_forgotten_and_neighbours_are_kept():
    s = generate_instance("mib.forgetting.v1", 5, rung=0)
    assert s["dimensions"] == ["selective_forgetting"]
    forgotten = next(p for p in s["probes"] if p["id"] == "p-forgotten")
    assert forgotten["oracle"]["expected_status"] == "unknown" and forgotten["oracle"]["forbidden"]
    assert {a["id"] for a in s["ablations"]} >= {"a-relevant-p-forgotten", "a-relevant-p-kept", "a-swap-p-kept", "a-no-maintenance"}
    runs = run_scenario(scenario=s, agent_factory=StructuredMemoryAgent, include_ablations=True)
    assert runs[0]["scenario_score"] == 1.0
    # Without the retraction the withdrawn value is used again: the relevant Ablation of forgetting.
    assert _score(runs, "relevant_ablation", "a-relevant-p-forgotten") == 0.0
    recency = run_scenario(scenario=s, agent_factory=RecencyAgent, include_ablations=False)[0]
    by = {p["probe_id"]: p for p in recency["probe_results"]}
    assert by["p-forgotten"]["score"] == 0.0 and "false_certainty" in by["p-forgotten"]["failure_codes"]
    assert by["p-kept"]["score"] == 1.0
    blind = run_scenario(scenario=s, agent_factory=NoMemoryAgent, include_ablations=False)[0]
    by = {p["probe_id"]: p for p in blind["probe_results"]}
    assert by["p-forgotten"]["score"] == 1.0 and by["p-kept"]["score"] == 0.0


def test_self_rule_holds_against_a_task_that_asks_for_the_forbidden_step():
    s = generate_instance("mib.prospective.v1", 9, rung=0)
    runs = run_scenario(scenario=s, agent_factory=StructuredMemoryAgent, include_ablations=True)
    by = {p["probe_id"]: p for p in runs[0]["probe_results"]}
    assert by["p-self"]["score"] == 1.0
    assert _score(runs, "relevant_ablation", "a-relevant-p-self") < 1.0
    blind = run_scenario(scenario=s, agent_factory=NoMemoryAgent, include_ablations=False)[0]
    row = next(p for p in blind["probe_results"] if p["probe_id"] == "p-self")
    assert row["score"] < 1.0 and "self_model_drift" in row["failure_codes"]
    assert {m["name"]: m["value"] for m in full_run_metrics([blind])}["self_limitation_continuity"] < 1.0


def test_negative_transfer_control_catches_overgeneralization():
    s = generate_instance("mib.skill.v1", 3, rung=0)
    assert [p["id"] for p in s["probes"]] == ["p-nonmatch", "p-match"]
    good = {m["name"]: m["value"] for m in paired_causal_metrics(run_scenario(scenario=s, agent_factory=StructuredMemoryAgent))}
    bad = {m["name"]: m["value"] for m in paired_causal_metrics(run_scenario(scenario=s, agent_factory=OvergeneralizingAgent))}
    assert good["negative_transfer"] == 0.0 and good["negative_transfer_rate"] == 0.0 and good["negative_transfer_resistance"] == 1.0
    assert bad["negative_transfer"] > 0.0 and bad["negative_transfer_rate"] == 1.0 and bad["negative_transfer_resistance"] < 1.0
    assert bad["memory_benefit"] == good["memory_benefit"]   # the skill still transfers where it applies


def test_lived_trials_form_a_learning_curve():
    s = generate_instance("mib.experience.v1", 3, rung=0)
    full = run_scenario(scenario=s, agent_factory=StructuredMemoryAgent, include_ablations=False)[0]
    assert [t["task_id"] for t in full["task_results"]] == ["t-past", "t-past-2"]
    assert full["task_results"][0]["score"] < full["task_results"][1]["score"] == 1.0
    m = {x["name"]: x["value"] for x in full_run_metrics([full])}
    assert m["learning_gain"] > 0 and m["area_under_learning_curve"] > 0.5 and m["error_avoidance_score"] == 1.0
    blind = run_scenario(scenario=s, agent_factory=NoMemoryAgent, include_ablations=False)[0]
    mb = {x["name"]: x["value"] for x in full_run_metrics([blind])}
    assert mb["learning_gain"] == 0.0 and mb["error_recurrence_rate"] == 1.0 and mb["memory_induced_error_rate"] == 1.0


def test_consolidation_is_load_bearing_for_an_agent_that_maintains():
    s = generate_instance("mib.temporal.v1", 4, rung=1)
    window = {m["name"]: m["value"] for m in paired_causal_metrics(run_scenario(scenario=s, agent_factory=WindowMemoryAgent))}
    consolidating = {m["name"]: m["value"] for m in paired_causal_metrics(run_scenario(scenario=s, agent_factory=ConsolidatingAgent))}
    assert window["consolidation_benefit"] == 0.0
    assert consolidating["consolidation_benefit"] > 0.0 and consolidating["content_tracking_rate"] == 1.0


def test_behaviour_diagnostics_read_off_full_runs():
    s = generate_instance("mib.epistemic.v1", 2, rung=0)   # a seed whose contradiction stays unresolved
    assert not any(e["id"] == "e-cal" for e in s["timeline"])
    use = next(p for p in s["probes"] if p["id"] == "p-use")
    assert "authority_confusion" in use["oracle"]["failure_code_by_value"].values()
    recency = run_scenario(scenario=s, agent_factory=RecencyAgent, include_ablations=False)[0]
    row = next(p for p in recency["probe_results"] if p["probe_id"] == "p-use")
    assert "authority_confusion" in row["failure_codes"] and "authority_confusion" in row["traps"]
    m = {x["name"]: x["value"] for x in full_run_metrics([recency])}
    assert m["authority_confusion_rate"] == 1.0 and m["source_attribution_accuracy"] == 1.0 and m["historical_fidelity"] == 1.0
    assert 0 < m["memory_induced_error_rate"] < 1
    structured = run_scenario(scenario=s, agent_factory=StructuredMemoryAgent, include_ablations=False)[0]
    ms = {x["name"]: x["value"] for x in full_run_metrics([structured])}
    assert ms["authority_confusion_rate"] == 0.0 and ms["memory_induced_error_rate"] == 0.0


def test_mib_m_ladder_and_distance_units():
    ladder = [0, 100, 1000]
    far = generate_instance("mib.temporal.v1", 7, rung=2, ladder=ladder)
    near = generate_instance("mib.temporal.v1", 7, rung=0, ladder=ladder)
    inst = far["instantiation"]
    assert inst["interference_count"] == 1000 and inst["interference_tokens"] > 1000 and inst["distance_hours"] > 0
    assert near["instantiation"]["interference_tokens"] == 0 and near["instantiation"]["distance_hours"] < inst["distance_hours"]
    assert validate_scenario(far, SCHEMA).valid
    # Distance is the only variable: the questions and their accepted answers do not change along the ladder.
    assert [(p["input"]["content"], p["oracle"]["accepted"]) for p in far["probes"]] == \
           [(p["input"]["content"], p["oracle"]["accepted"]) for p in near["probes"]]
    assert run_scenario(scenario=far, agent_factory=StructuredMemoryAgent, include_ablations=False)[0]["scenario_score"] == 1.0
    profile = json.loads((PROFILES / "MIB-Core-0.2-Dev-M.json").read_text())
    assert profile["scale"] == "MIB-M" and profile["ladder"] == ladder and profile["statistics"]["interval_method"] == "bca"


def test_bca_interval_corrects_a_skewed_bootstrap():
    rng = random.Random(1)
    draws = [min(100.0, 90.0 + abs(rng.gauss(0, 4))) for _ in range(2000)]
    jack = [95.0 + rng.gauss(0, 1) for _ in range(12)]
    bca = ci_bca(draws, 95.0, jack, 0.95, 2000, 1)
    pct = ci_percentile(draws, 0.95, "hierarchical_bootstrap_percentile", 2000, 1)
    assert bca["method"] == "bca" and bca["lower"] <= 95.0 <= bca["upper"]
    assert (bca["lower"], bca["upper"]) != (pct["lower"], pct["upper"])
    assert ci_bca([100.0] * 50, 100.0, [100.0] * 5, 0.95, 50, 1)["method"] == "hierarchical_bootstrap_percentile"


def test_bca_intervals_and_efficiency_on_a_generated_pack():
    profile = {**PROFILE, "statistics": {**PROFILE["statistics"], "min_templates_per_dimension": 2, "interval_method": "bca"}}
    report, _ = run_generated_pack(profile=profile, schema=SCHEMA, agent_factory=WindowMemoryAgent, seeds=[1, 2], repetitions=1,
                                   bootstrap_resamples=100)
    stats = report["statistics"]
    assert stats["bootstrap"]["method"] == "bca"
    assert stats["mib_score"]["ci"]["method"] in ("bca", "hierarchical_bootstrap_percentile")
    assert report["efficiency"]["runner_measured"]["tool_calls_total"] > 0
    assert any(r.get("interference_tokens") is not None for r in report["retention"][0]["rungs"])
    validate_report(report, REPORT_SCHEMA)
    v = verify_score(report)
    assert v["valid"] and v["verification_level"] == "full", v["errors"][:3]
