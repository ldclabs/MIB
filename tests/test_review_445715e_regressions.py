"""Measurement and evidence regressions from the review of commit 445715e."""
from __future__ import annotations

import copy
import json

import pytest

from mib_runner import same_model_calibration as calibration
from mib_runner.agents import NoMemoryAgent
from mib_runner.dependence import joint_evidence
from mib_runner.evaluation_service import ServiceConfigError
from mib_runner.generate import generate_instance
from mib_runner.hidden import HiddenEvalStore
from mib_runner.materialize import materialize
from mib_runner.report import verify_score
from mib_runner.runner import run_scenario
from mib_runner.scoring import validate_causal_pairs
from mib_runner.types import AgentOutput
from mib_runner.validation import load_json, validate_scenario
from mib_runner.worldmodel import Assertion, Source, WorldModel
from paths import EXAMPLES, SCENARIO_SCHEMA_PATH
from test_commit_673631a_regressions import _generated_store
from test_design_review_20260923b import PRIVATE_BANK
from test_evaluation_service import make_service
from test_review_7291876_regressions import bounded_experiment


def test_constant_answers_have_zero_cfe_even_when_prerequisites_fail():
    scenario = generate_instance('mib.forgetting.v1', 101, rung=0)
    twin = next(a for a in scenario['ablations'] if a['id'] == 'a-swap-withdrawal')
    value = twin['counterfactual']['oracle']['p-forgotten']['accepted'][0]
    scenario['ablations'] = [twin]

    class ConstantAnswer(NoMemoryAgent):
        def respond(self, **kwargs):
            return AgentOutput(type='structured', content=value, value={'value': value, 'status': 'known'})

    runs = run_scenario(scenario=scenario, agent_factory=ConstantAnswer)
    validate_causal_pairs(runs)
    for run in runs:
        assert run['scenario_score'] == 0
        for probe in run['probe_results']:
            if probe['probe_id'].startswith('p-forgotten'):
                assert probe['conditional_on']['met'] is False
                assert 'prerequisite_failed' in probe['failure_codes']
    evidence = joint_evidence(runs)[0]
    assert evidence['total_n'] == evidence['valid_n'] == 2
    assert evidence['twin_follow_n'] == evidence['full_follow_n'] == 2
    assert evidence['content_following_effect'] == 0


@pytest.mark.parametrize('source', ['calibration', 'hidden_store'])
def test_surface_bank_survives_seed_materialization(tmp_path, source):
    schema = load_json(SCENARIO_SCHEMA_PATH)
    if source == 'calibration':
        experiment = bounded_experiment(tmp_path)
        _, paths = calibration.load_experiment(experiment)
        profile = load_json(paths['profile'])
        profile['surface_bank'] = PRIVATE_BANK
        paths['profile'].write_text(json.dumps(profile), encoding='utf-8')
        template = calibration.load_experiment_templates(paths)[0]
    else:
        manifest = {'programs': [{'id': 'mib.recall.v1', 'public_id': 'demo', 'instances': 1}],
                    'ladder': [0], 'surface_bank': PRIVATE_BANK}
        (tmp_path / 'manifest.private.json').write_text(json.dumps(manifest), encoding='utf-8')
        template = HiddenEvalStore(tmp_path).load_templates(schema)[0][0]
    assert validate_scenario(template, schema).valid
    for seed in [101, 202]:
        actual = materialize(template, seed)
        expected = generate_instance('mib.recall.v1', seed, ladder=[0], surface_bank=PRIVATE_BANK)
        assert validate_scenario(actual, schema).valid
        assert actual['timeline'] == expected['timeline']
        assert actual['probes'] == expected['probes']
        assert actual['instantiation']['surface_bank_digest'] == expected['instantiation']['surface_bank_digest']


@pytest.fixture
def same_model_report(tmp_path):
    return calibration.run_same_model_calibration(bounded_experiment(tmp_path))


def test_legacy_same_model_report_without_invocation_fingerprints_still_verifies():
    report = load_json(EXAMPLES / 'same-model/same-model-stub.report.json')
    assert report['report_version'] == '0.1.0'
    assert 'model_identities' not in report['telemetry']['B1']
    assert verify_score(report)['valid']
    report['telemetry']['B1']['model_errors'] += 1
    assert not verify_score(report)['valid']


@pytest.mark.parametrize('tamper', ['cards', 'counts', 'model', 'telemetry', 'reference', 'preflight', 'pairing'])
def test_same_model_verification_rejects_inconsistent_evidence(same_model_report, tamper):
    assert verify_score(same_model_report)['valid']
    report = copy.deepcopy(same_model_report)
    if tamper == 'cards':
        report['calibration']['templates'] = []
    elif tamper == 'counts':
        count = report['calibration']['summary']['template_count']
        report['calibration']['summary']['provisional_full_gate_including_causal'] = count
        report['empirical_release_gate']['template_full_gate'].update(passed=count, all_pass=True)
    elif tamper == 'model':
        report['empirical_release_gate']['non_stub_model'] = True
    elif tamper == 'telemetry':
        report['telemetry']['B1']['model_errors'] += 1
    elif tamper == 'reference':
        report['additional_baselines']['unbounded_reference']['telemetry']['model_errors'] += 1
    elif tamper == 'preflight':
        report['statelessness_preflight']['passed'] = False
    else:
        report['pairing_audit']['valid'] = False
    assert not verify_score(report)['valid']


def test_world_model_cache_hit_does_not_rescan_the_record():
    class CountingList(list):
        scans = 0

        def __iter__(self):
            CountingList.scans += 1
            return super().__iter__()

    model = WorldModel()
    model.add_source(Source(id='s', authority=0.9))
    for i in range(3):
        model.add(Assertion(event_id=f'e{i}', seq=i + 1, source='s', subject='x', attribute='code', value=str(i), kind='state'))
    model.assertions = CountingList(model.assertions)
    model.truth_series('x', 'code')
    scans = CountingList.scans
    model._rows(())
    assert CountingList.scans == scans  # O(1) key: long ladders issue thousands of queries.
    model.assertions.pop()
    assert [a.event_id for a in model._rows(())[0]] == ['e0', 'e1']


def test_cycle_registration_binds_a_declared_surface_bank(tmp_path):
    _, profile, profile_path = _generated_store(tmp_path)
    manifest_path = tmp_path / 'manifest.private.json'
    manifest = json.loads(manifest_path.read_text())
    other = copy.deepcopy(PRIVATE_BANK)
    other['templates']['state.first'] = ['For the record, my {label} is {value}.']

    def register(profile_bank, store_bank, cycle):
        profile.pop('surface_bank', None)
        manifest.pop('surface_bank', None)
        if profile_bank is not None:
            profile['surface_bank'] = profile_bank
        if store_bank is not None:
            manifest['surface_bank'] = store_bank
        profile_path.write_text(json.dumps(profile))
        manifest_path.write_text(json.dumps(manifest))
        return make_service(tmp_path).register_cycle(cycle, store_path=tmp_path, profile_path=profile_path)

    # A public Profile may omit the evaluator-private bank held by the store.
    register(None, PRIVATE_BANK, 'private-store-bank')
    register(PRIVATE_BANK, PRIVATE_BANK, 'same-bank')
    for cycle, store_bank in [('missing-store-bank', None), ('different-store-bank', other)]:
        with pytest.raises(ServiceConfigError, match='surface_bank'):
            register(PRIVATE_BANK, store_bank, cycle)
