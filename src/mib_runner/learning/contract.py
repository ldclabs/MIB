"""Strict optional learning audit contract over the existing Agent transport."""
from __future__ import annotations

import copy
import re
import uuid
from dataclasses import asdict

from ..adapter_contract import AdapterLifecycleError, check_descriptor, digest, require_accepted

EXTENSION = "mib.learning_longitudinal.v1"
AUDIT_FORMAT = "mib-learning-audit/0.1"
CONDITIONS = ("normal", "no_memory", "ungated")
COUNT_FIELDS = ("skills", "revisions", "decisions", "attempts", "outcomes", "trials", "evaluations")


def check_learning_descriptor(descriptor, mode):
    check_descriptor(descriptor, ["observe", "respond", "act", "runner_managed_tools", "maintenance", "session_boundary", "virtual_time"])
    extension = descriptor.get("extensions", {}).get(EXTENSION)
    if not isinstance(extension, dict) or extension.get("mode") != mode or mode not in CONDITIONS:
        raise AdapterLifecycleError(f"missing explicit {EXTENSION} capability for {mode}")
    for field in ("configuration_digest", "execution_guard_digest"):
        if not re.fullmatch(r"sha256:[0-9a-f]{64}", str(extension.get(field, ""))):
            raise AdapterLifecycleError(f"learning descriptor lacks {field}")
    if not isinstance(extension.get("business_identity"), dict) or not extension["business_identity"]:
        raise AdapterLifecycleError("learning descriptor lacks fixed business model/prompt/tools/sampling/budget identity")
    for field in ("model_digest", "business_prompt_digest", "tools_digest", "budget_digest", "decoding_digest"):
        if not re.fullmatch(r"sha256:[0-9a-f]{64}", str(extension["business_identity"].get(field, ""))):
            raise AdapterLifecycleError(f"business identity lacks {field}")
    recall = extension.get("recall_budget", {})
    if not isinstance(recall, dict) or recall.get("tokenizer") != "o200k_base@tiktoken-rs-0.12.0" or type(recall.get("max_tokens")) is not int or not 1 <= recall["max_tokens"] <= 65536 or type(recall.get("context_tokens")) is not int or not 1 <= recall["context_tokens"] <= 131072:
        raise AdapterLifecycleError("missing pinned P5 Recall budget")
    if extension.get("audit_operation") != "learning_audit":
        raise AdapterLifecycleError("learning_audit operation must be explicitly declared")
    flags = ("native_comparison_and_review", "independent_observer", "isolated_trial_application", "cross_task_state")
    if any(type(extension.get(key)) is not bool for key in flags):
        raise AdapterLifecycleError("learning capability flags must be explicit booleans")
    if mode == "normal" and not all(extension[key] for key in ("native_comparison_and_review", "independent_observer", "cross_task_state")):
        raise AdapterLifecycleError("normal requires real native comparison/review and an independent observer")
    if mode == "ungated" and not all(extension[key] for key in ("isolated_trial_application", "cross_task_state")):
        raise AdapterLifecycleError("ungated requires isolated unproven trial application")
    if mode != "no_memory" and extension.get("native_task_family") != "tool_workflow.precondition.v1":
        raise AdapterLifecycleError("native task family is not bound to the frozen P0 precondition measurement")
    from .workflow import CONTRACT_DIGEST
    if mode != "no_memory" and extension.get("workflow_contract_digest") != CONTRACT_DIGEST:
        raise AdapterLifecycleError("P0 workflow contract digest mismatch")
    if mode == "no_memory" and extension["cross_task_state"]:
        raise AdapterLifecycleError("no_memory cannot retain cross-task state")
    return extension


def check_audit(body, run_id, mode):
    if not isinstance(body, dict) or body.get("format") != AUDIT_FORMAT or body.get("run_id") != run_id or body.get("mode") != mode:
        raise AdapterLifecycleError("learning audit format/run/mode mismatch")
    if type(body.get("complete")) is not bool or type(body.get("native_sequence")) is not int or body["native_sequence"] < 0:
        raise AdapterLifecycleError("learning audit requires completeness and native sequence")
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", str(body.get("state_digest", ""))):
        raise AdapterLifecycleError("learning audit requires a procedure projection digest")
    counts = body.get("counts", {})
    if any(type(counts.get(key)) is not int or counts[key] < 0 for key in COUNT_FIELDS):
        raise AdapterLifecycleError("learning audit counts missing or invalid")
    skills = body.get("skills")
    if not isinstance(skills, list) or len(skills) > 256:
        raise AdapterLifecycleError("learning audit skills must be bounded")
    seen = set()
    for row in skills:
        if not isinstance(row, dict) or not re.fullmatch(r"C-[1-9][0-9]*", str(row.get("skill_ref", ""))) or "revision_ref" not in row or row["revision_ref"] is not None and not re.fullmatch(r"C-[1-9][0-9]*", str(row["revision_ref"])):
            raise AdapterLifecycleError("learning audit requires exact native Skill/revision refs")
        if row["skill_ref"] in seen or not isinstance(row.get("status"), str):
            raise AdapterLifecycleError("learning audit duplicate skill or missing status")
        seen.add(row["skill_ref"])
        for field in ("evaluation_ref", "trial_ref"):
            if field not in row or row[field] is not None and not re.fullmatch(r"X-[1-9][0-9]*", str(row[field])):
                raise AdapterLifecycleError("learning audit verdict/trial must be native Activity refs or null")
        if row.get("recommendation_allowed") is not None and type(row["recommendation_allowed"]) is not bool:
            raise AdapterLifecycleError("invalid recommendation flag")
        if row.get("recommendation_allowed") is True and (row["status"] != "adopted" or row.get("evaluation_ref") is None or row["revision_ref"] is None):
            raise AdapterLifecycleError("recommendation flag contradicts native standing")
    if body["complete"] and counts["skills"] != len(skills):
        raise AdapterLifecycleError("complete audit skill count mismatch")
    if mode == "no_memory" and (body["complete"] is not True or skills or any(counts.values())):
        raise AdapterLifecycleError("no_memory leaked procedure state")
    return body


