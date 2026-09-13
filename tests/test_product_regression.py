import copy
import json
import subprocess
import sys
from pathlib import Path
import pytest

from mib_runner.adapter_contract import required_capabilities
from mib_runner.agents.product import ProductMemoryFixture
from mib_runner.generate import generate_instance
from mib_runner.generate.products import PRODUCT_PROGRAM_CLASSES, FACT_FORMAT
from mib_runner.report import verify_score
from mib_runner.runner import run_scenario
from mib_runner.validation import load_json, validate_scenario

ROOT=Path(__file__).resolve().parents[1]

@pytest.mark.parametrize('program',[p.ID for p in PRODUCT_PROGRAM_CLASSES])
def test_public_product_programs_are_valid_and_act_on_memory_not_keywords(program):
    schema=load_json(ROOT/'schemas/mib-scenario.schema.json')
    for rung in (0,1):
        scenario=generate_instance(program,101,rung=rung,session_boundary=True)
        assert validate_scenario(scenario,schema).valid
        assert scenario==generate_instance(program,101,rung=rung,session_boundary=True)
        run=run_scenario(scenario=scenario,agent_factory=ProductMemoryFixture,include_ablations=False)[0]
        assert run['status']=='succeeded' and run['scenario_score']==1.0
        assert all(p['delivery']=='act' and p['evaluators']==['eval-world'] for p in scenario['probes'])
        assert all(p['oracle']['world_assertions'][0]['operator']=='eq' for p in scenario['probes'])
        assert 'SEARCH CONCEPT' not in json.dumps(scenario)

class BadDraft(ProductMemoryFixture):
    def act(self,**kwargs):
        step=super().act(**kwargs)
        if step.tool=='workspace.edit_record' and isinstance(step.arguments.get('value'),dict):
            value=step.arguments['value']
            if 'budget' in value:value['budget']['certainty']='exact'
            if 'origin_airport' in value:value['destination']='Tokyo'
        return step

@pytest.mark.parametrize('program',['mib.product_budget.v1','mib.product_travel.v1'])
def test_correct_keywords_cannot_hide_false_precision_or_invented_destination(program):
    scenario=generate_instance(program,202,rung=0)
    good=run_scenario(scenario=scenario,agent_factory=ProductMemoryFixture,include_ablations=False)[0]
    bad=run_scenario(scenario=scenario,agent_factory=BadDraft,include_ablations=False)[0]
    assert good['scenario_score']==1.0 and bad['scenario_score']==0.0
    assert bad['status']=='succeeded', 'this is a behavioral failure, not unavailable infrastructure'

def test_withholding_actual_product_sources_removes_applicable_content():
    for kind in ('budget','travel','style'):
        scenario=generate_instance('mib.product_'+kind+'.v1',101,rung=1)
        ablation=next(a for a in scenario['ablations'] if a['id']=='a-required-product-history')
        from mib_runner.runner import run_condition
        run=run_condition(scenario=scenario,agent=ProductMemoryFixture(),condition='relevant_memory',ablation=ablation)
        assert run['scenario_score']==0.0
        assert run['extensions']['mib.runner.world_state']['workspace']['value'] is None

def test_counterparty_payload_cannot_impersonate_the_actual_observation_actor():
    scenario=generate_instance('mib.product_boundary.v1',101,rung=0)
    for event in scenario['timeline']:
        if event.get('payload',{}).get('format')==FACT_FORMAT and event['payload']['actor_id']=='alice':
            event['actor']='bob'
    run=run_scenario(scenario=scenario,agent_factory=ProductMemoryFixture,include_ablations=False)[0]
    assert [p['score'] for p in run['probe_results']]==[0.0,1.0]


@pytest.mark.parametrize('program',['mib.product_boundary.v1','mib.product_usage.v1'])
def test_shared_injection_anchor_precedes_every_product_probe(program):
    scenario=generate_instance(program,101,rung=0,session_boundary=True)
    positions={event['id']:index for index,event in enumerate(scenario['timeline'])}
    for ablation in scenario['ablations']:
        if ablation['method']!='replay_with_injections':continue
        anchor=ablation['injections'][0]['at']['after_event']
        assert all(positions[anchor]<positions[p['trigger']['after_event']] for p in scenario['probes'])


def test_expiry_and_repeated_usage_are_behavioral_not_graph_reinforcement_tests():
    discount=generate_instance('mib.product_discount.v1',101,rung=0)
    run=run_scenario(scenario=discount,agent_factory=ProductMemoryFixture,include_ablations=False)[0]
    assert run['extensions']['mib.runner.world_state']['workspace']['value']=={'discount_code':None,'pricing_basis':'current'}
    usage=generate_instance('mib.product_usage.v1',101,rung=0,session_boundary=True)
    run=run_scenario(scenario=usage,agent_factory=ProductMemoryFixture,include_ablations=False)[0]
    assert [p['score'] for p in run['probe_results']]==[1.0,1.0]
    text=json.dumps(usage)
    assert 'MnemonicState' not in text and 'recall_count' not in text and 'confidence' not in text

def test_spontaneous_emissions_are_explicitly_required_and_unsupported_is_not_pass():
    scenario=generate_instance('mib.prospective.v1',101,rung=0)
    assert 'spontaneous_emissions' in required_capabilities(scenario)
    run=run_scenario(scenario=scenario,agent_factory=ProductMemoryFixture,include_ablations=False)[0]
    assert run['status']=='invalid'
    assert all(p['outcome']=='execution_failure' for p in run['probe_results'])
    assert any('spontaneous_emissions' in receipt.get('error','') for receipt in run['adapter_contract']['operations'])

def test_brain_ci_entry_point_is_no_model_and_all_emitted_reports_replay(tmp_path):
    result=subprocess.run([sys.executable,str(ROOT/'scripts/check-brain-product-regression.py'),
        '--output-dir',str(tmp_path)],capture_output=True,text=True)
    assert result.returncode==0,result.stderr+result.stdout
    checks=load_json(tmp_path/'checks.json')
    assert checks['passed'] and checks['no_model']
    assert checks['product_behavior_evaluated_on_Brain'] is False and checks['learning']=='not_evaluated'
    assert checks['full_runs']==32 and checks['runs']==160
    for path in tmp_path.glob('*.report.json'):assert verify_score(load_json(path))['valid']
