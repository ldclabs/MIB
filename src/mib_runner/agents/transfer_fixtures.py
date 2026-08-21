"""Deterministic fixture Agents for transfer-diagnostic identifiability.

A diagnostic is only worth reporting if a known failure mode produces the
signature it claims to produce.  These fixtures have deliberately different
memory pathologies and are used to prove that Formation Efficiency, Routing
Efficiency, and the uptake ceiling separate them:

    fixture         AA    AO    OA    OO     signature
    Perfect         high  high  high  high   FE~1, RE~1
    BadFormation    low   low   high  high   FE~0, RE~1
    BadRouting      low   high  low   high   FE~1, RE~0
    BadUptake       low   low   low   low    OO low, ratios ineligible
    NoTransfer      low   low   low   high   FE~0, RE~0
    OverTransfer    high   -     -     -     positive transfer good,
                                             near-match resistance bad

They are fixtures, not baselines.  Nothing here is a claim about any real
memory system.

Each fixture is described by four independent switches:

``forms``
    what Formation produces, and therefore what ``export_artifacts`` returns:
    a usable procedure, an unusable one, or nothing.
``acts_on_experience``
    whether a raw failure/recovery narrative in the past is compiled into
    behaviour at task time.
``acts_on_pool_procedure``
    whether an explicit procedure seen earlier in the past stream is recalled.
``acts_on_task_time_procedure``
    whether an explicit procedure surfaced immediately before the task is used.

``respects_boundary`` additionally controls whether a declared applicability
counterexample suppresses the procedure.
"""

from __future__ import annotations

from typing import Any

from ..memory_adapter import InProcessMemoryAdapter, MemoryArtifact
from ..transfer import RECALL_PREFIX
from ..types import ActStep, AgentOutput, Observation

#: Text cues that identify a raw Experience narrative, per domain.
_EXPERIENCE_CUES = {
    "workspace": ("workspace_required", "selected the workspace", "select the workspace"),
    "canvas": ("workspace_required", "select the workspace", "context_required", "context was activated"),
    "deployment": ("wrong_target", "target mismatch", "missing_column", "inspected the actual target"),
}

#: Cue that an applicability counterexample was observed.
_BOUNDARY_CUES = ("global record", "no context is required", "no workspace is required")

#: Words a routed artifact must carry to be *usable* for a domain.  A system
#: handed an unusable artifact cannot act on it, which is what separates the
#: AO cell of a good former from that of a bad one.
_PROCEDURE_CUES = {
    "workspace": ("workspace",),
    "canvas": ("context", "scope"),
    "deployment": ("inspect", "target"),
}

#: One domain-agnostic compiled procedure: Formation abstracts the principle
#: rather than memorizing one surface.
_GOOD_ARTIFACT = (
    "Establish the required precondition before the mutating step: select the workspace or "
    "activate the required context or scope first, then edit, then save or commit exactly once. "
    "For a migration, inspect the actual target and select what the inspection reports before "
    "migrating, then restart the service afterwards."
)

_GARBAGE_ARTIFACT = "Something went wrong earlier and then it was fine."


