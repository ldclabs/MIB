#!/usr/bin/env python3
"""Public no-model CI entry point. Uses existing MIB evaluators, not a new score."""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from mib_runner.agents.product import ProductMemoryFixture
from mib_runner.benchmark import run_generated_pack
from mib_runner.generate import generate_instance
from mib_runner.report import build_basic_report,verify_score,validate_report
from mib_runner.runner import run_scenario
from mib_runner.validation import load_json

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir',required=True)
    args=parser.parse_args(argv)
    out=Path(args.output_dir);out.mkdir(parents=True,exist_ok=True)
    profile=load_json(ROOT/'profiles/MIB-Brain-Product-Regression-0.1-Dev.json')
    expected={'mib.product_'+name+'.v1' for name in ('style','budget','correction','reversal','boundary','travel','discount','usage')}
    actual=[entry['id'] for entry in profile['programs']]
    if len(actual)!=len(expected) or set(actual)!=expected or profile['instance_seeds']!=[101,202] or profile['ladder']!=[0,20] or profile['repetitions']!=1:
        raise ValueError('public product regression coverage/seed/rung contract changed')
    schema=load_json(ROOT/'schemas/mib-scenario.schema.json')
    report_schema=load_json(ROOT/'schemas/mib-report.schema.json')
    report,summary=run_generated_pack(profile=profile,schema=schema,agent_factory=ProductMemoryFixture,
        seeds=profile['instance_seeds'],repetitions=profile['repetitions'],include_ablations=True,bootstrap_resamples=0)
    validate_report(report,report_schema)
    verification=verify_score(report)
    full=[r for r in report['results']['runs'] if r['condition']=='full']
    positive=bool(full) and all(r['status']=='succeeded' and r['scenario_score']==1.0 for r in full)
    # A product fixture and today's Bot advertise no spontaneous emissions.
    # Requesting that capability must be an explicit unsupported execution.
    scenario=generate_instance('mib.prospective.v1',101,rung=0)
    rejected=run_scenario(scenario=scenario,agent_factory=ProductMemoryFixture,include_ablations=False)
    refusal=build_basic_report(runs=rejected,scenario=scenario,agent_descriptor=ProductMemoryFixture().describe())
    refused=all(r['status']=='invalid' and all(p['outcome']=='execution_failure' for p in r['probe_results'])
        and 'spontaneous_emissions' in r['adapter_contract']['required_capabilities'] for r in rejected)
    validate_report(refusal,report_schema)
    refusal_verification=verify_score(refusal)
    checks={'kind':'BrainProductRegressionCheck','version':'0.1.0','no_model':True,
        'product_behavior_evaluated_on_Brain':False,'learning':'not_evaluated','passed':positive and refused and verification['valid'] and refusal_verification['valid'],
        'full_runs':len(full),'runs':len(report['results']['runs']),'profile':profile['id'],
        'positive_fixture':positive,'unsupported_emissions_refused':refused,
        'score_verification':verification,'refusal_verification':refusal_verification}
    for name,value in [('brain-product-regression.report.json',report),('brain-product-regression.summary.json',summary),
        ('prospective-refusal.report.json',refusal),('checks.json',checks)]:
        (out/name).write_text(json.dumps(value,ensure_ascii=False,separators=(',',':'))+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in checks.items() if k not in {"score_verification","refusal_verification"}},indent=2))
    return 0 if checks['passed'] else 1

if __name__=='__main__':raise SystemExit(main())
