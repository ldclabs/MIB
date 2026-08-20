from __future__ import annotations

import json

from mib_runner.agents import ReferenceMemoryAgent
from mib_runner.materialize import materialize
from mib_runner.report import build_basic_report, validate_report, verify_score
from mib_runner.runner import run_scenario
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
