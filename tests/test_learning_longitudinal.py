"""Engineering-only contract fixtures; none implements native KIP learning."""
import copy
import json
from dataclasses import asdict
from pathlib import Path
import pytest

from mib_runner.adapter_contract import digest, AdapterLifecycleError
from mib_runner.learning.benchmark import run_experiment, verify_report, validate_profile
from mib_runner.learning.contract import CONDITIONS, EXTENSION, AUDIT_FORMAT, COUNT_FIELDS, check_audit, check_learning_descriptor
from mib_runner.learning.programs import generate, PROGRAMS
from mib_runner.learning.workflow import CONTRACT, CONTRACT_DIGEST, TOOLS, initial_state, execute, instrument
from mib_runner.report import verify_score
from mib_runner.types import AgentOutput, ActStep
from mib_runner.validation import load_json, validate_scenario
from mib_runner.world import WorldState

ROOT = Path(__file__).resolve().parents[1]

def profile():
    value = load_json(ROOT / 'profiles/MIB-Learning-Longitudinal-0.1-Dev.json')
    value.update(seeds=[101], repetitions=1, phases={'early': 2, 'late': 3, 'retrial': 3})
    value['statistics']['bootstrap_repetitions'] = 200
    return value

def descriptor(mode):
    return {'protocol': 'mib-agent/0.1', 'implementation': {'name': 'engineering-contract-stub-NOT-native-learning', 'version': '1'},
        'capabilities': dict.fromkeys(['observe','respond','act','runner_managed_tools','maintenance','virtual_time','session_boundary'], True),
        'extensions': {EXTENSION: {'mode': mode, 'configuration_digest': digest(mode),
            'business_identity': dict.fromkeys(['model_digest','business_prompt_digest','tools_digest','budget_digest','decoding_digest'], digest('same-fixture')),
            'execution_guard_digest': digest('same-guard'), 'recall_budget': {'tokenizer': 'o200k_base@tiktoken-rs-0.12.0', 'max_tokens':4096,'context_tokens':32768},
            'workflow_contract_digest': CONTRACT_DIGEST, 'native_task_family': CONTRACT['task_family'] if mode != 'no_memory' else None,
            'native_comparison_and_review': mode == 'normal', 'independent_observer': mode == 'normal',
            'isolated_trial_application': mode == 'ungated', 'cross_task_state': mode != 'no_memory', 'audit_operation': 'learning_audit'}}}

class Fixture:
    """Fixed policies solely for exercising transport/world/scoring contracts."""
    def __init__(self, mode, *, reject=None, audit_error=False, legacy=False, seen=None):
        self.mode, self.reject, self.audit_error, self.legacy = mode, reject, audit_error, legacy
        self.seen = seen if seen is not None else []
        self.step = 0
        self.last = {}
        self.cost_snapshots = []
    def describe(self):
        result = descriptor(self.mode)
        if self.legacy: result['extensions'].pop(EXTENSION)
        return result
    def reset(self, **kwargs):
        self.run_id = kwargs['run_id']; self.seen.append(('reset', kwargs)); return {'accepted':True}
    def observe(self, **kwargs):
        observation=kwargs['observation']; self.seen.append(('observe',asdict(observation)))
        if observation.type == 'tool_result': self.last=observation.payload
        return {'accepted':self.reject != 'observe'}
    def respond(self, **kwargs):
        self.seen.append(('respond',kwargs)); return AgentOutput(type='abstention', content='unknown')
    def act(self, **kwargs):
        self.seen.append(('act',kwargs))
        if not kwargs['continuation']: self.step=0; self.last={}
        self.step+=1
        if self.mode == 'ungated':
            action = 'prepare' if self.step == 1 else 'commit' if self.step == 2 else None
        else:
            action = 'inspect' if self.step == 1 else ('prepare' if self.last.get('preparation_requirement') == 'required' else 'commit') if self.step == 2 else 'commit' if self.last.get('prepared') and 'success' not in self.last else None
        if action is None: return ActStep(type='final',content='done')
        return ActStep(type='tool_call', tool='workflow.'+action,tool_call_id=f'{kwargs["task_id"]}-{self.step}',arguments={})
    def maintain(self, **kwargs): return {'accepted':self.reject != 'maintain'}
    def session_boundary(self, **kwargs): self.step=0; self.last={}; return {'accepted':self.reject != 'session_boundary'}
    def learning_audit(self, **kwargs):
        if self.audit_error: raise TimeoutError('audit fixture timeout')
        return {'format':AUDIT_FORMAT,'run_id':kwargs['run_id'],'mode':self.mode,'complete':True,'native_sequence':0,
            'state_digest':digest({'skills':[]}), 'counts':dict.fromkeys(COUNT_FIELDS,0), 'skills':[]}
    def close(self, **kwargs): pass

