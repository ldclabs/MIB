"""M6.2 — Memory Adapter, the 2x2 diagnostic matrix, and identifiability.

The point of Formation / Routing / Uptake diagnostics is that a known failure
mode produces the signature the metric claims. These tests run six fixture
Agents with deliberately different memory pathologies and pin the resulting
matrix, then check the invariants that keep the cells honest: paired execution,
no leakage into the MIB Score, and black-box Track B support without any
Memory Adapter.
"""

from __future__ import annotations

import json

import pytest

from mib_runner.agents import (
    BadFormationAgent,
    BadRoutingAgent,
    BadUptakeAgent,
    NoTransferAgent,
    OverTransferAgent,
    PerfectFormationPerfectRoutingAgent,
    ReferenceMemoryAgent,
)
from mib_runner.benchmark import load_templates, run_benchmark_pack
from mib_runner.calibration import DEFAULT_TRANSFER_THRESHOLDS, calibrate_transfer
from mib_runner.materialize import materialize
from mib_runner.experimental.memory_adapter import (
    InProcessMemoryAdapter,
    MIBMemoryAdapter,
    select_artifact_for_ability,
    supports_memory_adapter,
)
from mib_runner.runner import run_scenario
from mib_runner.experimental.transfer import RECALL_PREFIX, TRANSFER_DIAGNOSTICS_EXTENSION, parse_transfer_support
from mib_runner.experimental.transfer_diagnostics import build_transfer_diagnostics
from mib_runner.experimental.transfer_matrix import (
    baseline_excluded_event_ids,
    run_transfer_matrix,
    run_transfer_matrix_pack,
)

from paths import PROFILES, SCENARIO_SCHEMA_PATH, TRANSFER_PACK

SCHEMA = json.loads(SCENARIO_SCHEMA_PATH.read_text())
TRANSFER_PROFILE = json.loads((PROFILES / "MIB-Transfer-0.1-Dev.json").read_text())

# The near-match Template is excluded from the positive-transfer fixtures below
# only where a metric is about positive transfer; it is included everywhere else.
POSITIVE_TEMPLATE_IDS = ["MIB-SKILL-T01", "MIB-SKILL-T02", "MIB-SKILL-T03", "MIB-SKILL-T04", "MIB-SKILL-T05"]


def _templates(ids=None):
    rows = load_templates(TRANSFER_PACK)
    if ids is None:
        return rows
    return [t for t in rows if t["id"] in ids]


def _diagnose(factory, template_ids=POSITIVE_TEMPLATE_IDS, seed=101):
    templates = _templates(template_ids)
    runs, diagnostic = [], []
    for template in templates:
        instance = materialize(template, seed)
        runs += run_scenario(
            scenario=instance, agent_factory=factory,
            include_ablations=True, repetition=0, agent_seed=seed,
        )
        diagnostic += run_transfer_matrix(
            scenario=instance, agent_factory=factory, repetition=0, agent_seed=seed,
        )
    body = build_transfer_diagnostics(templates=templates, runs=runs, diagnostic_runs=diagnostic)
    return body, runs, diagnostic


# --- Identifiability ------------------------------------------------------


@pytest.mark.parametrize(
    "factory,formation,routing,uptake",
    [
        (PerfectFormationPerfectRoutingAgent, "high", "high", "high"),
        (BadFormationAgent, "low", "high", "high"),
        (BadRoutingAgent, "high", "low", "high"),
        (NoTransferAgent, "low", "low", "high"),
    ],
)
def test_formation_and_routing_efficiency_separate_the_failure_modes(factory, formation, routing, uptake):
    body, _, _ = _diagnose(factory)
    aggregate = body["aggregate"]
    assert body["diagnostic_mode"] == "decomposable_adapter"

    def band(value):
        return "high" if value >= 0.8 else "low" if value <= 0.2 else "mid"

    assert band(aggregate["formation_efficiency"]) == formation, aggregate
    assert band(aggregate["routing_efficiency"]) == routing, aggregate
    assert band(aggregate["oracle_routed_score"]) == uptake, aggregate


