"""Behavioral regressions from the review of commit 673631a."""
from __future__ import annotations

import json
import threading
from http.server import ThreadingHTTPServer

import jsonschema
import pytest

from mib_runner.agents import ReferenceMemoryAgent, StructuredMemoryAgent
from mib_runner.benchmark import run_benchmark_pack, run_materialized_pack
from mib_runner.evaluation_service import ServiceConfigError
from mib_runner.evaluator import evaluate_emission, evaluate_set_match, evaluate_structured
from mib_runner.generate import generate_instance, generate_pack
from mib_runner.hidden import HiddenEvalStore, redact_report_for_public
from mib_runner.materialize import materialize
from mib_runner.report import validate_report, verify_score
from mib_runner.runner import _emissions_of, run_scenario
from mib_runner.same_model_calibration import load_experiment_templates
from mib_runner.server import make_http_handler
from mib_runner.transports import HttpAgentAdapter
from mib_runner.types import AgentOutput
from mib_runner.validation import load_json, validate_scenario
from paths import DEV_PACK, PROFILES, REPORT_SCHEMA_PATH, SCENARIO_SCHEMA_PATH, SCHEMAS
from test_evaluation_service import make_service

SCHEMA = load_json(SCENARIO_SCHEMA_PATH)
REPORT_SCHEMA = load_json(REPORT_SCHEMA_PATH)


@pytest.mark.parametrize('seed', [2, 7, 11])
@pytest.mark.parametrize('count', [8, 14, 64])
def test_interleaved_rungs_preserve_answers_for_every_primary_actor(seed, count):
    worlds = [generate_instance('mib.interleaved_recall.v1', seed, rung=r,
                               parameters={'fact_count': count}) for r in range(3)]
    answers = lambda s: [(p['input'], p['oracle']['accepted'], p['oracle']['expected_status']) for p in s['probes']]
    assert all(answers(s) == answers(worlds[0]) for s in worlds)
    for s in worlds:
        assert validate_scenario(s, SCHEMA).valid


def test_bootstrap_replays_positive_tolerance_with_nonperfect_ablation_scores():
    template = load_json(DEV_PACK / 'time/MIB-TIME-003.json')
    instance = materialize(template, 1)
    distractor = next(e['content'] for e in instance['timeline'] if e['id'] == 'd-1')
    after_request = next(p['input']['content'] for p in instance['probes'] if p['id'] == 'p-after')

    class PartialRecall(ReferenceMemoryAgent):
        def reset(self, **kw):
            self.saw_distractor = False
            return super().reset(**kw)

        def observe(self, **kw):
            self.saw_distractor |= kw['observation'].content == distractor
            return super().observe(**kw)

        def respond(self, **kw):
            if kw['input_data'].get('content') == after_request and not self.saw_distractor:
                return AgentOutput(type='abstention')
            return super().respond(**kw)

    profile = load_json(PROFILES / 'MIB-Core-0.1-Dev-M3.json')
    profile.update(required_templates=[template['id']],
                   dimensions={d: {'weight': 1 / len(template['dimensions'])} for d in template['dimensions']})
    profile['statistics']['min_templates_per_dimension'] = 1
    report, _ = run_benchmark_pack(templates=[template], profile=profile, schema=SCHEMA,
        agent_factory=PartialRecall, instance_seeds=[1], repetitions=1, bootstrap_resamples=10)
    scores = {r['condition']: r['scenario_score'] for r in report['results']['runs']}
    assert scores['full'] == 1 and scores['irrelevant_ablation'] == 0.5
    stability = next(m['value'] for m in report['causal_metrics'] if m['name'] == 'irrelevant_memory_stability')
    assert stability == pytest.approx(1 - (0.5 - 0.05) / (1 - 0.05))
    validate_report(report, REPORT_SCHEMA)
    assert verify_score(report)['valid'], verify_score(report)['errors']
    public = redact_report_for_public(report, aliases={template['id']: 'family'}, redaction_key='test')
    assert verify_score(public)['valid']


def _trigger_result(factory, scenario=None):
    scenario = scenario or generate_instance('mib.prospective.v1', 9, rung=0)
    run = run_scenario(scenario=scenario, agent_factory=factory, include_ablations=False)[0]
    return next(p for p in run['probe_results'] if p['probe_id'] == 'p-trigger')


