"""Regenerate public fixture evidence for the current measurement revision.

Run with PYTHONPATH=src. No model endpoint or evaluator-private store is used.
"""
from __future__ import annotations

import json
from pathlib import Path

from mib_runner import MEASUREMENT_REVISION
from mib_runner.agents import (ConsolidatingAgent, NoMemoryAgent, OvergeneralizingAgent, StructuredMemoryAgent, WindowMemoryAgent)
from mib_runner.benchmark import run_generated_pack
from mib_runner.capability import render_capability_card
from mib_runner.generate import PROGRAMS, generate_instance
from mib_runner.report import validate_report, verify_score
from mib_runner.validation import load_json, validate_scenario

ROOT = Path(__file__).resolve().parents[1]


def write_json(path: Path, value) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')


def main() -> None:
    schema = load_json(ROOT / 'schemas/mib-scenario.schema.json')
    report_schema = load_json(ROOT / 'schemas/mib-report.schema.json')
    for program in sorted(PROGRAMS):
        instance = generate_instance(program, 7, rung=1)
        validation = validate_scenario(instance, schema)
        if not validation.valid:
            raise ValueError(validation.errors)
        write_json(ROOT / 'examples/scenario-instances/generated' / (instance['id'] + '.json'), instance)
    runs = [
        ('MIB-Core-0.2-Dev', StructuredMemoryAgent, 'MIB-Core-0.2-Dev', True),
        ('MIB-Core-0.2-Dev', WindowMemoryAgent, 'MIB-Core-0.2-Dev-WindowMemoryAgent', False),
        ('MIB-Core-0.2-Dev', NoMemoryAgent, 'MIB-Core-0.2-Dev-NoMemoryAgent', False),
        ('MIB-Core-0.2-Dev', OvergeneralizingAgent, 'MIB-Core-0.2-Dev-OvergeneralizingAgent', False),
        ('MIB-Core-0.2-Dev-M', ConsolidatingAgent, 'MIB-Core-0.2-Dev-M-ConsolidatingAgent', False),
        ('MIB-Core-0.2-Expanded-Dev', StructuredMemoryAgent, 'MIB-Core-0.2-Expanded-Dev', False),
        ('MIB-Core-0.2-Session-Dev', StructuredMemoryAgent, 'MIB-Core-0.2-Session-Dev', False),
        ('MIB-Core-0.2-Load-Dev', StructuredMemoryAgent, 'MIB-Core-0.2-Load-Dev', False),
    ]
    evidence = []
    for profile_id, agent, stem, full in runs:
        profile = load_json(ROOT / 'profiles' / (profile_id + '.json'))
        report, summary = run_generated_pack(profile=profile, agent_factory=agent, schema=schema,
            repetitions=profile['repetitions'], bootstrap_resamples=profile['statistics']['bootstrap_resamples'])
        validate_report(report, report_schema)
        verified = verify_score(report)
        if not verified['valid']:
            raise ValueError((profile_id, agent.__name__, verified['errors']))
        output = ROOT / 'examples/runs'
        write_json(output / (stem + '.summary.json'), summary)
        (output / (stem + '-Capability-Card.md')).write_text(render_capability_card(report), encoding='utf-8')
        if full:
            write_json(output / (stem + '.report.json'), report)
            write_json(output / (stem + '.verify-score.json'), verified)
        row = {'profile': profile_id, 'agent': agent.__name__, 'score': summary['mib_score'],
               'dependence_eligible': summary['memory_dependence']['eligible'], 'verified': True,
               'instances': summary['instance_count'], 'runs': summary['run_count']}
        evidence.append(row)
        print(json.dumps(row), flush=True)
    result = {'mib': '0.2', 'kind': 'MIBReviewFixtureValidation', 'version': MEASUREMENT_REVISION,
              'empirical': False, 'release_eligible': False, 'results': evidence}
    validate_report(result, load_json(ROOT / 'schemas/mib-review-validation.schema.json'))
    write_json(ROOT / 'examples/validation/v02-review-fixture-validation.json', result)


if __name__ == '__main__':
    main()
