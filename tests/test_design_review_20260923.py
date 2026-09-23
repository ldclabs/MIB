"""Behavioral regressions for the September 23 design review."""
import copy
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from mib_runner.agents import StructuredMemoryAgent
from mib_runner.backend_benchmark import backend_episode_plan
from mib_runner.benchmark import build_pack_report
from mib_runner.calibration import DEFAULT_THRESHOLDS
from mib_runner.dependence import joint_evidence, joint_dependence
from mib_runner.episode import validate_generated_instances
from mib_runner.evaluator import evaluate_structured
from mib_runner.generate import generate_instance
from mib_runner.report import verify_score, validate_report
from mib_runner.runner import run_scenario
from mib_runner.same_model_agent import SameModelAgent, InvocationRecorder, FullContextPolicy, observation_text
from mib_runner.same_model_calibration import _aggregate_calibration
from mib_runner.types import AgentOutput, Observation

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize('answer', ['Definitely not {answer}', '{answer} or IMPOSSIBLE-VALUE',
    ['{answer}'], {'candidate': '{answer}'}, 'Lisbon / Tokyo / Berlin / Toronto / Nairobi / Seoul / Denver / Warsaw'])
def test_generated_scalar_answers_cannot_negate_or_enumerate(answer):
    scenario = generate_instance('mib.recall.v1', 101)
    p = scenario['probes'][0]
    actual = p['oracle']['accepted'][0]
    if isinstance(answer, str): answer = answer.format(answer=actual)
    elif isinstance(answer, list): answer = [actual]
    else: answer = {'candidate': actual}
    config = scenario['evaluators'][0]['config']
    assert evaluate_structured(AgentOutput(type='structured', value={'value': answer, 'status': 'known'}), p['oracle'], config)['score'] == 0
    assert evaluate_structured(AgentOutput(type='structured', value={'value': actual, 'status': 'known'}), p['oracle'], config)['score'] == 1


def joint_runs(hard, repetitions=1, missing=False):
    def row(pid, score): return {'probe_id': pid, 'score': score, 'weight': 1, 'dimensions': ['d'], 'outcome': 'scored'}
    plan = [{'ablation_id': 'a', 'probe_id': p, 'dimensions': ['d']} for p in ['easy', 'hard']]
    runs = []
    for rep in range(repetitions):
        runs.append({'condition': 'full', 'repetition': rep, 'validity': {'runner_valid': True, 'counterfactual_plan': plan},
                     'probe_results': [row('easy', 1), row('hard', hard)]})
        if not missing:
            runs.append({'condition': 'counterfactual_content', 'ablation_id': 'a', 'repetition': rep,
                'validity': {'runner_valid': True, 'causal_pair_valid': True}, 'probe_results': [row('easy', 1), row('hard', 0)]})
    return runs


def gate(runs):
    instances = [{'template_id': 'T', 'joint_dependence_evidence': joint_evidence(runs)} for _ in range(5)]
    profile = {'dimensions': {'d': {'weight': 1}}, 'memory_dependence': {'metric': 'joint_twin_success', 'floor': .5,
        'min_instances': 5, 'min_coverage': 1, 'bootstrap_resamples': 50}}
    return joint_dependence(instances, profile)


def test_joint_gate_is_monotone_and_repetitions_do_not_inflate_independence():
    a, b = gate(joint_runs(.8)), gate(joint_runs(1))
    assert a['eligible'] == b['eligible'] is True
    assert a['joint_twin_success'] == b['joint_twin_success'] == .5
    repeated = gate(joint_runs(1, repetitions=4))
    assert repeated['dimensions'][0]['ci'] == b['dimensions'][0]['ci']
    assert repeated['dimensions'][0]['independent_instances'] == 5
    missing = gate(joint_runs(1, missing=True))
    assert missing['total_n'] == 10 and missing['eligible_n'] == 0 and missing['eligible'] is None


