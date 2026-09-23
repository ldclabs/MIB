"""Adversarial and independent checks for the September design review."""
from __future__ import annotations

import copy
import json
import random
import re
import threading
from http.server import ThreadingHTTPServer

import pytest

from mib_runner.agents import NoMemoryAgent, StructuredMemoryAgent
from mib_runner.benchmark import build_pack_report, run_generated_pack, run_materialized_pack
from mib_runner.evaluator import evaluate_structured, evaluate_set_match
from mib_runner.generate import PROGRAMS, generate_instance, generate_pack
from mib_runner.generate.interference import plan
from mib_runner.generate.pools import ATTRIBUTES, TOPICS
from mib_runner.hidden import HiddenEvalStore, redact_report_for_public
from mib_runner.leaderboard import paired_compare_reports
from mib_runner.model_clients import ModelCompletion
from mib_runner.report import validate_report, verify_score
from mib_runner.runner import run_scenario
from mib_runner.same_model_agent import InvocationRecorder, SameModelAgent
from mib_runner.scoring import full_run_metrics
from mib_runner.scoring import paired_causal_metrics
from mib_runner.server import make_http_handler
from mib_runner.transports import HttpAgentAdapter
from mib_runner.types import AgentOutput
from mib_runner.validation import load_json, validate_scenario
from mib_runner.worldmodel import Assertion, Source, WorldModel
from paths import PROFILES, REPORT_SCHEMA_PATH, SCENARIO_SCHEMA_PATH

PROFILE = load_json(PROFILES / 'MIB-Core-0.2-Dev.json')
SCHEMA = load_json(SCENARIO_SCHEMA_PATH)


@pytest.mark.parametrize('out', [
    AgentOutput(type='structured', value={'value': 'SECRET-91', 'status': 'unknown', 'confidence': 1}),
    AgentOutput(type='abstention', content='I cannot disclose SECRET-91.'),
    AgentOutput(type='structured', value={'value': 'unknown', 'status': 'unknown', 'explanation': 'SECRET-91'}),
    AgentOutput(type='message', content='value: unknown\nstatus: unknown\nexplanation: SECRET-91'),
])
def test_withdrawn_disclosure_cannot_hide_in_an_abstention(out):
    oracle = {'accepted': ['unknown'], 'expected_status': 'unknown', 'forbidden': ['SECRET-91']}
    for evaluator in [evaluate_structured, evaluate_set_match]:
        assert evaluator(out, oracle, None)['score'] == 0


def test_missing_required_fields_do_not_change_the_denominator():
    oracle = {'accepted': ['contested'], 'expected_status': 'contested'}
    missing = AgentOutput(type='structured', value={'value': 'contested'})
    wrong = AgentOutput(type='structured', value={'value': 'contested', 'status': 'known'})
    assert evaluate_structured(missing, oracle, None)['score'] == evaluate_structured(wrong, oracle, None)['score'] == 0.8
    correct = AgentOutput(type='structured', value={'value': 'contested', 'status': 'contested'})
    assert evaluate_structured(correct, oracle, {'weights': {'value': 0.6, 'status': 0.2, 'confidence': 0.2}})['score'] == 0.8


def test_noise_is_independent_of_excluded_answer_values():
    kwargs = dict(count=1000, subject_id='alice', subject_name='Alice', spec=ATTRIBUTES['office'], other_actors=[('bob', 'Bob')])
    a = plan(random.Random(7), exclude_values={'Harbor Loft'}, **kwargs)
    b = plan(random.Random(7), exclude_values=set(ATTRIBUTES['office'].values), **kwargs)
    assert a == b
    seen = {x.assertion['value'] for x in a if x.assertion}
    assert seen == set(ATTRIBUTES['office'].values), 'pool-complement guessing must expose no unique missing answer'


def test_information_load_profile_has_real_useful_facts_and_valid_identities():
    s = generate_instance('mib.interleaved_recall.v1', 7, rung=1, parameters={'fact_count': 64})
    assert validate_scenario(s, SCHEMA).valid
    assert sum(e['id'].startswith('fact-') for e in s['timeline']) == 64
    assert len(s['probes']) == 8
    assert run_scenario(scenario=s, agent_factory=StructuredMemoryAgent, include_ablations=False)[0]['scenario_score'] == 1


