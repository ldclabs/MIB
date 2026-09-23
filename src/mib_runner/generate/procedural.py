"""Episode-specific workflows: feedback teaches a rule, the next item tests it."""
from __future__ import annotations

import copy
import random
from typing import Any

from .base import ScenarioBuilder, stable_seed
from .interference import other_actors
from .pools import NAMES

WORKFLOW_TOOL = {
    'id': 'workflow', 'version': '1.0.0', 'visibility': 'agent', 'simulator_binding': 'mib.workflow.v1',
    'operations': [{'name': 'submit',
        'description': 'Execute an ordered recipe for the current item. A failed attempt returns corrective feedback. The first attempt and eventual completion are recorded.',
        'input_schema': {'type': 'object', 'additionalProperties': False, 'required': ['recipe'],
                         'properties': {'recipe': {'type': 'array', 'items': {'type': 'string'}, 'maxItems': 8}}}}],
}


def workflow_state(family: str, recipe: list[str], series: str | None = None) -> dict[str, Any]:
    state = {'family': family, 'recipe': recipe, 'attempts': 0, 'first_recipe': None,
             'first_attempt_correct': False, 'completed': False}
    if series:
        state['series'] = series
    return state


def workflow_oracle(recipe: list[str]) -> dict[str, Any]:
    return {'world_assertions': [
        {'path': '/workflow/first_recipe', 'operator': 'eq', 'value': recipe},
        {'path': '/workflow/completed', 'operator': 'eq', 'value': True},
    ], 'experienced_failure': 'recipe_mismatch'}