def test_calibration_missing_causal_evidence_is_unassessable():
    class Descriptor:
        def describe(self): return {'implementation': {'name': 'fixture'}}
    r = _aggregate_calibration(templates=[{'id': 'T', 'dimensions': ['d'], 'scoring': {'dimension_weights': {'d': 1}}}],
        profile={'id': 'P', 'version': '1', 'dimensions': {'d': {'weight': 1}}},
        raw={'T': {b: [{'seed': 1, 'score': s}] for b, s in [('B0', 0), ('B1', 1), ('B2', .5), ('B3', 1)]}},
        causal={}, factories={b: Descriptor for b in ['B0', 'B1', 'B2', 'B3']}, thresholds=DEFAULT_THRESHOLDS,
        bootstrap_resamples=20, bootstrap_seed=1, configuration={'instance_seeds': [1]})
    assert r['summary']['provisional_full_gate_including_causal'] == 0
    assert r['templates'][0]['gate_status']['causal_sensitivity'] == 'unassessable'


def test_backend_generated_plan_uses_program_identity_and_full_ladders():
    path = ROOT / 'profiles/MIB-Core-0.2-Calibration-Dev.json'
    profile = json.loads(path.read_text())
    templates, instances = backend_episode_plan({'execution': {'instance_seeds': [101]}}, {'profile': path})
    assert len(templates) == 14 and len(instances) == 42
    with pytest.raises(ValueError, match='every rung'):
        validate_generated_instances(profile, instances[:-1])
    runs = [r for s in instances for r in run_scenario(scenario=s, agent_factory=StructuredMemoryAgent, include_ablations=False)]
    report = build_pack_report(templates=templates, instances=instances, all_runs=runs, profile=profile,
                              agent_descriptor=StructuredMemoryAgent().describe())
    assert report['coverage']['overall'] == 1
    assert not report['aggregates']['mib_score']['partial']
    assert len(report['retention']) == 14
    assert all(len(r['rungs']) == 3 for r in report['retention'])
    assert verify_score(report)['valid']
    validate_report(report, json.loads((ROOT / 'schemas/mib-report.schema.json').read_text()))
    tampered = copy.deepcopy(report)
    tampered['aggregates']['scenario_instances'][0]['joint_dependence_evidence'][0]['joint_score'] = 1
    assert not verify_score(tampered)['valid']
    duplicated = copy.deepcopy(report)
    duplicated['aggregates']['scenario_instances'].append(copy.deepcopy(duplicated['aggregates']['scenario_instances'][0]))
    assert not verify_score(duplicated)['valid']


class RecordingModel:
    def __init__(self): self.calls = []
    def identity(self): return {'model_id': 'review-fixture'}
    def complete(self, **kwargs):
        self.calls.append(copy.deepcopy(kwargs))
        prompt = kwargs['messages'][-1]['content']
        result = {'emissions': [{'type': 'reminder', 'content': 'OUTPUT_RECEIPT_917'}]} if 'MODE: OBSERVE' in prompt else {
            'type': 'structured', 'value': {'value': 'ANSWER_RECEIPT_613', 'status': 'known'}}
        return SimpleNamespace(text=json.dumps(result), usage={})


def agent(condition, model, **memory):
    return SameModelAgent(condition=condition, model_client=model, system_prompt='', reasoning_policy='',
        model_parameters={}, recorder=InvocationRecorder(), memory_config=memory)


@pytest.mark.parametrize('limit', [1, 7, 100, 1000])
def test_final_memory_budget_is_hard_including_large_unicode_records(limit):
    model = RecordingModel(); a = agent('B1', model, max_memory_chars=limit)
    a.reset(run_id='r', seed=1, virtual_time=None)
    for i, content in enumerate(['short', '中' * 10000, 'later']):
        a.observe(run_id='r', request_id=str(i), observation=Observation(str(i), 'user_message', content=content))
    context, truncated, _ = a._memory_context('query')
    assert len(context) <= limit and truncated
    selected, truncated = FullContextPolicy().select([Observation('o', 'user_message', content='x'*10000)], query='', limit_chars=limit)
    assert not selected and truncated


