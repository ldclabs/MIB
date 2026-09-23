"""Regressions for the third September design review (measurement 0.5.0, folded into the same revision).

Each test pins one review item: the in-task recovery floor, the balanced
epistemic branch, prompt-value leakage, the diagnostics schedule, per-arm memory
pressure and the unbounded reference, enforced session isolation, bounded
transport retries, surface-bank readability, the long-horizon Profile, the
Capability Card's history statement, and the world-model cache.
"""
from __future__ import annotations

import copy
import json
import re
from pathlib import Path

import pytest

from mib_runner.agents import NoMemoryAgent, RecoverOnlyAgent, StructuredMemoryAgent
from mib_runner.benchmark import DIAGNOSTIC_INTERVENTIONS, run_generated_pack, session_isolation_policy
from mib_runner.capability import render_capability_card
from mib_runner.generate import generate_instance
from mib_runner.generate.pools import ATTRIBUTES
from mib_runner.generate.registry import PROGRAMS, generate_pack
from mib_runner.generate.surface import validate_bank
from mib_runner.runner import run_condition, run_scenario
from mib_runner.transports import AgentTransportError
from mib_runner.types import AgentOutput
from mib_runner.worldmodel import Assertion, Source, WorldModel
from paths import BASE as ROOT

SCHEMA = json.loads((ROOT / 'schemas/mib-scenario.schema.json').read_text())
CORE = ['mib.recall.v1', 'mib.temporal.v1', 'mib.epistemic.v1', 'mib.experience.v1', 'mib.skill.v1', 'mib.prospective.v1', 'mib.forgetting.v1']


def profile(name):
    return json.loads((ROOT / 'profiles' / (name + '.json')).read_text())


# ---------------------------------------------------------------- zero-memory floors

def test_in_task_recovery_earns_nothing_on_workflow_probes():
    """A policy that follows the simulator's corrective feedback inside the task, but
    remembers nothing across tasks, completed every workflow and used to score 50."""
    for name in ['MIB-Core-0.2-Dev', 'MIB-Mechanism-Challenges-0.1-Dev']:
        _, summary = run_generated_pack(profile=profile(name), agent_factory=RecoverOnlyAgent, include_ablations=False, seeds=[101, 202])
        assert all(v <= 10 for v in summary['dimensions'].values()), (name, summary['dimensions'])
    inst = generate_instance('mib.experience.v1', 101, rung=1)
    run = run_condition(scenario=inst, agent=RecoverOnlyAgent(), condition='full')
    probe = next(p for p in run['probe_results'] if p['probe_id'] == 'p-deploy')
    checks = probe['evaluator_results'][0]['details']['assertions']
    assert probe['score'] == 0 and [c['passed'] for c in checks] == [False, True]   # completed, but not from memory


def test_workflow_probes_are_conjunctive_everywhere():
    for pid in PROGRAMS:
        inst = generate_instance(pid, 101, rung=0)
        strict = {e['id'] for e in inst['evaluators'] if (e.get('config') or {}).get('require_all')}
        for p in inst['probes']:
            if 'world_assertions' in (p.get('oracle') or {}) and float(p.get('weight', 1)) > 0:
                assert set(p['evaluators']) <= strict, (pid, p['id'], p['evaluators'])


# ---------------------------------------------------------------- generator balance and leakage

def test_epistemic_resolution_branch_is_balanced_in_every_core_seed_set():
    for name in ['MIB-Core-0.2-Dev', 'MIB-Core-0.2-Expanded-Dev', 'MIB-Core-0.2-Pilot-Dev']:
        seeds = profile(name)['instance_seeds']
        resolved = [any(e['id'] == 'e-cal' for e in generate_instance('mib.epistemic.v1', s, rung=0)['timeline']) for s in seeds]
        assert 0 < sum(resolved) < len(resolved), (name, resolved)


ANSWER_WORDS = {'unknown', 'resolved', 'contested'}   # enumerated answer options, not leaked values


