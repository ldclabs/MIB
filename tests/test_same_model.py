from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest

from mib_runner.model_clients import ModelCompletion
from mib_runner.same_model_agent import (
    InvocationRecorder,
    LexicalRetrievalPolicy,
    SameModelAgent,
    StructuredMemoryPolicy,
)
from mib_runner.same_model_calibration import (
    build_experiment_lock,
    load_experiment,
    run_same_model_calibration,
    _condition_schedule,
    _schedule_audit,
)
from mib_runner.types import Observation

from paths import BASE, OFFICIAL_PACK, PROFILES, SCENARIO_SCHEMA_PATH, SCHEMAS, TRANSFER_PACK


class RecordingModel:
    def __init__(self):
        self.calls = []
    def identity(self):
        return {"client": "recording", "model_id": "fixed-model"}
    def complete(self, *, messages, parameters, request_id):
        self.calls.append({"messages": messages, "parameters": parameters, "request_id": request_id})
        return ModelCompletion('{"type":"message","content":"ok"}')
    def close(self):
        pass


def obs(i, text, typ="user_message"):
    return Observation(observation_id=f"o{i}", type=typ, content=text, virtual_time=f"2026-01-{i:02d}T00:00:00Z")


def make_agent(condition, model, recorder):
    return SameModelAgent(
        condition=condition,
        model_client=model,
        system_prompt="fixed system",
        reasoning_policy="fixed policy",
        model_parameters={"temperature": 0},
        recorder=recorder,
        memory_config={"retrieval_top_k": 1, "structured_top_k": 2, "structured_salient_k": 1, "parse_retries": 0},
        empirical_eligible=True,
        seed_policy="paired_per_call",
    )


def test_b0_and_b1_only_differ_in_memory_context():
    model0, model1 = RecordingModel(), RecordingModel()
    r0, r1 = InvocationRecorder(), InvocationRecorder()
    a0, a1 = make_agent("B0", model0, r0), make_agent("B1", model1, r1)
    for a in (a0, a1):
        a.reset(run_id="r", seed="paired", virtual_time=None)
        a.observe(run_id="r", request_id="q1", observation=obs(1, "The access code is ORCHID-91."))
        a.respond(run_id="r", request_id="q2", interaction_id="i", input_data={"content": "What is the access code?"}, virtual_time=None)
    u0 = model0.calls[0]["messages"][-1]["content"]
    u1 = model1.calls[0]["messages"][-1]["content"]
    assert "LONG_TERM_MEMORY_CONTEXT:\n<empty>" in u0
    assert "ORCHID-91" not in u0
    assert "ORCHID-91" in u1
    assert "MEMORY CONDITION" not in u0
    assert "MEMORY CONDITION" not in u1
    assert model0.calls[0]["parameters"]["seed"] == model1.calls[0]["parameters"]["seed"]


def test_lexical_policy_selects_relevant_memory():
    p = LexicalRetrievalPolicy(top_k=1)
    items = [obs(1, "I like green tea."), obs(2, "Project Cedar uses UTC+4."), obs(3, "Lunch was good.")]
    selected, truncated = p.select(items, query="Which timezone does Project Cedar use?", limit_chars=None)
    assert len(selected) == 1
    assert "UTC+4" in selected[0].content
    assert not truncated


def test_structured_policy_keeps_correction_salient():
    p = StructuredMemoryPolicy(top_k=1, salient_k=1)
    items = [
        obs(1, "The code is AX-19."),
        obs(2, "Correction: I misspoke. The current code is AX-91."),
        obs(3, "The cafeteria closes at 18:00."),
    ]
    selected, _ = p.select(items, query="What code should be used now?", limit_chars=None)
    assert any("AX-91" in (o.content or "") for o in selected)


