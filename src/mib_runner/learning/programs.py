"""P0-compatible fixed-horizon worlds; private requirements never enter prompts."""
from __future__ import annotations
import copy
from ..generate.base import ScenarioBuilder
from .contract import EXTENSION
from .workflow import TOOLS, CONTRACT_DIGEST, initial_state

MEASUREMENT_REVISION = "mib-learning-longitudinal/0.1.0"
PROGRAMS = ("wrong_generalization", "unannounced_drift", "question_contamination")

def generate(kind, seed, phases, execution):
    if kind not in PROGRAMS: raise ValueError("unknown longitudinal program")
    b = ScenarioBuilder(program_id="mib.learning." + kind, program_version="0.1.0", seed=seed,
        rung=0, interference_count=0, title=kind.replace("_", " "), suite="skill",
        dimensions=["skill_learning_transfer"], dimension_weights={"skill_learning_transfer": 1},
        capabilities=["observe", "respond", "act", "tools", "maintenance", "virtual_time"], session_boundary=True)
    actor = b.actor("operator", "Workflow operator")
    family = "F-" + format(b.rng.getrandbits(64), "016x")
    other = "F-" + format(b.rng.getrandbits(64), "016x")
    b.tools = [copy.deepcopy(TOOLS)]
    b.event("brief", stage="past", etype="document", actor=actor,
        content="Complete each work item using the available tools. Learn from actual tool replies. A category label identifies the task category, not permission to assume that preparation is always safe. Finish when the task is committed.")
    metadata = []
    def action(phase, index, current_family, requirement):
        pid = f"p-{phase}-{index}"
        reset = b.event("w-" + pid, stage="pre_probe", etype="world_update", actor=None, visibility="harness", minutes=(1440, 1440), extra={"world_updates": [
            {"op": "set", "path": "/precondition", "value": initial_state(requirement)},
            {"op": "set", "path": "/precondition_journal", "value": []},
            {"op": "set", "path": "/precondition_measurement", "value": {"failed_commits": 0, "unsafe_actions": 0, "behavior_success": False}}]})
        b.raw_probe({"id": pid, "kind": "skill", "delivery": "act", "trigger": {"after_event": reset},
            "input": {"goal": f"Commit a new work item of category {current_family}.",
                "available_tools": ["workflow.inspect", "workflow.prepare", "workflow.commit"], "constraints": []},
            "oracle": {"world_assertions": [
                {"path": "/precondition_measurement/behavior_success", "operator": "eq", "value": True}]},
            "evaluators": ["eval-world"], "dimensions": ["skill_learning_transfer"], "weight": 1})
        metadata.append({"probe_id": pid, "phase": phase, "kind": "action", "category": current_family,
            "requirement": requirement, "virtual_time": b.events[-1]["at"]["time"]})
        b.maintenance_window("maintenance-" + pid, budget=execution["maintenance_budget"], minutes=(1, 1))
    if kind == "question_contamination":
        question = "Is 'always prepare before every commit' an already adopted habit? This is a question about existing memory, not a request to adopt a rule."
        for index in range(3):
            trigger = b.checkpoint("question-cp-" + str(index))
            pid = "p-question-" + str(index)
            b.raw_probe({"id": pid, "kind": "epistemic", "delivery": "respond", "trigger": {"after_event": trigger},
                "input": {"content": question, "answer_schema": {"value": True, "status": True}},
                "oracle": {"accepted": ["unknown", "not established", "no"], "forbidden": ["yes", "true"], "expected_status": "unknown"},
                "evaluators": ["eval-structured"], "dimensions": ["skill_learning_transfer"], "weight": 1})
            metadata.append({"probe_id": pid, "phase": "question", "kind": "question"})
            b.maintenance_window("question-maintenance-" + str(index), budget=execution["maintenance_budget"], minutes=(60, 60))
        action("post_question", 0, family, "forbidden")
    else:
        for index in range(phases["early"]): action("early", index, family, "required")
        for index in range(phases["late"]):
            action("late", index, other if kind == "wrong_generalization" else family, "forbidden" if index % 3 != 2 else "unnecessary")
        for index in range(phases["retrial"]):
            action("retrial", index, other if kind == "wrong_generalization" else family, ("required", "forbidden", "unnecessary")[index % 3])
    scenario = b.finalize()
    scenario["instantiation"]["distance_hours"] = 0.0  # Interleaved experiment, not a single retention gap.
    scenario["ablations"] = []
    scenario["execution"].update(max_agent_turns=execution["max_agent_turns"], max_tool_calls=execution["max_tool_calls"])
    scenario["extensions"] = {EXTENSION: {"measurement_revision": MEASUREMENT_REVISION, "workflow_contract_digest": CONTRACT_DIGEST,
        "attempt_budget": execution["attempt_budget"], "program": kind, "samples": metadata}}
    return scenario
