"""Regressions for the second September 23 design review (measurement 0.5.0).

Expectations are stated independently of the generator where possible: role
vocabulary, zero-memory floors, gate power under a known data-generating
process, reminder contracts written from the Adapter documentation, and
surface-invariant Oracles.
"""
import copy
import json
import random
import re
import subprocess
import sys
from pathlib import Path

import pytest

from mib_runner.agents import GrammarOnlyAgent, NoMemoryAgent, RecoverOnlyAgent, StructuredMemoryAgent
from mib_runner.agents.v2 import _COMMITMENT
from mib_runner.benchmark import run_generated_pack
from mib_runner.capability import composite_sensitivity, render_capability_card
from mib_runner.dependence import CFE_METRIC, joint_dependence
from mib_runner.evaluator import evaluate_emission, evaluate_probe
from mib_runner.generate import generate_instance
from mib_runner.generate.base import GenerationError, ScenarioBuilder
from mib_runner.generate.registry import PROGRAMS
from mib_runner.report import verify_score
from mib_runner.runner import run_condition, run_scenario
from mib_runner.types import AgentOutput
from mib_runner.validation import validate_scenario

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = json.loads((ROOT / 'schemas/mib-scenario.schema.json').read_text())
CORE = [p for p in PROGRAMS if not p.startswith('mib.product')]


def profile(name):
    return json.loads((ROOT / 'profiles' / f'{name}.json').read_text())


def visible_strings(scenario):
    for event in scenario['timeline']:
        if event.get('visibility') not in {'agent', 'both'}:
            continue
        yield str(event.get('content') or '')
        if event.get('payload') is not None:
            yield json.dumps(event['payload'])
        yield str((event.get('task') or {}).get('goal') or '')
    for probe in scenario['probes']:
        data = probe.get('input') or {}
        yield str(data.get('content') or data.get('goal') or '')
        yield json.dumps(data.get('observation') or {})


ROLE_WORDS = re.compile(r'\b(held[- ]?out|practice|probe|distractor|oracle|placebo|test item|evaluation item|relevant)\b', re.I)


@pytest.mark.parametrize('program', sorted(PROGRAMS))
def test_participant_visible_text_names_no_test_role(program):
    for seed in (101, 202):
        for rung in range(3):
            hits = [s for s in visible_strings(generate_instance(program, seed, rung=rung)) if ROLE_WORDS.search(s)]
            assert not hits, hits[:3]


@pytest.mark.parametrize('name', ['MIB-Core-0.2-Dev', 'MIB-Core-0.2-Expanded-Dev'])
@pytest.mark.parametrize('agent', [GrammarOnlyAgent, NoMemoryAgent, RecoverOnlyAgent])
def test_zero_memory_policies_earn_no_structural_floor(name, agent):
    report, summary = run_generated_pack(profile=profile(name), agent_factory=agent, include_ablations=False)
    assert summary['dimensions'] and all(score <= 10 for score in summary['dimensions'].values()), summary['dimensions']
    _, full = run_generated_pack(profile=profile(name), agent_factory=StructuredMemoryAgent, seeds=[101], include_ablations=False)
    assert full['mib_score'] == 100


def synthetic_instances(rng, n, dims, follow_twin, follow_full, k=1):
    rows = []
    for d in dims:
        for _ in range(n):
            twin = sum(rng.random() < follow_twin for _ in range(k))
            full = sum(rng.random() < follow_full for _ in range(k))
            rows.append({'template_id': d, 'joint_dependence_evidence': [{
                'dimension': d, 'total_n': k, 'valid_n': k, 'successes': 0, 'joint_score': 0.0,
                'twin_follow_n': twin, 'full_follow_n': full, CFE_METRIC: (twin - full) / k}]})
    return rows


def test_content_following_gate_has_power_at_the_default_sample_and_rejects_the_null():
    policy = profile('MIB-Core-0.2-Dev')
    dims = list(policy['dimensions'])
    policy['memory_dependence']['bootstrap_resamples'] = 400
    def pass_rate(twin, full, trials=60):
        rng = random.Random(7)
        passes = 0
        for t in range(trials):
            policy['memory_dependence']['bootstrap_seed'] = f'power-{t}'
            instances = synthetic_instances(rng, 5, dims, twin, full)  # one opportunity per Instance: worst case
            passes += joint_dependence(instances, policy, field=CFE_METRIC, metric=CFE_METRIC)['eligible'] is True
        return passes / trials
    assert pass_rate(0.9, 0.0) >= 0.8
    assert pass_rate(1 / 7, 1 / 7) <= 0.05      # guessing from the public value pool
    assert pass_rate(0.0, 0.0) == 0             # constant answers or no memory


