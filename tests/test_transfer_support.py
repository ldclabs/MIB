"""M6.1 — Transfer Support Annotation.

The annotation is evaluator-private diagnostic metadata.  These tests pin the
three properties that make it safe to ship: legacy Scenarios keep validating
unchanged, broken references are caught at authoring time, and no annotation
reaches the Agent or a public report.
"""

from __future__ import annotations

import copy
import json
from dataclasses import asdict

import pytest

from mib_runner.agents import ReferenceMemoryAgent
from mib_runner.benchmark import load_templates
from mib_runner.hidden import redact_report_for_public
from mib_runner.materialize import materialize
from mib_runner.report import build_basic_report, verify_score
from mib_runner.runner import run_scenario
from mib_runner.transfer import (
    TRANSFER_EXTENSION,
    check_profile_transfer_coverage,
    inspect_transfer,
    parse_transfer_support,
    relation_for_probe,
    transfer_coverage,
    transfer_support_digest,
    validate_transfer_support,
)
from mib_runner.types import Observation
from mib_runner.validation import load_json, validate_scenario

from paths import DEV_PACK, SCHEMAS, SCENARIO_SCHEMA_PATH

SCHEMA = json.loads(SCENARIO_SCHEMA_PATH.read_text())
TRANSFER_SCHEMA = json.loads((SCHEMAS / "mib-transfer-support.schema.json").read_text())

ABILITY_ID = "ability.context_required_commit"


#: Templates the Phase 1 migration annotated in place.
ANNOTATED_DEV_TEMPLATES = {
    "MIB-SKILL-001", "MIB-SKILL-002", "MIB-SKILL-003",
    "MIB-X-003", "MIB-EXP-001", "MIB-EXP-002", "MIB-EXP-003",
}


def _base_scenario() -> dict:
    """MIB-X-003 with its shipped annotation removed, as the unannotated control."""
    scenario = json.loads((DEV_PACK / "cross" / "MIB-X-003.json").read_text())
    (scenario.get("extensions") or {}).pop(TRANSFER_EXTENSION, None)
    if scenario.get("extensions") == {}:
        scenario.pop("extensions")
    return scenario


def _annotation() -> dict:
    return {
        "version": "1.0.0",
        "abilities": [
            {
                "id": ABILITY_ID,
                "label": "Context-required commit procedure",
                "kind": "procedure",
                "support_event_ids": ["e-failure", "e-learning"],
                "counterexample_event_ids": ["e-counterexample"],
                "procedure": {"ordered_steps": ["activate_context", "edit_item", "commit"]},
                "applicability": {
                    "positive_cues": ["item is contextual"],
                    "negative_cues": ["item is global"],
                    "required_world_predicates": ["contextual_save.context_required == true"],
                },
                "oracle_artifact": {
                    "artifact_type": "skill",
                    "content": "When an item requires a context, activate its matching context before editing and committing. When the item is global, commit directly.",
                    "format": "natural_language_procedure",
                },
                "provenance": {"mode": "author_defined"},
            }
        ],
        "probe_relations": [
            {
                "probe_id": "p-match",
                "ability_ids": [ABILITY_ID],
                "relation": "structural_transfer",
                "support_expected": True,
                "transfer_distance": {"class": "D2", "normalized": 0.67},
            },
            {
                "probe_id": "p-nonmatch",
                "ability_ids": [ABILITY_ID],
                "relation": "near_match_non_applicable",
                "support_expected": False,
            },
        ],
    }


def _annotated(mutate=None) -> dict:
    scenario = _base_scenario()
    annotation = _annotation()
    if mutate is not None:
        mutate(annotation)
    scenario.setdefault("extensions", {})[TRANSFER_EXTENSION] = annotation
    return scenario


def _errors(scenario: dict) -> list[str]:
    support = parse_transfer_support(scenario)
    assert support is not None
    return [f["code"] for f in validate_transfer_support(scenario, support) if f["severity"] == "error"]


# --- 1. Legacy compatibility ---------------------------------------------


