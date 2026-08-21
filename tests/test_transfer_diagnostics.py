"""M6.2 / M6.3 — Transfer diagnostics, distance profile, and redaction.

Two properties matter most here and are pinned first: a pack with no Transfer
Support Annotation produces a byte-identical report, and no diagnostic value
ever enters the MIB Score.
"""

from __future__ import annotations

import copy
import json

import pytest

from mib_runner.agents import ReferenceMemoryAgent
from mib_runner.benchmark import load_templates, run_benchmark_pack
from mib_runner.capability import render_capability_card
from mib_runner.hidden import redact_report_for_public
from mib_runner.leaderboard import result_family
from mib_runner.report import validate_report, verify_score
from mib_runner.transfer import TRANSFER_DIAGNOSTICS_EXTENSION, TRANSFER_EXTENSION
from mib_runner.transfer_diagnostics import (
    DEFAULT_EPSILON,
    build_transfer_diagnostics,
    redact_transfer_diagnostics,
    transfer_diagnostic_aggregates,
    transfer_distance_aggregates,
    transfer_relation_aggregates,
)

from paths import DEV_PACK, PROFILES, REPORT_SCHEMA_PATH, SCENARIO_SCHEMA_PATH, TRANSFER_PACK

SCHEMA = json.loads(SCENARIO_SCHEMA_PATH.read_text())
REPORT_SCHEMA = json.loads(REPORT_SCHEMA_PATH.read_text())
TRANSFER_PROFILE = json.loads((PROFILES / "MIB-Transfer-0.1-Dev.json").read_text())
CORE_PROFILE = json.loads((PROFILES / "MIB-Core-0.1-Dev-M3.json").read_text())


@pytest.fixture(scope="module")
def transfer_run():
    templates = load_templates(TRANSFER_PACK)
    report, summary = run_benchmark_pack(
        templates=templates,
        schema=SCHEMA,
        profile=TRANSFER_PROFILE,
        agent_factory=ReferenceMemoryAgent,
        instance_seeds=[101, 202],
        repetitions=2,
        include_ablations=True,
        bootstrap_resamples=40,
        bootstrap_seed=4242,
    )
    return templates, report, summary


def _body(report):
    return report["extensions"][TRANSFER_DIAGNOSTICS_EXTENSION]


# --- Pack shape ------------------------------------------------------------


def test_transfer_dev_pack_is_six_annotated_templates_outside_the_core_pack():
    templates = load_templates(TRANSFER_PACK)
    assert len(templates) == 6
    assert {t["id"] for t in templates} == {f"MIB-SKILL-T0{i}" for i in range(1, 7)}
    for template in templates:
        assert (template.get("extensions") or {}).get(TRANSFER_EXTENSION) is not None
    # The MIB-Core Dev pack is untouched.
    assert len(load_templates(DEV_PACK)) == 24
    assert set(TRANSFER_PROFILE["required_templates"]).isdisjoint(CORE_PROFILE["required_templates"])


def test_transfer_profile_is_its_own_result_family():
    assert result_family(TRANSFER_PROFILE) == "transfer_diagnostic"
    assert result_family(CORE_PROFILE) == "core"


def test_transfer_pack_covers_every_declared_relation():
    from mib_runner.transfer import check_profile_transfer_coverage, transfer_coverage

    coverage = transfer_coverage(load_templates(TRANSFER_PACK))
    assert check_profile_transfer_coverage(TRANSFER_PROFILE, coverage) == []
    assert coverage["distance_classes"] == {"D0": 2, "D1": 1, "D2": 1, "D3": 1}


# --- Score compatibility ---------------------------------------------------


def test_a_wholly_unannotated_pack_carries_no_transfer_extension():
    stripped = []
    for template in load_templates(DEV_PACK):
        template = copy.deepcopy(template)
        (template.get("extensions") or {}).pop(TRANSFER_EXTENSION, None)
        stripped.append(template)
    report, _ = run_benchmark_pack(
        templates=stripped,
        schema=SCHEMA,
        profile=CORE_PROFILE,
        agent_factory=ReferenceMemoryAgent,
        instance_seeds=[101],
        repetitions=1,
        include_ablations=True,
    )
    assert TRANSFER_DIAGNOSTICS_EXTENSION not in (report.get("extensions") or {})
    assert build_transfer_diagnostics(templates=stripped, runs=report["results"]["runs"]) is None
    validate_report(report, REPORT_SCHEMA)
    assert verify_score(report)["valid"]