@pytest.mark.parametrize('program', sorted(PROGRAMS))
def test_scored_prompts_carry_no_pool_or_oracle_value(program):
    for seed in [101, 202]:
        for rung in [0, 1]:
            inst = generate_instance(program, seed, rung=rung)
            for p in inst['probes']:
                if float(p.get('weight', 1)) <= 0 or p.get('delivery') != 'respond':
                    continue
                text = json.dumps(p['input'], ensure_ascii=False)
                query = p.get('query') or {}
                attribute = query.get('attribute') or (query.get('attributes') or [None])[-1]
                pool = set(ATTRIBUTES[attribute].values) if attribute in ATTRIBUTES else set()
                accepted = set(map(str, (p.get('oracle') or {}).get('accepted', [])))
                hits = [v for v in (pool | accepted) - ANSWER_WORDS
                        if re.search(r'(?<![\w-])' + re.escape(str(v)) + r'(?![\w-])', text)]
                assert not hits, (program, seed, p['id'], hits)


# ---------------------------------------------------------------- schedule and cost

def test_diagnostics_off_keeps_the_headline_and_drops_the_control_runs():
    on = profile('MIB-Core-0.2-Dev')
    off = copy.deepcopy(on)
    off['measurement_regime']['diagnostics'] = 'off'
    seeds = [101, 202, 303, 404, 505]
    _, a = run_generated_pack(profile=on, agent_factory=StructuredMemoryAgent, seeds=seeds, bootstrap_resamples=50)
    _, b = run_generated_pack(profile=off, agent_factory=StructuredMemoryAgent, seeds=seeds, bootstrap_resamples=50)
    assert a['dimensions'] == b['dimensions'] and a['mib_score'] == b['mib_score']
    assert a['memory_dependence']['eligible'] is b['memory_dependence']['eligible'] is True
    assert a['memory_dependence']['content_following_effect'] == b['memory_dependence']['content_following_effect']
    assert a['run_count'] == 377 and b['run_count'] == 182   # 105 full + 77 twins; each resolved epistemic seed adds one control and one twin
    assert DIAGNOSTIC_INTERVENTIONS == {'relevant_memory', 'irrelevant_memory', 'harmful_memory', 'no_maintenance', 'negative_transfer'}


def test_horizon_profile_puts_history_beyond_a_transcript_reading():
    horizon = profile('MIB-Core-0.2-Horizon-Dev')
    assert horizon['ladder'] == [100, 2000, 10000] and horizon['canonical_rung'] == 1
    assert horizon['measurement_regime']['diagnostics'] == 'off'
    inst = generate_instance('mib.recall.v1', 101, rung=1, ladder=horizon['ladder'])
    assert inst['instantiation']['visible_history_chars'] > 60_000
    # The same seed's semantic content does not depend on the ladder length (forbidden sets may grow with mentions).
    short = generate_instance('mib.recall.v1', 101, rung=1)
    assert [p['oracle']['accepted'] for p in short['probes']] == [p['oracle']['accepted'] for p in inst['probes']]


# ---------------------------------------------------------------- same-model harness

def test_memory_pressure_requires_the_budget_to_bind_in_every_arm():
    from mib_runner.same_model_calibration import (estimate_experiment, load_experiment, load_experiment_templates,
                                                   require_memory_pressure)
    cfg, paths = load_experiment(ROOT / 'examples/same-model/same-model-generated.pilot.json')
    templates = load_experiment_templates(paths)
    pressure = estimate_experiment(cfg, templates)['memory_pressure']
    assert all(row['budget_binds'] for row in pressure['arms'].values()), pressure['arms']
    assert pressure['arms']['B2']['selection_records'] == 30 and pressure['arms']['B1']['selection_records'] is None
    require_memory_pressure(cfg, pressure)
    narrow = copy.deepcopy(cfg)
    narrow['agent']['retrieval_top_k'] = 4       # about 550 rendered characters of a 3,500 budget
    weak = estimate_experiment(narrow, templates)['memory_pressure']
    assert weak['arms']['B2']['budget_binds'] is False and weak['arms']['B2']['median_ratio'] >= 4
    with pytest.raises(ValueError, match='selection capacity'):
        require_memory_pressure(narrow, weak)
    assert cfg['calibration']['additional_baselines'] == {'unbounded_reference': True, 'oracle_reference': True}


