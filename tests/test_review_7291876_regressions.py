"""Failure-path regressions from the review of measurement-0.5 commit 7291876."""
from __future__ import annotations

import copy
import io
import json
import threading
from http.server import ThreadingHTTPServer
from unittest.mock import patch

import jsonschema
import pytest

from mib_runner import same_model_calibration as calibration
from mib_runner.adapter_contract import verify_run_contract
from mib_runner.agents import StructuredMemoryAgent
from mib_runner.benchmark import run_generated_pack
from mib_runner.dependence import CFE_METRIC, joint_dependence
from mib_runner.generate import generate_instance
from mib_runner.model_clients import ModelCompletion
from mib_runner.protocol import AgentHost
from mib_runner.report import build_basic_report, validate_report, verify_score
from mib_runner.runner import run_condition
from mib_runner.same_model_agent import SameModelAgent
from mib_runner.server import make_http_handler, serve_stdio
from mib_runner.transports import HttpAgentAdapter
from paths import EXAMPLES, PROFILES, REPORT_SCHEMA_PATH, SCHEMAS


def recall_profile():
    profile = json.loads((PROFILES / 'MIB-Core-0.2-Dev.json').read_text())
    profile.update(programs=[{'id': 'mib.recall.v1'}], ladder=[0], canonical_rung=0,
                   dimensions={'retention_retrieval': {'weight': 1}})
    profile['memory_dependence']['bootstrap_resamples'] = 30
    profile['measurement_regime']['diagnostics'] = 'off'
    return profile


class FailedSeedAgent(StructuredMemoryAgent):
    def reset(self, **kwargs):
        self.fail_formation = str(kwargs['seed']).startswith('606:')
        return super().reset(**kwargs)

    def observe(self, **kwargs):
        if self.fail_formation:
            return {'accepted': False}
        return super().observe(**kwargs)


@pytest.mark.parametrize('repetitions', [1, 3])
def test_failed_full_instance_stays_in_cfe_denominator(repetitions):
    report, _ = run_generated_pack(profile=recall_profile(), agent_factory=FailedSeedAgent,
                                  seeds=[101, 202, 303, 404, 505, 606], repetitions=repetitions)
    gate = report['memory_dependence']
    dimension = gate['dimensions'][0]
    # Recall has two frozen twin opportunities per independent seed.
    assert gate['total_n'] == 12 * repetitions
    assert gate['eligible_n'] == 10 * repetitions
    assert dimension['coverage'] == pytest.approx(5 / 6)
    assert dimension['independent_instances'] == 6 and dimension['eligible_instances'] == 5
    assert gate[CFE_METRIC] == pytest.approx(5 / 6)
    assert gate['eligible'] is False
    validate_report(report, json.loads(REPORT_SCHEMA_PATH.read_text()))
    assert verify_score(report)['valid']
    altered = copy.deepcopy(report)
    altered['memory_dependence']['total_n'] = 10 * repetitions
    altered['memory_dependence']['eligible'] = True
    assert not verify_score(altered)['valid']


def test_missing_cfe_evidence_remains_unassessable_with_its_planned_count():
    row = {'template_id': 'T', 'joint_dependence_evidence': [
        {'dimension': 'retention_retrieval', 'total_n': 2, 'valid_n': 0,
         'successes': 0, 'joint_score': 0.0}]}
    gate = joint_dependence([row], recall_profile(), field=CFE_METRIC, metric=CFE_METRIC)
    assert gate['total_n'] == 2 and gate['eligible_n'] == 0
    assert gate['eligible'] is None and gate[CFE_METRIC] is None


