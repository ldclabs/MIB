from __future__ import annotations

import copy
import json
import threading
from http.server import ThreadingHTTPServer

from mib_runner.agents import ReferenceMemoryAgent
from mib_runner.benchmark import run_materialized_pack, validate_causal_pairs
from mib_runner.hidden import HiddenEvalStore, redact_report_for_public
from mib_runner.report import validate_report, verify_score
from mib_runner.runner import run_scenario
from mib_runner.server import make_http_handler
from mib_runner.submission import build_submission_runtime, load_submission_spec
from mib_runner.transports import HttpAgentAdapter
from mib_runner.sandbox import SandboxPolicy, spawn_sandboxed_stdio

import pytest

from paths import (
    SANDBOX_AVAILABLE,
    SANDBOX_REASON,
    EXAMPLES,
    PRIVATE_EVAL_STORE_DEMO,
    PROFILES,
    REPORT_SCHEMA_PATH,
    SCENARIO_SCHEMA_PATH,
)

SCHEMA = json.loads(SCENARIO_SCHEMA_PATH.read_text())
REPORT_SCHEMA = json.loads(REPORT_SCHEMA_PATH.read_text())
STORE = PRIVATE_EVAL_STORE_DEMO
PROFILE = json.loads((PROFILES / "MIB-Core-0.1-Hidden-M4-Demo.json").read_text())
STDIO_SPEC = EXAMPLES / "submissions" / "reference-stdio.json"


def test_hidden_store_hmac_materialization_is_deterministic_and_cycle_scoped():
    store = HiddenEvalStore(STORE)
    t1, i1, a1 = store.materialize_instances(schema=SCHEMA, evaluation_key="secret-A", cycle_id="cycle-1")
    t2, i2, a2 = store.materialize_instances(schema=SCHEMA, evaluation_key="secret-A", cycle_id="cycle-1")
    _, i3, _ = store.materialize_instances(schema=SCHEMA, evaluation_key="secret-A", cycle_id="cycle-2")
    assert [x["instantiation"]["seed"] for x in i1] == [x["instantiation"]["seed"] for x in i2]
    assert [x["instantiation"]["seed"] for x in i1] != [x["instantiation"]["seed"] for x in i3]
    assert all(str(x["instantiation"]["seed"]).startswith("hs_") for x in i1)
    assert a1 == a2
    assert len(t1) == 6 and len(i1) == 12


def test_public_manifest_does_not_disclose_holdout_composition_or_paths():
    manifest = HiddenEvalStore(STORE).public_manifest()
    blob = json.dumps(manifest)
    assert "templates/holdout" not in blob
    assert "MIB-SKILL-901" not in blob
    assert "MIB-CAUSAL-901" not in blob
    assert manifest["private_holdout"]["count"] == 2
    # suite_counts intentionally describe only the disclosed Hidden Eval families.
    assert "skill" not in manifest["suite_counts"]
    assert "causal" not in manifest["suite_counts"]


def test_hidden_late_probe_variant_is_identical_across_causal_pair():
    store = HiddenEvalStore(STORE)
    templates, instances, _ = store.materialize_instances(schema=SCHEMA, evaluation_key="late-key", cycle_id="late-cycle")
    scenario = next(x for x in instances if x["id"] == "MIB-RET-901")
    runs = run_scenario(scenario=scenario, agent_factory=ReferenceMemoryAgent, include_ablations=True, repetition=0, agent_seed="opaque:0")
    valid, _, notes = validate_causal_pairs(runs)
    assert valid, notes
    full = next(r for r in runs if r["condition"] == "full")
    rel = next(r for r in runs if r["condition"] == "relevant_ablation")
    fd = full["extensions"]["mib.runner.probe_variant_digests"]["p-recall"]
    rd = rel["extensions"]["mib.runner.probe_variant_digests"]["p-recall"]
    assert fd == rd
    assert full["scenario_score"] == 1.0
    assert rel["scenario_score"] < full["scenario_score"]