def test_public_dev_pack_is_partly_annotated_and_wholly_clean():
    templates = load_templates(DEV_PACK)
    assert len(templates) == 24
    annotated = set()
    for template in templates:
        support = parse_transfer_support(template)
        if support is not None:
            annotated.add(template["id"])
        result = validate_scenario(template, SCHEMA, transfer_schema=TRANSFER_SCHEMA)
        assert result.valid, (template["id"], result.errors)
        # Annotated or not, no Template in the shipped pack carries a finding.
        assert not [w for w in result.warnings if w.startswith("transfer:")], (template["id"], result.warnings)
    # Phase 1 annotates Skill, the Skill-bearing Cross Template, and Experience.
    assert annotated == ANNOTATED_DEV_TEMPLATES


def test_unannotated_public_dev_templates_acquire_no_findings():
    for template in load_templates(DEV_PACK):
        if template["id"] in ANNOTATED_DEV_TEMPLATES:
            continue
        assert parse_transfer_support(template) is None
        result = validate_scenario(template, SCHEMA)
        assert result.valid and result.warnings == [], (template["id"], result.errors, result.warnings)


def test_every_annotated_dev_template_declares_an_oracle_artifact():
    for template in load_templates(DEV_PACK):
        support = parse_transfer_support(template)
        if support is None:
            continue
        assert all(a.oracle_artifact for a in support.abilities), template["id"]
        out = inspect_transfer(template, schema=TRANSFER_SCHEMA)
        assert out["errors"] == [] and out["warnings"] == [], (template["id"], out)


def test_missing_annotation_is_an_error_only_when_the_profile_requires_one():
    template = _base_scenario()
    assert validate_scenario(template, SCHEMA).valid
    strict = validate_scenario(template, SCHEMA, require_transfer_annotations=True)
    assert not strict.valid
    assert any("requires a mib.transfer_support.v1 annotation" in e for e in strict.errors)


# --- 2. Parsing and schema shape ------------------------------------------


def test_valid_annotation_parses_and_validates_against_both_schemas():
    scenario = _annotated()
    result = validate_scenario(scenario, SCHEMA, transfer_schema=TRANSFER_SCHEMA)
    assert result.valid, result.errors

    support = parse_transfer_support(scenario)
    assert support is not None
    assert support.version == "1.0.0"
    assert [a.id for a in support.abilities] == [ABILITY_ID]

    match = relation_for_probe(support, "p-match")
    assert match is not None
    assert match.support_expected is True
    assert match.distance_class == "D2"
    assert match.distance_normalized == pytest.approx(0.67)
    assert match.expected_behaviour == "apply"

    nonmatch = relation_for_probe(support, "p-nonmatch")
    assert nonmatch is not None
    assert nonmatch.support_expected is False
    # A negative control is a different causal class, not a farther distance.
    assert nonmatch.distance_normalized is None
    assert nonmatch.expected_behaviour == "withhold"

    ability = support.ability(ABILITY_ID)
    assert ability is not None
    assert ability.causal_information_sets == (("e-failure", "e-learning"),)
    assert ability.oracle_artifact is not None


def test_relation_for_unannotated_probe_is_none_not_false():
    support = parse_transfer_support(_annotated())
    assert relation_for_probe(support, "p-does-not-exist") is None


# --- 3. Semantic validation ------------------------------------------------


def test_unknown_support_event_id_fails():
    def mutate(a):
        a["abilities"][0]["support_event_ids"] = ["e-failure", "e-not-a-real-event"]

    assert "transfer.unknown_event" in _errors(_annotated(mutate))


def test_unknown_probe_id_fails():
    def mutate(a):
        a["probe_relations"][0]["probe_id"] = "p-not-a-real-probe"

    assert "transfer.unknown_probe" in _errors(_annotated(mutate))


def test_unknown_ability_reference_fails():
    def mutate(a):
        a["probe_relations"][0]["ability_ids"] = ["ability.ghost"]

    assert "transfer.unknown_ability" in _errors(_annotated(mutate))


def test_duplicate_ability_id_fails():
    def mutate(a):
        a["abilities"].append(copy.deepcopy(a["abilities"][0]))

    assert "transfer.duplicate_ability" in _errors(_annotated(mutate))


