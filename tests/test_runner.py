from __future__ import annotations

import json

import pytest

from mib_runner.agents import ReferenceMemoryAgent
from mib_runner.materialize import materialize
from mib_runner.report import build_basic_report, validate_report, verify_score
from mib_runner.runner import run_scenario
from mib_runner.types import AgentOutput
from mib_runner.validation import validate_scenario


from paths import DEV_PACK, REPORT_SCHEMA_PATH, SCENARIO_SCHEMA_PATH, SLICE_1, slice_files

SCENARIO_SCHEMA = json.loads(SCENARIO_SCHEMA_PATH.read_text())
REPORT_SCHEMA = json.loads(REPORT_SCHEMA_PATH.read_text())
PACK = DEV_PACK


def scenario_files():
    return slice_files(SLICE_1)


def test_all_public_slice_templates_validate():
    files = scenario_files()
    assert len(files) == 12
    for p in files:
        s = json.loads(p.read_text())
        r = validate_scenario(s, SCENARIO_SCHEMA)
        assert r.valid, (p, r.errors)
        inst = materialize(s, 101)
        r2 = validate_scenario(inst, SCENARIO_SCHEMA)
        assert r2.valid, (p, r2.errors)


def test_full_condition_reference_fixture_agent():
    scores = {}
    for p in scenario_files():
        s = materialize(json.loads(p.read_text()), 101)
        runs = run_scenario(
            scenario=s,
            agent_factory=ReferenceMemoryAgent,
            include_ablations=False,
            agent_seed=101,
        )
        assert len(runs) == 1
        scores[s["id"]] = runs[0]["scenario_score"]
    assert all(v == 1.0 for v in scores.values()), scores


def test_ablations_execute_and_reports_validate():
    for p in scenario_files():
        s = materialize(json.loads(p.read_text()), 202)
        runs = run_scenario(
            scenario=s,
            agent_factory=ReferenceMemoryAgent,
            include_ablations=True,
            agent_seed=202,
        )
        assert any(r["condition"] == "full" for r in runs)
        report = build_basic_report(
            runs=runs,
            scenario=s,
            agent_descriptor=ReferenceMemoryAgent().describe(),
        )
        validate_report(report, REPORT_SCHEMA)
        verification = verify_score(report)
        assert verification["valid"], verification


def test_time003_probe_is_triggered_before_completion():
    p = PACK / "time" / "MIB-TIME-003.json"
    s = materialize(json.loads(p.read_text()), 101)
    runs = run_scenario(
        scenario=s,
        agent_factory=ReferenceMemoryAgent,
        include_ablations=False,
        agent_seed=101,
    )
    pr = {x["probe_id"]: x for x in runs[0]["probe_results"]}
    assert pr["p-before"]["score"] == 1.0
    assert pr["p-after"]["score"] == 1.0


def test_ablation_executes_the_same_prior_probe_history_as_full():
    template = json.loads((PACK / "epistemic" / "MIB-EPI-002.json").read_text())
    scenario = materialize(template, 101)
    current = scenario["probes"][0]["oracle"]["accepted"][0]
    historical = scenario["probes"][1]["oracle"]["accepted"][0]

    class ProbeHistoryAgent:
        def __init__(self):
            self.calls = 0

        def reset(self, **_):
            self.calls = 0
            return {"accepted": True}

        def observe(self, **_):
            return {"accepted": True}

        def respond(self, **kwargs):
            self.calls += 1
            question = kwargs["input_data"]["content"]
            if "originally" in question:
                # This Agent deliberately needs the prior Probe interaction.  It
                # ignores every Timeline observation, so a causal delta here
                # could only be caused by mismatched future Probe history.
                answer = historical if self.calls > 1 else "unknown"
            else:
                answer = current
            return AgentOutput(type="message", content=answer)

    runs = run_scenario(
        scenario=scenario,
        agent_factory=ProbeHistoryAgent,
        include_ablations=True,
        agent_seed=101,
    )
    original_removed = next(r for r in runs if r.get("ablation_id") == "a-original")
    assert original_removed["scenario_score"] == 1.0
    assert [p["probe_id"] for p in original_removed["probe_results"]] == ["p-current", "p-history"]
    assert {p["probe_id"]: p["weight"] for p in original_removed["probe_results"]} == {
        "p-current": 0.0,
        "p-history": 1.0,
    }


def test_execution_failure_remains_a_zero_score_probe_in_the_denominator():
    template = json.loads((PACK / "epistemic" / "MIB-EPI-002.json").read_text())
    scenario = materialize(template, 101)
    current = scenario["probes"][0]["oracle"]["accepted"][0]

    class PartiallyFailingAgent:
        def reset(self, **_):
            self.calls = 0
            return {"accepted": True}

        def observe(self, **_):
            return {"accepted": True}

        def respond(self, **_):
            self.calls += 1
            if self.calls == 2:
                raise TimeoutError("simulated second-Probe timeout")
            return AgentOutput(type="message", content=current)

    full = run_scenario(
        scenario=scenario,
        agent_factory=PartiallyFailingAgent,
        include_ablations=False,
    )[0]
    assert full["status"] == "failed"
    assert [p["outcome"] for p in full["probe_results"]] == ["scored", "execution_failure"]
    assert full["scenario_score"] == pytest.approx(0.5)


def test_replay_with_injections_delivers_memory_before_the_probe():
    template = json.loads((PACK / "recall" / "MIB-RET-001.json").read_text())
    scenario = materialize(template, 101)
    accepted = scenario["probes"][0]["oracle"]["accepted"][0]
    scenario["ablations"] = [{
        "id": "a-harmful",
        "kind": "harmful_memory",
        "probes": ["p-recall"],
        "method": "replay_with_injections",
        "injections": [{
            "id": "inj-harmful",
            "stage": "pre_probe",
            "type": "document",
            "at": {"after_event": "cp"},
            "visibility": "agent",
            "content": "HARMFUL-MEMORY",
        }],
        "expected_effect": "resist",
    }]
    validation = validate_scenario(scenario, SCENARIO_SCHEMA)
    assert validation.valid, validation.errors

    class InjectionAwareAgent:
        def reset(self, **_):
            self.seen = []
            return {"accepted": True}

        def observe(self, *, observation, **_):
            self.seen.append(observation.content or "")
            return {"accepted": True}

        def respond(self, **_):
            answer = "wrong" if "HARMFUL-MEMORY" in self.seen else accepted
            return AgentOutput(type="message", content=answer)

    runs = run_scenario(scenario=scenario, agent_factory=InjectionAwareAgent, include_ablations=True)
    assert next(r for r in runs if r["condition"] == "full")["scenario_score"] == 1.0
    harmful = next(r for r in runs if r["condition"] == "harmful_memory")
    assert harmful["scenario_score"] == 0.0
    assert harmful["ablation_method"] == "replay_with_injections"