@pytest.mark.parametrize('pid', sorted(PROGRAMS))
def test_rungs_preserve_the_full_future_request(pid):
    worlds = [generate_instance(pid, 7, rung=r) for r in range(3)]
    assert all(validate_scenario(s, SCHEMA).valid for s in worlds)
    assert all([p['input'] for p in s['probes']] == [p['input'] for p in worlds[0]['probes']] for s in worlds)
    answers = lambda s: [(p['oracle'].get('accepted'), p['oracle'].get('expected_status')) for p in s['probes']]
    assert all(answers(s) == answers(worlds[0]) for s in worlds)
    assert all(s['instantiation']['distance_hours'] == worlds[0]['instantiation']['distance_hours'] for s in worlds)


def test_semantic_identifiers_are_not_delivered_and_renaming_is_invariant():
    seen = []
    class Capturing(StructuredMemoryAgent):
        def observe(self, **kw):
            seen.append(kw['observation'].observation_id)
            return super().observe(**kw)
        def respond(self, **kw):
            seen.append(kw['interaction_id'])
            return super().respond(**kw)
    s = generate_instance('mib.prospective.v1', 9, rung=1)
    before = run_scenario(scenario=s, agent_factory=Capturing, include_ablations=False)[0]
    assert all(re.fullmatch(r'(obs|interaction)_[0-9a-f]{24}', x) or x.startswith('obs_tool_') for x in seen)
    assert not any('trigger' in x or 'near' in x or 'commit' in x for x in seen)
    ids = [x['id'] for group in ['timeline', 'probes', 'ablations'] for x in s[group]]
    replacements = {old: f'x-{i}' for i, old in enumerate(ids)}
    def renamed(x):
        if isinstance(x, dict): return {replacements.get(k, k): renamed(v) for k, v in x.items()}
        if isinstance(x, list): return [renamed(v) for v in x]
        return replacements.get(x, x) if isinstance(x, str) else x
    after = run_scenario(scenario=renamed(s), agent_factory=StructuredMemoryAgent, include_ablations=False)[0]
    assert before['scenario_score'] == after['scenario_score'] == 1


def test_topic_spraying_and_early_reminders_fail_the_lifecycle():
    class Spray(StructuredMemoryAgent):
        def observe(self, **kw):
            response = super().observe(**kw)
            response['emissions'].append({'content': ' '.join(TOPICS)})
            return response
    s = generate_instance('mib.prospective.v1', 9, rung=1)
    full = run_scenario(scenario=s, agent_factory=Spray, include_ablations=False)[0]
    probe = next(p for p in full['probe_results'] if p['probe_id'] == 'p-trigger')
    assert probe['score'] == 0
    assert probe['evaluator_results'][0]['details']['false_alarms'] > 20


def test_world_model_matches_independent_bitemporal_truth_table():
    m = WorldModel(); m.add_source(Source('p'))
    m.add(Assertion('a', 10, 'p', 'p', 'code', 'A', valid_from=1))
    m.add(Assertion('b', 20, 'p', 'p', 'code', 'B', 'correction', True, 'a'))
    m.add(Assertion('c', 30, 'p', 'p', 'code', 'C', 'correction', True, 'b'))
    for recorded, expected in [(9, None), (15, 'A'), (25, 'B'), (35, 'C')]:
        assert m.evaluate({'op': 'bitemporal', 'subject': 'p', 'attribute': 'code', 'valid_at': 5, 'recorded_at': recorded}).value == expected
    assert m.current('p', 'code')[0] == 'C'
    assert m.first_stated('p', 'code') == 'A'


def test_withdrawal_removes_dependent_corrections_and_allows_fresh_authorization():
    m = WorldModel(); m.add_source(Source('p'))
    m.add(Assertion('a', 1, 'p', 'p', 'code', 'A'))
    m.add(Assertion('b', 2, 'p', 'p', 'code', 'B', 'correction', True, 'a'))
    m.add(Assertion('summary', 3, 'p', 'p', 'summary', 'B', derived_from=('b',)))
    m.add(Assertion('forget', 4, 'p', 'p', 'code', None, 'retraction', False, 'b'))
    assert m.current('p', 'code')[0] is None
    assert m.current('p', 'summary')[0] is None
    m.add(Assertion('fresh', 5, 'p', 'p', 'code', 'C'))
    assert m.current('p', 'code')[0] == 'C'


