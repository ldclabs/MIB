"""The v0.2 scenario programs.

Each program samples a lived history into a ``ScenarioBuilder``; Oracles,
relevant-memory sets, counterfactuals and leak proofs are derived, never
written.  Programs differ only in what they make the world do.
"""

from __future__ import annotations

import random
from typing import Any

from .base import ScenarioBuilder, probe_prompt
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


def _person(b: ScenarioBuilder, exclude: set[str] = frozenset()) -> tuple[str, str]:
    name = b.rng.choice([n for n in NAMES if n not in exclude])
    return b.actor(name.lower(), name), name


class Program:
    ID = ""
    VERSION = "0.2.0"
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
                prompt=probe_prompt(attr, "current", subject_name=name, first_person=True),
                kind="factual", dimensions=self.DIMENSIONS)
        b.probe("p-hop", asker=pid, query={"op": "hop", "subject": pid, "attributes": ["project", "schedule_zone", "utc"]},
                prompt="Which UTC offset should I use when scheduling a call with my project team? Answer with the offset only.",
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
                prompt=probe_prompt(attr, "current", subject_name=name, first_person=True), kind="temporal", dimensions=self.DIMENSIONS)
        b.probe("p-before", asker=pid, query={"op": "as_of", "subject": pid, "attribute": attr, "before_event": last},
                prompt=probe_prompt(attr, "before", subject_name=name, first_person=True), kind="historical",
                dimensions=self.DIMENSIONS, historical=True, swap=False)
        b.probe("p-first", asker=pid, query={"op": "first_stated", "subject": pid, "attribute": attr},
                prompt=probe_prompt(attr, "first", subject_name=name, first_person=True), kind="historical",
                dimensions=self.DIMENSIONS, historical=True, swap=False)


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
        b.say("e-org", source=oid, subject="review", attribute="meeting_start", value=t_org, kind="state", truth_bearing=True, subject_name=meeting)
        b.say("e-col", source=cid, subject="review", attribute="meeting_start", value=t_col, kind="contradiction", truth_bearing=False, subject_name=meeting)
        resolved = rng.random() < 0.5
        if resolved:
            b.observe_tool("e-cal", tool_actor="calendar", tool_name="calendar", subject="review", attribute="meeting_start", value=t_org)
        b.maintenance_window("mw-1")
        b.interfere(subject_id=pid, attribute="birthday", exclude_values={b0, b1}, other_actors=others)
        b.checkpoint()
        d = self.DIMENSIONS
        b.probe("p-bday", asker=pid, query={"op": "current", "subject": pid, "attribute": "birthday"},
                prompt=probe_prompt("birthday", "current", subject_name=name, first_person=True), kind="epistemic", dimensions=d)
        b.probe("p-bday-first", asker=pid, query={"op": "first_stated", "subject": pid, "attribute": "birthday"},
                prompt=probe_prompt("birthday", "first", subject_name=name, first_person=True), kind="historical",
                dimensions=d, historical=True, swap=False)
        b.probe("p-use", asker=pid, query={"op": "current", "subject": "review", "attribute": "meeting_start"},
                prompt=probe_prompt("meeting_start", "current", subject_name=meeting, first_person=False), kind="epistemic", dimensions=d)
        b.probe("p-said", asker=pid, query={"op": "said_by", "source": cid, "subject": "review", "attribute": "meeting_start"},
                prompt=probe_prompt("meeting_start", "said_by", subject_name=meeting, first_person=False, source_name=cname),
                kind="audit", dimensions=d)
        b.probe("p-status", asker=pid, query={"op": "status", "subject": "review", "attribute": "meeting_start"},
                prompt=probe_prompt("meeting_start", "status", subject_name=meeting, first_person=False), kind="epistemic", dimensions=d)
        b.probe("p-unknown", asker=pid, query={"op": "known", "subject": pid, "attribute": "office"},
                prompt=probe_prompt("office", "known", subject_name=name, first_person=True), kind="abstention", dimensions=d, swap=False)


def _deployment_state(actual: str, wrong: str) -> dict[str, Any]:
    return {"actual_target": actual, "selected_target": wrong, "migration_applied": False, "service_running": False, "last_error": None}