def test_duplicate_probe_relation_fails():
    def mutate(a):
        a["probe_relations"].append(copy.deepcopy(a["probe_relations"][0]))

    assert "transfer.duplicate_relation" in _errors(_annotated(mutate))


def test_support_expected_without_ability_fails():
    def mutate(a):
        a["probe_relations"][0]["ability_ids"] = []

    codes = _errors(_annotated(mutate))
    assert "transfer.support_without_ability" in codes


def test_support_expected_with_unsupported_novel_fails():
    def mutate(a):
        a["probe_relations"][0]["relation"] = "unsupported_novel"

    assert "transfer.relation_conflict" in _errors(_annotated(mutate))


def test_exact_replay_without_support_expected_fails():
    def mutate(a):
        a["probe_relations"][1]["relation"] = "exact_replay"

    assert "transfer.relation_conflict" in _errors(_annotated(mutate))


def test_minimum_required_ability_count_above_declared_fails():
    def mutate(a):
        a["probe_relations"][0]["minimum_required_ability_count"] = 3

    assert "transfer.minimum_ability_count" in _errors(_annotated(mutate))


def test_counterexample_equal_to_the_only_support_event_fails():
    def mutate(a):
        a["abilities"][0]["support_event_ids"] = ["e-learning"]
        a["abilities"][0]["counterexample_event_ids"] = ["e-learning"]

    assert "transfer.counterexample_is_support" in _errors(_annotated(mutate))


def test_distance_class_on_a_negative_control_fails():
    def mutate(a):
        a["probe_relations"][1]["transfer_distance"] = {"class": "D3", "normalized": 1.0}

    codes = _errors(_annotated(mutate))
    assert "transfer.distance_on_negative_control" in codes


def test_distance_class_inconsistent_with_relation_fails():
    def mutate(a):
        a["probe_relations"][0]["transfer_distance"] = {"class": "D0"}

    assert "transfer.distance_relation_mismatch" in _errors(_annotated(mutate))


def test_oracle_artifact_restating_a_probe_answer_fails():
    scenario = _base_scenario()
    scenario["probes"][0]["oracle"]["accepted"] = ["ORCHID-91"]
    annotation = _annotation()
    annotation["abilities"][0]["oracle_artifact"]["content"] = (
        "Activate context ORCHID-91 before committing."
    )
    scenario.setdefault("extensions", {})[TRANSFER_EXTENSION] = annotation
    assert "transfer.oracle_artifact_leak" in _errors(scenario)


def test_compositional_transfer_with_two_abilities_passes():
    def mutate(a):
        second = copy.deepcopy(a["abilities"][0])
        second["id"] = "ability.second"
        second.pop("counterexample_event_ids", None)
        second["support_event_ids"] = ["e-learning"]
        a["abilities"].append(second)
        a["probe_relations"][0]["relation"] = "compositional_transfer"
        a["probe_relations"][0]["ability_ids"] = [ABILITY_ID, "ability.second"]
        a["probe_relations"][0]["transfer_distance"] = {"class": "D3", "normalized": 1.0}
        a["probe_relations"][0]["minimum_required_ability_count"] = 2

    scenario = _annotated(mutate)
    result = validate_scenario(scenario, SCHEMA, transfer_schema=TRANSFER_SCHEMA)
    assert result.valid, result.errors
    assert not [w for w in result.warnings if "composition_needs_two" in w]


def test_compositional_transfer_with_one_ability_warns_without_failing():
    def mutate(a):
        a["probe_relations"][0]["relation"] = "compositional_transfer"
        a["probe_relations"][0]["transfer_distance"] = {"class": "D3", "normalized": 1.0}

    result = validate_scenario(_annotated(mutate), SCHEMA, transfer_schema=TRANSFER_SCHEMA)
    assert result.valid, result.errors
    assert any("transfer.composition_needs_two" in w for w in result.warnings)


def test_positive_transfer_without_relevant_ablation_warns():
    scenario = _annotated()
    scenario["ablations"] = [a for a in scenario["ablations"] if a["kind"] != "relevant_memory"]
    result = validate_scenario(scenario, SCHEMA, transfer_schema=TRANSFER_SCHEMA)
    assert result.valid, result.errors
    assert any("transfer.no_relevant_ablation" in w for w in result.warnings)