class FeedbackModel:
    """A deterministic stateless model that follows explicit workflow feedback."""
    def __init__(self): self.calls = []
    def identity(self): return {'client': 'test', 'model_id': 'feedback-model'}
    def close(self): pass
    def complete(self, *, messages, parameters, request_id):
        text = messages[-1]['content']; self.calls.append(text)
        if 'MODE: OBSERVE' in text: return ModelCompletion('{"emissions":[]}')
        if 'MODE: MAINTENANCE' in text: return ModelCompletion('{"memory_summary":""}')
        transient = text.split('CURRENT_TASK_TRANSIENT_STATE:\n')[1].split('\n\nREQUEST:')[0]
        if re.search(r'"success"\s*:\s*true', transient):
            return ModelCompletion('{"type":"final","content":"done"}')
        found = re.findall(r'"required_recipe":\s*(\[[^\]]*\])', text)
        recipe = json.loads(found[-1]) if found else []
        return ModelCompletion(json.dumps({'type': 'tool_call', 'tool': 'workflow.submit', 'arguments': {'recipe': recipe}}))


def test_lived_feedback_survives_task_completion_only_with_memory():
    s = generate_instance('mib.experience.v1', 101, rung=1)
    scores = {}
    for condition in ['B0', 'B1']:
        model = FeedbackModel()
        factory = lambda: SameModelAgent(condition=condition, model_client=model, system_prompt='fixed', reasoning_policy='fixed',
                      model_parameters={}, recorder=InvocationRecorder(), memory_config={'parse_retries': 0})
        r = run_scenario(scenario=s, agent_factory=factory, include_ablations=False)[0]
        scores[condition] = r['scenario_score']
    # B0 recovers from the feedback inside the task, which is conjunctively scored as nothing (measurement 0.5.0).
    assert scores == {'B0': 0.0, 'B1': 1.0}


def test_a_memoryless_guess_is_not_labelled_negative_transfer():
    s = generate_instance('mib.skill.v1', 101, rung=1)
    runs = run_scenario(scenario=s, agent_factory=NoMemoryAgent)
    metrics = {m['name']: m['value'] for m in paired_causal_metrics(runs)}
    assert metrics['negative_transfer'] == metrics['negative_transfer_rate'] == 0


def test_wire_id_randomization_does_not_change_fixed_model_inputs_or_seeds():
    from mib_runner.types import Observation
    class Model:
        def __init__(self): self.calls = []
        def identity(self): return {'client': 'test', 'model_id': 'fixed'}
        def complete(self, **kw):
            self.calls.append((kw['messages'], kw['parameters']))
            return ModelCompletion('{"emissions":[]}')
    calls = []
    for oid in ['opaque-first', 'opaque-second']:
        model = Model()
        agent = SameModelAgent(condition='B1', model_client=model, system_prompt='fixed', reasoning_policy='fixed', model_parameters={},
                                recorder=InvocationRecorder(), memory_config={'observe_decisions': True}, seed_policy='paired_per_call')
        agent.reset(run_id=oid, seed='paired', virtual_time=None)
        agent.observe(run_id=oid, request_id=oid, observation=Observation(observation_id=oid, type='user_message', content='A note.'))
        calls.append(model.calls)
    assert calls[0] == calls[1]


def test_http_maintenance_and_session_boundary_reach_the_agent():
    calls = []
    class Lifecycle(StructuredMemoryAgent):
        def maintain(self, **kw): calls.append('maintain'); return {'accepted': True}
        def session_boundary(self, **kw): calls.append('session'); return {'accepted': True}
    server = ThreadingHTTPServer(('127.0.0.1', 0), make_http_handler(Lifecycle))
    thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
    try:
        adapter = HttpAgentAdapter(f'http://127.0.0.1:{server.server_port}')
        adapter.reset(run_id='r', seed=1, virtual_time=None)
        assert adapter.maintain(run_id='r', request_id='m')['accepted']
        assert adapter.session_boundary(run_id='r', request_id='s')['accepted']
        assert calls == ['maintain', 'session']
        adapter.close(run_id='r')
    finally:
        server.shutdown(); server.server_close(); thread.join()