class TransferFixtureAgent:
    """Base fixture: an Agent plus an optional decomposable Memory Adapter."""

    forms: str = "good"                     # "good" | "garbage" | "none"
    acts_on_experience: bool = True
    acts_on_pool_procedure: bool = True
    acts_on_task_time_procedure: bool = True
    respects_boundary: bool = True
    fixture_name: str = "Transfer Fixture"

    def __init__(self) -> None:
        self.run_id = ""
        self.observations: list[Observation] = []
        self.seen_observe_requests: set[tuple[str, str]] = set()
        self.act_responses: dict[tuple[str, str], ActStep] = {}
        self.task_states: dict[str, dict[str, Any]] = {}
        self.tool_call_counter = 0
        self.memory = InProcessMemoryAdapter()

    # -- Agent Adapter ----------------------------------------------------

    def describe(self) -> dict[str, Any]:
        return {
            "protocol": "mib-agent/0.1",
            "implementation": {"name": self.fixture_name, "version": "0.1.0", "vendor": "MIB"},
            "track_support": ["integrated_agent"],
            "capabilities": {
                "observe": True, "respond": True, "act": True,
                "spontaneous_emissions": False, "maintenance": False,
                "runner_managed_tools": True, "structured_output": False,
                "virtual_time": True, "seedable": True,
            },
            "state": {"run_isolation": "hard", "observe_visibility": "read_after_write", "request_idempotency": True},
        }

    def reset(self, *, run_id: str, seed, virtual_time: str | None) -> dict[str, Any]:
        self.run_id = run_id
        self.observations = []
        self.seen_observe_requests = set()
        self.act_responses = {}
        self.task_states = {}
        self.tool_call_counter = 0
        self.memory.reset_memory({})
        return {"accepted": True}

    def observe(self, *, run_id: str, request_id: str, observation: Observation) -> dict[str, Any]:
        key = (run_id, request_id)
        if key in self.seen_observe_requests:
            return {"accepted": True, "emissions": []}
        self.seen_observe_requests.add(key)
        self.observations.append(observation)
        self.memory.observe_memory_event({
            "observation_id": observation.observation_id,
            "content": observation.content,
            "payload": observation.payload,
        })
        self._form(observation)
        return {"accepted": True, "emissions": []}

    def respond(self, *, run_id: str, request_id: str, interaction_id: str, input_data: dict[str, Any], virtual_time: str | None) -> AgentOutput:
        # These fixtures diagnose procedural transfer; they abstain on recall.
        return AgentOutput(type="message", content="unknown")

    def act(self, *, run_id: str, request_id: str, task_id: str, goal: str | None, constraints, tools, continuation: bool, virtual_time: str | None) -> ActStep:
        key = (run_id, request_id)
        if key in self.act_responses:
            return self.act_responses[key]
        state = self.task_states.get(task_id)
        if state is None:
            # The Runner supplies the tool list on the first turn only, so the
            # domain and the apply/withhold decision are fixed at task start.
            domain = self._domain({t["name"] for t in tools or ()})
            state = {"phase": 0, "domain": domain, "apply": self._decide(domain)}
            self.task_states[task_id] = state
        domain = state["domain"]

        def emit(step: ActStep) -> ActStep:
            self.act_responses[key] = step
            return step

        if domain is None:
            return emit(ActStep(type="abstention", content="No supported action policy for these tools."))
        sequence = self._sequence(domain, apply_procedure=state["apply"])
        phase = state["phase"]
        if phase >= len(sequence):
            return emit(ActStep(type="final", content="Task attempt complete."))
        state["phase"] = phase + 1
        tool, arguments = sequence[phase]
        if arguments.get("target") == "__inspected__":
            arguments = {"target": self._inspected_target()}
        self.tool_call_counter += 1
        return emit(ActStep(
            type="tool_call",
            tool_call_id=f"call_{self.tool_call_counter:04d}",
            tool=tool,
            arguments=arguments,
        ))

    # -- Memory Adapter ---------------------------------------------------

    def describe_memory(self) -> dict[str, Any]:
        return self.memory.describe_memory()

    def reset_memory(self, request: dict[str, Any]) -> dict[str, Any]:
        return self.memory.reset_memory(request)

    def observe_memory_event(self, request: dict[str, Any]) -> dict[str, Any]:
        return self.memory.observe_memory_event(request)

    def consolidate_memory(self, request: dict[str, Any]) -> dict[str, Any]:
        return self.memory.consolidate_memory(request)

    def export_artifacts(self, request: dict[str, Any] | None = None) -> dict[str, Any]:
        return self.memory.export_artifacts(request)

    def retrieve_artifacts(self, request: dict[str, Any] | None = None) -> dict[str, Any]:
        return self.memory.retrieve_artifacts(request)

    def inject_artifacts(self, request: dict[str, Any]) -> dict[str, Any]:
        return self.memory.inject_artifacts(request)

    # -- Internals --------------------------------------------------------

    def _form(self, observation: Observation) -> None:
        """Compile an artifact once the supporting Experience has been seen."""
        if self.forms == "none":
            return
        text = self._text_of(observation)
        if self._domain_from_text(text) is None:
            return
        content = _GOOD_ARTIFACT if self.forms == "good" else _GARBAGE_ARTIFACT
        if any(a.content == content for a in self.memory.artifacts):
            return
        self.memory.artifacts.append(MemoryArtifact(
            artifact_id=f"formed-{len(self.memory.artifacts) + 1}",
            artifact_type="skill",
            content=content,
            metadata={"source_event_ids": [observation.observation_id]},
        ))

    def _inspected_target(self) -> Any:
        """Read the actual target back from the inspection this task performed."""
        for observation in reversed(self.observations):
            if observation.tool == "deployment.inspect_target" and isinstance(observation.payload, dict):
                return observation.payload.get("actual_target")
        return None

    @staticmethod
    def _text_of(observation: Observation) -> str:
        parts = [observation.content or ""]
        if isinstance(observation.payload, dict):
            parts.append(" ".join(f"{k}={v}" for k, v in observation.payload.items()))
        return " ".join(parts).casefold()

    def _domain_from_text(self, text: str) -> str | None:
        for domain, cues in _EXPERIENCE_CUES.items():
            if any(cue in text for cue in cues):
                return domain
        return None

    @staticmethod
    def _domain(tool_names: set[str]) -> str | None:
        for prefix in ("workspace", "canvas", "deployment"):
            if any(n.startswith(prefix + ".") for n in tool_names):
                return prefix
        return None

    def _decide(self, domain: str | None) -> bool:
        """Whether to apply the procedure for this task."""
        if domain is None:
            return False
        texts = [self._text_of(o) for o in self.observations]
        marker = RECALL_PREFIX.casefold()
        # The applicability cue comes from the situation, never from the routed
        # procedure's own description of its boundary.
        situation = [t for t in texts if marker not in t]
        if self.respects_boundary and any(any(c in t for c in _BOUNDARY_CUES) for t in situation):
            return False

        # Artifacts surfaced in the unbroken block just before the task are routed
        # delivery; anything earlier in the stream must be recalled from the pool.
        # An Ability may route more than one artifact, so the whole trailing block
        # counts, not only the final observation.
        task_time_from = len(texts)
        while task_time_from > 0 and marker in texts[task_time_from - 1]:
            task_time_from -= 1

        usable = _PROCEDURE_CUES[domain]
        for index, text in enumerate(texts):
            if marker not in text or not any(cue in text for cue in usable):
                continue
            if index >= task_time_from:
                if self.acts_on_task_time_procedure:
                    return True
            elif self.acts_on_pool_procedure:
                return True

        if self.acts_on_experience:
            cues = _EXPERIENCE_CUES[domain]
            if any(any(cue in t for cue in cues) for t in texts if RECALL_PREFIX.casefold() not in t):
                return True
        return False

    @staticmethod
    def _sequence(domain: str, *, apply_procedure: bool) -> list[tuple[str, dict[str, Any]]]:
        if domain == "workspace":
            steps = [("workspace.edit_record", {"value": "updated"}), ("workspace.save", {})]
            if apply_procedure:
                steps.insert(0, ("workspace.select_workspace", {"workspace": "primary"}))
            return steps
        if domain == "canvas":
            steps = [("canvas.edit_item", {"value": "updated"}), ("canvas.commit", {})]
            if apply_procedure:
                steps.insert(0, ("canvas.activate_context", {"context": "primary"}))
            return steps
        steps = [("deployment.run_migration", {}), ("deployment.restart_service", {})]
        if apply_procedure:
            steps = [
                ("deployment.inspect_target", {}),
                ("deployment.select_target", {"target": "__inspected__"}),
                *steps,
            ]
        return steps