def test_bad_uptake_shows_a_low_ceiling_and_no_eligible_ratio():
    body, _, _ = _diagnose(BadUptakeAgent)
    aggregate = body["aggregate"]
    assert aggregate["oracle_routed_score"] <= 0.3
    # With no oracle headroom the ratios are undefined; undefined is absent,
    # never zero.
    assert "formation_efficiency" not in aggregate
    assert "routing_efficiency" not in aggregate
    for entry in body["templates"]:
        for row in entry["relations"]:
            if "formation_efficiency" in row:
                assert row["formation_efficiency"]["eligible"] is False
                assert row["formation_efficiency"]["value"] is None


def test_ao_exports_formed_artifacts_before_closing_the_formation_agent():
    class CloseSensitiveAgent(PerfectFormationPerfectRoutingAgent):
        def __init__(self):
            super().__init__()
            self.closed = False

        def reset(self, **kwargs):
            self.closed = False
            return super().reset(**kwargs)

        def export_artifacts(self, request):
            assert not self.closed, "artifacts exported after close"
            return super().export_artifacts(request)

        def close(self, **_):
            self.closed = True

    template = _templates(["MIB-SKILL-T01"])[0]
    scenario = materialize(template, 101)
    runs = run_transfer_matrix(
        scenario=scenario,
        agent_factory=CloseSensitiveAgent,
        repetition=0,
        agent_seed=101,
        cells=("AO",),
    )
    assert len(runs) == 1
    assert runs[0]["condition"] == "transfer_ao"


def test_over_transfer_scores_positive_transfer_well_and_fails_the_boundary():
    over, _, _ = _diagnose(OverTransferAgent)
    perfect, _, _ = _diagnose(PerfectFormationPerfectRoutingAgent)
    assert over["aggregate"]["supported_transfer_success_rate"] == pytest.approx(
        perfect["aggregate"]["supported_transfer_success_rate"]
    )
    assert over["aggregate"]["near_match_resistance"] < perfect["aggregate"]["near_match_resistance"]


def test_no_transfer_agent_matches_its_own_baseline():
    body, _, _ = _diagnose(NoTransferAgent)
    for entry in body["templates"]:
        for row in entry["relations"]:
            if "natural_transfer_gain" in row:
                assert row["natural_transfer_gain"]["value"] == pytest.approx(0.0)
    # ... while still able to execute a perfectly routed procedure.
    assert body["aggregate"]["oracle_routed_score"] >= 0.8


# --- Cell construction ----------------------------------------------------


def test_cells_are_paired_on_instance_repetition_probe_and_seed():
    template = _templates(["MIB-SKILL-T05"])[0]
    instance = materialize(template, 101)
    full = run_scenario(
        scenario=instance, agent_factory=PerfectFormationPerfectRoutingAgent,
        include_ablations=False, repetition=3, agent_seed="pair-seed",
    )[0]
    cells = run_transfer_matrix(
        scenario=instance, agent_factory=PerfectFormationPerfectRoutingAgent,
        repetition=3, agent_seed="pair-seed",
    )
    assert {r["extensions"]["mib.transfer.cell"] for r in cells} == {"B", "OA", "OO", "AO"}
    full_probes = {p["probe_id"] for p in full["probe_results"]}
    for run in cells:
        assert run["scenario_instance_id"] == full["scenario_instance_id"]
        assert run["template_id"] == full["template_id"]
        assert run["repetition"] == full["repetition"] == 3
        assert run["agent_seed"] == full["agent_seed"] == "pair-seed"
        assert {p["probe_id"] for p in run["probe_results"]} == full_probes


def test_baseline_cell_removes_every_causal_information_set():
    template = _templates(["MIB-SKILL-T04"])[0]
    support = parse_transfer_support(template)
    excluded = baseline_excluded_event_ids(template, support)
    # Both Abilities of the compositional Template, not just one.
    assert excluded == {"e-a1", "e-a2", "e-b1", "e-b2"}


def test_unsupported_template_baseline_removes_the_adjacent_memory():
    # The unsupported-novel Probe references no Ability, but the Template still
    # declares the adjacent one. The baseline withholds exactly that memory, so
    # the neutrality delta answers "did having it change the answer?".
    template = _templates(["MIB-SKILL-T06"])[0]
    support = parse_transfer_support(template)
    assert baseline_excluded_event_ids(template, support) == {"e-known"}


