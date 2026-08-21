"""Optional Memory Adapter (M6.2, Level B diagnostics).

MIB evaluates black-box Agents first.  A participant MUST NOT be required to
expose internal memory implementation details to receive a valid MIB score, and
the official Track B path stays usable without anything in this module.

A Memory Adapter is what a *decomposable* memory system may additionally
expose so the evaluator can separate Formation from Routing:

    Experience -> Formation -> artifacts -> Routing -> Uptake

Three of the four diagnostic cells (AA, OA, OO) are reachable through the
ordinary Agent Adapter alone, because the evaluator can withhold the supporting
Experience and surface a canonical artifact through the observation channel.
Only ``AO`` — the system's *own* formed content under oracle routing — requires
reaching into the memory system, which is what ``export_artifacts`` is for.

The Protocol here is synchronous, unlike the async sketch in the handoff.  The
in-process Agent Adapter in ``types.py`` is synchronous, and the first
implementation is in-process by design; introducing an event loop into the
Runner for one optional diagnostic would destabilize the M4/M5 external Agent
path for no benefit.  An HTTP or stdio Memory Adapter transport can adopt async
at the transport boundary later without changing this contract.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class MIBMemoryAdapter(Protocol):
    """Decomposable memory system interface.

    Every method takes and returns a JSON object so the same shape can later be
    carried over a wire transport unchanged.  No method may require chain of
    thought, and none of them is required for a black-box submission.
    """

    def describe_memory(self) -> dict[str, Any]:
        """Capabilities of this memory system: which methods are meaningful."""

    def reset_memory(self, request: dict[str, Any]) -> dict[str, Any]:
        """Return the memory system to its run-start state."""

    def observe_memory_event(self, request: dict[str, Any]) -> dict[str, Any]:
        """Offer one Experience event to Formation."""

    def consolidate_memory(self, request: dict[str, Any]) -> dict[str, Any]:
        """Run whatever offline compilation the system performs."""

    def export_artifacts(self, request: dict[str, Any]) -> dict[str, Any]:
        """Return the persistent artifacts Formation produced.

        ``metadata.source_event_ids`` is a diagnostic only.  It is self-reported
        and MUST NOT be trusted as ground truth for scoring or for oracle
        routing; the evaluator matches artifacts against its own Ability
        annotation instead.
        """

    def retrieve_artifacts(self, request: dict[str, Any]) -> dict[str, Any]:
        """Return what the system's *own* Routing would select for a task."""

    def inject_artifacts(self, request: dict[str, Any]) -> dict[str, Any]:
        """Place evaluator-supplied artifacts into the memory pool."""


@dataclass(frozen=True)
class MemoryArtifact:
    artifact_id: str
    artifact_type: str
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_json(self) -> dict[str, Any]:
        return {
            "artifact_id": self.artifact_id,
            "artifact_type": self.artifact_type,
            "content": self.content,
            "metadata": dict(self.metadata),
        }


def supports_memory_adapter(agent: Any) -> bool:
    """True when an Agent also exposes enough of the Memory Adapter for ``AO``."""
    return callable(getattr(agent, "export_artifacts", None))


_TOKEN = re.compile(r"[a-z0-9_]+")
_STOPWORDS = frozenset(
    """a an and are as at be before by for from in into is it its of on or that the then to when with
    your you we our this these those not no do does did have has had""".split()
)


def _tokens(text: str) -> set[str]:
    return {t for t in _TOKEN.findall(str(text).casefold()) if t not in _STOPWORDS and len(t) > 2}


def ability_reference_text(ability: Any) -> str:
    """Evaluator-side canonical description of an Ability, for artifact matching."""
    parts: list[str] = [getattr(ability, "label", "") or ""]
    raw = getattr(ability, "raw", {}) or {}
    artifact = raw.get("oracle_artifact") or {}
    parts.append(str(artifact.get("content") or ""))
    procedure = raw.get("procedure") or {}
    parts.extend(str(x) for x in procedure.get("ordered_steps") or ())
    parts.append(str(procedure.get("description") or ""))
    applicability = raw.get("applicability") or {}
    for key in ("positive_cues", "required_world_predicates"):
        parts.extend(str(x) for x in applicability.get(key) or ())
    return " ".join(p for p in parts if p)


