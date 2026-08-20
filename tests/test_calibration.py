from __future__ import annotations

import json

import jsonschema
import pytest

from mib_runner.calibration import calibrate_pack, load_private_templates
from mib_runner.calibration_baselines import (
    FullContextBaselineAgent,
    NoMemoryBaselineAgent,
    RetrievalBaselineAgent,
    StructuredMemoryBaselineAgent,
)
from mib_runner.materialize import materialize
from mib_runner.runner import run_scenario
from mib_runner.validation import load_json

from paths import EXAMPLES, OFFICIAL_PACK, PROFILES, SCENARIO_SCHEMA_PATH, SCHEMAS

OFFICIAL = OFFICIAL_PACK
SCHEMA = load_json(SCENARIO_SCHEMA_PATH)
PROFILE = load_json(PROFILES / 'MIB-Core-0.1.json')

# The official Hidden Eval / Holdout bodies are evaluator-only and are not
# shipped in this repository.  Point MIB_OFFICIAL_PACK at the private pack to
# run calibration locally.
pytestmark = pytest.mark.skipif(
    not (OFFICIAL / 'templates').is_dir(),
    reason=f'official private pack not available at {OFFICIAL}',
)


def _template(tid: str):
    p = next((OFFICIAL / 'templates').rglob(tid + '.json'))
    return json.loads(p.read_text())


def _score(tid: str, factory):
    s = materialize(_template(tid), 101)
    return run_scenario(scenario=s, agent_factory=factory, include_ablations=False, repetition=0, agent_seed='test')[0]['scenario_score']


def test_b0_vs_b1_memory_dependence():
    assert _score('MIB-RET-005', NoMemoryBaselineAgent) == 0.0
    assert _score('MIB-RET-005', FullContextBaselineAgent) == 1.0


def test_structured_beats_simple_retrieval_on_identity_holdout():
    assert _score('MIB-RET-010', RetrievalBaselineAgent) == 0.0
    assert _score('MIB-RET-010', StructuredMemoryBaselineAgent) == 1.0


def test_calibration_detects_no_memory_leakage():
    templates = [_template('MIB-CAUSAL-005'), _template('MIB-RET-005')]
    report = calibrate_pack(
        templates=templates,
        schema=SCHEMA,
        profile={**PROFILE, 'required_templates': [t['id'] for t in templates]},
        seeds=[101], repetitions=1, bootstrap_resamples=20,
        causal_seeds=[101], causal_repetitions=1,
    )
    cards = {x['template_id']: x for x in report['templates']}
    assert cards['MIB-CAUSAL-005']['metrics']['no_memory'] <= 0.60
    assert cards['MIB-CAUSAL-005']['recommendation'] == 'provisional_pass'
    assert cards['MIB-RET-005']['recommendation'] == 'provisional_pass'


def test_reference_report_validates_schema():
    report = json.loads((EXAMPLES / 'calibration' / 'MIB-v0.1-reference-calibration.json').read_text())
    schema = json.loads((SCHEMAS / 'mib-calibration-report.schema.json').read_text())
    jsonschema.Draft202012Validator(schema).validate(report)
    assert report['summary']['template_count'] == 36
    assert report['release_calibration_eligible'] is False