def factories(**options):
    return {mode: lambda mode=mode: Fixture(mode, **options) for mode in CONDITIONS}

@pytest.fixture(scope='module')
def report():
    return run_experiment(profile(), factories(), engineering_fixture=True,
        schema=load_json(ROOT/'schemas/mib-scenario.schema.json'))

def test_generator_is_fixed_paired_p0_contract_and_drift_is_not_an_observation():
    cfg=profile()
    for program in PROGRAMS:
        a=generate(program,101,cfg['phases'],cfg['execution'])
        assert a==generate(program,101,cfg['phases'],cfg['execution'])
        assert a!=generate(program,202,cfg['phases'],cfg['execution'])
        assert validate_scenario(a,load_json(ROOT/'schemas/mib-scenario.schema.json')).valid
        assert a['extensions'][EXTENSION]['workflow_contract_digest']==CONTRACT_DIGEST
        public=[event for event in a['timeline'] if event['visibility']=='agent']
        assert all(event['type']!='world_update' and 'oracle' not in event for event in public)
        assert all('requirement' not in p['input']['goal'] for p in a['probes'] if p['delivery']=='act')
        requirements={s['requirement'] for s in a['extensions'][EXTENSION]['samples'] if s['phase']=='retrial'}
        if program!='question_contamination': assert requirements==set(CONTRACT['requirements'])
    # Vendored file is the complete P0 contract, not an invented success rule.
    brain=ROOT.parent/'anda-brain/anda_brain/assets/learning/workflow-contract-v1.json'
    if brain.exists(): assert (ROOT/'src/mib_runner/learning/workflow-contract-v1.json').read_bytes()==brain.read_bytes()

def journal(requirement, actions):
    state=initial_state(requirement)
    return [{'action': action,'result':execute(state,action)} for action in actions]

def test_independent_instrument_preserves_unsafe_and_retry_failures_and_unknown_precedes_failure():
    budget=profile()['execution']['attempt_budget']
    for requirement, actions in [('required',['commit','prepare','commit']),('forbidden',['prepare','commit'])]:
        rows=journal(requirement,actions)
        unknown=instrument(requirement,rows,finished=True,budget=budget)
        assert unknown['outcome_status']=='unknown' and unknown['final_committed']
        assert not unknown['behavior_success']
        measured=instrument(requirement,rows,finished=True,budget=budget,elapsed_ms=3,input_tokens=0,output_tokens=0,accounting_complete=True)
        assert measured['outcome_status']=='failure'
    rows=journal('required',['inspect','prepare','commit'])
    assert instrument('required',rows,finished=True,budget=budget,elapsed_ms=3,input_tokens=0,output_tokens=0,accounting_complete=True)['outcome_status']=='success'
    for bad in [float('nan'),float('inf'),-1,True,1.5]:
        with pytest.raises(ValueError): instrument('required',rows,finished=True,budget=budget,elapsed_ms=bad)
    rows[0]['result']['preparation_requirement']='forbidden'
    with pytest.raises(ValueError): instrument('required',rows,finished=True,budget=budget)

def test_true_simulator_and_independent_instrument_match_all_p0_states():
    for requirement in CONTRACT['requirements']:
        world=WorldState.from_scenario({'tools':[TOOLS],'state':{'precondition':initial_state(requirement),'precondition_journal':[],
            'precondition_measurement':{'failed_commits':0,'unsafe_actions':0}}})
        before=copy.deepcopy(world.state['precondition'])
        world.execute_tool('workflow.inspect',{})
        assert before==world.state['precondition']
        world.execute_tool('workflow.prepare',{});world.execute_tool('workflow.commit',{})
        measured=instrument(requirement,world.state['precondition_journal'],finished=True,budget=profile()['execution']['attempt_budget'])
        assert measured['unsafe_actions']==world.state['precondition_measurement']['unsafe_actions']
        assert measured['final_committed']