def test_content_following_gate_end_to_end():
    policy = profile('MIB-Core-0.2-Dev')
    report, summary = run_generated_pack(profile=policy, agent_factory=StructuredMemoryAgent)
    dep = summary['memory_dependence']
    assert dep['metric'] == CFE_METRIC and dep['eligible'] is True and dep[CFE_METRIC] == 1
    assert verify_score(report)['valid']
    tampered = copy.deepcopy(report)
    tampered['memory_dependence'][CFE_METRIC] = 0.5
    assert not verify_score(tampered)['valid']
    _, blind = run_generated_pack(profile=policy, agent_factory=GrammarOnlyAgent)
    assert blind['memory_dependence']['eligible'] is False
    assert blind['memory_dependence'][CFE_METRIC] == 0


class StructuredReminderAgent(StructuredMemoryAgent):
    """Emits payload-only reminders that reference the commitment observation it saw."""
    wrong_reference = False

    def _emissions_for(self, observation):
        out = []
        for emission in super()._emissions_for(observation):
            name, topic = re.fullmatch(r'Reminder: ask (.+) about the (.+)\.', emission['content']).groups()
            source = [o for o in self._memory() if (m := _COMMITMENT.match((o.content or '').strip()))
                      and m.group('name') == name and m.group('topic') == topic][-1]
            ref = observation.observation_id if self.wrong_reference else source.observation_id
            out.append({'type': 'reminder', 'payload': {'recipient': name, 'topic': topic, 'commitment_ref': ref}})
        return out


class WrongReferenceAgent(StructuredReminderAgent):
    wrong_reference = True


@pytest.mark.parametrize('program', ['mib.prospective.v1', 'mib.cancelled_commitment.v1', 'mib.commitment_lifecycle.v1'])
def test_reminders_follow_the_documented_contract(program):
    scenario = generate_instance(program, 101, rung=1)
    trigger = lambda agent: next(p for p in run_condition(scenario=scenario, agent=agent())['probe_results'] if p['probe_id'] == 'p-trigger')
    assert trigger(StructuredMemoryAgent)['score'] == 1      # canonical text from the Adapter document
    assert trigger(StructuredReminderAgent)['score'] == 1    # payload with a visible commitment reference
    assert trigger(WrongReferenceAgent)['score'] == 0


def test_a_premature_reminder_is_penalized_once():
    item = {'after_event': 'p-trigger', 'commitment_id': 'hidden', 'recipient': 'Bob', 'topic': 'audit findings', 'commitment_event': 'e-commit'}
    oracle = {'expected_emission': {'lifecycle': True, 'start_after': 'e-commit', 'window': 0, 'expected': [item]}}
    log = [{'index': 2, 'emissions': [{'content': 'Reminder: ask Bob about the audit findings.'}]},
           {'index': 3, 'emissions': [{'content': 'Reminder: ask Bob about the audit findings.'}]}]
    config = {'observation_indices': {'e-commit': 1, 'p-trigger': 3}, 'observation_ids': {'e-commit': 'obs_a'}}
    result = evaluate_emission(log, 3, oracle, config)
    assert result['details']['false_alarms'] == 1 and result['score'] == 0
    payload = [{'index': 3, 'emissions': [{'type': 'reminder', 'payload': {'recipient': 'Bob', 'topic': 'audit findings', 'commitment_ref': 'obs_a'}}]}]
    assert evaluate_emission(payload, 3, oracle, config)['score'] == 1
    for scenario in [generate_instance('mib.prospective.v1', 5), generate_instance('mib.commitment_lifecycle.v1', 5)]:
        diagnostics = [p for p in scenario['probes'] if p['id'] in {'p-near', 'p-repeat'}]
        assert diagnostics and all(p['weight'] == 0 for p in diagnostics)


def structured(value, content=None):
    return AgentOutput(type='structured', value={'value': value, 'status': 'known'}, content=content)