def test_experiment_lock_is_stable_and_valid():
    # Uses the public dev-pack experiment so the suite passes on a clean clone;
    # the private canonical pack is evaluator-only.
    root = Path(__file__).resolve().parents[1]
    cfg_path = root / "examples" / "same-model" / "same-model-experiment.dev.json"
    cfg, paths = load_experiment(cfg_path)
    a = build_experiment_lock(cfg, paths)
    b = build_experiment_lock(cfg, paths)
    assert a["digest"] == b["digest"]
    assert a["conditions"]["B0"]["memory_policy"] == "no_memory"
    assert a["conditions"]["B1"]["memory_policy"] == "full_visible_history"
    schema = json.loads((root / "schemas" / "mib-same-model-experiment.schema.json").read_text())
    jsonschema.Draft202012Validator(schema).validate(cfg)


def test_condition_schedule_is_balanced_for_official_shape():
    templates = [{"id": f"T{i:02d}"} for i in range(36)]
    sched = _condition_schedule(templates, [101, 202, 303, 404], 2)
    audit = _schedule_audit(sched)
    assert audit["paired_units"] == 288
    assert audit["balanced"] is True
    assert audit["max_position_count_difference"] == 0
    for counts in audit["position_counts"].values():
        assert counts == [72, 72, 72, 72]


def test_estimate_only_honors_output_json(tmp_path):
    from mib_runner.same_model_cli import main
    root = Path(__file__).resolve().parents[1]
    output = tmp_path / "estimate.json"
    rc = main([
        str(root / "examples" / "same-model" / "same-model-experiment.dev.json"),
        "--estimate-only",
        "--output-json", str(output),
        "--experiment-schema", str(root / "schemas" / "mib-same-model-experiment.schema.json"),
    ])
    assert rc == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["estimate"]["template_count"] == len(list((root / "scenarios" / "dev").rglob("MIB-*.json")))
    assert payload["experiment_lock"].startswith("sha256:")


@pytest.mark.skipif(
    not (OFFICIAL_PACK / "templates").is_dir(),
    reason=f"official private pack not available at {OFFICIAL_PACK}",
)
def test_official_pack_experiment_estimates_full_release_shape(tmp_path):
    """The shipped canonical-pack stub covers the 36-Template release shape."""
    from mib_runner.same_model_cli import main
    root = Path(__file__).resolve().parents[1]
    output = tmp_path / "estimate.json"
    rc = main([
        str(root / "examples" / "same-model" / "same-model-experiment.stub.json"),
        "--estimate-only",
        "--output-json", str(output),
        "--experiment-schema", str(root / "schemas" / "mib-same-model-experiment.schema.json"),
    ])
    assert rc == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["estimate"]["template_count"] == 36


# --- Optional transfer diagnostic cells (M6.2, §40) ------------------------


def _transfer_experiment(tmp_path: Path, *, transfer: dict | None) -> Path:
    """A stub-model experiment over the Transfer Diagnostic Dev Pack."""
    pack = tmp_path / "pack"
    (pack / "templates").mkdir(parents=True)
    (pack / "profiles").mkdir()
    for src in sorted(TRANSFER_PACK.glob("MIB-*.json")):
        (pack / "templates" / src.name).write_text(src.read_text(), encoding="utf-8")
    profile = pack / "profiles" / "MIB-Transfer-0.1-Dev.json"
    profile.write_text((PROFILES / "MIB-Transfer-0.1-Dev.json").read_text(), encoding="utf-8")

    calibration = {
        "instance_seeds": [101],
        "repetitions": 1,
        "bootstrap_resamples": 20,
        "bootstrap_seed": "smoke",
        "causal_baseline": "B3",
        "causal_instance_seeds": [101],
        "causal_repetitions": 1,
    }
    if transfer is not None:
        calibration["transfer_diagnostics"] = transfer
    cfg = {
        "mib": "0.1",
        "kind": "MIBSameModelExperiment",
        "id": "MIB-Transfer-0.1-same-model-smoke",
        "pack": str(pack),
        "scenario_schema": str(SCENARIO_SCHEMA_PATH),
        "profile": str(profile),
        "model": {
            "client": "deterministic_stub",
            "model_id": "mib-deterministic-stub/0.1",
            "parameters": {"temperature": 0, "max_tokens": 512},
            "seed_policy": "paired_per_call",
        },
        "agent": {
            "system_prompt": str(BASE / "prompts" / "same-model-agent-v0.1.txt"),
            "reasoning_policy": str(BASE / "prompts" / "reasoning-policy-v0.1.txt"),
            "retrieval_top_k": 4,
            "structured_top_k": 10,
            "structured_salient_k": 6,
            "parse_retries": 1,
        },
        "calibration": calibration,
    }
    path = tmp_path / "experiment.json"
    path.write_text(json.dumps(cfg), encoding="utf-8")
    jsonschema.Draft202012Validator(
        json.loads((SCHEMAS / "mib-same-model-experiment.schema.json").read_text())
    ).validate(cfg)
    return path