def test_annotating_the_core_pack_adds_diagnostics_without_moving_the_score():
    annotated = load_templates(DEV_PACK)
    stripped = []
    for template in annotated:
        template = copy.deepcopy(template)
        (template.get("extensions") or {}).pop(TRANSFER_EXTENSION, None)
        stripped.append(template)
    kwargs = dict(
        schema=SCHEMA, profile=CORE_PROFILE, agent_factory=ReferenceMemoryAgent,
        instance_seeds=[101], repetitions=1, include_ablations=True,
    )
    with_annotations, _ = run_benchmark_pack(templates=annotated, **kwargs)
    without, _ = run_benchmark_pack(templates=stripped, **kwargs)

    assert TRANSFER_DIAGNOSTICS_EXTENSION in with_annotations["extensions"]
    assert with_annotations["aggregates"] == without["aggregates"]
    assert with_annotations["causal_metrics"] == without["causal_metrics"]
    assert with_annotations["coverage"] == without["coverage"]
    assert verify_score(with_annotations)["valid"]
    validate_report(with_annotations, REPORT_SCHEMA)

    body = with_annotations["extensions"][TRANSFER_DIAGNOSTICS_EXTENSION]
    assert body["coverage"]["annotated_templates"] == 7
    assert body["aggregate"]["near_match_resistance"] is not None


def test_diagnostics_are_supplemental_and_never_enter_the_score(transfer_run):
    templates, report, _ = transfer_run
    validate_report(report, REPORT_SCHEMA)
    assert verify_score(report)["valid"], verify_score(report)

    stripped = copy.deepcopy(report)
    stripped["extensions"].pop(TRANSFER_DIAGNOSTICS_EXTENSION)
    assert verify_score(stripped)["valid"]
    assert (
        stripped["aggregates"]["mib_score"]["final_score"]
        == report["aggregates"]["mib_score"]["final_score"]
    )


def test_disabling_diagnostics_leaves_the_annotated_pack_score_unchanged():
    templates = load_templates(TRANSFER_PACK)
    kwargs = dict(
        templates=templates, schema=SCHEMA, profile=TRANSFER_PROFILE,
        agent_factory=ReferenceMemoryAgent, instance_seeds=[101], repetitions=1,
        include_ablations=True,
    )
    with_diagnostics, _ = run_benchmark_pack(**kwargs, transfer_diagnostics=True)
    without, _ = run_benchmark_pack(**kwargs, transfer_diagnostics=False)
    assert TRANSFER_DIAGNOSTICS_EXTENSION in with_diagnostics["extensions"]
    assert "extensions" not in without
    assert (
        with_diagnostics["aggregates"]["mib_score"]["final_score"]
        == without["aggregates"]["mib_score"]["final_score"]
    )
    assert with_diagnostics["aggregates"]["templates"] == without["aggregates"]["templates"]
    assert with_diagnostics["causal_metrics"] == without["causal_metrics"]


# --- Relation and distance aggregation -------------------------------------


def test_relation_rows_are_template_first_and_carry_the_declared_relation(transfer_run):
    _, report, _ = transfer_run
    body = _body(report)
    assert body["diagnostic_mode"] == "behavioral"
    by_template = {e["template_id"]: e for e in body["templates"]}
    assert set(by_template) == {f"MIB-SKILL-T0{i}" for i in range(1, 7)}

    t01 = by_template["MIB-SKILL-T01"]["relations"][0]
    assert t01["relation"] == "exact_replay"
    assert t01["distance_class"] == "D0"
    assert t01["support_expected"] is True
    assert t01["expected_behaviour"] == "apply"
    # Two seeds x two repetitions collapse to two Scenario Instances.
    assert t01["instance_count"] == 2
    # Without the supporting Experience the fixture Agent skips the precondition:
    # the world assertion fails outright and only one trajectory requirement holds.
    assert t01["natural_score"] == pytest.approx(1.0)
    assert t01["baseline_score"] == pytest.approx(0.4 / 3.0)
    assert t01["natural_transfer_gain"]["value"] == pytest.approx(1.0 - 0.4 / 3.0)