@pytest.mark.parametrize('http', [False, True])
@pytest.mark.parametrize('content_mode', ['absent', 'canonical', 'extra', 'text_alias'])
def test_payload_reminders_work_through_runner_and_http(http, content_mode):
    scenario = generate_instance('mib.prospective.v1', 9, rung=0)
    expected = next(p for p in scenario['probes'] if p['id'] == 'p-trigger')['oracle']['expected_emission']['expected'][0]
    # This scenario explicitly gives the Agent its commitment ID and fields.
    visible = {k: expected[k] for k in ['commitment_id', 'recipient', 'topic']}
    next(e for e in scenario['timeline'] if e['id'] == 'e-commit')['payload'] = visible

    class PayloadReminder(StructuredMemoryAgent):
        def _emissions_for(self, observation):
            if isinstance(observation.payload, dict) and 'commitment_id' in observation.payload:
                self.commitment = observation.payload
            result = []
            for row in super()._emissions_for(observation):
                reminder = {'type': 'reminder', 'payload': self.commitment}
                if content_mode != 'absent':
                    text = row['content'] + (' Also ask about every other topic.' if content_mode == 'extra' else '')
                    reminder['text' if content_mode == 'text_alias' else 'content'] = text
                result.append(reminder)
            return result

    if not http:
        assert _trigger_result(PayloadReminder, scenario)['score'] == float(content_mode != 'extra')
        return
    server = ThreadingHTTPServer(('127.0.0.1', 0), make_http_handler(PayloadReminder))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        assert _trigger_result(lambda: HttpAgentAdapter(f'http://127.0.0.1:{server.server_port}'), scenario)['score'] == float(content_mode != 'extra')
    finally:
        server.shutdown(); server.server_close(); thread.join()


@pytest.mark.parametrize('payload', ['sent', ['sent'], 7, None, {'unrelated': True}])
@pytest.mark.parametrize('correct_text', [True, False])
def test_arbitrary_payload_metadata_never_aborts_reminder_scoring(payload, correct_text):
    class TextReminder(StructuredMemoryAgent):
        def _emissions_for(self, observation):
            return [{**row, 'payload': payload, 'content': row['content'] if correct_text else ''}
                    for row in super()._emissions_for(observation)]

    probe = _trigger_result(TextReminder)
    assert probe['score'] == float(correct_text)
    assert probe['outcome'] == 'scored'


def test_legacy_emission_payload_still_matches_topic():
    log = [{'index': 1, 'emissions': _emissions_of({'emissions': [{'payload': {'topic': 'report'}}]})}]
    assert evaluate_emission(log, 1, {'expected_emission': {'topic': 'report'}}, None)['score'] == 1


@pytest.mark.parametrize('confidence', [0, 0.95, 1])
@pytest.mark.parametrize('form', ['structured', 'json', 'fields', 'answer_alias'])
def test_disclosure_ignores_envelope_keys_and_valid_metadata(confidence, form):
    value = {'value': '42', 'status': 'known', 'confidence': confidence}
    output = AgentOutput(type='structured', value=value)
    if form == 'json':
        output = AgentOutput(type='message', content=json.dumps(value))
    elif form == 'fields':
        output = AgentOutput(type='message', content='\n'.join(f'{k}: {v}' for k, v in value.items()))
    elif form == 'answer_alias':
        value['answer'] = value.pop('value')
    oracle = {'accepted': ['42'], 'expected_status': 'known', 'forbidden': ['value', 'content', 'null', 'known', '0', '1']}
    for evaluator in [evaluate_structured, evaluate_set_match]:
        assert evaluator(output, oracle, None)['score'] == 1


def test_disclosure_does_not_treat_nested_container_keys_as_values():
    oracle = {'accepted': ['42'], 'expected_status': 'known', 'forbidden': ['value', 'content']}
    output = AgentOutput(type='structured', value={'value': {'content': '42'}, 'status': 'known'})
    result = evaluate_structured(output, oracle, None)
    assert result['score'] == 0  # A container is not the scalar answer 42.
    assert result['details']['forbidden_match'] is False  # Keys are still not disclosures.
    for output in [AgentOutput(type='structured', value={'content': '42'}),
                   AgentOutput(type='message', content='{"content":"42"}')]:
        assert evaluate_set_match(output, oracle, None)['score'] == 1


@pytest.mark.parametrize('extra', [
    {'explanation': {'confidence': 'SECRET-91'}},
    {'confidence': 'SECRET-91'},
    {'status': 'SECRET-91'},
    {'explanation': ['SECRET-91']},
    {'explanation': 0},
    {'explanation': 'value'},
])
def test_disclosure_still_checks_real_auxiliary_values_and_invalid_metadata(extra):
    output = AgentOutput(type='structured', value={'value': '42', 'status': 'known', **extra})
    oracle = {'accepted': ['42'], 'expected_status': 'known', 'forbidden': ['SECRET-91', 'value', '0']}
    for evaluator in [evaluate_structured, evaluate_set_match]:
        assert evaluator(output, oracle, None)['score'] == 0


def test_abstention_null_placeholders_are_not_disclosures_but_attribution_is():
    oracle = {'accepted': ['unknown'], 'expected_status': 'unknown', 'forbidden': ['null', 'value', '0']}
    for evaluator in [evaluate_structured, evaluate_set_match]:
        assert evaluator(AgentOutput(type='abstention'), oracle, None)['score'] == 1
        output = AgentOutput(type='abstention', attribution={'source': '0'})
        assert evaluator(output, oracle, None)['score'] == 0