@pytest.mark.parametrize('condition', ['B0', 'B1', 'B2', 'B3'])
def test_public_dialogue_and_emissions_survive_boundary_only_with_memory(condition):
    model = RecordingModel(); a = agent(condition, model, observe_decisions=True)
    a.reset(run_id='r', seed=1, virtual_time=None)
    kw = dict(run_id='r', request_id='o', observation=Observation('o', 'user_message', content='input'))
    a.observe(**kw)
    before = len(a.long_term)
    a.observe(**kw)
    assert len(a.long_term) == before  # idempotent delivery
    a.respond(run_id='r', request_id='q1', interaction_id='q1', input_data={'content': 'question one'}, virtual_time=None)
    a.session_boundary(run_id='r', request_id='s', virtual_time=None)
    a.respond(run_id='r', request_id='q2', interaction_id='q2', input_data={'content': 'question two'}, virtual_time=None)
    prompt = model.calls[-1]['messages'][-1]['content']
    assert ('ANSWER_RECEIPT_613' in prompt) == (condition != 'B0')
    assert ('question one' in prompt) == (condition != 'B0')
    assert ('OUTPUT_RECEIPT_917' in prompt) == (condition != 'B0')
    a.reset(run_id='fresh', seed=2, virtual_time=None)
    assert a._memory_context('query')[0] == '<empty>'


def test_core_stream_defeats_prefix_only_memory_without_breaking_reference():
    from mib_runner.benchmark import run_generated_pack
    class PrefixMemory(StructuredMemoryAgent):
        def reset(self, **kwargs):
            self.freeze = False
            return super().reset(**kwargs)
        def maintain(self, **kwargs):
            self.freeze = True
            return super().maintain(**kwargs)
        def observe(self, **kwargs):
            if self.freeze and kwargs['observation'].type == 'user_message':
                return {'accepted': True, 'emissions': []}
            return super().observe(**kwargs)
    profile = json.loads((ROOT / 'profiles/MIB-Core-0.2-Dev.json').read_text())
    _, weak = run_generated_pack(profile=profile, agent_factory=PrefixMemory, seeds=[101, 202], include_ablations=False)
    _, full = run_generated_pack(profile=profile, agent_factory=StructuredMemoryAgent, seeds=[101, 202], include_ablations=False)
    assert full['mib_score'] == 100
    assert weak['mib_score'] < 90


@pytest.mark.parametrize('program', ['mib.feature_policy.v1', 'mib.commitment_lifecycle.v1'])
def test_new_mechanism_challenges_and_twins_have_observable_success(program):
    from mib_runner.validation import validate_scenario
    for seed in [101, 202]:
        scenarios = [generate_instance(program, seed, rung=r) for r in range(3)]
        assert all(s['probes'] == scenarios[0]['probes'] for s in scenarios)
        assert all(validate_scenario(s, json.loads((ROOT / 'schemas/mib-scenario.schema.json').read_text())).valid for s in scenarios)
        runs = run_scenario(scenario=scenarios[1], agent_factory=StructuredMemoryAgent)
        assert runs[0]['scenario_score'] == 1
        assert all(r['scenario_score'] == 1 for r in runs if r['condition'] == 'counterfactual_content')
        assert any(r['scenario_score'] < 1 for r in runs if r['condition'] == 'relevant_ablation')


def test_family_lookup_cannot_solve_unseen_feature_composition():
    class FamilyLookup(StructuredMemoryAgent):
        def observe(self, **kwargs):
            obs = kwargs['observation']
            if isinstance(obs.payload, dict) and obs.payload.get('format') == 'mib.feature-recipe/1':
                return {'accepted': True}
            return super().observe(**kwargs)
    scenario = generate_instance('mib.feature_policy.v1', 101)
    run = run_scenario(scenario=scenario, agent_factory=FamilyLookup, include_ablations=False)[0]
    matching = next(p for p in run['probe_results'] if p['probe_id'] == 'p-3')
    assert matching['score'] < 1


def test_signed_harm_does_not_rectify_zero_mean_variation():
    from mib_runner.scoring import paired_causal_metrics
    runs = []
    for rep, (base, variant) in enumerate([(1, 0), (0, 1)]):
        for condition, score in [('full', base), ('harmful_memory', variant)]:
            runs.append({'condition': condition, 'repetition': rep,
                'probe_results': [{'probe_id': 'p', 'score': score, 'weight': 1, 'outcome': 'scored'}]})
    metrics = {r['name']: r for r in paired_causal_metrics(runs)}
    assert metrics['memory_harm']['value'] == .5
    assert metrics['memory_harm_effect']['value'] == 0
    assert metrics['memory_harm_effect']['unit'] == 'normalized_delta'


