"""Regression tests for the 2026-09-04 review fixes (REVIEW-2026-09-04.md)."""

from __future__ import annotations

import copy
import json

import pytest

from mib_runner.agents import ReferenceMemoryAgent
from mib_runner.benchmark import load_templates, run_benchmark_pack, select_profile_templates
from mib_runner.evaluator import evaluate_set_match, evaluate_trajectory
from mib_runner.materialize import materialize
from mib_runner.report import build_basic_report, validate_report, verify_score
from mib_runner.runner import _virtual_time_for_event, run_scenario
from mib_runner.scoring import HMB, HRS, IMS, causal_score01
from mib_runner.types import ActStep, AgentOutput
from mib_runner.util import advance_iso_time
from mib_runner.validation import validate_scenario

from paths import DEV_PACK, PROFILES, REPORT_SCHEMA_PATH, SCENARIO_SCHEMA_PATH

SCHEMA = json.loads(SCENARIO_SCHEMA_PATH.read_text())
REPORT_SCHEMA = json.loads(REPORT_SCHEMA_PATH.read_text())
PROFILE = json.loads((PROFILES / "MIB-Core-0.1-Dev-M3.json").read_text())


class MemoryBlindAgent:
    """Ignores every observation: answers unknown, abstains from acting."""

    def describe(self):
        return {
            "protocol": "mib-agent/0.1",
            "implementation": {"name": "MemoryBlind", "version": "0"},
            "capabilities": {"observe": True, "respond": True, "act": True},
        }

    def reset(self, **_):
        return {"accepted": True}

    def observe(self, **_):
        return {"accepted": True, "emissions": []}

    def respond(self, **_):
        return AgentOutput(type="message", content="unknown")

    def act(self, **_):
        return ActStep(type="abstention", content="no policy")


class LoopingAgent(MemoryBlindAgent):
    def __init__(self) -> None:
        self.n = 0

    def act(self, **_):
        self.n += 1
        return ActStep(type="tool_call", tool_call_id=f"c{self.n}", tool="deployment.inspect_target", arguments={})


class RogueToolAgent(MemoryBlindAgent):
    def act(self, **_):
        return ActStep(type="tool_call", tool_call_id="c1", tool="deployment.drop_database", arguments={})


class NoActAgent(ReferenceMemoryAgent):
    def describe(self):
        d = super().describe()
        d["capabilities"]["act"] = False
        return d


def _pack_report(agent_factory, profile=PROFILE, **kw):
    return run_benchmark_pack(
        templates=load_templates(DEV_PACK), schema=SCHEMA, profile=profile, agent_factory=agent_factory,
        instance_seeds=[101], repetitions=1, include_ablations=True, **kw,
    )


def test_causal_dimension_is_zero_for_a_memory_blind_agent():
    report, summary = _pack_report(MemoryBlindAgent)
    assert summary["dimensions"]["causal_memory_impact"] == 0.0
    assert summary["dimensions"]["retention_retrieval"] == 0.0
    # IMS stays visible as a raw diagnostic even though it earns no dimension credit.
    assert summary["causal_metrics"]["irrelevant_memory_stability"] == 1.0
    assert not any(m["name"] == "causal_memory_impact" for m in report["causal_metrics"])


def test_causal_score_formula_gates_selectivity_by_benefit():
    assert causal_score01([{"name": IMS, "value": 1.0}, {"name": HRS, "value": 1.0}]) == (None, {})
    assert causal_score01([{"name": HMB, "value": 0.0}, {"name": IMS, "value": 1.0}, {"name": HRS, "value": 1.0}])[0] == 0.0
    assert causal_score01([{"name": HMB, "value": 1.0}, {"name": IMS, "value": 1.0}, {"name": HRS, "value": 1.0}])[0] == 1.0
    score, _ = causal_score01([{"name": HMB, "value": 0.8}, {"name": IMS, "value": 0.5}])
    assert score == pytest.approx(0.8 * (0.5 + 0.1) / 0.7)