def _generated_store(tmp_path, *, profile_ladder=None, store_ladder=None):
    profile = load_json(PROFILES / 'MIB-Core-0.2-Dev.json')
    entry = {'id': 'mib.recall.v1'}
    profile.update(programs=[entry], dimensions={'retention_retrieval': {'weight': 1}})
    if profile_ladder is not None:
        entry['ladder'] = profile_ladder
    manifest_entry = {'id': entry['id'], 'public_id': 'public-recall', 'instances': 1}
    if store_ladder is not None:
        manifest_entry['ladder'] = store_ladder
    manifest = {'mib': '0.2', 'kind': 'MIBPrivateEvaluationStore', 'id': 'generated-test', 'version': '0.3.0',
                'profile': profile['id'], 'ladder': profile['ladder'], 'programs': [manifest_entry]}
    (tmp_path / 'manifest.private.json').write_text(json.dumps(manifest))
    path = tmp_path / 'profile.json'
    path.write_text(json.dumps(profile))
    return HiddenEvalStore(tmp_path), profile, path


@pytest.mark.parametrize('ladder', [[0, 3, 9], [0, 3, 9, 15]])
def test_program_ladder_override_is_shared_by_all_materialization_paths(tmp_path, ladder):
    store, profile, path = _generated_store(tmp_path, profile_ladder=ladder, store_ladder=ladder)
    jsonschema.validate(store.manifest, load_json(SCHEMAS / 'mib-private-eval-store.schema.json'))
    make_service(tmp_path).register_cycle('matching', store_path=tmp_path, profile_path=path)
    templates, instances, _ = store.materialize_instances(schema=SCHEMA, evaluation_key='test', cycle_id='matching')
    _, public = generate_pack(profile, seeds=[0])
    calibration = [materialize(t, 0) for t in load_experiment_templates({'profile': path})]
    regenerated = [materialize(templates[0], 0)]
    for worlds in [instances, public, calibration, regenerated]:
        assert [s['instantiation']['interference_count'] for s in worlds] == ladder[:len(worlds)]
    assert len(instances) == len(calibration) == len(public) == len(ladder)
    report, _ = run_materialized_pack(templates=templates, instances=instances, schema=SCHEMA,
        profile=profile, agent_factory=StructuredMemoryAgent, repetitions=1, bootstrap_resamples=5)
    assert verify_score(report)['valid']


def test_cycle_registration_rejects_different_effective_program_ladders(tmp_path):
    _, _, path = _generated_store(tmp_path, profile_ladder=[0, 200, 1000])
    with pytest.raises(ServiceConfigError, match='ladder'):
        make_service(tmp_path).register_cycle('mismatch', store_path=tmp_path, profile_path=path)


def test_direct_hidden_execution_rejects_wrong_ladder_before_agent_runs(tmp_path):
    store, profile, _ = _generated_store(tmp_path, profile_ladder=[0, 200, 1000])
    templates, instances, _ = store.materialize_instances(schema=SCHEMA, evaluation_key='test', cycle_id='mismatch')
    def unexpected_agent():
        pytest.fail('mismatched materialized instances reached the Agent')
    with pytest.raises(ValueError, match='ladder'):
        run_materialized_pack(templates=templates, instances=instances, schema=SCHEMA,
            profile=profile, agent_factory=unexpected_agent, repetitions=1)


@pytest.mark.parametrize('change', ['missing', 'duplicate', 'count'])
def test_hidden_ladder_validation_rejects_incomplete_or_altered_instances(tmp_path, change):
    store, profile, _ = _generated_store(tmp_path, profile_ladder=[0, 3, 9, 15], store_ladder=[0, 3, 9, 15])
    templates, instances, _ = store.materialize_instances(schema=SCHEMA, evaluation_key='test', cycle_id='complete')
    if change == 'missing':
        instances.pop()
    elif change == 'duplicate':
        instances.append(instances[0])
    else:
        instances[1]['instantiation']['interference_count'] = 20
    with pytest.raises(ValueError, match='rung|duplicate|ladder'):
        run_materialized_pack(templates=templates, instances=instances, schema=SCHEMA,
            profile=profile, agent_factory=StructuredMemoryAgent, repetitions=1)


def test_string_program_entries_resolve_the_default_ladder(tmp_path):
    store, profile, path = _generated_store(tmp_path)
    profile['programs'] = ['mib.recall.v1']
    path.write_text(json.dumps(profile))
    make_service(tmp_path).register_cycle('default', store_path=tmp_path, profile_path=path)
    _, instances, _ = store.materialize_instances(schema=SCHEMA, evaluation_key='test', cycle_id='default')
    assert [s['instantiation']['interference_count'] for s in instances] == profile['ladder']
