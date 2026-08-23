"""M6.4 — MIB-R Reality Track prototype.

MIB-R asks whether the same memory intelligence survives in a realistic
external task environment. Its contribution is not the tasks; it is that every
condition is paired and only memory state varies. These tests pin the pairing,
the negative controls, the evaluator-private transfer graph, the public
redaction, and the separation from MIB-Core.
"""

from __future__ import annotations

import json

import pytest

from mib_runner.agents.reality_fixtures import (
    NaiveRealityAgent,
    OverGeneralizingRealityAgent,
    RuleLearningRealityAgent,
)
from mib_runner.leaderboard import paired_compare_reports, result_family
from mib_runner.reality import (
    CONDITIONS,
    REALITY_EXTENSION,
    attest_reality_result,
    load_adapter,
    load_reality_pack,
    redact_reality_report,
    render_reality_card,
    run_reality_benchmark,
    run_reality_pair,
    verify_reality_attestation,
)
from mib_runner.reality_domains.ledger_codes import (
    ABILITY_MOD97,
    UNKNOWN_ANSWER,
    ability_is_load_bearing,
)
from mib_runner.reality_domains.ledger_codes import test_tasks as held_out_tasks
from mib_runner.reality_domains.ledger_codes import train_tasks as acquisition_tasks
from mib_runner.reality_graph import (
    load_reality_graph,
    parse_reality_graph,
    redact_reality_graph,
    validate_reality_graph,
)
from mib_runner.types import AgentOutput

from paths import BASE, PROFILES, SCHEMAS

PACK_PATH = BASE / "reality" / "MIB-R-Demo-LedgerCodes" / "pack.json"
PACK_SCHEMA = json.loads((SCHEMAS / "mib-reality-pack.schema.json").read_text())
PROFILE = json.loads((PROFILES / "MIB-R-0.1-Dev.json").read_text())


@pytest.fixture(scope="module")
def pack():
    return load_reality_pack(PACK_PATH)


@pytest.fixture(scope="module")
def graph(pack):
    return load_reality_graph(PACK_PATH, pack)


@pytest.fixture(scope="module")
def healthy(pack):
    report, summary = run_reality_benchmark(
        pack=pack, pack_path=PACK_PATH, agent_factory=RuleLearningRealityAgent,
        bootstrap_resamples=40, bootstrap_seed=7,
    )
    return report, summary


def _metrics(report):
    return report["extensions"][REALITY_EXTENSION]["transfer_metrics"]


# --- Pack shape -----------------------------------------------------------


def test_pack_meets_the_prototype_acceptance_counts(pack):
    import jsonschema

    jsonschema.Draft202012Validator(PACK_SCHEMA).validate(pack)
    assert len(pack["train_tasks"]) >= PROFILE["minimum_task_counts"]["train_tasks"]
    assert len(pack["test_tasks"]) >= PROFILE["minimum_task_counts"]["test_tasks"]
    assert set(pack["conditions"]) == set(CONDITIONS)
    # The pack redistributes no upstream payload.
    assert load_adapter(pack).describe()["redistributes_external_data"] is False


def test_graph_covers_every_declared_relation(pack, graph):
    counts = redact_reality_graph(graph)["relations"]
    for relation, minimum in PROFILE["required_relations"].items():
        assert counts.get(relation, 0) >= minimum, (relation, counts)
    findings = validate_reality_graph(
        graph,
        train_task_ids={t["task_id"] for t in pack["train_tasks"]},
        test_task_ids={t["task_id"] for t in pack["test_tasks"]},
    )
    assert [f for f in findings if f["severity"] == "error"] == []
    assert [f for f in findings if f["severity"] == "warning"] == []


def test_every_declared_convention_is_load_bearing():
    for task in (*acquisition_tasks(), *held_out_tasks()):
        for ability in task["required_abilities"]:
            assert ability_is_load_bearing(task, ability), (task["task_id"], ability)