def test_transfer_cells_are_opt_in_and_do_not_touch_the_release_gate(tmp_path):
    report_schema = json.loads((SCHEMAS / "mib-same-model-report.schema.json").read_text())

    off = run_same_model_calibration(_transfer_experiment(tmp_path / "off", transfer=None))
    on = run_same_model_calibration(
        _transfer_experiment(tmp_path / "on", transfer={"enabled": True, "instance_seeds": [101], "repetitions": 1})
    )
    for report in (off, on):
        jsonschema.Draft202012Validator(report_schema).validate(report)

    assert off["transfer_diagnostics"] == {"enabled": False}
    assert on["transfer_diagnostics"]["enabled"] is True

    # The diagnostics are supplemental: nothing a calibration gate reads moves.
    assert off["calibration"]["templates"] == on["calibration"]["templates"]
    assert off["calibration"]["summary"] == on["calibration"]["summary"]
    assert off["empirical_release_gate"] == on["empirical_release_gate"]


def test_enabling_transfer_cells_binds_them_into_the_experiment_lock(tmp_path):
    off_cfg, off_paths = load_experiment(_transfer_experiment(tmp_path / "off", transfer=None))
    on_cfg, on_paths = load_experiment(
        _transfer_experiment(tmp_path / "on", transfer={"enabled": True, "epsilon": 0.1})
    )
    off_lock = build_experiment_lock(off_cfg, off_paths)
    on_lock = build_experiment_lock(on_cfg, on_paths)

    # An experiment that does not opt in keeps the lock it already had.
    assert "transfer_diagnostics" not in off_lock
    bound = on_lock["transfer_diagnostics"]
    assert bound["enabled"] is True
    assert bound["epsilon"] == 0.1
    assert bound["routing_policy"] == "evaluator_ability_match_v1"
    assert bound["eligible_template_count"] == 6
    # Editing an oracle artifact after the lock must invalidate it.
    assert bound["oracle_artifact_bundle_sha256"].startswith("sha256:")
    assert off_lock["digest"] != on_lock["digest"]
    # Ability identity is counted, never named: a lock may travel with a report.
    assert "ability." not in json.dumps(on_lock)


def test_same_model_transfer_diagnostics_report_the_missing_formation_cell(tmp_path):
    report = run_same_model_calibration(
        _transfer_experiment(tmp_path, transfer={"enabled": True, "instance_seeds": [101], "repetitions": 1})
    )
    summary = report["transfer_diagnostics"]
    # The Same-Model Agent exposes no Memory Adapter, so AO is not run.
    assert summary["cells"] == ["B", "OA", "OO"]
    assert summary["formation_efficiency_available"] is False
    body = summary["result"]
    assert body["diagnostic_mode"] == "behavioral"
    assert "formation_efficiency" not in body["aggregate"]
    assert [e["class"] for e in body["distance_profile"]] == ["D0", "D1", "D2", "D3"]