class ExperienceProgram(Program):
    ID = "mib.experience.v1"
    SUITE = "experience"
    TITLE = "Two lived deployment trials (failure, then recovery), then a related deployment"
    DIMENSIONS = ["experience_memory"]
    WEIGHTS = {"experience_memory": 1.0}
    CAPABILITIES = ["observe", "respond", "act", "tools", "virtual_time"]

    def build(self, b: ScenarioBuilder) -> None:
        rng = b.rng
        pid, name = _person(b)
        others = other_actors(rng, {name})
        targets = rng.sample(DEPLOY_TARGETS, 6)
        b.tools = [DEPLOYMENT_TOOL]
        b.world_state["deployment"] = _deployment_state(targets[0], targets[1])
        tools = [f"deployment.{op['name']}" for op in DEPLOYMENT_TOOL["operations"]]
        goal = "Deploy the service: run the database migration and restart the service so that it is running."
        trial_oracle = {
            "world_assertions": [
                {"path": "/deployment/service_running", "operator": "eq", "value": True},
                {"path": "/deployment/migration_applied", "operator": "eq", "value": True},
            ],
            "trajectory_requirements": [
                {"type": "before", "first": "deployment.inspect_target", "second": "deployment.run_migration"},
                {"type": "no_recurrence", "action": "deployment.run_migration", "without_prior": "deployment.inspect_target"},
            ],
        }
        b.event("e-brief", stage="past", etype="interaction", actor=pid,
                content="You are on deployment duty this week. Use the deployment tool; the environment may have surprises.")
        # Trial 1: the environment's selected target is wrong; the Agent lives the failure.
        b.task("t-past", actor=pid, goal=goal, tools=tools, oracle=trial_oracle)
        b.event("w-reset", stage="past", etype="world_update", actor=None, visibility="harness",
                extra={"world_updates": [{"op": "set", "path": "/deployment", "value": _deployment_state(targets[2], targets[3])}]})
        b.event("e-again", stage="past", etype="interaction", actor=pid,
                content="Another environment is ready now; please deploy there as well.")
        # Trial 2: the same trap; a learning Agent inspects first.  Both trials are learning-curve samples, never scores.
        b.task("t-past-2", actor=pid, goal=goal, tools=tools, oracle=trial_oracle)
        b.event("w-reset-2", stage="past", etype="world_update", actor=None, visibility="harness",
                extra={"world_updates": [{"op": "set", "path": "/deployment", "value": _deployment_state(targets[4], targets[5])}]})
        b.event("e-next", stage="past", etype="interaction", actor=pid,
                content="Thanks. A different environment is being prepared; I will ask you to deploy there later.")
        b.maintenance_window("mw-1")
        b.interfere(subject_id=pid, attribute="office", exclude_values=set(), other_actors=others)
        b.checkpoint()
        b.raw_probe({
            "id": "p-deploy", "kind": "action", "trigger": {"after_event": "cp"}, "delivery": "act",
            "input": {"goal": goal, "available_tools": tools, "constraints": []},
            "oracle": trial_oracle,
            "evaluators": ["eval-action"], "dimensions": self.DIMENSIONS, "weight": 1.0,
        })
        b.ablation({"id": "a-relevant-p-deploy", "kind": "relevant_memory", "probes": ["p-deploy"], "method": "replay_excluding_events",
                    "targets": {"event_ids": ["t-past", "t-past-2"]}, "expected_effect": "degrade",
                    "description": "Withholding the lived trials removes the Agent's own failure and recovery."})


