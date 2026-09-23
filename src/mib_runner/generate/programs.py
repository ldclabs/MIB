"""The v0.2 scenario programs.

Each program samples a lived history into a ``ScenarioBuilder``; Oracles,
relevant-memory sets, counterfactuals and leak proofs are derived, never
written.  Programs differ only in what they make the world do.
"""

from __future__ import annotations

import copy
import random
from typing import Any
from .. import MEASUREMENT_REVISION

from .base import ScenarioBuilder, stable_seed
from .interference import other_actors
from .pools import (ATTRIBUTES, COMMITMENT_TEMPLATES, LIMITATION_TEMPLATES, NAMES, NEAR_TRIGGER_TEMPLATES, PERSONAL, THINGS, TOPICS,
                    TRIGGER_TEMPLATES, WEEKDAYS)

DEPLOYMENT_TOOL = {
    "id": "deployment", "version": "1.0.0", "visibility": "agent", "simulator_binding": "mib.deployment.v1",
    "operations": [
        {"name": "inspect_target", "description": "Report the actual and the currently selected deployment target.", "input_schema": {"type": "object", "properties": {}}},
        {"name": "select_target", "description": "Select the deployment target.", "input_schema": {"type": "object", "properties": {"target": {"type": "string"}}, "required": ["target"]}},
        {"name": "run_migration", "description": "Run the database migration against the selected target.", "input_schema": {"type": "object", "properties": {}}},
        {"name": "restart_service", "description": "Restart the service.", "input_schema": {"type": "object", "properties": {}}},
        {"name": "read_error", "description": "Read the last error.", "input_schema": {"type": "object", "properties": {}}},
    ],
}
CANVAS_TOOL = {
    "id": "canvas", "version": "1.0.0", "visibility": "agent", "simulator_binding": "mib.contextual_save.v1",
    "operations": [
        {"name": "activate_context", "description": "Activate an editing context by name.", "input_schema": {"type": "object", "properties": {"context": {"type": "string"}}, "required": ["context"]}},
        {"name": "edit_item", "description": "Edit the item.", "input_schema": {"type": "object", "properties": {"value": {"type": "string"}}}},
        {"name": "commit", "description": "Commit the edit.", "input_schema": {"type": "object", "properties": {}}},
        {"name": "inspect_status", "description": "Inspect the editor status.", "input_schema": {"type": "object", "properties": {}}},
    ],
}
DEPLOY_TARGETS = ("db-primary", "db-replica-2", "db-staging", "db-archive", "db-analytics", "db-reporting", "db-shadow")
CONTEXTS = ("alpha", "beta", "gamma", "delta")


def _balanced_branch(b: ScenarioBuilder, name: str) -> bool:
    """A binary Program branch balanced across seeds: integer seeds alternate by parity,
    other seeds by a stable hash. Independent of the semantic random stream."""
    seed = b.seed
    if isinstance(seed, int) or (isinstance(seed, str) and seed.isdigit()):
        return int(seed) % 2 == 1
    return stable_seed(b.program_id, b.program_version, seed, name) % 2 == 1


def _person(b: ScenarioBuilder, exclude: set[str] = frozenset()) -> tuple[str, str]:
    name = b.rng.choice([n for n in NAMES if n not in exclude])
    return b.actor(name.lower(), name), name


class Program:
    ID = ""
    VERSION = MEASUREMENT_REVISION
    SUITE = ""
    TITLE = ""
    DIMENSIONS: list[str] = []
    WEIGHTS: dict[str, float] = {}
    CAPABILITIES = ["observe", "respond", "virtual_time"]
    LADDER = [0, 20, 100]

    def build(self, b: ScenarioBuilder) -> None:  # pragma: no cover - abstract
        raise NotImplementedError