def test_portable_audit_uses_host_ids_and_pinned_host_tokenizer():
    from test_learning_longitudinal import descriptor, Fixture
    from mib_runner.learning.contract import check_learning_descriptor, check_audit, EXTENSION
    d = descriptor('normal')
    d['extensions'][EXTENSION]['audit_binding'] = 'portable_v1'
    d['extensions'][EXTENSION]['recall_budget']['tokenizer'] = 'host-tokenizer@1'
    assert check_learning_descriptor(d, 'normal')
    body = Fixture('normal').learning_audit(run_id='r')
    body['counts']['skills'] = 1
    body['skills'] = [{'skill_ref': 'skill:abc', 'revision_ref': 'revision:v2', 'status': 'proposed',
                       'evaluation_ref': None, 'trial_ref': 'trial:abc', 'recommendation_allowed': False}]
    assert check_audit(body, 'r', 'normal', 'portable_v1')
    with pytest.raises(Exception, match='native Skill'):
        check_audit(body, 'r', 'normal')


def test_longitudinal_repetitions_are_clustered_under_seed():
    from mib_runner.learning.scoring import seed_cluster_summary
    lock = {'profile': {'seeds': [1, 2, 3], 'repetitions': 1}, 'statistics': {'bootstrap_seed': 1, 'bootstrap_repetitions': 200}}
    a = seed_cluster_summary({(s, 0): s/4 for s in [1, 2, 3]}, lock)
    lock['profile']['repetitions'] = 10
    b = seed_cluster_summary({(s, r): s/4 for s in [1, 2, 3] for r in range(10)}, lock)
    assert a == b and b['measured_pairs'] == 3


def test_public_observation_router_stores_all_inputs_but_only_invokes_declared_types():
    model = RecordingModel()
    a = agent('B1', model, observe_decisions=True, observe_decision_types=['environment_event'])
    a.reset(run_id='r', seed=1, virtual_time=None)
    a.observe(run_id='r', request_id='1', observation=Observation('1', 'user_message', content='remember me'))
    assert not model.calls
    a.observe(run_id='r', request_id='2', observation=Observation('2', 'environment_event', content='ordinary event'))
    assert len(model.calls) == 1
    assert 'remember me' in model.calls[0]['messages'][-1]['content']


def test_pilot_budget_and_plan_are_bound_before_execution():
    from mib_runner.same_model_calibration import load_experiment, load_experiment_templates, build_experiment_lock, estimate_experiment
    cfg, paths = load_experiment(ROOT / 'examples/same-model/same-model-generated.pilot.json')
    estimate = estimate_experiment(cfg, load_experiment_templates(paths))
    assert estimate['minimum_model_turns'] < 10000
    lock = build_experiment_lock(cfg, paths)
    cfg['calibration']['instance_seeds'] = [777]
    assert build_experiment_lock(cfg, paths)['digest'] != lock['digest']
    assert lock['calibration_plan']['purpose'] == 'pilot'


def test_run_estimate_and_verify_aliases(capsys):
    from mib_runner.cli import main, build_parser
    assert main(['run', str(ROOT / 'examples/same-model/same-model-generated.pilot.json'), '--estimate-only']) == 0
    assert 'minimum_model_turns' in capsys.readouterr().out
    assert build_parser().parse_args(['verify', 'report.json']).func == build_parser().parse_args(['verify-score', 'report.json']).func


def test_materialized_static_episode_is_not_relabelled_as_independent_seeds():
    from mib_runner.episode import materialize_episode_plan
    scenario = generate_instance('mib.recall.v1', 101)
    scenario.pop('instantiation')
    templates, instances = materialize_episode_plan({}, [101], static_templates=[scenario])
    assert instances == templates == [scenario]
    with pytest.raises(ValueError, match='use repetitions'):
        materialize_episode_plan({}, [101, 202], static_templates=[scenario])