@pytest.mark.parametrize('late_boundary', [False, True])
def test_invalid_persisted_state_invalidates_all_scheduled_probes(late_boundary):
    class BadStateAgent(StructuredMemoryAgent):
        def session_boundary(self, **kwargs):
            return {'accepted': True, 'persisted_state': {}}

    scenario = generate_instance('mib.recall.v1', 101, session_boundary=True)
    if late_boundary:
        boundary = next(e for e in scenario['timeline'] if e['type'] == 'session_boundary')
        scenario['timeline'].remove(boundary)
        boundary['at'] = {**scenario['timeline'][-1]['at'],
                          'sequence': scenario['timeline'][-1]['at']['sequence'] + 1}
        scenario['timeline'].append(boundary)
    agent = BadStateAgent()
    run = run_condition(scenario=scenario, agent=agent, agent_factory=BadStateAgent,
                        session_isolation='persisted_state')
    assert run['status'] == 'invalid' and run['validity']['runner_valid'] is False
    assert len(run['probe_results']) == len(scenario['probes'])
    assert all(p['outcome'] == 'execution_failure' and p['score'] == 0 for p in run['probe_results'])
    receipts = [r for r in run['adapter_contract']['operations'] if r['operation'] == 'session_boundary']
    assert len(receipts) == 1 and receipts[0]['outcome'] == 'failure'
    if late_boundary:
        assert all(p['score'] == 1 for p in run['adapter_contract']['pre_invalidation_probe_results'])
    assert verify_run_contract(run) == []
    report = build_basic_report(runs=[run], scenario=scenario, agent_descriptor=agent.describe())
    validate_report(report, json.loads(REPORT_SCHEMA_PATH.read_text()))
    assert verify_score(report)['valid']


def test_http_session_rebuild_restores_memory_through_the_host():
    restored = []

    class RestoredAgent(StructuredMemoryAgent):
        def restore(self, **kwargs):
            restored.append(kwargs['state'])
            return super().restore(**kwargs)

    server = ThreadingHTTPServer(('127.0.0.1', 0), make_http_handler(RestoredAgent))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        def factory():
            return HttpAgentAdapter(f'http://127.0.0.1:{server.server_port}')
        scenario = generate_instance('mib.recall.v1', 101, session_boundary=True)
        run = run_condition(scenario=scenario, agent=factory(), agent_factory=factory,
                            session_isolation='persisted_state')
        assert run['status'] == 'succeeded' and run['scenario_score'] == 1
        assert restored and json.loads(restored[0])['observations']
        assert any(r['operation'] == 'restore' and r['outcome'] == 'success'
                   for r in run['adapter_contract']['operations'])
        assert verify_run_contract(run) == []
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


def request(operation, body=None):
    return {'mib': '0.1', 'protocol': 'mib-agent/0.1', 'run_id': 'r', 'request_id': operation,
            'operation': operation, 'virtual_time': '2026-01-01T09:00:00Z', 'body': body or {}}


def test_stdio_restore_dispatch_preserves_state_and_request_context(monkeypatch):
    calls = []

    class RestoreRecorder(StructuredMemoryAgent):
        def restore(self, **kwargs):
            calls.append(kwargs)
            return {'accepted': True}

    messages = [request('reset', {'seed': 101}), request('restore', {'state': '保留\nstate'})]
    output = io.StringIO()
    monkeypatch.setattr('sys.stdin', io.StringIO('\n'.join(json.dumps(r) for r in messages)))
    monkeypatch.setattr('sys.stdout', output)
    assert serve_stdio(RestoreRecorder) == 0
    replies = [json.loads(line) for line in output.getvalue().splitlines()]
    assert replies[-1]['status'] == 'ok' and replies[-1]['body'] == {'accepted': True}
    assert calls == [{'run_id': 'r', 'request_id': 'restore', 'state': '保留\nstate',
                      'virtual_time': '2026-01-01T09:00:00Z'}]


def test_host_restore_without_a_hook_is_explicitly_unsupported():
    class NoRestore(StructuredMemoryAgent):
        restore = None

    host = AgentHost(NoRestore)
    host.dispatch(request('reset', {'seed': 101}))
    response = host.dispatch(request('restore', {'state': 'record'}))
    assert response['status'] == 'error' and response['error']['code'] == 'unsupported_operation'