def test_template_with_no_declared_ability_falls_back_to_no_past_at_all():
    template = _templates(["MIB-SKILL-T06"])[0]
    stripped = json.loads(json.dumps(template))
    stripped["extensions"]["mib.transfer_support.v1"]["abilities"] = []
    support = parse_transfer_support(stripped)
    assert baseline_excluded_event_ids(stripped, support) == {"e-known", "d-1"}


def test_oracle_content_replaces_the_experience_it_stands_in_for():
    template = _templates(["MIB-SKILL-T01"])[0]
    instance = materialize(template, 101)
    cells = {
        r["extensions"]["mib.transfer.cell"]: r
        for r in run_transfer_matrix(
            scenario=instance, agent_factory=PerfectFormationPerfectRoutingAgent,
            repetition=0, agent_seed=101,
        )
    }
    # OA and OO both carry oracle content and differ only in when it arrives,
    # which is what isolates Routing.
    assert cells["OA"]["scenario_score"] == pytest.approx(cells["OO"]["scenario_score"])
    routing_blind = {
        r["extensions"]["mib.transfer.cell"]: r
        for r in run_transfer_matrix(
            scenario=instance, agent_factory=BadRoutingAgent, repetition=0, agent_seed=101,
        )
    }
    assert routing_blind["OA"]["scenario_score"] < routing_blind["OO"]["scenario_score"]


def test_routed_artifact_is_framed_as_a_recalled_procedure_and_carries_no_answer():
    template = _templates(["MIB-SKILL-T05"])[0]
    support = parse_transfer_support(template)
    artifact = support.abilities[0].oracle_artifact["content"]
    assert RECALL_PREFIX.endswith(": ")
    # The oracle artifact states a reusable procedure and its trigger; it never
    # states the Probe's own oracle value.
    for probe in template["probes"]:
        for value in (probe.get("oracle") or {}).get("accepted", []):
            assert str(value).casefold() not in artifact.casefold()


# --- Black-box compatibility ----------------------------------------------


def test_black_box_agent_gets_routing_and_uptake_cells_without_a_memory_adapter():
    assert not supports_memory_adapter(ReferenceMemoryAgent())
    template = _templates(["MIB-SKILL-T01"])[0]
    instance = materialize(template, 101)
    cells = run_transfer_matrix(
        scenario=instance, agent_factory=ReferenceMemoryAgent, repetition=0, agent_seed=101,
    )
    kinds = {r["extensions"]["mib.transfer.cell"] for r in cells}
    assert kinds == {"B", "OA", "OO"}

    runs = run_scenario(scenario=instance, agent_factory=ReferenceMemoryAgent, include_ablations=True, repetition=0, agent_seed=101)
    body = build_transfer_diagnostics(templates=[template], runs=runs, diagnostic_runs=cells)
    assert body["diagnostic_mode"] == "behavioral"
    row = body["templates"][0]["relations"][0]
    assert row["routing_efficiency"]["eligible"] is True
    assert row["formation_efficiency"]["eligible"] is False
    assert row["formation_efficiency"]["reason"] == "missing_cell"


# --- Score isolation ------------------------------------------------------


def test_diagnostic_runs_never_reach_the_report_or_move_the_score():
    templates = _templates()
    kwargs = dict(
        templates=templates, schema=SCHEMA, profile=TRANSFER_PROFILE,
        agent_factory=PerfectFormationPerfectRoutingAgent,
        instance_seeds=[101], repetitions=1, include_ablations=True,
    )
    plain, plain_summary = run_benchmark_pack(**kwargs)
    with_cells, cell_summary = run_benchmark_pack(**kwargs, transfer_matrix=True)

    assert cell_summary["transfer_diagnostic_run_count"] > 0
    assert "transfer_diagnostic_run_count" not in plain_summary
    assert plain_summary["mib_score"] == cell_summary["mib_score"]
    assert plain["aggregates"] == with_cells["aggregates"]
    assert plain["causal_metrics"] == with_cells["causal_metrics"]
    assert plain["coverage"] == with_cells["coverage"]
    assert plain["execution"]["scheduled_runs"] == with_cells["execution"]["scheduled_runs"]

    conditions = {r["condition"] for r in with_cells["results"]["runs"]}
    assert not any(c.startswith("transfer_") for c in conditions)
    # Only the supplemental extension differs.
    body = with_cells["extensions"][TRANSFER_DIAGNOSTICS_EXTENSION]
    assert body["diagnostic_mode"] == "decomposable_adapter"


