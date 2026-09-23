"""Reproduce measurement-0.4 engineering evidence without a model or private pack."""
from __future__ import annotations
import argparse
import json
from pathlib import Path

from mib_runner import __version__, MEASUREMENT_REVISION
from mib_runner.agents import StructuredMemoryAgent
from mib_runner.benchmark import run_generated_pack
from mib_runner.report import verify_score, validate_report
from mib_runner.same_model_calibration import load_experiment, load_experiment_templates, estimate_experiment
from mib_runner.util import runner_source_digest

ROOT = Path(__file__).resolve().parents[1]


class PrefixMemory(StructuredMemoryAgent):
    NAME = 'Prefix-only adversarial engineering fixture'
    def reset(self, **kwargs):
        self.frozen = False
        return super().reset(**kwargs)
    def maintain(self, **kwargs):
        self.frozen = True
        return super().maintain(**kwargs)
    def observe(self, **kwargs):
        if self.frozen and kwargs['observation'].type == 'user_message':
            return {'accepted': True, 'emissions': []}
        return super().observe(**kwargs)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output-dir', required=True)
    args = p.parse_args()
    output = Path(args.output_dir); output.mkdir(parents=True, exist_ok=True)
    schema = json.loads((ROOT / 'schemas/mib-scenario.schema.json').read_text())
    report_schema = json.loads((ROOT / 'schemas/mib-report.schema.json').read_text())
    results = []
    for name, factory in [('MIB-Core-0.2-Dev', StructuredMemoryAgent), ('MIB-Core-0.2-Dev', PrefixMemory),
                          ('MIB-Core-0.2-Session-Dev', StructuredMemoryAgent),
                          ('MIB-Mechanism-Challenges-0.1-Dev', StructuredMemoryAgent)]:
        profile = json.loads((ROOT / 'profiles' / (name + '.json')).read_text())
        report, summary = run_generated_pack(profile=profile, agent_factory=factory, schema=schema,
            repetitions=profile['repetitions'], bootstrap_resamples=200)
        validate_report(report, report_schema)
        verification = verify_score(report)
        if not verification['valid']:
            raise ValueError(verification['errors'])
        if factory is StructuredMemoryAgent and summary['mib_score'] != 100:
            raise ValueError('complete reference regressed')
        if factory is PrefixMemory and summary['mib_score'] >= 90:
            raise ValueError('prefix shortcut remains effective')
        filename = name + '-' + factory.__name__ + '.report.json'
        (output / filename).write_text(json.dumps(report, indent=2) + '\n')
        row = {'profile': name, 'fixture': factory.__name__, 'score': summary['mib_score'],
               'coverage': summary['coverage'], 'dependence_eligible': summary['memory_dependence']['eligible'],
               'instances': summary['instance_count'], 'runs': summary['run_count'], 'verified': True, 'report_file': filename}
        results.append(row)
        print(json.dumps(row), flush=True)
    cfg, paths = load_experiment(ROOT / 'examples/same-model/same-model-generated.pilot.json')
    evidence = {'implementation': __version__, 'measurement_revision': MEASUREMENT_REVISION,
        'runner_source_digest': runner_source_digest(), 'empirical': False, 'release_eligible': False,
        'results': results, 'pilot_estimate': estimate_experiment(cfg, load_experiment_templates(paths))}
    (output / 'validation.json').write_text(json.dumps(evidence, indent=2) + '\n')


if __name__ == '__main__':
    main()