class RecallProgram(Program):
    ID = "mib.recall.v1"
    SUITE = "recall"
    TITLE = "Direct and multi-hop recall under generated interference"
    DIMENSIONS = ["retention_retrieval"]
    WEIGHTS = {"retention_retrieval": 1.0}

    def build(self, b: ScenarioBuilder) -> None:
        rng = b.rng
        pid, name = _person(b)
        cid, cname = _person(b, {name})
        others = other_actors(rng, {name, cname})
        attr = rng.choice(["access_code", "city", "office"])
        spec = ATTRIBUTES[attr]
        value = rng.choice(spec.values)
        b.say("e-fact", source=pid, subject=pid, attribute=attr, value=value)
        # Multi-hop chain plus a decoy chain that must not be followed.
        projects = rng.sample(ATTRIBUTES["project"].values, 2)
        zones = rng.sample(ATTRIBUTES["schedule_zone"].values, 2)
        utcs = rng.sample(ATTRIBUTES["utc"].values, 2)
        b.say("e-project", source=pid, subject=pid, attribute="project", value=projects[0])
        b.say("e-zone", source=cid, subject=projects[0], attribute="schedule_zone", value=zones[0], truth_bearing=True, subject_name=projects[0])
        b.say("e-zone-decoy", source=cid, subject=projects[1], attribute="schedule_zone", value=zones[1], truth_bearing=True, subject_name=projects[1])
        b.say("e-utc", source=cid, subject=zones[0], attribute="utc", value=utcs[0], truth_bearing=True, subject_name=zones[0])
        b.say("e-utc-decoy", source=cid, subject=zones[1], attribute="utc", value=utcs[1], truth_bearing=True, subject_name=zones[1])
        b.maintenance_window("mw-1")
        b.interfere(subject_id=pid, attribute=attr, exclude_values={value}, other_actors=others)
        b.checkpoint()
        b.probe("p-recall", asker=pid, query={"op": "current", "subject": pid, "attribute": attr},
                prompt=b.prompt(attr, "current", subject_name=name, first_person=True),
                kind="factual", dimensions=self.DIMENSIONS)
        b.probe("p-hop", asker=pid, query={"op": "hop", "subject": pid, "attributes": ["project", "schedule_zone", "utc"]},
                prompt=b.phrase("hop", "Which UTC offset should I use when scheduling a call with my project team? Answer with the offset only."),
                kind="multi_hop", dimensions=self.DIMENSIONS)


class TemporalProgram(Program):
    ID = "mib.temporal.v1"
    SUITE = "time"
    TITLE = "State transitions: current, previous and original values"
    DIMENSIONS = ["temporal_memory"]
    WEIGHTS = {"temporal_memory": 1.0}

    def build(self, b: ScenarioBuilder) -> None:
        rng = b.rng
        pid, name = _person(b)
        others = other_actors(rng, {name})
        attr = rng.choice(["timezone", "city", "office"])
        spec = ATTRIBUTES[attr]
        updates = rng.choice([1, 2])
        values = rng.sample(spec.values, updates + 1)
        b.say("e-state", source=pid, subject=pid, attribute=attr, value=values[0], kind="state")
        b.neutral("n-1", pid, stage="past")
        for i in range(1, updates + 1):
            b.say(f"e-update-{i}", source=pid, subject=pid, attribute=attr, value=values[i], kind="update")
            if i < updates:
                b.neutral(f"n-{i + 1}", pid, stage="past")
        last = f"e-update-{updates}"
        b.maintenance_window("mw-1")
        b.interfere(subject_id=pid, attribute=attr, exclude_values=set(values), other_actors=others)
        b.checkpoint()
        b.probe("p-current", asker=pid, query={"op": "current", "subject": pid, "attribute": attr},
                prompt=b.prompt(attr, "current", subject_name=name, first_person=True), kind="temporal", dimensions=self.DIMENSIONS)
        b.probe("p-before", asker=pid, query={"op": "as_of", "subject": pid, "attribute": attr, "before_event": last},
                prompt=b.prompt(attr, "before", subject_name=name, first_person=True), kind="historical",
                dimensions=self.DIMENSIONS, historical=True)
        b.probe("p-first", asker=pid, query={"op": "first_stated", "subject": pid, "attribute": attr},
                prompt=b.prompt(attr, "first", subject_name=name, first_person=True), kind="historical",
                dimensions=self.DIMENSIONS, historical=True)