def test_matrix_pack_skips_unannotated_instances():
    instances = [materialize(t, 101) for t in _templates(["MIB-SKILL-T01"])]
    plain = dict(instances[0])
    plain.pop("extensions")
    runs = run_transfer_matrix_pack(
        instances=[plain], agent_factory=PerfectFormationPerfectRoutingAgent, repetitions=1,
    )
    assert runs == []


# --- Memory Adapter -------------------------------------------------------


def test_fixture_agents_satisfy_the_memory_adapter_protocol():
    agent = PerfectFormationPerfectRoutingAgent()
    assert isinstance(agent, MIBMemoryAdapter)
    assert supports_memory_adapter(agent)
    assert agent.describe_memory()["capabilities"]["export_artifacts"] is True


def test_oracle_routing_does_not_trust_self_reported_provenance():
    template = _templates(["MIB-SKILL-T01"])[0]
    ability = parse_transfer_support(template).abilities[0]
    artifacts = [
        {
            "artifact_id": "liar",
            "content": "Nothing useful happened.",
            "metadata": {"source_event_ids": ["e-failure", "e-recovery"]},
        },
        {
            "artifact_id": "honest",
            "content": "Select the workspace first, then edit the record, then save it exactly once.",
            "metadata": {},
        },
    ]
    chosen, score = select_artifact_for_ability(artifacts, ability)
    assert chosen["artifact_id"] == "honest"
    assert score > 0.0


def test_in_process_memory_adapter_round_trip():
    adapter = InProcessMemoryAdapter()
    adapter.observe_memory_event({"observation_id": "o1", "content": "hello"})
    assert adapter.export_artifacts()["artifacts"] == []
    adapter.inject_artifacts({"artifacts": [{"artifact_id": "x", "content": "select the workspace before saving"}]})
    exported = adapter.export_artifacts()["artifacts"]
    assert [a["artifact_id"] for a in exported] == ["x"]
    retrieved = adapter.retrieve_artifacts({"goal": "save the workspace record"})["artifacts"]
    assert retrieved and retrieved[0]["artifact_id"] == "x"
    adapter.reset_memory({})
    assert adapter.export_artifacts()["artifacts"] == []


# --- Calibration ----------------------------------------------------------


def test_transfer_calibration_gates_the_oracle_edge_not_the_baseline():
    report = calibrate_transfer(
        templates=_templates(), schema=SCHEMA, seeds=[101], repetitions=1, baseline_id="B3",
    )
    assert report["enabled"] is True
    assert report["annotated_template_count"] == 6
    assert report["thresholds"] == DEFAULT_TRANSFER_THRESHOLDS
    by_id = {c["template_id"]: c for c in report["templates"]}
    assert set(by_id) == {f"MIB-SKILL-T0{i}" for i in range(1, 7)}
    for card in report["templates"]:
        assert card["risks"] == [], (card["template_id"], card["risks"])
        assert card["recommendation"] == "provisional_pass"
    # The D1 Template is genuinely hard for a lexical baseline. That is a note
    # about the baseline, not a defect in the Template, so the edge still passes.
    assert by_id["MIB-SKILL-T02"]["baseline_notes"] == ["p-surface:baseline_shows_no_natural_transfer"]
    assert by_id["MIB-SKILL-T02"]["gates"]["oracle_skill_solvable"] is True
    # The near-match trap must actually trap.
    near = next(r for r in by_id["MIB-SKILL-T05"]["relations"] if r["relation"] == "near_match_non_applicable")
    assert near["near_match_harm"] >= DEFAULT_TRANSFER_THRESHOLDS["near_match_trap_min"]


def test_transfer_calibration_is_absent_without_annotations():
    templates = [dict(t) for t in _templates(["MIB-SKILL-T01"])]
    templates[0].pop("extensions")
    assert calibrate_transfer(templates=templates, schema=SCHEMA, seeds=[101]) is None