def test_full_three_arm_report_replays_but_fixture_never_claims_learning_pass(report):
    assert verify_score(report)['valid']
    assert report['fairness_audit']['valid']
    assert report['aggregates']['learning_evaluation']['status']=='not_evaluated'
    assert report['total_cost'] is None and report['accounting_complete'] is False
    assert len(report['units'])==9
    normal=next(u for u in report['units'] if u['condition']=='normal' and u['program']=='unannounced_drift')
    ungated=next(u for u in report['units'] if u['condition']=='ungated' and u['program']=='unannounced_drift')
    assert normal['metrics']['late_damage_units']==0
    assert ungated['metrics']['late_damage_units']==2
    assert all(s['first_success'] for s in ungated['metrics']['samples'] if s['phase']=='early')
    assert all(s['measurement']['outcome_status']=='unknown' for s in normal['metrics']['samples'])
    assert normal['metrics']['use_after_revoke'] is None
    assert all(u['metrics']['candidate_retained_unproven_at_cutoff'] is False for u in report['units'])

@pytest.mark.parametrize('failure',[{'reject':'maintain'},{'audit_error':True},{'legacy':True}])
def test_refused_capabilities_failed_maintenance_and_unknown_audits_keep_every_sample(failure):
    result=run_experiment(profile(),factories(**failure),engineering_fixture=True)
    assert verify_score(result)['valid']
    assert not result['fairness_audit']['valid']
    assert len(result['units'])==9
    assert all(not u['metrics']['runner_valid'] and u['metrics']['execution_failures']==u['metrics']['planned'] for u in result['units'])
    assert all(u['metrics']['behavioral_contamination_marker'] is None
               for u in result['units'] if u['program']=='question_contamination')


def test_preexisting_revocation_is_not_reported_as_a_response_to_late_damage():
    class PreexistingRevocation(Fixture):
        def learning_audit(self, **kwargs):
            body = super().learning_audit(**kwargs)
            if self.mode != 'no_memory':
                body['counts']['skills'] = 1
                body['skills'] = [{'skill_ref':'C-1','revision_ref':'C-2','status':'revoked',
                    'trial_ref':'X-1','evaluation_ref':'X-2','recommendation_allowed':False}]
            return body
    report = run_experiment(profile(), {mode: lambda mode=mode: PreexistingRevocation(mode) for mode in CONDITIONS},
                            engineering_fixture=True)
    unit = next(u for u in report['units']
                if u['condition']=='ungated' and u['program']=='unannounced_drift')
    assert unit['metrics']['first_late_error_index'] is not None
    assert unit['metrics']['revocation_latency']['right_censored'] is True
    assert unit['metrics']['revocation_latency']['steps'] is None

def test_audit_accepts_incomplete_proposed_skill_but_does_not_promote_it():
    a=Fixture('normal').learning_audit(run_id='r',request_id='a')
    a['counts']['skills']=1
    a['skills']=[{'skill_ref':'C-1','revision_ref':None,'status':'proposed','trial_ref':None,'evaluation_ref':None,'recommendation_allowed':None}]
    check_audit(a,'r','normal')
    a['skills'][0].update(revision_ref='C-2',status='adopted',trial_ref='X-1',evaluation_ref='X-2')
    check_audit(a,'r','normal')
    a['skills'][0]['evaluation_ref']='E-2'
    with pytest.raises(AdapterLifecycleError):check_audit(a,'r','normal')

@pytest.mark.parametrize('mutate',[
    lambda r:r['units'].pop(),
    lambda r:r['units'][0]['run']['probe_results'][0].update(score=0.125),
    lambda r:r['units'][0]['metrics'].update(late_damage_units=999),
    lambda r:r.update(measurement_revision='unrelated'),
    lambda r:r.update(total_cost=0),
])
def test_report_tampering_fails_even_after_recomputing_the_outer_digest(report,mutate):
    bad=copy.deepcopy(report);mutate(bad);bad['evidence_digest']=digest(bad['units'])
    assert not verify_report(bad)['valid']