def test_near_match_without_a_boundary_warns():
    def mutate(a):
        a["abilities"][0].pop("counterexample_event_ids", None)

    scenario = _annotated(mutate)
    scenario["ablations"] = [a for a in scenario["ablations"] if a["kind"] != "counterexample"]
    result = validate_scenario(scenario, SCHEMA, transfer_schema=TRANSFER_SCHEMA)
    assert result.valid, result.errors
    assert any("transfer.near_match_without_boundary" in w for w in result.warnings)


def test_unannotated_skill_probe_warns_when_the_scenario_is_annotated():
    def mutate(a):
        a["probe_relations"] = [a["probe_relations"][0]]

    result = validate_scenario(_annotated(mutate), SCHEMA, transfer_schema=TRANSFER_SCHEMA)
    assert result.valid, result.errors
    assert any("transfer.unannotated_probe" in w and "p-nonmatch" in w for w in result.warnings)


def test_transfer_schema_rejects_an_unknown_relation_value():
    def mutate(a):
        a["probe_relations"][0]["relation"] = "teleportation"

    result = validate_scenario(_annotated(mutate), SCHEMA, transfer_schema=TRANSFER_SCHEMA)
    assert not result.valid
    assert any(e.startswith("transfer-schema:") for e in result.errors)


# --- 4. Inspection and coverage -------------------------------------------


def test_inspect_transfer_summarizes_relations_and_distances():
    out = inspect_transfer(_annotated(), schema=TRANSFER_SCHEMA)
    assert out["scenario_id"] == "MIB-X-003"
    assert out["annotated"] is True
    assert out["abilities"] == 1
    assert out["annotated_probes"] == 2
    assert out["relations"] == {"near_match_non_applicable": 1, "structural_transfer": 1}
    assert out["distance_classes"] == {"D2": 1}
    assert out["oracle_artifacts"] == 1
    assert out["errors"] == []
    assert out["digest"].startswith("sha256:")


def test_inspect_transfer_on_an_unannotated_scenario_reports_no_annotation():
    out = inspect_transfer(_base_scenario())
    assert out["annotated"] is False
    assert out["abilities"] == 0
    assert out["errors"] == []


def test_transfer_support_digest_changes_with_the_oracle_artifact():
    before = transfer_support_digest(parse_transfer_support(_annotated()))

    def mutate(a):
        a["abilities"][0]["oracle_artifact"]["content"] = "A different reusable procedure."

    after = transfer_support_digest(parse_transfer_support(_annotated(mutate)))
    assert before != after


def test_profile_transfer_coverage_shortfall_is_reported():
    coverage = transfer_coverage([_annotated()])
    assert coverage["annotated_templates"] == 1
    assert coverage["annotated_probes"] == 2
    profile = {"transfer_coverage": {"required_relations": {"structural_transfer": 1, "exact_replay": 2}}}
    findings = check_profile_transfer_coverage(profile, coverage)
    assert [f["relation"] for f in findings] == ["exact_replay"]


# --- 5. Leakage -----------------------------------------------------------


class _RecordingAgent(ReferenceMemoryAgent):
    """Reference Agent that keeps every request payload it was handed."""

    seen: list[str] = []

    def reset(self, *, run_id, seed, virtual_time):
        _RecordingAgent.seen.append(json.dumps({"seed": seed, "virtual_time": virtual_time}, default=str))
        return super().reset(run_id=run_id, seed=seed, virtual_time=virtual_time)

    def observe(self, *, run_id, request_id, observation: Observation):
        _RecordingAgent.seen.append(json.dumps(asdict(observation), default=str, ensure_ascii=False))
        return super().observe(run_id=run_id, request_id=request_id, observation=observation)

    def respond(self, *, run_id, request_id, interaction_id, input_data, virtual_time):
        _RecordingAgent.seen.append(json.dumps(input_data, default=str, ensure_ascii=False))
        return super().respond(
            run_id=run_id, request_id=request_id, interaction_id=interaction_id,
            input_data=input_data, virtual_time=virtual_time,
        )

    def act(self, *, run_id, request_id, task_id, goal, constraints, tools, continuation, virtual_time):
        _RecordingAgent.seen.append(json.dumps({"goal": goal, "constraints": constraints, "tools": tools}, default=str, ensure_ascii=False))
        return super().act(
            run_id=run_id, request_id=request_id, task_id=task_id, goal=goal,
            constraints=constraints, tools=tools, continuation=continuation, virtual_time=virtual_time,
        )