def _ret001():
    return json.loads((DEV_PACK / "recall" / "MIB-RET-001.json").read_text())


@pytest.mark.parametrize("mutate,needle", [
    (lambda s: s["evaluators"][0].__setitem__("type", "exact"), "evaluator type"),
    (lambda s: s["probes"][0].__setitem__("trigger", {"at_sequence": 99}), "trigger"),
    (lambda s: s["probes"][0].__setitem__("delivery", "batch"), "delivery"),
    (lambda s: s["ablations"][0].__setitem__("method", "memory_mask"), "ablation method"),
    (lambda s: s["timeline"].insert(0, {
        "id": "batch", "stage": "interference", "type": "distractor_batch", "at": {"sequence": 0},
        "visibility": "agent", "generator": {"id": "routine-chat-v1", "count": 5}}), "generator"),
    (lambda s: s["evaluators"][0].__setitem__("config", {"normalization": "levenshtein"}), "normalization"),
    (lambda s: s["world"].__setitem__("tools", [{
        "id": "x", "version": "1.0.0", "simulator_binding": "mib.other.v1", "operations": [{"name": "do"}]}]),
     "simulator_binding"),
])
def test_validator_rejects_what_the_reference_runner_cannot_execute(mutate, needle):
    s = _ret001()
    mutate(s)
    vr = validate_scenario(s, SCHEMA)
    assert not vr.valid
    assert any(e.startswith("unsupported:") and needle in e for e in vr.errors), vr.errors


def test_agent_misbehaviour_is_a_cognitive_failure_not_an_execution_failure():
    scenario = materialize(json.loads((DEV_PACK / "experience" / "MIB-EXP-001.json").read_text()), 101)
    for factory, code in [(LoopingAgent, "trajectory_collapse"), (RogueToolAgent, "agent_protocol_violation")]:
        full = run_scenario(scenario=scenario, agent_factory=factory, include_ablations=False)[0]
        assert full["status"] == "succeeded"
        assert all(p["outcome"] == "scored" for p in full["probe_results"])
        assert any(p["failure_codes"] == [code] and p["score"] == 0.0 for p in full["probe_results"]), (code, full["probe_results"])


def test_single_scenario_report_matches_pack_aggregation():
    template = json.loads((DEV_PACK / "time" / "MIB-TIME-001.json").read_text())
    instance = materialize(template, 101)
    runs = run_scenario(scenario=instance, agent_factory=ReferenceMemoryAgent, include_ablations=True, repetition=0, agent_seed="101:0")
    basic = build_basic_report(runs=runs, scenario=instance, agent_descriptor=ReferenceMemoryAgent().describe())
    validate_report(basic, REPORT_SCHEMA)
    assert verify_score(basic)["valid"]
    report, _ = run_benchmark_pack(
        templates=[template], schema=SCHEMA, profile={**PROFILE, "required_templates": [template["id"]]},
        agent_factory=ReferenceMemoryAgent, instance_seeds=[101], repetitions=1,
    )
    a = basic["aggregates"]["scenario_instances"][0]
    b = report["aggregates"]["scenario_instances"][0]
    assert a["dimension_scores"] == b["dimension_scores"]
    assert {m["name"]: m["value"] for m in a["causal_metrics"]} == {m["name"]: m["value"] for m in b["causal_metrics"]}


def test_verify_score_recomputes_from_probe_results():
    report, _ = _pack_report(ReferenceMemoryAgent)
    verification = verify_score(report)
    assert verification["valid"], verification["errors"]
    assert verification["verification_level"] == "full"
    tampered = copy.deepcopy(report)
    tampered["results"]["runs"][0]["probe_results"][0]["score"] = 0.25
    assert not verify_score(tampered)["valid"]
    tampered = copy.deepcopy(report)
    tampered["aggregates"]["scenario_instances"][0]["causal_metrics"][0]["value"] += 0.1
    assert not verify_score(tampered)["valid"]
    public = copy.deepcopy(report)
    public["results"]["runs"] = []
    assert verify_score(public)["verification_level"] == "aggregates_only"


