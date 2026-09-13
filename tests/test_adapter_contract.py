import copy
import json

import pytest

from mib_runner.adapter_contract import digest, verify_run_contract
from mib_runner.agents import ReferenceMemoryAgent
from mib_runner.benchmark import agent_supports_template
from mib_runner.materialize import materialize
from mib_runner.report import build_basic_report, validate_report, verify_score
from mib_runner.runner import run_condition
from paths import DEV_PACK, REPORT_SCHEMA_PATH


def scenario():
    s = materialize(json.loads((DEV_PACK / 'epistemic/MIB-EPI-002.json').read_text()), 101)
    s['timeline'].append({'id': 'last-maintenance', 'type': 'maintenance_window',
                          'visibility': 'agent', 'at': {'sequence': 999}, 'payload': {'budget': 'PT1H'}})
    return s


class GatedAgent(ReferenceMemoryAgent):
    failed_op = None
    failure = 'reject'

    def describe(self):
        d = super().describe()
        d['capabilities'].update(maintenance=True, session_boundary=True)
        return d

    def fail(self, operation):
        if self.failed_op != operation:
            return {'accepted': True}
        if self.failure == 'timeout':
            raise TimeoutError('terminal completion timed out')
        if self.failure == 'error':
            raise RuntimeError('formation failed')
        if self.failure == 'partial':
            return {'accepted': True, 'error': {'message': 'partial work failed'}}
        return {'accepted': False, 'reason': 'not complete'}

    def reset(self, **kwargs):
        super().reset(**kwargs)
        return self.fail('reset')

    def observe(self, **kwargs):
        super().observe(**kwargs)
        return self.fail('observe')

    def maintain(self, **kwargs): return self.fail('maintain')
    def session_boundary(self, **kwargs): return self.fail('session_boundary')


@pytest.mark.parametrize('op', ['reset', 'observe', 'maintain', 'session_boundary'])
@pytest.mark.parametrize('failure', ['reject', 'timeout', 'error', 'partial'])
def test_lifecycle_failure_preserves_denominator_and_is_verifiable(op, failure):
    s = scenario()
    if op == 'session_boundary':
        s['timeline'][-1]['type'] = 'session_boundary'
    a = GatedAgent(); a.failed_op = op; a.failure = failure
    run = run_condition(scenario=s, agent=a)
    assert run['status'] == 'invalid'
    assert run['validity']['runner_valid'] is False
    assert len(run['probe_results']) == len(s['probes'])
    assert all(p['outcome'] == 'execution_failure' and p['score'] == 0 for p in run['probe_results'])
    if op in {'maintain', 'session_boundary'}:
        prior = run['adapter_contract']['pre_invalidation_probe_results']
        assert all(p['score'] == 1 for p in prior)
    assert verify_run_contract(run) == []
    report = build_basic_report(runs=[run], scenario=s, agent_descriptor=a.describe())
    validate_report(report, json.loads(REPORT_SCHEMA_PATH.read_text()))
    assert verify_score(report)['valid']
    altered = copy.deepcopy(report)
    altered['results']['runs'][0]['validity']['runner_valid'] = True
    assert not verify_score(altered)['valid']


def test_unknown_capability_cannot_be_inferred_and_failure_receipt_cannot_be_hidden():
    s = scenario(); a = GatedAgent()
    a.describe = lambda: {'protocol': 'mib-agent/0.1', 'capabilities': {}}
    assert not agent_supports_template(a.describe(), s)
    r = run_condition(scenario=s, agent=a)
    assert r['status'] == 'invalid'
    contract = r['adapter_contract']
    contract['operations'] = [op for op in contract['operations'] if op['outcome'] != 'failure']
    contract['digest'] = digest({k: v for k, v in contract.items() if k != 'digest'})
    assert verify_run_contract(r)


def test_successful_contract_cannot_omit_describe_and_close_receipts():
    s = scenario(); a = GatedAgent()
    report = build_basic_report(runs=[run_condition(scenario=s, agent=a)], scenario=s, agent_descriptor=a.describe())
    contract = report['results']['runs'][0]['adapter_contract']
    contract['operations'] = [op for op in contract['operations'] if op['operation'] == 'reset']
    contract['operations'][0]['sequence'] = 0
    contract['digest'] = digest({k: v for k, v in contract.items() if k != 'digest'})
    result = verify_score(report)
    assert not result['valid']
    assert any('describe must begin' in error for error in result['errors'])
    assert any('close must end' in error for error in result['errors'])


def test_explicit_optional_maintenance_false_is_recorded_skip():
    r = run_condition(scenario=scenario(), agent=ReferenceMemoryAgent())
    assert r['status'] == 'succeeded'
    assert any(op['operation'] == 'maintain' and op['outcome'] == 'skipped' for op in r['adapter_contract']['operations'])
    assert not verify_run_contract(r)