class SkillProgram(Program):
    ID = "mib.skill.v1"
    SUITE = "skill"
    TITLE = "A learned precondition, transferred where it applies and withheld where it does not"
    DIMENSIONS = ["skill_learning_transfer"]
    WEIGHTS = {"skill_learning_transfer": 1.0}
    CAPABILITIES = ["observe", "respond", "act", "tools", "virtual_time"]

    def build(self, b: ScenarioBuilder) -> None:
        rng = b.rng
        pid, name = _person(b)
        others = other_actors(rng, {name})
        ctx = rng.sample(CONTEXTS, 3)
        b.tools = [CANVAS_TOOL]
        b.world_state["contextual_save"] = {"context_required": True, "active_context": None, "edited": False, "committed": False, "policy_violation": False, "last_error": None}
        tools = [f"canvas.{op['name']}" for op in CANVAS_TOOL["operations"]]
        b.event("e-brief", stage="past", etype="interaction", actor=pid,
                content=f"Please update the item in the '{ctx[0]}' workspace of the canvas tool and commit the change.")
        b.task("t-past", actor=pid, goal=f"Update the item in the '{ctx[0]}' workspace and commit the change.", tools=tools,
               oracle={"world_assertions": [{"path": "/contextual_save/committed", "operator": "eq", "value": True}],
                       "trajectory_requirements": [{"type": "before", "first": "canvas.activate_context", "second": "canvas.commit"}]})
        b.event("w-reset", stage="past", etype="world_update", actor=None, visibility="harness",
                extra={"world_updates": [{"op": "set", "path": "/contextual_save", "value": {"context_required": True, "active_context": None, "edited": False, "committed": False, "policy_violation": False, "last_error": None}}]})
        b.maintenance_window("mw-1")
        b.interfere(subject_id=pid, attribute="office", exclude_values=set(), other_actors=others)
        b.checkpoint()
        # The non-matching task runs first: in the Negative Transfer control (skill memory
        # withheld) nothing earlier in the Probe program may re-teach the skill.
        b.event("w-global", stage="pre_probe", etype="world_update", actor=None, visibility="harness",
                extra={"world_updates": [{"op": "set", "path": "/contextual_save", "value": {"context_required": False, "active_context": None, "edited": False, "committed": False, "policy_violation": False, "last_error": None}}]})
        b.raw_probe({
            "id": "p-nonmatch", "kind": "skill", "trigger": {"after_event": "w-global"}, "delivery": "act",
            "input": {"goal": f"This item is a global record ('{ctx[2]}' is not a workspace): no context activation is needed or allowed. Update the item and commit the change.",
                      "available_tools": tools, "constraints": ["Do not activate a context for global records."]},
            "oracle": {
                "world_assertions": [
                    {"path": "/contextual_save/committed", "operator": "eq", "value": True},
                    {"path": "/contextual_save/policy_violation", "operator": "eq", "value": False},
                ],
                "trajectory_requirements": [
                    {"type": "forbidden_action", "action": "canvas.activate_context"},
                    {"type": "required_action", "action": "canvas.commit"},
                ],
            },
            "evaluators": ["eval-action"], "dimensions": self.DIMENSIONS, "weight": 1.0,
        })
        b.event("w-match", stage="pre_probe", etype="world_update", actor=None, visibility="harness",
                extra={"world_updates": [{"op": "set", "path": "/contextual_save", "value": {"context_required": True, "active_context": None, "edited": False, "committed": False, "policy_violation": False, "last_error": None}}]})
        b.raw_probe({
            "id": "p-match", "kind": "skill", "trigger": {"after_event": "w-match"}, "delivery": "act",
            "input": {"goal": f"Update the item in the '{ctx[1]}' workspace and commit the change.", "available_tools": tools, "constraints": []},
            "oracle": {
                "world_assertions": [{"path": "/contextual_save/committed", "operator": "eq", "value": True}],
                "trajectory_requirements": [
                    {"type": "before", "first": "canvas.activate_context", "second": "canvas.commit"},
                    {"type": "no_recurrence", "action": "canvas.commit", "without_prior": "canvas.activate_context"},
                ],
            },
            "evaluators": ["eval-action"], "dimensions": self.DIMENSIONS, "weight": 1.0,
        })
        b.ablation({"id": "a-relevant-p-match", "kind": "relevant_memory", "probes": ["p-match"], "method": "replay_excluding_events",
                    "targets": {"event_ids": ["t-past"]}, "expected_effect": "degrade"})
        # MIB-Specification §7.8: the standardized Negative Transfer control is the
        # non-matching task *without* the skill memory; the skill may not hurt it.
        b.ablation({"id": "a-negative-transfer-p-nonmatch", "kind": "negative_transfer", "probes": ["p-nonmatch"],
                    "method": "replay_excluding_events", "targets": {"event_ids": ["t-past"]}, "expected_effect": "resist",
                    "description": "Negative Transfer control: the non-matching task with the skill memory withheld."})


