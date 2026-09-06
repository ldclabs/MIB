"""Episode-specific workflows: feedback teaches a rule, the next item tests it."""
from __future__ import annotations

import copy
from typing import Any

from .base import ScenarioBuilder
from .interference import other_actors
from .pools import NAMES

WORKFLOW_TOOL = {
    'id': 'workflow', 'version': '1.0.0', 'visibility': 'agent', 'simulator_binding': 'mib.workflow.v1',
    'operations': [{'name': 'submit',
        'description': 'Execute an ordered recipe for the current item. A failed attempt returns corrective feedback. The first attempt and eventual completion are recorded.',
        'input_schema': {'type': 'object', 'additionalProperties': False, 'required': ['recipe'],
                         'properties': {'recipe': {'type': 'array', 'items': {'type': 'string'}, 'maxItems': 8}}}}],
}


def workflow_state(family: str, recipe: list[str]) -> dict[str, Any]:
    return {'family': family, 'recipe': recipe, 'attempts': 0, 'first_recipe': None,
            'first_attempt_correct': False, 'completed': False}


def workflow_oracle(recipe: list[str]) -> dict[str, Any]:
    return {'world_assertions': [
        {'path': '/workflow/first_recipe', 'operator': 'eq', 'value': recipe},
        {'path': '/workflow/completed', 'operator': 'eq', 'value': True},
    ], 'experienced_failure': 'recipe_mismatch'}


def build_workflow(b: ScenarioBuilder, transfer: bool, *, composition: bool = False, revision: bool = False) -> None:
    rng = b.rng
    name = rng.choice(NAMES)
    pid = b.actor(name.lower(), name)
    families = [f'F-{rng.getrandbits(48):012x}' for _ in range(2)]
    recipe = [f'op-{rng.getrandbits(48):012x}' for _ in range(2)]
    alternate = [f'op-{rng.getrandbits(48):012x}' for _ in range(2)]
    other_recipe = [f'op-{rng.getrandbits(48):012x}']
    b.tools = [copy.deepcopy(WORKFLOW_TOOL)]
    # No operation or current request exposes the episode's rule. Feedback is
    # real simulator output, not an evaluator-authored answer injected later.
    b.event('brief', stage='past', etype='document', actor=pid,
            content='Each item family uses a stable recipe across items and versions. Learn from the workflow feedback, recover when necessary, and reuse a recipe only for the family it belongs to. An empty recipe is allowed.')
    def reset(eid: str, family: str, commands: list[str], stage: str = 'past'):
        b.event(eid, stage=stage, etype='world_update', actor=None, visibility='harness',
                extra={'world_updates': [{'op': 'set', 'path': '/workflow', 'value': workflow_state(family, commands)}]})
    def goal(family: str, item: str) -> str:
        suffix = ' Apply the learned recipe in reverse order for this item.' if composition and item == 'held-out' else ''
        return f'Process item {item} of family {family} using workflow.submit.{suffix}'
    reset('w-acquire', families[0], recipe)
    b.task('t-past', actor=pid, goal=goal(families[0], 'practice-1'), tools=['workflow.submit'], oracle=workflow_oracle(recipe))
    reset('w-repeat', families[0], recipe)
    b.task('t-past-2', actor=pid, goal=goal(families[0], 'practice-2'), tools=['workflow.submit'], oracle=workflow_oracle(recipe))
    if revision:
        recipe = [f'op-{rng.getrandbits(48):012x}' for _ in range(2)]
        b.event('revision', stage='past', etype='document', actor=pid,
                content=f'Family {families[0]} has changed its procedure. Learn the revised recipe on the next practice item; the earlier recipe is obsolete.')
        reset('w-revision', families[0], recipe)
        b.task('t-revision', actor=pid, goal=goal(families[0], 'revision-practice'), tools=['workflow.submit'], oracle=workflow_oracle(recipe))
    if transfer:
        reset('w-boundary', families[1], other_recipe)
        b.task('t-boundary', actor=pid, goal=goal(families[1], 'practice-1'), tools=['workflow.submit'], oracle=workflow_oracle(other_recipe))
    b.maintenance_window('mw-1')
    b.interfere(subject_id=pid, attribute='office', exclude_values=set(), other_actors=other_actors(rng, {name}))
    b.checkpoint()
    if transfer:
        reset('w-nonmatch', families[1], other_recipe, 'pre_probe')
        b.raw_probe({'id': 'p-nonmatch', 'kind': 'skill', 'delivery': 'act', 'trigger': {'after_event': 'w-nonmatch'},
            'input': {'goal': goal(families[1], 'held-out'), 'available_tools': ['workflow.submit'], 'constraints': []},
            'oracle': workflow_oracle(other_recipe), 'evaluators': ['eval-world'], 'dimensions': b.dimensions, 'weight': 1})
        b.ablation({'id': 'a-negative-transfer-p-nonmatch', 'kind': 'negative_transfer', 'method': 'replay_excluding_events',
                    'probes': ['p-nonmatch'], 'targets': {'event_ids': ['t-past', 't-past-2']}, 'expected_effect': 'resist'})
    expected = list(reversed(recipe)) if composition else recipe
    cf_expected = list(reversed(alternate)) if composition else alternate
    reset('w-future', families[0], expected, 'pre_probe')
    probe_id = 'p-match' if transfer else 'p-deploy'
    b.raw_probe({'id': probe_id, 'kind': 'skill' if transfer else 'experience', 'delivery': 'act', 'trigger': {'after_event': 'w-future'},
        'input': {'goal': goal(families[0], 'held-out'), 'available_tools': ['workflow.submit'], 'constraints': []},
        'oracle': workflow_oracle(expected), 'evaluators': ['eval-world'], 'dimensions': b.dimensions, 'weight': 1})
    b.ablation({'id': f'a-relevant-{probe_id}', 'kind': 'relevant_memory', 'method': 'replay_excluding_events',
                'probes': [probe_id], 'targets': {'event_ids': ['t-revision'] if revision else ['t-past', 't-past-2']}, 'expected_effect': 'degrade'})
    # A policy twin changes the latent convention and its acquisition feedback
    # together. It is distinct from a content-only intervention; future input,
    # tools, family identity and initial operational state remain paired.
    b.ablation({'id': 'a-policy-twin', 'kind': 'counterfactual_policy', 'method': 'replay_policy_twin',
        'probes': [probe_id], 'targets': {'event_ids': ['w-revision', 'w-future'] if revision else ['w-acquire', 'w-repeat', 'w-future']}, 'expected_effect': 'track',
        'counterfactual': {'events': {}, 'oracle': {probe_id: workflow_oracle(cf_expected)},
            'world_updates': {eid: [{'op': 'set', 'path': '/workflow', 'value': workflow_state(families[0], commands)}]
                              for eid, commands in ([('w-revision', alternate), ('w-future', cf_expected)] if revision else
                                                    [('w-acquire', alternate), ('w-repeat', alternate), ('w-future', cf_expected)])}}})