def test_bounded_b1_gates_use_the_unbounded_reference(tmp_path):
    from mib_runner.same_model_calibration import run_same_model_calibration
    src = ROOT / 'examples/same-model/same-model-generated.stub.json'
    cfg = json.loads(src.read_text())
    for key in ['pack', 'scenario_schema', 'profile']:
        cfg[key] = str((src.parent / cfg[key]).resolve())
    for key in ['system_prompt', 'reasoning_policy']:
        cfg['agent'][key] = str((src.parent / cfg['agent'][key]).resolve())
    cfg['agent']['memory_char_limits'] = {'B0': 400, 'B1': 400, 'B2': 400, 'B3': 400}
    cfg['calibration']['instance_seeds'] = [101]
    cfg['calibration']['causal_instance_seeds'] = [101]
    cfg['calibration']['additional_baselines'] = {'unbounded_reference': True}
    path = tmp_path / 'bounded.json'
    path.write_text(json.dumps(cfg))
    report = run_same_model_calibration(path)
    reference = report['additional_baselines']['unbounded_reference']
    assert reference['enters_release_gate'] is True and reference['templates']
    by_id = {row['template_id']: row['score'] for row in reference['templates']}
    for card in report['calibration']['templates']:
        assert card['metrics']['full_context'] == by_id[card['template_id']]
        assert card['metrics']['bounded_history'] is not None
        assert card['metrics']['memory_discriminativeness_index'] == pytest.approx(by_id[card['template_id']] - card['metrics']['no_memory'])
    assert 'full_context_reference_not_truncated' in report['fairness_audit']['checks']
    # Without the reference a bounded B1 cannot stand in for full context.
    cfg['calibration']['additional_baselines'] = {}
    path.write_text(json.dumps(cfg))
    report = run_same_model_calibration(path)
    assert all(c['metrics']['full_context'] is None and c['gate_status']['full_context'] == 'unassessable' for c in report['calibration']['templates'])
    assert report['fairness_audit']['checks']['full_context_reference_not_truncated'] is False


# ---------------------------------------------------------------- session isolation

class ForgetfulAgent(StructuredMemoryAgent):
    """Keeps everything in process memory and hands nothing across the boundary."""
    def session_boundary(self, **kwargs):
        super().session_boundary(**kwargs)
        return {'accepted': True}


class BrokenRestoreAgent(StructuredMemoryAgent):
    def restore(self, **kwargs):
        return {'accepted': False}


def test_persisted_state_isolation_is_enforced_by_the_runner():
    session = profile('MIB-Core-0.2-Session-Dev')
    assert session_isolation_policy(session) == 'persisted_state'
    inst = generate_instance('mib.recall.v1', 101, rung=1, session_boundary=True)
    assert any(e['type'] == 'session_boundary' for e in inst['timeline'])
    kept = run_condition(scenario=inst, agent=StructuredMemoryAgent(), condition='full', agent_factory=StructuredMemoryAgent,
                         session_isolation='persisted_state')
    assert kept['scenario_score'] == 1 and kept['session_isolation']['mode'] == 'persisted_state'
    assert kept['session_isolation']['boundaries'] >= 1 and kept['session_isolation']['persisted_bytes'] > 0
    lost = run_condition(scenario=inst, agent=ForgetfulAgent(), condition='full', agent_factory=ForgetfulAgent, session_isolation='persisted_state')
    assert lost['scenario_score'] < 1 and lost['session_isolation']['persisted_bytes'] == 0
    acknowledged = run_condition(scenario=inst, agent=ForgetfulAgent(), condition='full', agent_factory=ForgetfulAgent)
    assert acknowledged['scenario_score'] == 1 and acknowledged['session_isolation']['mode'] == 'acknowledged'
    broken = run_condition(scenario=inst, agent=BrokenRestoreAgent(), condition='full', agent_factory=BrokenRestoreAgent,
                           session_isolation='persisted_state')
    assert broken['validity']['runner_valid'] is False
    with pytest.raises(Exception, match='requires an Agent factory'):
        run_condition(scenario=inst, agent=StructuredMemoryAgent(), condition='full', session_isolation='persisted_state')


