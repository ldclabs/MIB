"""Independent semantic mechanisms for the expanded development profile."""
from __future__ import annotations

from datetime import timedelta

from ..worldmodel import Assertion
from .base import ScenarioBuilder
from .interference import other_actors
from .pools import ATTRIBUTES, NAMES
from .programs import (RecallProgram, TemporalProgram, EpistemicProgram, ExperienceProgram,
                       SkillProgram, ProspectiveProgram, ForgettingProgram)
from .procedural import build_workflow


class InterleavedRecallProgram(RecallProgram):
    ID = 'mib.interleaved_recall.v1'
    TITLE = 'Interleaved facts with useful information arriving after maintenance'

    def build(self, b: ScenarioBuilder) -> None:
        count = int(b.parameters.get('fact_count', 8))
        if not 8 <= count <= 4096:
            raise ValueError('fact_count must be between 8 and 4096')
        names = b.rng.sample(NAMES, count) if count <= len(NAMES) else [f'{NAMES[i % len(NAMES)]} {i // len(NAMES) + 1}' for i in range(count)]
        selected = sorted(b.rng.sample(range(count), min(8, count // 2)))
        start = b._clock
        b.interference_hours = 24.0 / count
        for i, name in enumerate(names):
            b._clock = start + timedelta(hours=24.0 * i / count)
            pid = b.actor(name.lower().replace(' ', '-'), name)
            attr = b.rng.choice(['city', 'office', 'access_code'])
            value = b.rng.choice(ATTRIBUTES[attr].values)
            b.say(f'fact-{i}', source=pid, subject=pid, attribute=attr, value=value, minutes=(0, 0))
            if i == count // 2 - 1:
                b.maintenance_window('mw-1', minutes=(0, 0))
            noise_count = b.interference_count // count + int(i < b.interference_count % count)
            b.interfere(subject_id=pid, attribute=attr, exclude_values=set(),
                        other_actors=other_actors(b.rng, set(names)), count=noise_count, prefix=f'noise-{i}')
            if i in selected:
                b.probe(f'p-{i}', asker=pid, query={'op': 'current', 'subject': pid, 'attribute': attr},
                        prompt=b.prompt(attr, 'current', subject_name=name, first_person=True),
                        kind='factual', dimensions=self.DIMENSIONS)
        b.checkpoint()


class BitemporalProgram(TemporalProgram):
    ID = 'mib.bitemporal.v1'
    TITLE = 'Valid-time history viewed before and after a delayed correction'

    def build(self, b: ScenarioBuilder) -> None:
        name = b.rng.choice(NAMES); pid = b.actor(name.lower(), name)
        b.actor('registry', 'Registry', kind='tool')
        values = b.rng.sample(ATTRIBUTES['office'].values, 3)
        records = [(10, 10, values[0], 'state', None), (30, 10, values[1], 'correction', 'record-0'),
                   (40, 35, values[2], 'update', None)]
        public_ids = [f'r-{b.rng.getrandbits(64):016x}' for _ in records]
        for i, (recorded, valid, value, kind, parent) in enumerate(records):
            eid = f'record-{i}'
            payload = {'kind': 'temporal_record', 'record_id': public_ids[i], 'subject': pid, 'attribute': 'office',
                       'value': value, 'recorded_at': recorded, 'valid_from': valid, 'assertion_kind': kind,
                       'supersedes': public_ids[0] if parent else None}
            b.event(eid, stage='past', etype='tool_result', actor='registry', payload=payload,
                    extra={'tool': 'registry.lookup', 'tool_call_id': 'call-' + eid})
            b.model.add(Assertion(eid, recorded, 'registry', pid, 'office', value, kind, True, parent, valid_from=valid))
            b._realization[eid] = {'record_payload': payload}
        b.maintenance_window('mw-1')
        b.interfere(subject_id=pid, attribute='city', exclude_values=set(), other_actors=other_actors(b.rng, {name}))
        b.checkpoint()
        for i, (valid, recorded) in enumerate([(15, 20), (15, 35), (36, 45)]):
            b.probe(f'p-time-{i}', asker=pid, query={'op': 'bitemporal', 'subject': pid, 'attribute': 'office', 'valid_at': valid, 'recorded_at': recorded},
                    prompt=b.phrase('bitemporal', 'At valid time {valid}, using records received by time {recorded}, what was my office?', valid=valid, recorded=recorded),
                    kind='historical', dimensions=self.DIMENSIONS, historical=True)


class AuthorityProgram(EpistemicProgram):
    ID = 'mib.authority.v1'
    TITLE = 'Scoped authority with identical claim wording and randomized source order'

    def build(self, b: ScenarioBuilder) -> None:
        names = b.rng.sample(NAMES, 3)
        pid, owner, other = [b.actor(n.lower(), n) for n in names]
        values = b.rng.sample(ATTRIBUTES['office'].values, 2)
        b.event('authority', stage='past', etype='document', actor=pid,
                content=f'{names[1]} is the decision owner for my office. Other people may report it, but their reports do not override the owner.',
                payload={'kind': 'authority_record', 'subject': pid, 'attribute': 'office', 'source': owner})
        b.model.add(Assertion('authority', b._seq, pid, pid, 'authority.office', owner))
        order = [(owner, values[0]), (other, values[1])]; b.rng.shuffle(order)
        for source, value in order:
            b.say('claim-' + source, source=source, subject=pid, attribute='office', value=value,
                  truth_bearing=source == owner, subject_name=names[0])
        b.maintenance_window('mw-1')
        b.interfere(subject_id=pid, attribute='city', exclude_values=set(), other_actors=other_actors(b.rng, set(names)))
        b.checkpoint()
        b.probe('p-owner', asker=pid, query={'op': 'according_to_authority', 'subject': pid, 'attribute': 'office'},
                prompt=b.phrase('authority', 'According to the decision owner, what is my office?'), kind='audit', dimensions=self.DIMENSIONS)


class RevisedExperienceProgram(ExperienceProgram):
    ID = 'mib.revised_experience.v1'
    TITLE = 'A learned workflow becomes obsolete and must be learned again'

    def build(self, b: ScenarioBuilder) -> None:
        build_workflow(b, transfer=False, revision=True)


class CompositionProgram(SkillProgram):
    ID = 'mib.composed_skill.v1'
    TITLE = 'Compose a remembered ordered recipe with a new transformation'

    def build(self, b: ScenarioBuilder) -> None:
        build_workflow(b, transfer=True, composition=True)


class CancelledCommitmentProgram(ProspectiveProgram):
    ID = 'mib.cancelled_commitment.v1'
    TITLE = 'Cancel one commitment while another stays active, without forgetting the standing authorization'
    CANCELLED = True


class RelearningProgram(ForgettingProgram):
    ID = 'mib.relearning.v1'
    TITLE = 'Fresh authorization after withdrawal permits relearning without restoring obsolete content'

    def build(self, b: ScenarioBuilder) -> None:
        super().build(b)
        original = b.model.assertion('e-forget')
        value = b.rng.choice([v for v in ATTRIBUTES[original.attribute].values if v != original.value])
        b.events.pop()  # Move the checkpoint after new, explicitly authorized information.
        b.event('renew', stage='past', etype='document', actor=original.source,
                content=f'I authorize you to remember a new {ATTRIBUTES[original.attribute].label}. The withdrawn value remains unavailable.')
        b.say('relearn', source=original.source, subject=original.subject, attribute=original.attribute, value=value)
        b.checkpoint()
        b.ablations = [a for a in b.ablations if a['id'] != 'a-swap-withdrawal']
        for p in b.probes:
            if p['id'] in {'p-forgotten', 'p-forgotten-history'}:
                p['kind'] = 'historical' if p['id'].endswith('history') else 'factual'
                b._probe_meta[p['id']]['swap'] = True
                b._probe_meta[p['id']]['historical'] = p['kind'] == 'historical'


EXTENDED_PROGRAM_CLASSES = [InterleavedRecallProgram, BitemporalProgram, AuthorityProgram, RevisedExperienceProgram,
                            CompositionProgram, CancelledCommitmentProgram, RelearningProgram]