def test_whole_output_scan_is_reserved_for_withdrawn_values():
    s = generate_instance('mib.temporal.v1', 101, rung=2)
    emap = {e['id']: e for e in s['evaluators']}
    by = {p['id']: p for p in s['probes']}
    current, previous = by['p-current']['oracle']['accepted'][0], by['p-before']['oracle']['accepted'][0]
    note = f'It changed from {previous} to {current}.'
    assert evaluate_probe(structured(current, note), by['p-current'], emap)[0] == 1
    assert evaluate_probe(structured(previous), by['p-current'], emap)[0] == 0
    f = generate_instance('mib.relearning.v1', 101, rung=1)
    emap = {e['id']: e for e in f['evaluators']}
    probe = next(p for p in f['probes'] if p['id'] == 'p-forgotten')
    withdrawn = probe['oracle']['withdrawn'][0]
    answer = probe['oracle']['accepted'][0]
    assert evaluate_probe(structured(answer), probe, emap)[0] == 1
    assert evaluate_probe(structured(answer, f'Not the old {withdrawn}.'), probe, emap)[0] == 0


class VerboseAgent(StructuredMemoryAgent):
    """Correct answers plus an explanation that names every other pool value."""
    def _answer(self, input_data):
        out = super()._answer(input_data)
        from mib_runner.generate.pools import ATTRIBUTES
        value = str((out.value or {}).get('value'))
        others = sorted({v for spec in ATTRIBUTES.values() for v in spec.values if v != value})
        return AgentOutput(type=out.type, value=out.value, content='Other values I have seen: ' + ', '.join(others))


def test_explanations_do_not_turn_the_retention_curve_into_a_verbosity_curve():
    p = profile('MIB-Core-0.2-Dev')
    p['programs'] = [{'id': 'mib.recall.v1'}, {'id': 'mib.temporal.v1'}, {'id': 'mib.epistemic.v1'}]
    p['dimensions'] = {d: {'weight': 1 / 3} for d in ['retention_retrieval', 'temporal_memory', 'epistemic_memory']}
    _, summary = run_generated_pack(profile=p, agent_factory=VerboseAgent, seeds=[101, 202, 303], include_ablations=False)
    assert all(curve == [1.0, 1.0, 1.0] for curve in summary['retention'].values()), summary['retention']


def test_twins_are_real_changes_and_identical_across_rungs():
    for seed in range(1, 120):
        scenarios = [generate_instance('mib.temporal.v1', seed, rung=r) for r in range(3)]
        by = {p['id']: p['oracle']['accepted'][0] for p in scenarios[0]['probes']}
        swap = next(a for a in scenarios[0]['ablations'] if a['id'] == 'a-swap-p-current')
        new = swap['counterfactual']['oracle']['p-current']['accepted'][0]
        assert new not in {by['p-current'], by['p-before'], by['p-first']}
        for other in scenarios[1:]:
            # The twin value and replaced event are rung-invariant; forbidden
            # sets legitimately grow with interference mentions, as in Full.
            twin = next(a for a in other['ablations'] if a['id'] == 'a-swap-p-current')
            assert twin['counterfactual']['events'] == swap['counterfactual']['events']
            assert twin['counterfactual']['oracle']['p-current']['accepted'] == swap['counterfactual']['oracle']['p-current']['accepted']


class FamilyLookupAgent(StructuredMemoryAgent):
    """Learns a family-to-recipe table and ignores the declared series."""
    def act(self, *, goal, **kwargs):
        return super().act(goal=re.sub(r' in series S-[0-9a-f]+', '', goal) if goal else goal, **kwargs)


def test_series_scoped_procedure_transfers_to_new_families_only_within_scope():
    scenario = generate_instance('mib.skill.v1', 101, rung=1)
    assert {a['id'] for a in scenario['ablations'] if a['kind'] == 'counterfactual_policy'} == {'a-policy-twin', 'a-policy-twin-boundary'}
    runs = run_scenario(scenario=scenario, agent_factory=StructuredMemoryAgent)
    assert runs[0]['scenario_score'] == 1 and all(r['scenario_score'] == 1 for r in runs if r['condition'] == 'counterfactual_content')
    lookup = run_scenario(scenario=scenario, agent_factory=FamilyLookupAgent, include_ablations=False)[0]
    assert all(p['score'] < 1 for p in lookup['probe_results'] if p['probe_id'] in {'p-match', 'p-nonmatch'})