def test_session_profile_reports_persisted_state_on_the_card():
    session = profile('MIB-Core-0.2-Session-Dev')
    report, summary = run_generated_pack(profile=session, agent_factory=StructuredMemoryAgent, seeds=[101], include_ablations=False)
    assert summary['mib_score'] == 100
    rows = [i for i in report['aggregates']['scenario_instances'] if i.get('session_isolation')]
    assert rows and all(i['session_isolation']['mode'] == 'persisted_state' and i['session_isolation']['persisted_bytes'] > 0 for i in rows)
    card = render_capability_card(report)
    assert 'Session isolation: persisted_state' in card and 'Visible history at the capability rung' in card
    _, none = run_generated_pack(profile=session, agent_factory=NoMemoryAgent, seeds=[101], include_ablations=False)
    assert none['mib_score'] == 0


# ---------------------------------------------------------------- transport retries

class FlakyAgent(StructuredMemoryAgent):
    failures = 1
    def observe(self, **kwargs):
        if self.failures:
            self.failures -= 1
            raise AgentTransportError('connection reset')
        return super().observe(**kwargs)


def test_transport_faults_are_retried_once_and_recorded():
    inst = generate_instance('mib.recall.v1', 101, rung=0)
    run = run_condition(scenario=inst, agent=FlakyAgent(), condition='full')
    assert run['validity']['runner_valid'] is True and run['scenario_score'] == 1
    assert run['extensions']['mib.runner.operation_usage']['observe']['transport_retries'] == 1
    assert any('transport retry 1 for observe' in w for w in run['warnings'])
    persistent = FlakyAgent(); persistent.failures = 3
    run = run_condition(scenario=inst, agent=persistent, condition='full', transport_retries=1)
    assert run['validity']['runner_valid'] is False
    unretried = FlakyAgent()
    run = run_condition(scenario=inst, agent=unretried, condition='full', transport_retries=0)
    assert run['validity']['runner_valid'] is False


# ---------------------------------------------------------------- surface bank readability

def test_surface_bank_must_keep_the_world_readable():
    from test_design_review_20260923b import PRIVATE_BANK
    validate_bank(PRIVATE_BANK)
    hidden = copy.deepcopy(PRIVATE_BANK)
    hidden['templates']['state.first'] = ['Please note the {label} on my file.']
    with pytest.raises(ValueError, match='does not carry the value'):
        validate_bank(hidden)
    with pytest.raises(ValueError, match='does not carry the value'):
        generate_instance('mib.recall.v1', 101, rung=0, surface_bank=hidden)
    mute = copy.deepcopy(PRIVATE_BANK)
    mute['prompts']['known'] = 'Tell me {subject_poss} {label}.'
    with pytest.raises(ValueError, match="abstention word"):
        validate_bank(mute)
    with pytest.raises(ValueError, match='unknown template key'):
        validate_bank({'templates': {'rumour.first': ['{label} {value}']}})
    with pytest.raises(ValueError, match='unsupported slot'):
        validate_bank({'prompts': {'current': 'What is {subject_poss} {label} on {planet}?'}})


# ---------------------------------------------------------------- world-model cache

def test_world_model_live_cache_follows_mutations():
    model = WorldModel()
    model.add_source(Source(id='a', authority=0.5))
    model.add(Assertion(event_id='e1', seq=1, source='a', subject='a', attribute='office', value='4B', kind='state'))
    assert [a.event_id for a in model._live()] == ['e1']
    model.add(Assertion(event_id='e2', seq=2, source='a', subject='a', attribute='office', value=None, kind='retraction', supersedes='e1'))
    assert model._live() == [] and model.retracted_values('a', 'office') == ['4B']
    assert [a.event_id for a in model._live(exclude={'e2'})] == ['e1']
    twin = model.with_value('e1', '7C')
    assert twin.retracted_values('a', 'office') == ['7C'] and model.retracted_values('a', 'office') == ['4B']
    model.assertions = [a for a in model.assertions if a.kind != 'retraction']
    model.invalidate()
    assert [a.event_id for a in model._live()] == ['e1']
