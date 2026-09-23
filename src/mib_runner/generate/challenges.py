"""Mechanism challenges kept separate from the frozen seven/fourteen Program packs."""
from __future__ import annotations
import copy
from .programs import Program
from .procedural import WORKFLOW_TOOL, workflow_state, workflow_oracle
from .interference import other_actors
from .pools import NAMES, TOPICS

FEATURE_FORMAT = 'mib.feature-recipe/1'


class FeaturePolicyProgram(Program):
    ID = 'mib.feature_policy.v1'
    SUITE = 'skill'
    TITLE = 'Compose feedback-derived feature operations for a previously unseen family'
    DIMENSIONS = ['procedural_memory']
    WEIGHTS = {'procedural_memory': 1.0}
    CAPABILITIES = ['observe', 'respond', 'act', 'tools', 'virtual_time']

    def build(self, b):
        actor = b.actor('operator', 'Operator')
        families = [f'F-{b.rng.getrandbits(48):012x}' for _ in range(4)]
        operations = [f'op-{b.rng.getrandbits(48):012x}' for _ in range(2)]
        alternate = [f'op-{b.rng.getrandbits(48):012x}' for _ in range(2)]
        b.tools = [copy.deepcopy(WORKFLOW_TOOL)]
        b.event('brief', stage='past', etype='document', actor=actor,
            content='Feature flags determine recipes across all families. Each enabled flag contributes its learned operation in flag-index order; disabled flags contribute nothing. Infer each operation from actual workflow feedback. Family names do not change this rule.')
        def setup(index, flags, stage):
            family = families[index]
            b.event(f'features-{index}', stage=stage, etype='interaction', actor=actor,
                payload={'format': FEATURE_FORMAT, 'family': family, 'flags': flags})
            recipe = [op for op, enabled in zip(operations, flags) if enabled]
            b.event(f'world-{index}', stage=stage, etype='world_update', actor=None, visibility='harness',
                extra={'world_updates': [{'op': 'set', 'path': '/workflow', 'value': workflow_state(family, recipe)}]})
            return recipe, f'Process this item of family {family} using workflow.submit and its recorded feature flags.'
        for index, flags in enumerate([[True, False], [False, True]]):
            recipe, goal = setup(index, flags, 'past')
            b.task(f'acquire-{index}', actor=actor, goal=goal, tools=['workflow.submit'], oracle=workflow_oracle(recipe))
        b.maintenance_window('mw-1')
        b.interfere(subject_id=actor, attribute='office', exclude_values=set(), other_actors=other_actors(b.rng, {'Operator'}))
        b.checkpoint()
        # Both scored items need a remembered flag-to-operation mapping on a new
        # family. An all-disabled item would accept the empty first attempt that
        # a policy with no memory submits anyway (measurement 0.5.0).
        for index, flags in [(2, [False, True]), (3, [True, True])]:
            recipe, goal = setup(index, flags, 'pre_probe')
            b.raw_probe({'id': f'p-{index}', 'kind': 'skill', 'delivery': 'act', 'trigger': {'after_event': f'world-{index}'},
                'input': {'goal': goal, 'available_tools': ['workflow.submit'], 'constraints': []},
                'oracle': workflow_oracle(recipe), 'evaluators': ['eval-world-strict'], 'dimensions': self.DIMENSIONS, 'weight': 1})
        b.ablation({'id': 'a-feature-acquisition', 'kind': 'relevant_memory', 'method': 'replay_excluding_events',
            'targets': {'event_ids': ['acquire-0', 'acquire-1']}, 'probes': ['p-3'], 'expected_effect': 'degrade'})
        b.ablation({'id': 'a-feature-policy', 'kind': 'counterfactual_policy', 'method': 'replay_policy_twin',
            'targets': {'event_ids': ['world-0', 'world-1', 'world-2', 'world-3']}, 'probes': ['p-3'], 'expected_effect': 'track',
            'counterfactual': {'events': {}, 'oracle': {'p-3': workflow_oracle(alternate)},
                'world_updates': {f'world-{i}': [{'op': 'set', 'path': '/workflow', 'value': workflow_state(families[i], recipe)}]
                    for i, recipe in [(0, alternate[:1]), (1, alternate[1:]), (2, alternate[1:]), (3, alternate)]}}})


class CommitmentLifecycleProgram(Program):
    ID = 'mib.commitment_lifecycle.v1'
    SUITE = 'prospective'
    TITLE = 'Multiple commitments, cancellation, renewed authorization and repeated triggers'
    DIMENSIONS = ['prospective_self_memory']
    WEIGHTS = {'prospective_self_memory': 1.0}

    def build(self, b):
        owner, target = b.rng.sample(NAMES, 2)
        actor = b.actor(owner.lower(), owner)
        b.actor(target.lower(), target)
        b.actor('system', 'Call System', kind='system')
        topics = b.rng.sample(TOPICS, 2)
        def commitment(eid, topic):
            b.event(eid, stage='past', etype='interaction', actor=actor,
                content=f'When {target} joins the call, remind me to ask about the {topic}.')
        commitment('commit-original', topics[0])
        b.maintenance_window('mw-1')
        b.interfere(subject_id=actor, attribute='office', exclude_values=set(),
                    other_actors=other_actors(b.rng, {owner, target}))
        b.event('cancel', stage='past', etype='interaction', actor=actor,
                content=f'Cancel the reminder for {target} about the {topics[0]}.')
        commitment('commit-other', topics[1])
        commitment('commit-renewed', topics[0])
        b.checkpoint()
        expected = [{'after_event': 'p-trigger', 'commitment_id': f'rem-{b.rng.getrandbits(64):016x}',
                     'recipient': target, 'topic': topic, 'commitment_event': event}
                    for topic, event in zip(topics, ['commit-renewed', 'commit-other'])]
        oracle = {'expected_emission': {'lifecycle': True, 'start_after': 'commit-original', 'window': 0, 'expected': expected}}
        for pid in ['p-trigger', 'p-repeat']:
            b.raw_probe({'id': pid, 'kind': 'prospective', 'delivery': 'observe_only', 'trigger': {'after_event': 'cp'},
                'input': {'observation': {'type': 'environment_event', 'actor': 'system', 'content': f'{target} joined the call.'}},
                'oracle': oracle if pid == 'p-trigger' else {'expected_emission': {'must_not_emit': True, 'topic': target, 'window': 0}},
                # A repeated emission is already a lifecycle false alarm of
                # p-trigger; p-repeat is a zero-weight diagnostic, not a second penalty.
                'evaluators': ['eval-emission'], 'dimensions': self.DIMENSIONS, 'weight': 1 if pid == 'p-trigger' else 0})
        b.ablation({'id': 'a-renewal', 'kind': 'relevant_memory', 'method': 'replay_excluding_events',
            'targets': {'event_ids': ['commit-renewed']}, 'probes': ['p-trigger'], 'expected_effect': 'degrade'})
        twin = copy.deepcopy(oracle)
        twin['expected_emission']['expected'] = [expected[1]]
        b.ablation({'id': 'a-renewal-twin', 'kind': 'counterfactual_content', 'method': 'swap_parameter',
            'targets': {'event_ids': ['commit-renewed']}, 'probes': ['p-trigger'], 'expected_effect': 'track',
            'counterfactual': {'events': {'commit-renewed': {'content': f'The cancellation of the {topics[0]} reminder remains in effect.'}},
                               'oracle': {'p-trigger': twin}}})


CHALLENGE_PROGRAM_CLASSES = [FeaturePolicyProgram, CommitmentLifecycleProgram]