def test_distance_profile_is_ordered_and_positive_only(transfer_run):
    _, report, _ = transfer_run
    profile = _body(report)["distance_profile"]
    assert [x["class"] for x in profile] == ["D0", "D1", "D2", "D3"]
    assert profile[0]["template_count"] == 2  # T01 and the T05 supported Probe
    for entry in profile:
        assert 0.0 <= entry["score"] <= 1.0
    # Negative controls are a different causal class, never a farther distance.
    classes = {c for e in _body(report)["templates"] for r in e["relations"] for c in [r.get("distance_class")]}
    assert None in classes  # the near-match and unsupported rows carry no class
    for entry in _body(report)["templates"]:
        for row in entry["relations"]:
            if row["relation"] in {"near_match_non_applicable", "unsupported_novel"}:
                assert "distance_class" not in row
                assert "distance_normalized" not in row


def test_negative_controls_report_resistance_and_neutrality_not_distance(transfer_run):
    _, report, _ = transfer_run
    body = _body(report)
    aggregate = body["aggregate"]
    assert aggregate["near_match_resistance"] == pytest.approx(1.0)
    assert aggregate["unsupported_memory_neutrality"] == pytest.approx(1.0)
    assert aggregate["negative_transfer_rate"] == pytest.approx(0.0)

    by_template = {e["template_id"]: e for e in body["templates"]}
    near = next(r for r in by_template["MIB-SKILL-T05"]["relations"] if r["relation"] == "near_match_non_applicable")
    # No relevant-memory Ablation targets the near-match Probe by design, so the
    # baseline is unknown.  Unknown is null, not zero.
    assert near["baseline_score"] is None
    assert "natural_transfer_gain" not in near
    assert near["natural_score"] == pytest.approx(1.0)

    unsupported = by_template["MIB-SKILL-T06"]["relations"][0]
    assert unsupported["unsupported_memory_delta"]["value"] == pytest.approx(0.0)
    assert unsupported["unsupported_memory_neutrality"]["value"] == pytest.approx(1.0)


def test_efficiency_deltas_are_reported_per_probe(transfer_run):
    _, report, _ = transfer_run
    by_template = {e["template_id"]: e for e in _body(report)["templates"]}
    # Applying the learned procedure costs one extra tool call on the D0 Template.
    assert by_template["MIB-SKILL-T01"]["efficiency"]["tool_call_delta"] == pytest.approx(1.0)
    # Nothing was learned for the unsupported Probe, so cost does not move.
    assert by_template["MIB-SKILL-T06"]["efficiency"]["tool_call_delta"] == pytest.approx(0.0)


def test_transfer_profile_has_confidence_intervals(transfer_run):
    _, report, _ = transfer_run
    stats = _body(report)["statistics"]
    assert set(stats) == {"aggregate", "distance_profile"}
    for entry in stats["distance_profile"].values():
        assert entry["level"] == 0.95
        assert entry["method"] == "template_bootstrap_percentile"
        assert entry["lower"] <= entry["upper"]


# --- Formation / Routing eligibility ---------------------------------------


def _synthetic_rows(*, aa, b, ao=None, oa=None, oo=None):
    template = {
        "id": "MIB-SKILL-TSY",
        "extensions": {
            TRANSFER_EXTENSION: {
                "version": "1.0.0",
                "abilities": [{"id": "a.x", "kind": "procedure", "support_event_ids": ["e1"]}],
                "probe_relations": [{
                    "probe_id": "p", "ability_ids": ["a.x"], "relation": "structural_transfer",
                    "support_expected": True, "transfer_distance": {"class": "D2"},
                }],
            }
        },
    }

    def run(condition, score):
        return {
            "template_id": "MIB-SKILL-TSY",
            "scenario_instance_id": "MIB-SKILL-TSY:1",
            "condition": condition,
            "repetition": 0,
            "probe_results": [{"probe_id": "p", "outcome": "scored", "score": score, "weight": 1.0}],
        }

    runs = [run("full", aa), run("relevant_ablation", b)]
    diagnostic = []
    for condition, value in (("transfer_ao", ao), ("transfer_oa", oa), ("transfer_oo", oo)):
        if value is not None:
            diagnostic.append(run(condition, value))
    return transfer_relation_aggregates([template], runs, diagnostic_runs=diagnostic)


