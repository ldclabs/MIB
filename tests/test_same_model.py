from __future__ import annotations

import json
from pathlib import Path

import jsonschema

from mib_runner.model_clients import ModelCompletion
from mib_runner.same_model_agent import (
    InvocationRecorder,
    LexicalRetrievalPolicy,
    SameModelAgent,
    StructuredMemoryPolicy,
)
from mib_runner.same_model_calibration import build_experiment_lock, load_experiment, _condition_schedule, _schedule_audit
from mib_runner.types import Observation


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
    root = Path(__file__).resolve().parents[1]
    cfg_path = root / "examples" / "same-model" / "same-model-experiment.stub.json"
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
        str(root / "examples" / "same-model" / "same-model-experiment.stub.json"),
        "--estimate-only",
        "--output-json", str(output),
        "--experiment-schema", str(root / "schemas" / "mib-same-model-experiment.schema.json"),
    ])
    assert rc == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["estimate"]["template_count"] == 36
    assert payload["experiment_lock"].startswith("sha256:")