@pytest.fixture(scope='module')
def revised_report():
    return run_generated_pack(profile=PROFILE, schema=SCHEMA, agent_factory=StructuredMemoryAgent, seeds=[101], bootstrap_resamples=10)[0]


@pytest.mark.parametrize('field', ['gate', 'official', 'ctr', 'retention', 'interval', 'coverage'])
def test_verification_rejects_interpretation_and_statistics_tampering(revised_report, field):
    r = copy.deepcopy(revised_report)
    if field == 'gate': r['memory_dependence']['eligible'] = True
    elif field == 'official': r['aggregates']['mib_score']['official'] = True
    elif field == 'ctr': next(x for x in r['causal_metrics'] if x['name'] == 'content_tracking_rate')['value'] = 0.25
    elif field == 'retention': r['retention'][0]['rungs'][0]['full_score'] = 0.25
    elif field == 'interval': r['statistics']['mib_score']['value'] = 99
    elif field == 'coverage': r['coverage']['overall'] = 0.5
    assert verify_score(revised_report)['valid']
    assert not verify_score(r)['valid']


def test_unassessable_tracking_retains_zero_eligible_count():
    class NoCorrectAnswers(NoMemoryAgent):
        def respond(self, **kw):
            return AgentOutput(type='structured', value={'value': 'UNSUPPORTED-VALUE-XYZZY', 'status': 'known'})
    report, _ = run_generated_pack(profile=PROFILE, agent_factory=NoCorrectAnswers, seeds=[101])
    # Joint evidence keeps valid wrong answers in the fixed denominator.
    assert report['memory_dependence']['eligible_n'] > 0
    assert report['memory_dependence']['total_n'] > 0
    assert report['memory_dependence']['eligible'] is False
    assert report['memory_dependence']['content_tracking_rate'] is None


def test_paired_interval_uses_only_the_canonical_rung(revised_report):
    descriptors, instances = generate_pack(PROFILE, seeds=[101])
    def artificial(canonical):
        runs = copy.deepcopy([r for r in revised_report['results']['runs'] if r['condition'] == 'full'])
        for run in runs:
            value = float(run['scenario_instance_id'].endswith(':r1') == canonical)
            run['scenario_score'] = value
            for p in run['probe_results']: p['score'] = value
        return build_pack_report(templates=descriptors, instances=instances, all_runs=runs, profile=PROFILE, agent_descriptor=NoMemoryAgent().describe())
    a, b = artificial(True), artificial(False)
    assert verify_score(a)['valid'] and verify_score(b)['valid']
    result = paired_compare_reports(a, b, resamples=20)
    assert result['mib_score_delta_a_minus_b'] == result['paired_ci']['lower'] == result['paired_ci']['upper'] == 100
    b['benchmark']['track'] = 'memory_system'
    with pytest.raises(ValueError, match='track'): paired_compare_reports(a, b, resamples=20)


def test_generated_hidden_pack_redacts_seeds_and_remains_verifiable(tmp_path):
    manifest = {'mib': '0.2', 'kind': 'MIBPrivateEvaluationStore', 'id': 'demo-generated', 'version': '0.3.0',
                'profile': 'test', 'programs': [{'id': 'mib.recall.v1', 'public_id': 'public-family', 'instances': 1}], 'ladder': [0, 20, 100]}
    (tmp_path / 'manifest.private.json').write_text(json.dumps(manifest))
    store = HiddenEvalStore(tmp_path)
    templates, instances, aliases = store.materialize_instances(schema=SCHEMA, evaluation_key='test-key', cycle_id='test-cycle')
    assert len(instances) == 3 and len({s['instantiation']['seed'] for s in instances}) == 1
    assert all(s['instantiation']['seed'].startswith('hs_') for s in instances)
    profile = copy.deepcopy(PROFILE); profile['programs'] = [{'id': 'mib.recall.v1'}]
    profile['dimensions'] = {'retention_retrieval': {'weight': 1}}
    r, _ = run_materialized_pack(templates=templates, instances=instances, schema=SCHEMA, profile=profile, agent_factory=StructuredMemoryAgent, repetitions=1)
    pub = redact_report_for_public(r, aliases=aliases, redaction_key='redaction-key')
    validate_report(pub, load_json(REPORT_SCHEMA_PATH))
    assert verify_score(pub)['valid']
    assert 'hs_' not in json.dumps(pub)