class PerfectFormationPerfectRoutingAgent(TransferFixtureAgent):
    fixture_name = "Perfect Formation / Perfect Routing Fixture"


class BadFormationAgent(TransferFixtureAgent):
    """Never compiles a procedure from raw Experience, but follows an explicit one."""

    fixture_name = "Bad Formation Fixture"
    forms = "garbage"
    acts_on_experience = False


class BadRoutingAgent(TransferFixtureAgent):
    """Compiles well, but only acts on what is surfaced at task time."""

    fixture_name = "Bad Routing Fixture"
    forms = "good"
    acts_on_experience = False
    acts_on_pool_procedure = False


class BadUptakeAgent(TransferFixtureAgent):
    """Forms and routes fine, and still cannot execute the procedure."""

    fixture_name = "Bad Uptake Fixture"
    forms = "good"
    acts_on_experience = False
    acts_on_pool_procedure = False
    acts_on_task_time_procedure = False


class NoTransferAgent(TransferFixtureAgent):
    """No persistent memory at all; follows only a procedure handed to it now."""

    fixture_name = "No Transfer Fixture"
    forms = "none"
    acts_on_experience = False
    acts_on_pool_procedure = False


class OverTransferAgent(TransferFixtureAgent):
    """Transfers well and fires the procedure outside its applicability boundary."""

    fixture_name = "Over Transfer Fixture"
    respects_boundary = False