class NoMaintenanceAgent(StructuredMemoryAgent):
    def describe(self):
        d = super().describe()
        d['capabilities']['maintenance'] = False
        return d


def test_interventions_run_only_where_an_aggregate_uses_them():
    p = profile('MIB-Core-0.2-Dev')
    legacy = copy.deepcopy(p)
    legacy['measurement_regime'].pop('intervention_rungs')
    legacy['measurement_regime'].pop('maintenance_control')
    lean_report, lean = run_generated_pack(profile=p, agent_factory=StructuredMemoryAgent, seeds=[101, 202])
    full_report, full = run_generated_pack(profile=legacy, agent_factory=StructuredMemoryAgent, seeds=[101, 202])
    assert lean['run_count'] < 0.5 * full['run_count']
    for key in ['mib_score', 'dimensions', 'causal_metrics', 'memory_dependence', 'retention']:
        assert lean[key] == full[key], key
    assert verify_score(lean_report)['valid']
    _, skipped = run_generated_pack(profile=p, agent_factory=NoMaintenanceAgent, seeds=[101, 202])
    assert skipped['run_count'] == lean['run_count'] - 2 * 7
    assert 'consolidation_benefit' not in skipped['causal_metrics']


def test_world_model_order_invariant_rejects_reordered_history():
    b = ScenarioBuilder(program_id='mib.test.v1', program_version='0.3.0', seed=1, rung=0, interference_count=0,
                        title='t', suite='t', dimensions=['temporal_memory'], dimension_weights={'temporal_memory': 1.0},
                        capabilities=['observe', 'respond'])
    b.actor('ana', 'Ana')
    b.say('e1', source='ana', subject='ana', attribute='city', value='Tokyo')
    b.say('e2', source='ana', subject='ana', attribute='city', value='Lisbon', kind='update')
    b.checkpoint()
    b.probe('p', asker='ana', query={'op': 'current', 'subject': 'ana', 'attribute': 'city'}, prompt='?',
            kind='temporal', dimensions=['temporal_memory'])
    b.events[0], b.events[1] = b.events[1], b.events[0]
    with pytest.raises(GenerationError, match='world-model order'):
        b.finalize()


def test_questioning_control_is_matched_and_not_a_fixed_pool_choice():
    alternatives = set()
    for program in CORE:
        for seed in (101, 202, 303):
            scenario = generate_instance(program, seed)
            by = {a['id']: a['injections'][0]['content'] for a in scenario['ablations'] if a['id'] in {'a-placebo', 'a-questioning'}}
            assert len(by['a-placebo'].split()) == len(by['a-questioning'].split())
            assert 'Perhaps' not in by['a-placebo']
            alternatives.add(by['a-questioning'])
    assert len(alternatives) > len(CORE)


def test_respond_order_is_counterbalanced_by_seed_and_fixed_across_rungs():
    firsts = set()
    for seed in range(1, 25):
        orders = [[p['id'] for p in generate_instance('mib.epistemic.v1', seed, rung=r)['probes']] for r in range(3)]
        assert orders[0] == orders[1] == orders[2]
        firsts.add(orders[0][0])
        skill = [p['id'] for p in generate_instance('mib.skill.v1', seed)['probes']]
        assert skill.index('p-nonmatch') < skill.index('p-match')
        prospective = [p['id'] for p in generate_instance('mib.prospective.v1', seed)['probes']]
        assert prospective.index('p-near') < prospective.index('p-trigger')
    assert len(firsts) > 2


def test_memory_pressure_preflight_rejects_a_budget_that_never_binds():
    from mib_runner.same_model_calibration import (estimate_experiment, load_experiment, load_experiment_templates,
                                                   require_memory_pressure)
    cfg, paths = load_experiment(ROOT / 'examples/same-model/same-model-generated.pilot.json')
    templates = load_experiment_templates(paths)
    pressure = estimate_experiment(cfg, templates)['memory_pressure']
    assert pressure['regime'] == 'budgeted' and all(row['median_ratio'] >= 4 for row in pressure['arms'].values())
    require_memory_pressure(cfg, pressure)
    loose = copy.deepcopy(cfg)
    loose['agent']['memory_char_limits'] = {k: 100000 for k in ['B0', 'B1', 'B2', 'B3']}
    with pytest.raises(ValueError, match='does not bind'):
        require_memory_pressure(loose, estimate_experiment(loose, templates)['memory_pressure'])
    loose['calibration']['purpose'] = 'smoke'
    require_memory_pressure(loose, estimate_experiment(loose, templates)['memory_pressure'])