@pytest.mark.skipif(not SANDBOX_AVAILABLE, reason=SANDBOX_REASON)
def test_stdio_external_agent_smoke_and_sandbox_descriptor():
    spec = load_submission_spec(STDIO_SPEC)
    runtime = build_submission_runtime(spec)
    agent = runtime.factory()
    try:
        desc = agent.describe()
        assert desc["protocol"] == "mib-agent/0.1"
        assert desc["extensions"]["mib.sandbox"]["transport"] == "stdio"
        agent.reset(run_id="r1", seed="s", virtual_time=None)
        from mib_runner.types import Observation
        agent.observe(run_id="r1", request_id="q1", observation=Observation(
            observation_id="o1", type="user_message", content="The access code for my private demo project is ORCHID-91."
        ))
        out = agent.respond(run_id="r1", request_id="q2", interaction_id="i", input_data={
            "content": "What is the access code for my private demo project? Answer with the code only."
        }, virtual_time=None)
        assert out.content == "ORCHID-91"
    finally:
        agent.close(run_id="r1")


def test_http_external_agent_profile():
    server = ThreadingHTTPServer(("127.0.0.1", 0), make_http_handler(ReferenceMemoryAgent))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        adapter = HttpAgentAdapter(f"http://127.0.0.1:{server.server_port}")
        assert adapter.describe()["protocol"] == "mib-agent/0.1"
        adapter.reset(run_id="http-r", seed=1, virtual_time=None)
        from mib_runner.types import Observation
        adapter.observe(run_id="http-r", request_id="o", observation=Observation(
            observation_id="obs", type="user_message", content="The access code for my private demo project is EMBER-47."
        ))
        out = adapter.respond(run_id="http-r", request_id="q", interaction_id="i", input_data={
            "content": "What is the access code for my private demo project? Answer with the code only."
        }, virtual_time=None)
        assert out.content == "EMBER-47"
        adapter.close(run_id="http-r")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)



@pytest.mark.skipif(not SANDBOX_AVAILABLE, reason=SANDBOX_REASON)
def test_namespace_sandbox_hides_evaluator_storage_when_supported():
    policy = SandboxPolicy(network="disabled_strict", hide_paths=["/mnt/data"], memory_mb=512, cpu_seconds=10)
    box = spawn_sandboxed_stdio(["python", "-c", "import os; print('visible' if os.path.exists('/mnt/data/MIB-Reference-Runner-M4/private-eval-store-demo') else 'hidden', flush=True)"], policy=policy)
    try:
        assert box.network_isolated is True
        assert box.filesystem_isolated is True
        assert box.process.stdout.readline().strip() == "hidden"
    finally:
        box.terminate()

def test_hidden_pack_report_can_be_redacted_and_still_verify():
    store = HiddenEvalStore(STORE)
    templates, instances, aliases = store.materialize_instances(schema=SCHEMA, evaluation_key="report-key", cycle_id="report-cycle")
    report, summary = run_materialized_pack(
        templates=templates,
        instances=instances,
        schema=SCHEMA,
        profile=PROFILE,
        agent_factory=ReferenceMemoryAgent,
        repetitions=1,
        include_ablations=True,
        bootstrap_resamples=20,
        bootstrap_seed=99,
    )
    assert summary["mib_score"] == 100.0
    assert report["aggregates"]["mib_score"]["official"] is True
    public = redact_report_for_public(report, aliases=aliases, redaction_key="report-key")
    validate_report(public, REPORT_SCHEMA)
    checked = verify_score(public)
    assert checked["valid"], checked
    assert public["results"]["runs"] == []
    blob = json.dumps(public)
    for private_id in aliases:
        assert private_id not in blob
    assert "instance_seed" not in blob
    assert "agent_seed" not in blob
    assert public["scope"] == "public"