def test_templates_outside_the_profile_are_rejected():
    templates = load_templates(DEV_PACK)
    with pytest.raises(ValueError, match="not listed by profile"):
        select_profile_templates(templates + [{"id": "MIB-EXTRA-999"}], PROFILE)
    assert len(select_profile_templates(templates, PROFILE)) == 24


def test_unsupported_templates_are_skipped_and_reduce_coverage():
    report, _ = _pack_report(NoActAgent)
    assert report["coverage"]["unsupported_required_templates"]
    assert report["coverage"]["overall"] < 1.0
    assert report["aggregates"]["mib_score"]["partial"] is True
    assert report["execution"]["unsupported_rate"] > 0
    assert any(w["code"] == "coverage.unsupported_templates" for w in report["warnings"])
    validate_report(report, REPORT_SCHEMA)


def test_bootstrap_interval_requires_enough_templates():
    report, _ = _pack_report(ReferenceMemoryAgent, bootstrap_resamples=30)
    assert "ci" not in report["aggregates"]["mib_score"]
    assert any(w["code"] == "statistics.insufficient_templates" for w in report["warnings"])
    assert report["statistics"]["mib_score"]["value"] == report["aggregates"]["mib_score"]["base_score"]
    validate_report(report, REPORT_SCHEMA)
    profile = {**PROFILE, "statistics": {**PROFILE["statistics"], "min_templates_per_dimension": 1}}
    report, _ = _pack_report(ReferenceMemoryAgent, profile=profile, bootstrap_resamples=30)
    assert "ci" in report["aggregates"]["mib_score"]
    validate_report(report, REPORT_SCHEMA)


def test_relative_time_advance_moves_the_virtual_clock():
    assert advance_iso_time("2026-01-01T00:00:00Z", "P1DT2H30M") == "2026-01-02T02:30:00Z"
    event = {"id": "t", "type": "time_advance", "at": {"sequence": 5}, "payload": {"duration": "PT12H"}}
    assert _virtual_time_for_event(event, "2026-01-01T00:00:00Z") == "2026-01-01T12:00:00Z"
    absolute = {"id": "e", "type": "interaction", "at": {"time": "2026-02-01T00:00:00Z"}}
    assert _virtual_time_for_event(absolute, "2026-01-01T00:00:00Z") == "2026-02-01T00:00:00Z"


def test_abstention_scoring_follows_expected_status():
    unknown = {"accepted": ["unknown"], "expected_status": "unknown"}
    known = {"accepted": ["pasta"], "expected_status": "known"}
    assert evaluate_set_match(AgentOutput(type="abstention", content="I cannot tell"), unknown, None)["score"] == 1.0
    r = evaluate_set_match(AgentOutput(type="message", content="yes"), unknown, None)
    assert r["score"] == 0.0 and r["failure_codes"] == ["false_certainty"]
    r = evaluate_set_match(AgentOutput(type="abstention", content="unknown"), known, None)
    assert r["score"] == 0.0 and r["failure_codes"] == ["retrieval_miss"]
    hedged = evaluate_set_match(
        AgentOutput(type="message", content="UTC+1, previously UTC+8"),
        {"accepted": ["UTC+1"], "forbidden": ["UTC+8"]}, None,
    )
    assert hedged["score"] == 0.0 and hedged["failure_codes"] == ["stale_memory_adoption"]


def test_forbidden_action_earns_nothing_for_inaction():
    oracle = {"trajectory_requirements": [{"type": "forbidden_action", "action": "canvas.activate_context"}]}
    assert evaluate_trajectory([], oracle, None)["score"] == 0.0
    assert evaluate_trajectory([{"kind": "tool_call", "tool": "canvas.commit"}], oracle, None)["score"] == 1.0
    bad = evaluate_trajectory([{"kind": "tool_call", "tool": "canvas.activate_context"}], oracle, None, probe_kind="experience")
    assert bad["failure_codes"] == ["error_recurrence"]