def bounded_experiment(tmp_path):
    source = EXAMPLES / 'same-model/same-model-generated.stub.json'
    cfg = json.loads(source.read_text())
    for key in ['pack', 'scenario_schema']:
        cfg[key] = str((source.parent / cfg[key]).resolve())
    for key in ['system_prompt', 'reasoning_policy']:
        cfg['agent'][key] = str((source.parent / cfg['agent'][key]).resolve())
    profile_path = tmp_path / 'profile.json'
    profile_path.write_text(json.dumps(recall_profile()))
    cfg['profile'] = str(profile_path)
    cfg['agent']['memory_char_limits'] = {k: 400 for k in calibration.CONDITIONS}
    cfg['calibration']['additional_baselines'] = {'unbounded_reference': True}
    path = tmp_path / 'experiment.json'
    path.write_text(json.dumps(cfg))
    return path


@pytest.mark.parametrize('fault, failed_check', [
    (None, None),
    ('transport', 'no_model_transport_or_parse_errors'),
    ('parse', 'no_model_transport_or_parse_errors'),
    ('identity', 'single_model_identity'),
    ('lifecycle', 'full_lifecycle_execution_clean'),
    ('seed', 'paired_agent_seed_and_future_probe'),
])
def test_admission_reference_is_included_in_fairness_audit(tmp_path, monkeypatch, fault, failed_check):
    class ReferenceFaultAgent(SameModelAgent):
        injected = False

        def is_reference(self):
            return self.condition == 'B1' and self.memory_config.get('max_memory_chars') is None

        def observe(self, **kwargs):
            if self.is_reference() and fault == 'lifecycle':
                return {'accepted': False}
            return super().observe(**kwargs)

        def _call(self, **kwargs):
            if not self.is_reference() or ReferenceFaultAgent.injected:
                return super()._call(**kwargs)
            ReferenceFaultAgent.injected = True
            if fault == 'identity':
                with patch.object(self.model, 'identity', return_value={'client': 'test', 'model_id': 'different'}):
                    return super()._call(**kwargs)
            if fault in {'transport', 'parse'}:
                original = self.model.complete
                first = True

                def complete(**request_kwargs):
                    nonlocal first
                    if first:
                        first = False
                        if fault == 'transport':
                            raise ConnectionError('reference connection dropped')
                        return ModelCompletion('invalid JSON')
                    return original(**request_kwargs)

                with patch.object(self.model, 'complete', side_effect=complete):
                    return super()._call(**kwargs)
            return super()._call(**kwargs)

    monkeypatch.setattr(calibration, 'SameModelAgent', ReferenceFaultAgent)
    # Inject a runner-level seed mismatch so the pairing audit, which records
    # the seed sent to reset, has independent evidence of the mismatch.
    if fault == 'seed':
        original_run = calibration.run_condition

        def unpaired_reference(**kwargs):
            if kwargs['agent'].is_reference():
                kwargs['agent_seed'] = 'unpaired'
            return original_run(**kwargs)

        monkeypatch.setattr(calibration, 'run_condition', unpaired_reference)
    report = calibration.run_same_model_calibration(bounded_experiment(tmp_path))
    reference = report['additional_baselines']['unbounded_reference']['telemetry']
    audit = report['fairness_audit']
    assert audit['evidence']['observed_model_calls'] == sum(t['model_calls'] for t in report['telemetry'].values()) + reference['model_calls']
    if failed_check:
        assert audit['checks'][failed_check] is False and audit['valid'] is False
    else:
        assert audit['valid'] is True
    if fault in {'transport', 'parse'}:
        assert reference[f'{fault}_errors'] == audit['evidence'][f'{fault}_errors'] == 1
    assert report['empirical_release_gate']['eligible'] is False  # engineering stub only
    jsonschema.Draft202012Validator(json.loads((SCHEMAS / 'mib-same-model-report.schema.json').read_text())).validate(report)