def test_provisional_family_has_no_convention_and_expects_abstention():
    provisional = [t for t in held_out_tasks() if t["family"] == "provisional"]
    assert len(provisional) >= 2
    for task in provisional:
        assert task["expected"] == UNKNOWN_ANSWER
        assert task["required_abilities"] == []


def test_task_content_digest_mismatch_fails_loudly(pack):
    adapter = load_adapter(pack)
    ref = dict(pack["test_tasks"][0])
    ref["content_digest"] = "sha256:" + "0" * 64
    with pytest.raises(ValueError, match="content digest mismatch"):
        adapter.load_task(ref)


def test_graph_digest_mismatch_fails_loudly(pack):
    tampered = json.loads(json.dumps(pack))
    tampered["transfer_graph"]["digest"] = "sha256:" + "0" * 64
    with pytest.raises(Exception, match="digest mismatch"):
        load_reality_graph(PACK_PATH, tampered)


# --- Paired execution -----------------------------------------------------


def test_conditions_are_paired_on_everything_but_memory(pack, graph):
    adapter = load_adapter(pack)
    train = {r["task_id"]: adapter.load_task(r) for r in pack["train_tasks"]}
    target = adapter.load_task(next(r for r in pack["test_tasks"] if r["task_id"] == "test-01"))
    rows = [
        run_reality_pair(
            adapter=adapter, graph=graph, agent_factory=RuleLearningRealityAgent,
            train_tasks=train, test_task=target, condition=condition, seed=99, repetition=2,
        )
        for condition in CONDITIONS
    ]
    for row in rows:
        assert row["target_task_id"] == "test-01"
        assert row["task_content_digest"] == target["content_digest"]
        assert row["seed"] == 99
        assert row["repetition"] == 2
        assert row["relation"] == "surface_shift"
        assert row["distance_class"] == "D1"
    acquisition = {r["condition"]: r["acquisition_task_count"] for r in rows}
    withheld = {r["condition"]: r["withheld_task_count"] for r in rows}
    assert acquisition["no_memory"] == 0
    assert acquisition["natural_memory"] == len(train)
    assert acquisition["relevant_ability_ablated"] < acquisition["natural_memory"]
    # The irrelevant control withholds as much past as the relevant one, capped
    # by how many acquisition tasks this target genuinely does not depend on.
    assert withheld["irrelevant_ability_ablated"] == min(
        withheld["relevant_ability_ablated"], len(train) - len(set(graph.causal_task_ids("test-01")))
    )
    # The oracle conditions stand in for the same withheld Experience.
    assert withheld["oracle_skill"] == withheld["relevant_ability_ablated"]
    assert withheld["oracle_routing"] == withheld["relevant_ability_ablated"]


def test_reality_adapter_uses_the_run_id_that_was_reset(pack, graph):
    adapter = load_adapter(pack)
    train = {r["task_id"]: adapter.load_task(r) for r in pack["train_tasks"]}
    target = adapter.load_task(pack["test_tasks"][0])

    class StrictRunAgent:
        def reset(self, *, run_id, **_):
            self.run_id = run_id
            return {"accepted": True}

        def observe(self, *, run_id, **_):
            assert run_id == self.run_id
            return {"accepted": True}

        def respond(self, *, run_id, **_):
            assert run_id == self.run_id
            return AgentOutput(type="message", content="unknown")

    row = run_reality_pair(
        adapter=adapter,
        graph=graph,
        agent_factory=StrictRunAgent,
        train_tasks=train,
        test_task=target,
        condition="no_memory",
        seed=101,
        repetition=0,
    )
    assert row["condition"] == "no_memory"


def test_irrelevant_ablation_never_removes_load_bearing_experience(pack, graph):
    adapter = load_adapter(pack)
    train = {r["task_id"]: adapter.load_task(r) for r in pack["train_tasks"]}
    for target_id in ("test-01", "test-05", "test-08", "test-09"):
        target = adapter.load_task({"task_id": target_id})
        rows = {
            condition: run_reality_pair(
                adapter=adapter, graph=graph, agent_factory=RuleLearningRealityAgent,
                train_tasks=train, test_task=target, condition=condition, seed=101, repetition=0,
            )
            for condition in ("natural_memory", "irrelevant_ability_ablated")
        }
        assert rows["irrelevant_ability_ablated"]["score"] == rows["natural_memory"]["score"], target_id