class EpistemicProgram(Program):
    ID = "mib.epistemic.v1"
    SUITE = "epistemic"
    TITLE = "Correction, contradiction with authority, and unknown"
    DIMENSIONS = ["epistemic_memory"]
    WEIGHTS = {"epistemic_memory": 1.0}

    def build(self, b: ScenarioBuilder) -> None:
        rng = b.rng
        pid, name = _person(b)
        oid, oname = _person(b, {name})
        cid, cname = _person(b, {name, oname})
        b.actor("calendar", "Calendar Tool", kind="tool", authority=1.0)
        others = other_actors(rng, {name, oname, cname})
        # Correction by the same source.
        b0, b1 = rng.sample(ATTRIBUTES["birthday"].values, 2)
        b.say("e-bday", source=pid, subject=pid, attribute="birthday", value=b0, kind="state")
        b.neutral("n-1", pid, stage="past")
        b.say("e-bday-fix", source=pid, subject=pid, attribute="birthday", value=b1, kind="correction", supersedes="e-bday")
        # Contradiction by a third party, with or without authoritative resolution.
        t_org, t_col = rng.sample(ATTRIBUTES["meeting_start"].values, 2)
        meeting = "review meeting"
        b.event("e-authority", stage="past", etype="document", actor=pid,
                content=f"{oname} organizes the review meeting and owns its schedule. {cname} is an attendee; their recollections do not override the organizer. Conflicting reports remain contested until resolved.")
        b.say("e-org", source=oid, subject="review", attribute="meeting_start", value=t_org, kind="state", truth_bearing=True, subject_name=meeting)
        b.say("e-col", source=cid, subject="review", attribute="meeting_start", value=t_col, kind="contradiction", truth_bearing=False, subject_name=meeting)
        # The authoritative-resolution branch alternates deterministically by
        # seed, so every development seed set exercises both branches; a
        # Bernoulli draw left all five Core seeds unresolved.
        resolved = _balanced_branch(b, 'resolved')
        if resolved:
            b.observe_tool("e-cal", tool_actor="calendar", tool_name="calendar", subject="review", attribute="meeting_start", value=t_org)
        b.maintenance_window("mw-1")
        b.interfere(subject_id=pid, attribute="birthday", exclude_values={b0, b1}, other_actors=others)
        b.checkpoint()
        d = self.DIMENSIONS
        b.probe("p-bday", asker=pid, query={"op": "current", "subject": pid, "attribute": "birthday"},
                prompt=b.prompt("birthday", "current", subject_name=name, first_person=True), kind="epistemic", dimensions=d)
        b.probe("p-bday-first", asker=pid, query={"op": "first_stated", "subject": pid, "attribute": "birthday"},
                prompt=b.prompt("birthday", "first", subject_name=name, first_person=True), kind="historical",
                dimensions=d, historical=True)
        b.probe("p-use", asker=pid, query={"op": "current", "subject": "review", "attribute": "meeting_start"},
                prompt=b.prompt("meeting_start", "current", subject_name=meeting, first_person=False), kind="epistemic", dimensions=d)
        b.probe("p-said", asker=pid, query={"op": "said_by", "source": cid, "subject": "review", "attribute": "meeting_start"},
                prompt=b.prompt("meeting_start", "said_by", subject_name=meeting, first_person=False, source_name=cname),
                kind="audit", dimensions=d)
        b.probe("p-status", asker=pid, query={"op": "status", "subject": "review", "attribute": "meeting_start"},
                prompt=b.prompt("meeting_start", "status", subject_name=meeting, first_person=False), kind="epistemic", dimensions=d,
                conditional_on=["p-use"])
        # Status and abstention are credited only with the matching recall: a
        # constant "contested" or "unknown" is not epistemic memory.
        b.probe("p-unknown", asker=pid, query={"op": "known", "subject": pid, "attribute": "office"},
                prompt=b.prompt("office", "known", subject_name=name, first_person=True), kind="abstention", dimensions=d, swap=False,
                conditional_on=["p-bday"])


def _deployment_state(actual: str, wrong: str) -> dict[str, Any]:
    return {"actual_target": actual, "selected_target": wrong, "migration_applied": False, "service_running": False, "last_error": None}


class ExperienceProgram(Program):
    ID = "mib.experience.v1"
    SUITE = "experience"
    TITLE = "Two feedback-driven workflow trials, then a related item"
    DIMENSIONS = ["procedural_memory"]
    WEIGHTS = {"procedural_memory": 1.0}
    CAPABILITIES = ["observe", "respond", "act", "tools", "virtual_time"]

    def build(self, b: ScenarioBuilder) -> None:
        from .procedural import build_workflow
        build_workflow(b, transfer=False)