def test_unused_reference_failures_remain_diagnostic(tmp_path, monkeypatch):
    path = bounded_experiment(tmp_path)
    cfg = json.loads(path.read_text())
    cfg['agent']['memory_char_limits']['B1'] = None
    path.write_text(json.dumps(cfg))
    original_run = calibration.run_condition

    def failed_additional_run(**kwargs):
        if 'pre_probe_injections' in kwargs:
            kwargs['agent'].observe = lambda **_: {'accepted': False}
        return original_run(**kwargs)

    monkeypatch.setattr(calibration, 'run_condition', failed_additional_run)
    report = calibration.run_same_model_calibration(path)
    assert report['additional_baselines']['unbounded_reference']['enters_release_gate'] is False
    assert report['fairness_audit']['valid'] is True
    assert report['fairness_audit']['evidence']['observed_model_calls'] == sum(t['model_calls'] for t in report['telemetry'].values())


def test_worldmodel_chained_correction_exclusion_and_inplace_cache():
    from mib_runner.worldmodel import Assertion, Source, WorldModel
    model = WorldModel()
    model.add_source(Source(id='s', authority=0.9))
    model.add(Assertion(event_id='s0', seq=1, source='s', subject='x', attribute='code', value='OLD', kind='state'))
    model.add(Assertion(event_id='c1', seq=2, source='s', subject='x', attribute='code', value='MID', kind='correction', supersedes='s0'))
    model.add(Assertion(event_id='c2', seq=3, source='s', subject='x', attribute='code', value='NEW', kind='correction', supersedes='c1'))
    series = model.truth_series('x', 'code', exclude={'c1'})
    assert series == [(1, 'NEW', 's0')]
    # In-place mutation of assertions list without invalidate() must not hit stale cache.
    model.assertions.pop()
    assert model.truth_series('x', 'code') == [(1, 'MID', 's0')]


def test_conditional_probe_clears_counterfactual_follows_when_prerequisite_fails():
    from mib_runner.runner import run_condition

    class FailKeptFollowForgottenAgent(StructuredMemoryAgent):
        def respond(self, *, run_id, request_id, probe):
            if 'retained' in (probe.content or '').lower() or probe.probe_id.endswith('kept'):
                return {'output': {'type': 'structured', 'content': 'wrong', 'value': 'wrong', 'confidence': 0.9, 'status': 'known'}}
            return super().respond(run_id=run_id, request_id=request_id, probe=probe)

    scenario = generate_instance('mib.forgetting.v1', 101, rung=0)
    twin_ablation = next(a for a in scenario['ablations'] if a.get('kind') == 'counterfactual_content')
    # Make p-kept always fail so the prerequisite for p-forgotten is unmet.
    kept_probe = next(p for p in scenario['probes'] if p['id'] == 'p-kept')
    kept_probe['oracle']['accepted'] = ['__impossible_prerequisite_value__']
    run = run_condition(
        scenario=scenario,
        agent=StructuredMemoryAgent(),
        condition='counterfactual_content',
        ablation=twin_ablation,
        repetition=0,
        agent_seed=0,
    )
    by_id = {r['probe_id']: r for r in run['probe_results']}
    assert by_id['p-kept']['score'] == 0.0
    assert by_id['p-forgotten']['score'] == 0.0
    assert 'prerequisite_failed' in by_id['p-forgotten']['failure_codes']
    assert by_id['p-forgotten']['counterfactual']['tracks'] is False
    assert by_id['p-forgotten']['counterfactual']['follows'] is False


def test_relearning_and_feature_policy_program_structure():
    relearn = generate_instance('mib.relearning.v1', 101, rung=1)
    ids = [e['id'] for e in relearn['timeline']]
    assert ids.index('relearn') < ids.index('mw-1') < ids.index('cp')
    assert relearn['instantiation']['distance_hours'] >= 24.0
    fp = generate_instance('mib.feature_policy.v1', 101, rung=0)
    by_id = {a['id']: a for a in fp['ablations']}
    assert by_id['a-feature-acquisition']['probes'] == ['p-2', 'p-3']
    assert by_id['a-feature-policy']['probes'] == ['p-2', 'p-3']
    assert set(by_id['a-feature-policy']['counterfactual']['oracle']) == {'p-2', 'p-3'}