# --- Diagnostics ----------------------------------------------------------


def test_capped_irrelevant_ablation_is_reported_not_hidden(healthy):
    report, _ = healthy
    codes = {w["code"] for w in report["warnings"]}
    assert "reality.ablation_magnitude_mismatch" in codes


def test_a_healthy_memory_system_transfers_and_withholds(healthy):
    report, _ = healthy
    metrics = _metrics(report)
    assert metrics["supported_transfer_success_rate"] == pytest.approx(1.0)
    assert metrics["natural_transfer_gain"] > 0.5
    assert metrics["relevant_ablation_delta"] > 0.5
    assert metrics["irrelevant_stability"] == pytest.approx(1.0)
    assert metrics["near_match_resistance"] == pytest.approx(1.0)
    assert metrics["unsupported_memory_neutrality"] == pytest.approx(1.0)
    # Injecting a plausible over-generalization does measurable harm.
    assert metrics["memory_harm"] > 0.0


def test_a_system_that_remembers_nothing_shows_no_transfer_but_stays_neutral(pack):
    report, _ = run_reality_benchmark(pack=pack, pack_path=PACK_PATH, agent_factory=NaiveRealityAgent)
    metrics = _metrics(report)
    assert metrics["natural_transfer_gain"] == pytest.approx(0.0)
    assert metrics["supported_transfer_success_rate"] == pytest.approx(0.0)
    # Remembering nothing means never over-applying.
    assert metrics["unsupported_memory_neutrality"] == pytest.approx(1.0)


def test_an_over_generalizing_system_helps_and_fails_the_boundary(pack, healthy):
    report, _ = run_reality_benchmark(pack=pack, pack_path=PACK_PATH, agent_factory=OverGeneralizingRealityAgent)
    metrics = _metrics(report)
    healthy_metrics = _metrics(healthy[0])
    assert metrics["supported_transfer_success_rate"] == pytest.approx(
        healthy_metrics["supported_transfer_success_rate"]
    )
    assert metrics["near_match_resistance"] == pytest.approx(0.0)
    assert metrics["near_match_resistance"] < healthy_metrics["near_match_resistance"]


def test_distance_profile_covers_every_positive_class(healthy):
    report, _ = healthy
    profile = report["extensions"][REALITY_EXTENSION]["distance_profile"]
    assert [x["class"] for x in profile] == ["D0", "D1", "D2", "D3"]
    for entry in profile:
        assert entry["condition_scores"]["natural_memory"] >= 0.0


def test_negative_controls_are_not_encoded_as_distance(healthy):
    report, _ = healthy
    for row in report["extensions"][REALITY_EXTENSION]["by_task"]:
        if row["relation"] in {"near_match_non_applicable", "unsupported_novel"}:
            assert row["distance_class"] is None


def test_signed_deltas_are_not_absolute_values(pack):
    report, _ = run_reality_benchmark(pack=pack, pack_path=PACK_PATH, agent_factory=OverGeneralizingRealityAgent)
    # Removing memory an over-generalizing system should not have been using
    # improves it. A signed delta shows that; an absolute value would hide it.
    assert _metrics(report)["irrelevant_ablation_delta"] < 0.0


def test_bootstrap_gives_confidence_intervals(healthy):
    report, _ = healthy
    ci = report["statistics"]["overall"]["natural_transfer_gain"]
    assert ci["level"] == 0.95
    assert ci["method"] == "paired_task_bootstrap_percentile"
    assert ci["lower"] <= ci["upper"]


# --- Separation, redaction, attestation -----------------------------------