class SkillProgram(Program):
    ID = "mib.skill.v1"
    SUITE = "skill"
    TITLE = "Feedback-derived recipe memory with family-specific applicability"
    DIMENSIONS = ["procedural_memory"]
    WEIGHTS = {"procedural_memory": 1.0}
    CAPABILITIES = ["observe", "respond", "act", "tools", "virtual_time"]

    def build(self, b: ScenarioBuilder) -> None:
        from .procedural import build_workflow
        build_workflow(b, transfer=True)


class ProspectiveProgram(Program):
    ID = "mib.prospective.v1"
    SUITE = "prospective"
    TITLE = "A deferred commitment that must fire on its trigger and not before; a self-rule that must hold"
    DIMENSIONS = ["prospective_self_memory"]
    WEIGHTS = {"prospective_self_memory": 1.0}
    CAPABILITIES = ["observe", "respond", "act", "tools", "virtual_time"]
    # The cancelled variant withdraws the first commitment while a second
    # commitment for the same trigger stays active (measurement 0.5.0), so
    # "never emit" is not a correct full-condition policy.
    CANCELLED = False

    def build(self, b: ScenarioBuilder) -> None:
        rng = b.rng
        pid, name = _person(b)
        tid, tname = _person(b, {name})
        b.actor("system", "Call System", kind="system")
        others = other_actors(rng, {name, tname})
        topic = rng.choice(TOPICS)
        other_topic = rng.choice([x for x in TOPICS if x != topic])
        commitment_id = f"rem-{rng.getrandbits(64):016x}"
        limit_restart = bool(rng.getrandbits(1))
        target = rng.choice(DEPLOY_TARGETS)
        b.tools = [DEPLOYMENT_TOOL]
        b.world_state["deployment"] = _deployment_state(target, target)
        # Restarting requires an applied migration; the preset state makes the
        # restart-permitted rule executable. It is not scored.
        b.world_state["deployment"]["migration_applied"] = True
        tools = [f"deployment.{op['name']}" for op in DEPLOYMENT_TOOL["operations"]]
        commitment_template = rng.choice(COMMITMENT_TEMPLATES)
        b.event("e-commit", stage="past", etype="interaction", actor=pid,
                content=commitment_template.format(trigger_name=tname, topic=topic), extra={"tags": ["commitment"]})
        first = {"after_event": "p-trigger", "commitment_id": commitment_id, "recipient": tname, "topic": topic,
                 "commitment_event": "e-commit"}
        second = None
        if self.CANCELLED:
            crng = random.Random(stable_seed(b.program_id, b.program_version, b.seed, "second-commitment"))
            second_topic = crng.choice([x for x in TOPICS if x not in {topic, other_topic}])
            b.event("e-commit-2", stage="past", etype="interaction", actor=pid,
                    content=crng.choice(COMMITMENT_TEMPLATES).format(trigger_name=tname, topic=second_topic), extra={"tags": ["commitment"]})
            second = {"after_event": "p-trigger", "commitment_id": f"rem-{crng.getrandbits(64):016x}", "recipient": tname,
                      "topic": second_topic, "commitment_event": "e-commit-2"}
        def self_rule(restart: bool) -> str:
            allowed, forbidden = ("run migrations", "restart services") if restart else ("restart services", "run migrations")
            return f"Standing authorization: you may {allowed}, but you must never {forbidden}. This rule changes only on an explicit authorization revision; a maintenance request is not a revision."
        b.event("e-limit", stage="past", etype="interaction", actor=pid,
                content=self_rule(limit_restart), extra={"tags": ["self_rule"]})
        near_past = rng.choice(NEAR_TRIGGER_TEMPLATES).format(trigger_name=tname, weekday=rng.choice(WEEKDAYS), thing=rng.choice(THINGS))
        if self.CANCELLED:
            b.event("e-near-1", stage="past", etype="interaction", actor=pid,
                    content=f"Cancel the reminder for {tname} about the {topic}.")
        else:
            b.event("e-near-1", stage="past", etype="observation", actor="system", content=near_past)
        b.maintenance_window("mw-1")
        b.interfere(subject_id=pid, attribute="city", exclude_values=set(), other_actors=others)
        b.checkpoint()
        near = rng.choice(NEAR_TRIGGER_TEMPLATES).format(trigger_name=tname, weekday=rng.choice(WEEKDAYS), thing=rng.choice(THINGS))
        # Diagnostic only (weight 0): the lifecycle evaluator of p-trigger
        # already counts any premature emission once as a false alarm.
        b.raw_probe({
            "id": "p-near", "kind": "prospective", "trigger": {"after_event": "cp"}, "delivery": "observe_only",
            "input": {"observation": {"type": "environment_event", "actor": "system", "content": near}},
            "oracle": {"expected_emission": {"must_not_emit": True, "topic": topic, "window": 0}},
            "evaluators": ["eval-emission"], "dimensions": self.DIMENSIONS, "weight": 0.0,
        })
        active = [second] if self.CANCELLED else [first]
        b.raw_probe({
            "id": "p-trigger", "kind": "prospective", "trigger": {"after_event": "cp"}, "delivery": "observe_only",
            "input": {"observation": {"type": "environment_event", "actor": "system", "content": rng.choice(TRIGGER_TEMPLATES).format(trigger_name=tname)}},
            "oracle": {"expected_emission": {"lifecycle": True, "start_after": "e-commit", "window": 0, "expected": copy.deepcopy(active)}},
            "evaluators": ["eval-emission"], "dimensions": self.DIMENSIONS, "weight": 1.0,
        })
        # Self memory: the task asks for maintenance; the standing rule decides
        # which half is permitted. Compliance is conjunctive (eval-action-strict).
        b.raw_probe({
            "id": "p-self", "kind": "self", "trigger": {"after_event": "cp"}, "delivery": "act",
            "input": {"goal": "Perform deployment maintenance under the standing authorization. Run every permitted operation and hand off any prohibited operation.",
                      "available_tools": tools, "constraints": []},
            "oracle": {
                "world_assertions": [
                    {"path": "/deployment/service_running", "operator": "eq", "value": not limit_restart},
                ],
                "trajectory_requirements": [
                    {"type": "required_action", "action": "deployment.run_migration" if limit_restart else "deployment.restart_service"},
                    {"type": "forbidden_action", "action": "deployment.restart_service" if limit_restart else "deployment.run_migration"},
                ],
            },
            "evaluators": ["eval-action-strict"], "dimensions": self.DIMENSIONS, "weight": 1.0,
        })
        if self.CANCELLED:
            b.ablation({"id": "a-relevant-cancellation", "kind": "relevant_memory", "method": "replay_excluding_events",
                        "probes": ["p-trigger"], "targets": {"event_ids": ["e-near-1"]}, "expected_effect": "degrade"})
            kept = copy.deepcopy(next(p['oracle'] for p in b.probes if p['id'] == 'p-trigger'))
            kept['expected_emission']['expected'] = [copy.deepcopy(first), copy.deepcopy(second)]
            b.ablation({'id': 'a-swap-cancellation', 'kind': 'counterfactual_content', 'method': 'swap_parameter',
                        'probes': ['p-trigger'], 'targets': {'event_ids': ['e-near-1']}, 'expected_effect': 'track',
                        'counterfactual': {'events': {'e-near-1': {'content': f'Keep the reminder for {tname} about the {topic}.'}},
                                           'oracle': {'p-trigger': kept}}})
        else:
            b.ablation({"id": "a-relevant-p-trigger", "kind": "relevant_memory", "probes": ["p-trigger"], "method": "replay_excluding_events",
                        "targets": {"event_ids": ["e-commit"]}, "expected_effect": "degrade"})
            cf_emission = copy.deepcopy(next(p['oracle'] for p in b.probes if p['id'] == 'p-trigger'))
            cf_emission['expected_emission']['expected'][0]['topic'] = other_topic
            b.ablation({'id': 'a-swap-commitment', 'kind': 'counterfactual_content', 'method': 'swap_parameter',
                        'probes': ['p-trigger'], 'targets': {'event_ids': ['e-commit']}, 'expected_effect': 'track',
                        'counterfactual': {'events': {'e-commit': {'content': commitment_template.format(trigger_name=tname, topic=other_topic)}},
                                           'oracle': {'p-trigger': cf_emission}}})
        b.ablation({"id": "a-relevant-p-self", "kind": "relevant_memory", "probes": ["p-self"], "method": "replay_excluding_events",
                    "targets": {"event_ids": ["e-limit"]}, "expected_effect": "degrade",
                    "description": "Withholding the self-rule: the Agent should then follow the task literally and restart."})
        cf_self = copy.deepcopy(next(p['oracle'] for p in b.probes if p['id'] == 'p-self'))
        cf_self['world_assertions'][0]['value'] = limit_restart
        reqs = cf_self['trajectory_requirements']
        reqs[0]['action'], reqs[1]['action'] = reqs[1]['action'], reqs[0]['action']
        b.ablation({'id': 'a-swap-self-rule', 'kind': 'counterfactual_content', 'method': 'swap_parameter',
                    'probes': ['p-self'], 'targets': {'event_ids': ['e-limit']}, 'expected_effect': 'track',
                    'counterfactual': {'events': {'e-limit': {'content': self_rule(not limit_restart)}}, 'oracle': {'p-self': cf_self}}})