def test_same_frozen_lock_reuses_paired_business_seeds_and_is_durable_before_reset(tmp_path):
    lockpath=tmp_path/'first.lock.json'
    class LockChecked(Fixture):
        def reset(self,**kwargs):
            assert lockpath.exists(); json.loads(lockpath.read_text()); return super().reset(**kwargs)
    first=run_experiment(profile(),{m:lambda m=m:LockChecked(m) for m in CONDITIONS},engineering_fixture=True,lock_path=lockpath,progress_path=tmp_path/'first.units.jsonl')
    second=run_experiment(profile(),factories(),engineering_fixture=True,frozen_lock=first['experiment_lock'],lock_path=tmp_path/'second.lock.json')
    assert first['experiment_lock']==second['experiment_lock']
    assert [u['run']['agent_seed'] for u in first['units']]==[u['run']['agent_seed'] for u in second['units']]
    assert [u['run']['run_id'] for u in first['units']] != [u['run']['run_id'] for u in second['units']]
    assert len((tmp_path/'first.units.jsonl').read_text().splitlines())==9
    assert verify_score(second)['valid']

def test_oracle_labels_and_audit_snapshots_are_not_sent_to_learner():
    seen=[]
    report=run_experiment(profile(),factories(seen=seen),engineering_fixture=True)
    for op,body in seen:
        text=json.dumps(body)
        assert 'state_digest' not in text and 'world_updates' not in text and 'oracle' not in text
        if op=='act' and not body['continuation']:
            assert 'required' not in body['goal'] and 'forbidden' not in body['goal'] and 'late' not in body['goal']
        if op=='reset': assert body['seed'] not in profile()['seeds']
    assert verify_score(report)['valid']


def test_no_memory_needs_no_native_observer_contract_and_null_recall_budget_is_refused():
    body=descriptor('no_memory')
    body['extensions'][EXTENSION].update(native_task_family=None,workflow_contract_digest=None)
    check_learning_descriptor(body,'no_memory')
    body['extensions'][EXTENSION]['recall_budget']=None
    with pytest.raises(AdapterLifecycleError): check_learning_descriptor(body,'no_memory')
    for mode in ('normal','ungated'):
        body=descriptor(mode)
        body['extensions'][EXTENSION]['workflow_contract_digest']=None
        with pytest.raises(AdapterLifecycleError): check_learning_descriptor(body,mode)


@pytest.mark.parametrize("failure", ["unavailable", "duplicate", "arguments", "turn_limit", "call_limit"])
def test_behavior_failures_preserve_fixed_horizon_and_replay_unfinished_actions(failure):
    class FailingAction(Fixture):
        def act(self, **kwargs):
            if not kwargs['continuation']:
                self.step = 0
            self.step += 1
            name = 'workflow.not_available' if failure == 'unavailable' else 'workflow.prepare'
            return ActStep(type='tool_call', tool=name,
                tool_call_id='duplicate' if failure == 'duplicate' else f'{kwargs["task_id"]}-{self.step}',
                arguments={'unexpected': True} if failure == 'arguments' else {})
    cfg = profile()
    cfg['execution']['max_agent_turns'] = 4
    cfg['execution']['max_tool_calls'] = 2 if failure == 'call_limit' else 4
    cfg['execution']['attempt_budget']['tool_calls'] = cfg['execution']['max_tool_calls']
    report = run_experiment(cfg, {mode: lambda mode=mode: FailingAction(mode) for mode in CONDITIONS}, engineering_fixture=True)
    assert verify_report(report)['valid']
    assert len(report['units']) == 9
    for unit in report['units']:
        assert unit['metrics']['runner_valid']
        assert unit['metrics']['execution_failures'] == 0
        assert unit['metrics']['first_success_rate'] == 0
        actions = [r for r in unit['run']['probe_results'] if r['probe_kind'] == 'skill']
        assert actions and all(r['outcome'] == 'scored' and r['score'] == 0 for r in actions)
        if unit['program'] == 'unannounced_drift' and failure in {'duplicate', 'turn_limit', 'call_limit'}:
            assert unit['metrics']['late_damage_units'] > 0
    bad = copy.deepcopy(report)
    failed = next(r for r in bad['units'][0]['run']['probe_results'] if r['probe_kind'] == 'skill')
    failed['failure_codes'] = ['made_up_failure']
    bad['evidence_digest'] = digest(bad['units'])
    assert not verify_report(bad)['valid']