def test_agent_host_dispatches_close_and_learning_audit():
    closed = []

    class AuditedHostAgent(StructuredMemoryAgent):
        def close(self, run_id=None):
            closed.append(run_id)

        def learning_audit(self, *, run_id, request_id):
            return {'run_id': run_id, 'request_id': request_id, 'counts': {'skills': 0}}

    host = AgentHost(AuditedHostAgent)
    host.dispatch(request('reset', {'seed': 101}))
    audit = host.dispatch(request('learning_audit'))
    assert audit['status'] == 'ok' and audit['body']['run_id'] == 'r'
    close_resp = host.dispatch(request('close'))
    assert close_resp['status'] == 'ok' and closed == ['r']


def test_condition_label_visibility_ignores_ordinary_content_and_catches_prompt_leaks():
    from mib_runner.same_model_agent import InvocationRecorder
    from test_same_model import RecordingModel
    model = RecordingModel()
    agent = SameModelAgent(
        condition='B1', model_client=model, system_prompt='fixed system',
        reasoning_policy='fixed policy', model_parameters={'temperature': 0},
        recorder=InvocationRecorder(), memory_config={},
    )
    clean_msgs = [
        {'role': 'system', 'content': 'You are a helpful assistant.'},
        {'role': 'user', 'content': 'The meeting is in room B1 with badge ID-B1.'},
    ]
    assert agent._audit_fields(clean_msgs)['condition_label_visible'] is False
    leak_system = [
        {'role': 'system', 'content': 'You are running under B1 memory policy.'},
        {'role': 'user', 'content': 'Hello.'},
    ]
    assert agent._audit_fields(leak_system)['condition_label_visible'] is True
    leak_header = [
        {'role': 'system', 'content': 'You are a helpful assistant.'},
        {'role': 'user', 'content': 'MEMORY CONDITION: B1\nHello.'},
    ]
    assert agent._audit_fields(leak_header)['condition_label_visible'] is True


def test_verify_same_model_report_and_profile_schemas(tmp_path):
    report = calibration.run_same_model_calibration(bounded_experiment(tmp_path))
    res = verify_score(report)
    assert res['valid'] is True and res['verification_level'] == 'same_model_calibration'
    tampered = copy.deepcopy(report)
    tampered['empirical_release_gate']['eligible'] = True
    assert verify_score(tampered)['valid'] is False

    profile_schema = json.loads((SCHEMAS / 'mib-profile.schema.json').read_text())
    validator = jsonschema.Draft202012Validator(profile_schema)
    for p in sorted(PROFILES.glob('*.json')):
        validator.validate(json.loads(p.read_text()))

    backend_schema = json.loads((SCHEMAS / 'mib-memory-backend-report.schema.json').read_text())
    longitudinal_schema = json.loads((SCHEMAS / 'mib-learning-longitudinal-report.schema.json').read_text())
    jsonschema.Draft202012Validator.check_schema(backend_schema)
    jsonschema.Draft202012Validator.check_schema(longitudinal_schema)
    from mib_runner.backend_benchmark import run_backend_benchmark
    from mib_runner.memory_backend import NullMemoryBackend
    from test_memory_backend import Model as BackendModel, config as backend_config
    from test_learning_longitudinal import factories as learning_factories, profile as learning_profile
    from mib_runner.learning.benchmark import run_experiment as run_learning_experiment
    backend_dir = tmp_path / 'backend'
    backend_dir.mkdir()
    backend_report = run_backend_benchmark(
        backend_config(backend_dir, 'http://127.0.0.1:9'),
        model_client=BackendModel(),
        candidate_factory=lambda: NullMemoryBackend(),
    )
    jsonschema.Draft202012Validator(backend_schema).validate(backend_report)
    long_report = run_learning_experiment(learning_profile(), learning_factories(), engineering_fixture=True)
    jsonschema.Draft202012Validator(longitudinal_schema).validate(long_report)