def select_artifact_for_ability(
    artifacts: list[dict[str, Any]],
    ability: Any,
) -> tuple[dict[str, Any] | None, float]:
    """Oracle routing over a system's own formed artifacts.

    The evaluator selects the formed artifact closest to its own canonical
    description of the Ability.  Self-reported ``source_event_ids`` only break
    ties, so a system cannot win the AO cell by labelling an unusable artifact
    with the right provenance.
    """
    reference = _tokens(ability_reference_text(ability))
    support = {str(x) for x in getattr(ability, "support_event_ids", ()) or ()}
    best: dict[str, Any] | None = None
    # 0.0 is the floor, not a sentinel: an artifact that shares nothing with the
    # evaluator's description of the Ability was not routed, and reporting it as
    # a match would make "formed nothing usable" indistinguishable from
    # "formed something and the router picked it".
    best_score = 0.0
    for artifact in artifacts:
        candidate = _tokens(artifact.get("content", ""))
        if not reference or not candidate:
            overlap = 0.0
        else:
            overlap = len(reference & candidate) / len(reference | candidate)
        claimed = {str(x) for x in (artifact.get("metadata") or {}).get("source_event_ids") or ()}
        tiebreak = 1e-6 * len(claimed & support)
        score = overlap + tiebreak
        if score > best_score:
            best, best_score = artifact, score
    if best is None:
        return None, 0.0
    return best, max(0.0, best_score)


class InProcessMemoryAdapter:
    """Minimal reference Memory Adapter for in-process fixtures and tests.

    It is a demonstration of the contract, not a benchmark baseline claim.
    """

    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []
        self.artifacts: list[MemoryArtifact] = []
        self.injected: list[MemoryArtifact] = []

    def describe_memory(self) -> dict[str, Any]:
        return {
            "protocol": "mib-memory/0.1",
            "implementation": {"name": "MIB In-Process Memory Adapter", "version": "0.1.0"},
            "capabilities": {
                "export_artifacts": True,
                "retrieve_artifacts": True,
                "inject_artifacts": True,
                "consolidate_memory": True,
            },
        }

    def reset_memory(self, request: dict[str, Any] | None = None) -> dict[str, Any]:
        self.events.clear()
        self.artifacts.clear()
        self.injected.clear()
        return {"accepted": True}

    def observe_memory_event(self, request: dict[str, Any]) -> dict[str, Any]:
        self.events.append(dict(request))
        return {"accepted": True}

    def consolidate_memory(self, request: dict[str, Any] | None = None) -> dict[str, Any]:
        return {"accepted": True, "artifact_count": len(self.artifacts)}

    def export_artifacts(self, request: dict[str, Any] | None = None) -> dict[str, Any]:
        return {"artifacts": [a.to_json() for a in (*self.artifacts, *self.injected)]}

    def retrieve_artifacts(self, request: dict[str, Any] | None = None) -> dict[str, Any]:
        query = _tokens((request or {}).get("goal") or "")
        scored = []
        for artifact in (*self.artifacts, *self.injected):
            candidate = _tokens(artifact.content)
            overlap = len(query & candidate) / len(query | candidate) if query and candidate else 0.0
            scored.append((overlap, artifact))
        scored.sort(key=lambda x: x[0], reverse=True)
        limit = int((request or {}).get("limit", 3))
        return {"artifacts": [a.to_json() for _, a in scored[:limit]]}

    def inject_artifacts(self, request: dict[str, Any]) -> dict[str, Any]:
        added = []
        for raw in request.get("artifacts") or []:
            artifact = MemoryArtifact(
                artifact_id=str(raw.get("artifact_id") or f"injected-{len(self.injected)}"),
                artifact_type=str(raw.get("artifact_type") or "skill"),
                content=str(raw.get("content") or ""),
                metadata=dict(raw.get("metadata") or {}),
            )
            self.injected.append(artifact)
            added.append(artifact.artifact_id)
        return {"accepted": True, "artifact_ids": added}