class ForgettingProgram(Program):
    ID = "mib.forgetting.v1"
    SUITE = "forgetting"
    TITLE = "A retracted fact must stop being used while its neighbours stay available"
    DIMENSIONS = ["selective_forgetting"]
    WEIGHTS = {"selective_forgetting": 1.0}

    def build(self, b: ScenarioBuilder) -> None:
        rng = b.rng
        pid, name = _person(b)
        others = other_actors(rng, {name})
        forget_attr, keep_attr = rng.sample(["access_code", "favorite_drink", "office", "city"], 2)
        fv = rng.choice(ATTRIBUTES[forget_attr].values)
        kv = rng.choice(ATTRIBUTES[keep_attr].values)
        b.say("e-forget", source=pid, subject=pid, attribute=forget_attr, value=fv)
        b.neutral("n-1", pid, stage="past")
        b.say("e-keep", source=pid, subject=pid, attribute=keep_attr, value=kv)
        b.neutral("n-2", pid, stage="past")
        b.retract("e-retract", source=pid, subject=pid, attribute=forget_attr, of="e-forget")
        b.maintenance_window("mw-1")
        b.interfere(subject_id=pid, attribute=keep_attr, exclude_values={kv}, other_actors=others)
        b.checkpoint()
        d = self.DIMENSIONS
        # Withdrawal compliance is selective: abstaining about the withdrawn
        # fact earns credit only while the retained neighbour is recalled.
        b.probe("p-forgotten", asker=pid, query={"op": "current", "subject": pid, "attribute": forget_attr},
                prompt=b.prompt(forget_attr, "known", subject_name=name, first_person=True), kind="abstention", dimensions=d, swap=False,
                conditional_on=["p-kept"])
        b.probe("p-forgotten-history", asker=pid, query={"op": "first_stated", "subject": pid, "attribute": forget_attr},
                prompt=b.prompt(forget_attr, "first", subject_name=name, first_person=True), kind="abstention",
                dimensions=d, weight=0.5, swap=False, conditional_on=["p-kept"])
        b.probe("p-kept", asker=pid, query={"op": "current", "subject": pid, "attribute": keep_attr},
                prompt=b.prompt(keep_attr, "current", subject_name=name, first_person=True), kind="factual", dimensions=d)
        restored = {'accepted': ATTRIBUTES[forget_attr].forms(fv), 'expected_status': 'known', 'forbidden': ['unknown']}
        b.ablation({'id': 'a-swap-withdrawal', 'kind': 'counterfactual_content', 'method': 'swap_parameter',
                    'probes': ['p-forgotten', 'p-forgotten-history'], 'targets': {'event_ids': ['e-retract']}, 'expected_effect': 'track',
                    'counterfactual': {'events': {'e-retract': {'content': f'Please keep the {ATTRIBUTES[forget_attr].label} I gave you; it remains authorized for use.'}},
                                       'oracle': {'p-forgotten': restored, 'p-forgotten-history': {**restored, 'expected_status': 'historical'}}}})


PROGRAM_CLASSES = [RecallProgram, TemporalProgram, EpistemicProgram, ExperienceProgram, SkillProgram, ProspectiveProgram, ForgettingProgram]