def build_workflow(b: ScenarioBuilder, transfer: bool, *, composition: bool = False, revision: bool = False) -> None:
    """Experience: the same family recurs. Procedural applicability (``transfer``):
    a recipe belongs to a visible series, and the future items are *new*
    families, so a family-to-recipe lookup cannot solve them (measurement 0.5.0).

    Item identifiers are opaque; no participant-visible text names an item's
    role as practice or evaluation. Scored workflow Probes are conjunctive
    (``eval-world-strict``): recovering from the simulator's feedback inside
    the Probe's own task earns nothing, only a remembered first recipe does.
    """
    rng = b.rng
    name = rng.choice(NAMES)
    pid = b.actor(name.lower(), name)
    families = [f'F-{rng.getrandbits(48):012x}' for _ in range(2)]
    recipe = [f'op-{rng.getrandbits(48):012x}' for _ in range(2)]
    alternate = [f'op-{rng.getrandbits(48):012x}' for _ in range(2)]
    other_recipe = [f'op-{rng.getrandbits(48):012x}']
    series: list[str | None] = [None, None]
    future_families = [families[0], families[1]]
    other_alternate: list[str] = []
    if transfer:
        srng = random.Random(stable_seed(b.program_id, b.program_version, b.seed, 'series'))
        series = [f'S-{srng.getrandbits(48):012x}' for _ in range(2)]
        future_families = [f'F-{srng.getrandbits(48):012x}' for _ in range(2)]
        other_alternate = [f'op-{srng.getrandbits(48):012x}']
    b.tools = [copy.deepcopy(WORKFLOW_TOOL)]
    # No operation or current request exposes the episode's rule. Feedback is
    # real simulator output, not an evaluator-authored answer injected later.
    if transfer:
        brief = ('Families in the same series share one stable recipe across items and versions. Learn it from the workflow '
                 'feedback, recover when necessary, and reuse a recipe only within the series it belongs to. An empty recipe is allowed.')
    else:
        brief = ('Each item family uses a stable recipe across items and versions. Learn from the workflow feedback, recover '
                 'when necessary, and reuse a recipe only for the family it belongs to. An empty recipe is allowed.')
    b.event('brief', stage='past', etype='document', actor=pid, content=brief)

    def reset(eid: str, family: str, commands: list[str], stage: str = 'past', series_id: str | None = None):
        b.event(eid, stage=stage, etype='world_update', actor=None, visibility='harness',
                extra={'world_updates': [{'op': 'set', 'path': '/workflow', 'value': workflow_state(family, commands, series_id)}]})

    def goal(family: str, role: str, series_id: str | None = None, compose: bool = False) -> str:
        where = f' in series {series_id}' if series_id else ''
        suffix = ' Apply the learned recipe in reverse order for this item.' if compose else ''
        return f'Process item {b.opaque("item", role)} of family {family}{where} using workflow.submit.{suffix}'

    reset('w-acquire', families[0], recipe, series_id=series[0])
    b.task('t-past', actor=pid, goal=goal(families[0], 'acquire-1', series[0]), tools=['workflow.submit'], oracle=workflow_oracle(recipe))
    reset('w-repeat', families[0], recipe, series_id=series[0])
    b.task('t-past-2', actor=pid, goal=goal(families[0], 'acquire-2', series[0]), tools=['workflow.submit'], oracle=workflow_oracle(recipe))
    if revision:
        recipe = [f'op-{rng.getrandbits(48):012x}' for _ in range(2)]
        b.event('revision', stage='past', etype='document', actor=pid,
                content=f'Family {families[0]} has changed its procedure. Learn the revised recipe on the next item; the earlier recipe is obsolete.')
        reset('w-revision', families[0], recipe)
        b.task('t-revision', actor=pid, goal=goal(families[0], 'revision'), tools=['workflow.submit'], oracle=workflow_oracle(recipe))
    if transfer:
        reset('w-boundary', families[1], other_recipe, series_id=series[1])
        b.task('t-boundary', actor=pid, goal=goal(families[1], 'boundary', series[1]), tools=['workflow.submit'], oracle=workflow_oracle(other_recipe))
    b.maintenance_window('mw-1')
    b.interfere(subject_id=pid, attribute='office', exclude_values=set(), other_actors=other_actors(rng, {name}))
    b.checkpoint()
    if transfer:
        reset('w-nonmatch', future_families[1], other_recipe, 'pre_probe', series[1])
        b.raw_probe({'id': 'p-nonmatch', 'kind': 'skill', 'delivery': 'act', 'trigger': {'after_event': 'w-nonmatch'},
            'input': {'goal': goal(future_families[1], 'nonmatch', series[1]), 'available_tools': ['workflow.submit'], 'constraints': []},
            'oracle': workflow_oracle(other_recipe), 'evaluators': ['eval-world-strict'], 'dimensions': b.dimensions, 'weight': 1})
        b.ablation({'id': 'a-negative-transfer-p-nonmatch', 'kind': 'negative_transfer', 'method': 'replay_excluding_events',
                    'probes': ['p-nonmatch'], 'targets': {'event_ids': ['t-past', 't-past-2']}, 'expected_effect': 'resist'})
        # The non-matching series has its own policy twin, so each Instance
        # carries two changed-behavior opportunities for this dimension.
        b.ablation({'id': 'a-policy-twin-boundary', 'kind': 'counterfactual_policy', 'method': 'replay_policy_twin',
            'probes': ['p-nonmatch'], 'targets': {'event_ids': ['w-boundary', 'w-nonmatch']}, 'expected_effect': 'track',
            'counterfactual': {'events': {}, 'oracle': {'p-nonmatch': workflow_oracle(other_alternate)},
                'world_updates': {'w-boundary': [{'op': 'set', 'path': '/workflow', 'value': workflow_state(families[1], other_alternate, series[1])}],
                                  'w-nonmatch': [{'op': 'set', 'path': '/workflow', 'value': workflow_state(future_families[1], other_alternate, series[1])}]}}})
    expected = list(reversed(recipe)) if composition else recipe
    cf_expected = list(reversed(alternate)) if composition else alternate
    reset('w-future', future_families[0], expected, 'pre_probe', series[0])
    probe_id = 'p-match' if transfer else 'p-deploy'
    b.raw_probe({'id': probe_id, 'kind': 'skill' if transfer else 'experience', 'delivery': 'act', 'trigger': {'after_event': 'w-future'},
        'input': {'goal': goal(future_families[0], 'future', series[0], compose=composition), 'available_tools': ['workflow.submit'], 'constraints': []},
        'oracle': workflow_oracle(expected), 'evaluators': ['eval-world-strict'], 'dimensions': b.dimensions, 'weight': 1})
    b.ablation({'id': f'a-relevant-{probe_id}', 'kind': 'relevant_memory', 'method': 'replay_excluding_events',
                'probes': [probe_id], 'targets': {'event_ids': ['t-revision'] if revision else ['t-past', 't-past-2']}, 'expected_effect': 'degrade'})
    # A policy twin changes the latent convention and its acquisition feedback
    # together. It is distinct from a content-only intervention; future input,
    # tools, family identity and initial operational state remain paired.
    updates = ([('w-revision', families[0], alternate), ('w-future', future_families[0], cf_expected)] if revision else
               [('w-acquire', families[0], alternate), ('w-repeat', families[0], alternate), ('w-future', future_families[0], cf_expected)])
    b.ablation({'id': 'a-policy-twin', 'kind': 'counterfactual_policy', 'method': 'replay_policy_twin',
        'probes': [probe_id], 'targets': {'event_ids': [eid for eid, _, _ in updates]}, 'expected_effect': 'track',
        'counterfactual': {'events': {}, 'oracle': {probe_id: workflow_oracle(cf_expected)},
            'world_updates': {eid: [{'op': 'set', 'path': '/workflow', 'value': workflow_state(family, commands, series[0])}]
                              for eid, family, commands in updates}}})
