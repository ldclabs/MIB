from __future__ import annotations

import json

from mib_runner.agents import ReferenceMemoryAgent
from mib_runner.materialize import materialize
from mib_runner.report import build_basic_report, validate_report, verify_score
from mib_runner.runner import run_scenario
from mib_runner.validation import validate_scenario

from paths import DEV_PACK, REPORT_SCHEMA_PATH, SCENARIO_SCHEMA_PATH, SLICE_1, SLICE_2, slice_files

SCENARIO_SCHEMA = json.loads(SCENARIO_SCHEMA_PATH.read_text())
REPORT_SCHEMA = json.loads(REPORT_SCHEMA_PATH.read_text())
PACK = DEV_PACK


def action_scenario_files():
    return slice_files(SLICE_2)


def test_action_templates_validate_and_materialize():
    files = action_scenario_files()
    assert len(files) == 9
    for p in files:
        template = json.loads(p.read_text())
        v = validate_scenario(template, SCENARIO_SCHEMA)
        assert v.valid, (p, v.errors)
        inst = materialize(template, 101)
        v2 = validate_scenario(inst, SCENARIO_SCHEMA)
        assert v2.valid, (p, v2.errors)


def test_full_action_conditions_succeed():
    scores = {}
    for p in action_scenario_files():
        s = materialize(json.loads(p.read_text()), 101)
        runs = run_scenario(
            scenario=s,
            agent_factory=ReferenceMemoryAgent,
            include_ablations=False,
            agent_seed=101,
        )
        scores[s["id"]] = runs[0]["scenario_score"]
        assert runs[0]["status"] == "succeeded"
        assert runs[0]["extensions"]["mib.runner.action_trace"], s["id"]
    assert all(v == 1.0 for v in scores.values()), scores


def test_experience_relevant_ablation_changes_future_action():
    p = PACK / "experience" / "MIB-EXP-001.json"
    s = materialize(json.loads(p.read_text()), 101)
    runs = run_scenario(scenario=s, agent_factory=ReferenceMemoryAgent, include_ablations=True, agent_seed=101)
    full = next(r for r in runs if r["condition"] == "full")
    abl = next(r for r in runs if r["condition"] == "relevant_ablation")
    assert full["scenario_score"] == 1.0
    assert abl["scenario_score"] < full["scenario_score"]
    full_tools = [x["tool"] for x in full["extensions"]["mib.runner.action_trace"]]
    assert full_tools[:4] == [
        "deployment.inspect_target",
        "deployment.select_target",
        "deployment.run_migration",
        "deployment.restart_service",
    ]
    assert full["extensions"]["mib.runner.world_state"]["deployment"]["service_running"] is True
    assert abl["extensions"]["mib.runner.world_state"]["deployment"]["service_running"] is False


def test_skill_positive_and_negative_transfer():
    p = PACK / "skill" / "MIB-SKILL-002.json"
    s = materialize(json.loads(p.read_text()), 101)
    runs = run_scenario(scenario=s, agent_factory=ReferenceMemoryAgent, include_ablations=True, agent_seed=101)
    assert next(r for r in runs if r["condition"] == "full")["scenario_score"] == 1.0
    assert next(r for r in runs if r["condition"] == "relevant_ablation")["scenario_score"] == 0.0

    p = PACK / "skill" / "MIB-SKILL-003.json"
    s = materialize(json.loads(p.read_text()), 101)
    runs = run_scenario(scenario=s, agent_factory=ReferenceMemoryAgent, include_ablations=True, agent_seed=101)
    full = next(r for r in runs if r["condition"] == "full")
    counter = next(r for r in runs if r["condition"] == "counterexample")
    assert full["scenario_score"] == 1.0
    assert counter["scenario_score"] < full["scenario_score"]
    assert full["extensions"]["mib.runner.world_state"]["contextual_save"]["policy_violation"] is False
    assert counter["extensions"]["mib.runner.world_state"]["contextual_save"]["policy_violation"] is True


def test_action_reports_validate_and_scores_recompute():
    for p in action_scenario_files():
        s = materialize(json.loads(p.read_text()), 202)
        runs = run_scenario(scenario=s, agent_factory=ReferenceMemoryAgent, include_ablations=True, agent_seed=202)
        report = build_basic_report(runs=runs, scenario=s, agent_descriptor=ReferenceMemoryAgent().describe())
        validate_report(report, REPORT_SCHEMA)
        assert verify_score(report)["valid"]


def test_recall_time_epistemic_full_conditions_still_pass():
    files = slice_files(SLICE_1)
    assert len(files) == 12
    for p in files:
        s = materialize(json.loads(p.read_text()), 101)
        runs = run_scenario(scenario=s, agent_factory=ReferenceMemoryAgent, include_ablations=False, agent_seed=101)
        assert runs[0]["scenario_score"] == 1.0, p


def test_reference_action_request_idempotency():
    from mib_runner.types import Observation
    a = ReferenceMemoryAgent()
    a.reset(run_id="r", seed=1, virtual_time=None)
    a.observe(
        run_id="r",
        request_id="obs1",
        observation=Observation(
            observation_id="o1",
            type="feedback",
            content="The lesson was to inspect the actual target before migration after a missing_column failure.",
        ),
    )
    tools = [
        {"name": "deployment.inspect_target", "input_schema": {}},
        {"name": "deployment.select_target", "input_schema": {}},
        {"name": "deployment.run_migration", "input_schema": {}},
        {"name": "deployment.restart_service", "input_schema": {}},
    ]
    first = a.act(
        run_id="r", request_id="same-request", task_id="t", goal="repair", constraints=[],
        tools=tools, continuation=False, virtual_time=None,
    )
    second = a.act(
        run_id="r", request_id="same-request", task_id="t", goal="repair", constraints=[],
        tools=tools, continuation=False, virtual_time=None,
    )
    assert first == second
    assert first.tool_call_id == second.tool_call_id