PRIVATE_BANK = {
    'templates': {
        'state.first': ['Please note that the {label} on my file reads {value}.'],
        'update.first': ['My file now lists {value} as my {label}.'],
        'correction.first': ['Earlier I gave the wrong {label}; the right one is {value}.'],
        'question.first': ['Could my {label} possibly be {value}?'],
        'hypothetical.first': ['Suppose my {label} became {value} someday.'],
        'retraction.first': ['Drop my {label} from your records entirely.'],
    },
    'prompts': {'current': 'Tell me {subject_poss} present {label}. Reply with the value alone.',
                'before': 'Which {label} did {subject_nom} have just before the latest change? Reply with the value alone.',
                'first': 'Which {label} was on file for {subject_poss} record at the very start? Reply with the value alone.',
                'known': "Tell me {subject_poss} {label}. Reply 'unknown' if it was never on file."},
}


@pytest.mark.parametrize('program', ['mib.recall.v1', 'mib.temporal.v1', 'mib.forgetting.v1'])
def test_private_surface_keeps_oracles_and_defeats_the_public_grammar_parser(program):
    public = generate_instance(program, 101, rung=1)
    private = generate_instance(program, 101, rung=1, surface_bank=PRIVATE_BANK)
    assert validate_scenario(private, SCHEMA).valid
    assert [p['oracle'] for p in public['probes']] == [p['oracle'] for p in private['probes']]
    assert private['instantiation']['surface_bank_digest'].startswith('sha256:')
    score = lambda s: run_scenario(scenario=s, agent_factory=StructuredMemoryAgent, include_ablations=False)[0]['scenario_score']
    assert score(public) == 1 and score(private) < 0.5


def test_core_measurement_modules_do_not_import_experimental_families():
    code = ('import sys\n'
            'for m in ["runner","evaluator","scoring","aggregation","dependence","episode","worldmodel","world",'
            '"generate","benchmark","report","capability","validation"]: __import__("mib_runner." + m)\n'
            'print(sorted(m for m in sys.modules if m.startswith(("mib_runner.experimental", "mib_runner.learning"))))')
    out = subprocess.run([sys.executable, '-c', code], capture_output=True, text=True, check=True,
                         env={'PYTHONPATH': str(ROOT / 'src')}).stdout.strip()
    assert out == '[]'


def test_conditional_credit_and_its_validation():
    scenario = generate_instance('mib.forgetting.v1', 101)
    bad = copy.deepcopy(scenario)
    next(p for p in bad['probes'] if p['id'] == 'p-forgotten')['conditional_on'] = ['p-missing']
    assert any('conditional_on' in e for e in validate_scenario(bad, SCHEMA).errors)
    run = run_condition(scenario=scenario, agent=StructuredMemoryAgent())
    row = next(p for p in run['probe_results'] if p['probe_id'] == 'p-forgotten')
    assert row['score'] == 1 and row['conditional_on'] == {'probes': ['p-kept'], 'met': True}


def test_self_rule_compliance_is_conjunctive():
    scenario = generate_instance('mib.prospective.v1', 101)
    probe = next(p for p in scenario['probes'] if p['id'] == 'p-self')
    assert probe['evaluators'] == ['eval-action-strict']
    assert [a['path'] for a in probe['oracle']['world_assertions']] == ['/deployment/service_running']


def test_capability_card_headline_and_composite_sensitivity():
    report, _ = run_generated_pack(profile=profile('MIB-Core-0.2-Dev'), agent_factory=StructuredMemoryAgent, seeds=[101])
    card = render_capability_card(report)
    assert card.index('Capability') < card.index('Memory Dependence') < card.index('Composite MIB Score')
    assert 'Causal Diagnostics (not part of the headline)' in card and 'Equal weights' in card
    rows = [{'score': 100, 'weight': 0.5}, {'score': 0, 'weight': 0.5}]
    assert composite_sensitivity(rows) == {'equal_weight': 50, 'leave_one_out_min': 0, 'leave_one_out_max': 100}