def test_formation_and_routing_efficiency_use_the_oracle_ceiling():
    rows = _synthetic_rows(aa=0.5, b=0.1, ao=0.4, oa=0.9, oo=1.0)
    row = rows[0]["relations"][0]
    assert row["formation_efficiency"]["value"] == pytest.approx((0.4 - 0.1) / (1.0 - 0.1))
    assert row["routing_efficiency"]["value"] == pytest.approx((0.9 - 0.1) / (1.0 - 0.1))
    assert row["natural_transfer_efficiency"]["value"] == pytest.approx((0.5 - 0.1) / (1.0 - 0.1))
    losses = row["loss_decomposition"]
    assert losses["formation_loss"] == pytest.approx(0.6)
    assert losses["routing_loss"] == pytest.approx(0.1)
    assert losses["deployment_gap"] == pytest.approx(0.5)
    # The decomposition is explicitly not additive.
    assert losses["interaction_residual"] == pytest.approx(0.5 - 0.7)
    assert rows[0]["diagnostic_mode"] == "decomposable_adapter"


def test_insufficient_oracle_headroom_is_unknown_not_zero():
    rows = _synthetic_rows(aa=0.98, b=0.98, ao=0.98, oa=0.98, oo=1.0)
    row = rows[0]["relations"][0]
    for name in ("formation_efficiency", "routing_efficiency", "natural_transfer_efficiency"):
        assert row[name]["value"] is None
        assert row[name]["eligible"] is False
        assert row[name]["reason"] == "insufficient_oracle_headroom"
        assert row[name]["epsilon"] == DEFAULT_EPSILON
    aggregate = transfer_diagnostic_aggregates(rows)
    assert "formation_efficiency" not in aggregate
    assert "routing_efficiency" not in aggregate


def test_missing_oracle_cell_is_unknown_not_zero():
    rows = _synthetic_rows(aa=0.5, b=0.1, oa=0.9)
    row = rows[0]["relations"][0]
    assert row["routing_efficiency"]["eligible"] is False
    assert row["routing_efficiency"]["reason"] == "missing_cell"
    assert row["formation_efficiency"]["value"] is None


def test_raw_efficiency_keeps_out_of_range_values_and_clips_only_the_display():
    rows = _synthetic_rows(aa=0.9, b=0.1, ao=1.0, oa=-0.1, oo=0.8)
    row = rows[0]["relations"][0]
    assert row["formation_efficiency"]["value"] > 1.0
    assert row["formation_efficiency"]["display"] == 1.0
    assert row["routing_efficiency"]["value"] < 0.0
    assert row["routing_efficiency"]["display"] == 0.0


def test_negative_natural_transfer_gain_is_signed_and_counted():
    template_rows = _synthetic_rows(aa=0.2, b=0.7)
    row = template_rows[0]["relations"][0]
    assert row["natural_transfer_gain"]["value"] == pytest.approx(-0.5)
    assert transfer_diagnostic_aggregates(template_rows)["negative_transfer_rate"] == pytest.approx(1.0)