def test_mib_r_is_its_own_result_family_and_is_never_cross_ranked(healthy):
    report, _ = healthy
    assert result_family(PROFILE) == "reality"
    assert report["benchmark"]["result_family"] == "reality"
    assert report["benchmark"]["official"] is False
    assert "mib_score" not in json.dumps(report["benchmark"])

    core_report = {"benchmark": {"profile": {"id": "MIB-Core-0.1"}}}
    reality_report = {"benchmark": {"profile": {"id": "MIB-R-0.1-Dev"}}}
    with pytest.raises(ValueError, match="cannot compare across result families"):
        paired_compare_reports(core_report, reality_report)


def test_public_report_withholds_per_task_and_graph_structure(healthy):
    report, _ = healthy
    public = redact_reality_report(report)
    assert public["scope"] == "public"
    assert public["results"]["runs"] == []
    body = public["extensions"][REALITY_EXTENSION]
    assert "by_task" not in body
    assert "by_relation" not in body
    assert set(body["transfer_graph"]) == {"ability_count", "edge_count", "digest", "statement"}
    for entry in body["distance_profile"]:
        assert "condition_scores" not in entry

    blob = json.dumps(public, ensure_ascii=False)
    for needle in [ABILITY_MOD97, "train-mod97-01", "test-08", "near_match_non_applicable", "source_task_ids"]:
        assert needle not in blob, needle
    # The aggregate surface a leaderboard needs survives.
    assert body["transfer_metrics"]["natural_transfer_gain"] > 0.0


def test_attestation_binds_the_pack_graph_and_environment(healthy):
    report, _ = healthy
    public = redact_reality_report(report)
    signed = attest_reality_result(report=report, public_report=public, root_secret="demo-secret")
    assert verify_reality_attestation(signed, root_secret="demo-secret")
    assert not verify_reality_attestation(signed, root_secret="another-secret")

    attestation = signed["attestation"]
    assert attestation["result_family"] == "reality"
    assert attestation["official"] is False
    assert attestation["transfer_graph_digest"].startswith("sha256:")
    assert attestation["reality_pack"]["id"] == "MIB-R-Demo-LedgerCodes"
    assert "score" not in attestation

    tampered = json.loads(json.dumps(signed))
    tampered["attestation"]["transfer_graph_digest"] = "sha256:" + "0" * 64
    assert not verify_reality_attestation(tampered, root_secret="demo-secret")


def test_reality_card_states_the_prototype_boundary(healthy):
    report, _ = healthy
    card = render_reality_card(report)
    assert "MIB-R" in card
    assert "never ranked against MIB-Core" in card
    assert "Near-Match Resistance" in card
    for needle in [ABILITY_MOD97, "train-mod97-01", "test-08"]:
        assert needle not in card, needle


def test_graph_is_resolvable_only_through_its_private_reference(pack):
    assert "edges" not in pack["transfer_graph"]
    assert pack["transfer_graph"]["private_ref"].endswith(".json")
    assert pack["transfer_graph"]["digest"].startswith("sha256:")
    # No Ability identity or support mapping appears in the published manifest.
    blob = json.dumps(pack, ensure_ascii=False)
    assert ABILITY_MOD97 not in blob
    assert "source_task_ids" not in blob


def test_inline_graph_is_accepted_for_evaluator_side_use():
    raw = {
        "abilities": [{"id": "a.x", "kind": "procedure"}],
        "edges": [{
            "target_task_id": "test-01", "ability_ids": ["a.x"],
            "relation": "surface_shift", "support_expected": True,
            "source_task_ids": ["train-01"],
        }],
    }
    graph = parse_reality_graph(raw)
    assert graph.edge_for("test-01").distance_class == "D1"
    # causal_task_ids defaults to the declared support.
    assert graph.causal_task_ids("test-01") == ("train-01",)
    findings = validate_reality_graph(graph, train_task_ids={"train-01"}, test_task_ids={"test-01"})
    assert [f["code"] for f in findings if f["severity"] == "error"] == []
    assert {f["code"] for f in findings if f["severity"] == "warning"} == {"reality.missing_negative_control"}