def test_no_transfer_annotation_reaches_any_agent_request():
    _RecordingAgent.seen = []
    instance = materialize(_annotated(), 101)
    run_scenario(scenario=instance, agent_factory=_RecordingAgent, include_ablations=True, repetition=0, agent_seed=101)
    assert _RecordingAgent.seen
    blob = "\n".join(_RecordingAgent.seen)
    for needle in [TRANSFER_EXTENSION, ABILITY_ID, "support_event_ids", "oracle_artifact", "structural_transfer", "near_match_non_applicable"]:
        assert needle not in blob, needle


def test_public_redaction_of_an_annotated_scenario_leaks_no_ability_id():
    instance = materialize(_annotated(), 101)
    runs = run_scenario(scenario=instance, agent_factory=ReferenceMemoryAgent, include_ablations=True, repetition=0, agent_seed=101)
    report = build_basic_report(runs=runs, scenario=instance, agent_descriptor=ReferenceMemoryAgent().describe())
    public = redact_report_for_public(report, aliases={"MIB-X-003": "hidden-fam-01"}, redaction_key="k")
    blob = json.dumps(public, ensure_ascii=False)
    for needle in [ABILITY_ID, "support_event_ids", "oracle_artifact", TRANSFER_EXTENSION]:
        assert needle not in blob, needle


# --- 6. Score compatibility -----------------------------------------------


def test_annotation_does_not_change_scores_or_score_verification():
    plain = materialize(_base_scenario(), 101)
    annotated = materialize(_annotated(), 101)
    assert (annotated.get("extensions") or {}).get(TRANSFER_EXTENSION) is not None

    plain_runs = run_scenario(scenario=plain, agent_factory=ReferenceMemoryAgent, include_ablations=True, repetition=0, agent_seed=101)
    annotated_runs = run_scenario(scenario=annotated, agent_factory=ReferenceMemoryAgent, include_ablations=True, repetition=0, agent_seed=101)
    assert [r["scenario_score"] for r in plain_runs] == [r["scenario_score"] for r in annotated_runs]

    descriptor = ReferenceMemoryAgent().describe()
    plain_report = build_basic_report(runs=plain_runs, scenario=plain, agent_descriptor=descriptor)
    annotated_report = build_basic_report(runs=annotated_runs, scenario=annotated, agent_descriptor=descriptor)
    assert (
        plain_report["aggregates"]["mib_score"]["final_score"]
        == annotated_report["aggregates"]["mib_score"]["final_score"]
    )
    assert verify_score(annotated_report)["valid"]


def test_materialization_preserves_annotations_and_resolves_placeholders():
    scenario = _base_scenario()
    annotation = _annotation()
    # Annotations may reference instantiated values; placeholders must resolve
    # exactly as they do in the Scenario body.
    annotation["abilities"][0]["label"] = "Context procedure learned with ${user_name}"
    scenario.setdefault("extensions", {})[TRANSFER_EXTENSION] = annotation

    instance = materialize(scenario, 101)
    support = parse_transfer_support(instance)
    assert support is not None
    label = support.abilities[0].label
    assert "${user_name}" not in label
    assert instance["actors"][0]["display_name"] in label
    assert validate_scenario(instance, SCHEMA, transfer_schema=TRANSFER_SCHEMA).valid


def test_transfer_support_schema_file_is_a_valid_json_schema():
    import jsonschema

    jsonschema.Draft202012Validator.check_schema(TRANSFER_SCHEMA)
    assert TRANSFER_SCHEMA["$id"] == "urn:mib:0.1:schema:transfer-support"
    assert load_json(SCHEMAS / "mib-transfer-support.schema.json") == TRANSFER_SCHEMA