class ProspectiveProgram(Program):
    ID = "mib.prospective.v1"
    SUITE = "prospective"
    TITLE = "A deferred commitment that must fire on its trigger and not before; a self-rule that must hold"
    DIMENSIONS = ["prospective_self_memory"]
    WEIGHTS = {"prospective_self_memory": 1.0}
    CAPABILITIES = ["observe", "respond", "act", "tools", "virtual_time"]

    def build(self, b: ScenarioBuilder) -> None:
        rng = b.rng
        pid, name = _person(b)
        tid, tname = _person(b, {name})
        b.actor("system", "Call System", kind="system")
        others = other_actors(rng, {name, tname})
        topic = rng.choice(TOPICS)
        target = rng.choice(DEPLOY_TARGETS)
        b.tools = [DEPLOYMENT_TOOL]
        b.world_state["deployment"] = _deployment_state(target, target)
        tools = [f"deployment.{op['name']}" for op in DEPLOYMENT_TOOL["operations"]]
        b.event("e-commit", stage="past", etype="interaction", actor=pid,
                content=rng.choice(COMMITMENT_TEMPLATES).format(trigger_name=tname, topic=topic), extra={"tags": ["commitment"]})
        b.event("e-limit", stage="past", etype="interaction", actor=pid,
                content=rng.choice(LIMITATION_TEMPLATES).format(name=tname), extra={"tags": ["self_rule"]})
        b.event("e-near-1", stage="past", etype="observation", actor="system",
                content=rng.choice(NEAR_TRIGGER_TEMPLATES).format(trigger_name=tname, weekday=rng.choice(WEEKDAYS), thing=rng.choice(THINGS)))
        b.maintenance_window("mw-1")
        b.interfere(subject_id=pid, attribute="city", exclude_values=set(), other_actors=others)
        b.checkpoint()
        near = rng.choice(NEAR_TRIGGER_TEMPLATES).format(trigger_name=tname, weekday=rng.choice(WEEKDAYS), thing=rng.choice(THINGS))
        b.raw_probe({
            "id": "p-near", "kind": "prospective", "trigger": {"after_event": "cp"}, "delivery": "observe_only",
            "input": {"observation": {"type": "environment_event", "actor": "system", "content": near}},
            "oracle": {"expected_emission": {"must_not_emit": True, "topic": topic, "window": 0}},
            "evaluators": ["eval-emission"], "dimensions": self.DIMENSIONS, "weight": 0.5,
        })
        b.raw_probe({
            "id": "p-trigger", "kind": "prospective", "trigger": {"after_event": "cp"}, "delivery": "observe_only",
            "input": {"observation": {"type": "environment_event", "actor": "system", "content": rng.choice(TRIGGER_TEMPLATES).format(trigger_name=tname)}},
            "oracle": {"expected_emission": {"must_contain": [topic], "window": 1}},
            "evaluators": ["eval-emission"], "dimensions": self.DIMENSIONS, "weight": 1.0,
        })
        # Self memory: the task asks for the restart; the standing rule about the Agent says no.
        b.raw_probe({
            "id": "p-self", "kind": "self", "trigger": {"after_event": "cp"}, "delivery": "act",
            "input": {"goal": "Deploy the service: run the database migration and then restart the service.",
                      "available_tools": tools, "constraints": []},
            "oracle": {
                "world_assertions": [
                    {"path": "/deployment/migration_applied", "operator": "eq", "value": True},
                    {"path": "/deployment/service_running", "operator": "eq", "value": False},
                ],
                "trajectory_requirements": [
                    {"type": "required_action", "action": "deployment.run_migration"},
                    {"type": "forbidden_action", "action": "deployment.restart_service"},
                ],
            },
            "evaluators": ["eval-action"], "dimensions": self.DIMENSIONS, "weight": 1.0,
        })
        b.ablation({"id": "a-relevant-p-trigger", "kind": "relevant_memory", "probes": ["p-trigger"], "method": "replay_excluding_events",
                    "targets": {"event_ids": ["e-commit"]}, "expected_effect": "degrade"})
        b.ablation({"id": "a-relevant-p-self", "kind": "relevant_memory", "probes": ["p-self"], "method": "replay_excluding_events",
                    "targets": {"event_ids": ["e-limit"]}, "expected_effect": "degrade",
                    "description": "Withholding the self-rule: the Agent should then follow the task literally and restart."})


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
        b.probe("p-forgotten", asker=pid, query={"op": "current", "subject": pid, "attribute": forget_attr},
                prompt=probe_prompt(forget_attr, "known", subject_name=name, first_person=True), kind="abstention", dimensions=d, swap=False)
        b.probe("p-forgotten-history", asker=pid, query={"op": "first_stated", "subject": pid, "attribute": forget_attr},
                prompt=probe_prompt(forget_attr, "first", subject_name=name, first_person=True), kind="abstention",
                dimensions=d, weight=0.5, swap=False)
        b.probe("p-kept", asker=pid, query={"op": "current", "subject": pid, "attribute": keep_attr},
                prompt=probe_prompt(keep_attr, "current", subject_name=name, first_person=True), kind="factual", dimensions=d)


PROGRAM_CLASSES = [RecallProgram, TemporalProgram, EpistemicProgram, ExperienceProgram, SkillProgram, ProspectiveProgram, ForgettingProgram]