def test_distance_aggregation_is_template_first_not_probe_count_weighted():
    # One Template with four D2 Probes must not outvote one Template with one.
    def template(tid, probes):
        return {
            "id": tid,
            "extensions": {TRANSFER_EXTENSION: {
                "version": "1.0.0",
                "abilities": [{"id": "a", "kind": "procedure", "support_event_ids": ["e1"]}],
                "probe_relations": [
                    {"probe_id": p, "ability_ids": ["a"], "relation": "structural_transfer",
                     "support_expected": True, "transfer_distance": {"class": "D2"}}
                    for p in probes
                ],
            }},
        }

    def runs(tid, probes, score):
        return [{
            "template_id": tid, "scenario_instance_id": f"{tid}:1", "condition": "full", "repetition": 0,
            "probe_results": [{"probe_id": p, "outcome": "scored", "score": score, "weight": 1.0} for p in probes],
        }]

    templates = [template("MIB-SKILL-TA", ["p1", "p2", "p3", "p4"]), template("MIB-SKILL-TB", ["p1"])]
    all_runs = runs("MIB-SKILL-TA", ["p1", "p2", "p3", "p4"], 0.0) + runs("MIB-SKILL-TB", ["p1"], 1.0)
    rows = transfer_relation_aggregates(templates, all_runs)
    profile = transfer_distance_aggregates(rows)
    assert len(profile) == 1
    assert profile[0]["score"] == pytest.approx(0.5)


# --- Redaction and public surface ------------------------------------------


def test_public_redaction_exposes_aggregates_only(transfer_run):
    templates, report, _ = transfer_run
    aliases = {t["id"]: f"hidden-fam-{i:02d}" for i, t in enumerate(templates)}
    public = redact_report_for_public(report, aliases=aliases, redaction_key="secret-key")
    body = public["extensions"][TRANSFER_DIAGNOSTICS_EXTENSION]
    assert body["scope"] == "public"
    assert set(body["coverage"]) == {"annotated_templates", "annotated_probes"}
    for row in body["templates"]:
        assert "template_id" not in row
        assert "relations" not in row
        assert row["template_alias"] in set(aliases.values())

    blob = json.dumps(public, ensure_ascii=False)
    for needle in [
        "ability.select_before_save", "ability.class_a7_scoped_commit",
        "support_event_ids", "oracle_artifact", "p-nearmatch", "p-composition",
        "near_match_non_applicable", "MIB-SKILL-T05", TRANSFER_EXTENSION,
    ]:
        assert needle not in blob, needle
    assert verify_score(public)["valid"]

    # Even with no evaluator alias map the diagnostics body aliases Template
    # identity on its own, so the transfer surface can never be the leak.
    unaliased = redact_report_for_public(report, aliases={}, redaction_key="secret-key")
    body = unaliased["extensions"][TRANSFER_DIAGNOSTICS_EXTENSION]
    for row in body["templates"]:
        assert row["template_alias"].startswith("xfer-")
        assert "MIB-SKILL-T" not in row["template_alias"]


def test_redaction_aliases_are_keyed_so_two_evaluators_do_not_agree():
    body = {
        "version": "1.0.0",
        "coverage": {"annotated_templates": 1, "annotated_probes": 1, "relations": {"exact_replay": 1}},
        "templates": [{"template_id": "MIB-SKILL-T01", "relations": [{"probe_id": "p"}], "diagnostic_mode": "behavioral"}],
        "distance_profile": [],
        "aggregate": {},
    }
    a = redact_transfer_diagnostics(body, redaction_key="key-a")["templates"][0]["template_alias"]
    b = redact_transfer_diagnostics(body, redaction_key="key-b")["templates"][0]["template_alias"]
    assert a != b


# --- Capability Card -------------------------------------------------------


def test_capability_card_renders_transfer_sections_only_when_present(transfer_run):
    _, report, _ = transfer_run
    card = render_capability_card(report)
    assert "Transfer Diagnostics" in card
    assert "Transfer Profile" in card
    assert "D0 Exact Replay" in card
    assert "D3 Compositional" in card
    assert "do not enter the MIB Score" in card
    # Absent metrics are omitted, not shown as zero.
    assert "Formation Efficiency" not in card
    assert "Routing Efficiency" not in card
    # No evaluator-private identifier reaches the card.
    for needle in ["ability.", "p-nearmatch", "support_event_ids"]:
        assert needle not in card, needle

    without = copy.deepcopy(report)
    without.pop("extensions")
    assert "Transfer Diagnostics" not in render_capability_card(without)