class AuditedAgent:
    """No oracle/scenario/control label enters this wrapper's Agent calls.

    Audit calls are read-only and never projected through observe. The original
    Runner still owns all simulator outcomes, schema validation and call limits.
    """
    def __init__(self, agent, mode, expected_descriptor=None):
        self.agent, self.mode = agent, mode
        self.expected_descriptor = expected_descriptor
        self.run_id = None
        self.descriptor = None
        self.snapshots, self.completed, self.calls = [], [], []
        self.pending = {}

    @property
    def cost_snapshots(self):
        return getattr(self.agent, "cost_snapshots", [])

    def describe(self):
        self.descriptor = self.agent.describe()
        if self.expected_descriptor is not None and self.descriptor != self.expected_descriptor:
            raise AdapterLifecycleError("runtime descriptor changed after experiment lock")
        check_learning_descriptor(self.descriptor, self.mode)
        if not callable(getattr(self.agent, "learning_audit", None)):
            raise AdapterLifecycleError("learning_audit has no callable transport")
        return self.descriptor

    def audit(self, operation, edge):
        row = {"operation": operation, "edge": edge, "sequence": len(self.snapshots)}
        try:
            raw = self.agent.learning_audit(run_id=self.run_id, request_id="audit_" + uuid.uuid4().hex)
            row["body"] = copy.deepcopy(raw)
            check_audit(raw, self.run_id, self.mode)
        except Exception as exc:
            row["error"] = repr(exc)
            self.snapshots.append(row)
            raise AdapterLifecycleError(f"learning_audit: {exc}") from exc
        self.snapshots.append(row)
        return len(self.snapshots) - 1

    def reset(self, **kwargs):
        self.run_id = kwargs["run_id"]
        result = self.agent.reset(**kwargs)
        require_accepted("reset", result)
        self.audit("reset", "after")
        return result

    def observe(self, **kwargs):
        return self.agent.observe(**kwargs)

    def respond(self, **kwargs):
        before = self.audit("respond", "before")
        output = self.agent.respond(**kwargs)
        after = self.audit("respond", "after")
        self.completed.append({"kind": "respond", "input": copy.deepcopy(kwargs["input_data"]),
                               "output": asdict(output), "before": before, "after": after})
        return output

    def act(self, **kwargs):
        task_id = kwargs["task_id"]
        if not kwargs["continuation"]:
            self.pending[task_id] = {"kind": "act", "task_id": task_id, "goal": kwargs["goal"],
                                     "before": self.audit("act", "before"), "steps": []}
        output = self.agent.act(**kwargs)
        self.calls.append({"task_id": task_id, "output": asdict(output)})
        row = self.pending[task_id]
        row["steps"].append(asdict(output))
        if output.type in {"final", "abstention"}:
            row["after"] = self.audit("act", "after")
            self.completed.append(self.pending.pop(task_id))
        return output

    def maintain(self, **kwargs):
        self.audit("maintain", "before")
        result = self.agent.maintain(**kwargs)
        require_accepted("maintain", result)
        self.audit("maintain", "after")
        return result

    def session_boundary(self, **kwargs):
        result = self.agent.session_boundary(**kwargs)
        require_accepted("session_boundary", result)
        self.audit("session_boundary", "after")
        return result

    def close(self, *, run_id=None):
        # Always release the host, even when the final audit itself fails.
        try:
            if self.run_id is not None:
                self.audit("close", "before")
        finally:
            self.agent.close(run_id=run_id)

    def evidence(self):
        return copy.deepcopy({"descriptor": self.descriptor, "snapshots": self.snapshots,
                              "completed": self.completed, "calls": self.calls,
                              "pending": self.pending, "cost_snapshots": self.cost_snapshots})
