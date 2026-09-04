"""Reality Transfer Graph (M6.4).

The evaluator-private claim about which past task supports which held-out task,
through which reusable Ability:

    TrainTask-17 ──supports──►  Ability-A
    TrainTask-29 ──supports──►  Ability-A
    Ability-A    ──applies──►   TestTask-42
    Ability-A    ──near_match_but_not_applicable──►  TestTask-51
    Ability-A + Ability-B  ──compose──►  TestTask-77

The graph MUST NOT be participant-visible during official evaluation.  A public
MIB-R pack carries only a digest and a private reference that resolves inside
the evaluator environment; transfer graphs are especially vulnerable to
adaptive reverse engineering across repeated submissions.
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .transfer import (
    ABILITY_OPTIONAL_RELATIONS,
    NEGATIVE_CONTROL_RELATIONS,
    POSITIVE_RELATIONS,
    RELATION_DISTANCE_CLASS,
    RELATIONS,
)

#: Environment variable that overrides where a private graph resolves, so a
#: public pack can name a reference that only exists on the evaluator host.
GRAPH_ROOT_ENV = "MIB_REALITY_GRAPH_ROOT"


class RealityGraphError(ValueError):
    pass


@dataclass(frozen=True)
class RealityAbility:
    id: str
    kind: str
    oracle_artifact: dict[str, Any] | None
    label: str = ""


@dataclass(frozen=True)
class RealitySupportEdge:
    source_task_ids: tuple[str, ...]
    ability_ids: tuple[str, ...]
    target_task_id: str
    relation: str
    support_expected: bool
    #: Every acquisition task the target's correct answer actually depends on.
    #: On a near-match edge this differs from ``source_task_ids``: the named
    #: Ability is the one that must be *withheld*, while the target still needs
    #: whatever governs it correctly.  The irrelevant-ablation control removes
    #: only tasks outside this set, so "irrelevant" never means "load-bearing".
    causal_task_ids: tuple[str, ...] = ()

    @property
    def distance_class(self) -> str | None:
        return RELATION_DISTANCE_CLASS.get(self.relation) if self.support_expected else None


@dataclass(frozen=True)
class RealityTransferGraph:
    abilities: tuple[RealityAbility, ...]
    edges: tuple[RealitySupportEdge, ...]
    raw: dict[str, Any]

    def ability(self, ability_id: str) -> RealityAbility | None:
        return next((a for a in self.abilities if a.id == ability_id), None)

    def edge_for(self, target_task_id: str) -> RealitySupportEdge | None:
        return next((e for e in self.edges if e.target_task_id == target_task_id), None)

    def supporting_task_ids(self, target_task_id: str) -> tuple[str, ...]:
        edge = self.edge_for(target_task_id)
        return edge.source_task_ids if edge else ()

    def causal_task_ids(self, target_task_id: str) -> tuple[str, ...]:
        edge = self.edge_for(target_task_id)
        return edge.causal_task_ids if edge else ()

    def abilities_for(self, target_task_id: str) -> tuple[RealityAbility, ...]:
        edge = self.edge_for(target_task_id)
        if edge is None:
            return ()
        return tuple(a for a in (self.ability(x) for x in edge.ability_ids) if a is not None)

    @property
    def digest(self) -> str:
        blob = json.dumps(self.raw, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        return "sha256:" + hashlib.sha256(blob.encode("utf-8")).hexdigest()


def parse_reality_graph(raw: dict[str, Any]) -> RealityTransferGraph:
    abilities = tuple(
        RealityAbility(
            id=str(a["id"]),
            kind=str(a.get("kind", "custom")),
            oracle_artifact=dict(a["oracle_artifact"]) if isinstance(a.get("oracle_artifact"), dict) else None,
            label=str(a.get("label") or a["id"]),
        )
        for a in raw.get("abilities") or []
    )
    edges = tuple(
        RealitySupportEdge(
            source_task_ids=tuple(str(x) for x in e.get("source_task_ids") or ()),
            ability_ids=tuple(str(x) for x in e.get("ability_ids") or ()),
            target_task_id=str(e["target_task_id"]),
            relation=str(e.get("relation", "custom")),
            support_expected=bool(e.get("support_expected", False)),
            causal_task_ids=tuple(str(x) for x in (e.get("causal_task_ids") or e.get("source_task_ids") or ())),
        )
        for e in raw.get("edges") or []
    )
    return RealityTransferGraph(abilities=abilities, edges=edges, raw=raw)


def resolve_graph_path(pack_path: str | Path, private_ref: str) -> Path:
    """Resolve a private graph reference.

    ``MIB_REALITY_GRAPH_ROOT`` wins, so a published pack can name a reference
    that exists only inside the evaluator environment.
    """
    root = os.environ.get(GRAPH_ROOT_ENV)
    base = Path(root) if root else Path(pack_path).parent
    candidate = (base / private_ref).resolve()
    if not candidate.exists():
        raise RealityGraphError(
            f"private Reality Transfer Graph not resolvable: {private_ref} "
            f"(searched {base}; set {GRAPH_ROOT_ENV} to the evaluator graph root)"
        )
    return candidate


def load_reality_graph(pack_path: str | Path, pack: dict[str, Any]) -> RealityTransferGraph:
    spec = pack.get("transfer_graph") or {}
    if "edges" in spec:
        # The manifest fields that *carry* the reference are not part of the
        # graph body.  Hashing them together with the graph would make the
        # declared digest self-referential and impossible to satisfy.
        graph = parse_reality_graph({k: v for k, v in spec.items() if k not in {"digest", "private_ref"}})
    else:
        private_ref = spec.get("private_ref")
        if not private_ref:
            raise RealityGraphError("pack declares no transfer_graph.private_ref and no inline graph")
        raw = json.loads(resolve_graph_path(pack_path, private_ref).read_text(encoding="utf-8"))
        graph = parse_reality_graph(raw)
    declared = spec.get("digest")
    if declared and declared != graph.digest:
        raise RealityGraphError(f"transfer graph digest mismatch: manifest {declared} != resolved {graph.digest}")
    return graph


def validate_reality_graph(
    graph: RealityTransferGraph,
    *,
    train_task_ids: set[str],
    test_task_ids: set[str],
) -> list[dict[str, Any]]:
    """Semantic validation, mirroring the Scenario-side transfer validator."""
    findings: list[dict[str, Any]] = []

    def fail(code: str, message: str, **scope: Any) -> None:
        findings.append({"severity": "error", "code": code, "message": message, **scope})

    def warn(code: str, message: str, **scope: Any) -> None:
        findings.append({"severity": "warning", "code": code, "message": message, **scope})

    seen: set[str] = set()
    for ability in graph.abilities:
        if ability.id in seen:
            fail("reality.duplicate_ability", f"duplicate Ability id {ability.id}", ability_id=ability.id)
        seen.add(ability.id)

    targets: set[str] = set()
    for edge in graph.edges:
        scope = {"target_task_id": edge.target_task_id}
        if edge.target_task_id in targets:
            fail("reality.duplicate_edge", f"duplicate edge for {edge.target_task_id}", **scope)
        targets.add(edge.target_task_id)
        if edge.target_task_id not in test_task_ids:
            fail("reality.unknown_target", f"edge targets unknown test task {edge.target_task_id}", **scope)
        for tid in (*edge.source_task_ids, *edge.causal_task_ids):
            if tid not in train_task_ids:
                fail("reality.unknown_source", f"edge references unknown train task {tid}", **scope)
        for aid in edge.ability_ids:
            if aid not in seen:
                fail("reality.unknown_ability", f"edge references unknown Ability {aid}", **scope)
        if edge.relation not in RELATIONS:
            fail("reality.unknown_relation", f"unknown relation {edge.relation}", **scope)
        if edge.support_expected and edge.relation in NEGATIVE_CONTROL_RELATIONS:
            fail("reality.relation_conflict", f"{edge.relation} is a negative control and cannot expect support", **scope)
        if not edge.support_expected and edge.relation in POSITIVE_RELATIONS:
            fail("reality.relation_conflict", f"{edge.relation} is a positive class and requires support_expected=true", **scope)
        if edge.support_expected and not edge.source_task_ids:
            fail("reality.support_without_source", f"{edge.target_task_id} expects support but names no train task", **scope)
        if not edge.ability_ids and edge.relation not in ABILITY_OPTIONAL_RELATIONS:
            fail("reality.edge_without_ability", f"{edge.relation} requires at least one Ability", **scope)
        if edge.relation == "compositional_transfer" and len(edge.ability_ids) < 2:
            warn("reality.composition_needs_two", f"{edge.target_task_id} declares composition with fewer than two Abilities", **scope)

    missing = sorted(test_task_ids - targets)
    if missing:
        warn("reality.unannotated_test_task", f"held-out tasks with no transfer edge: {missing}")

    relations = {e.relation for e in graph.edges}
    for required in ("near_match_non_applicable", "unsupported_novel"):
        if required not in relations:
            warn(
                "reality.missing_negative_control",
                f"no {required} edge: a memory system should also be scored on staying neutral, "
                "not only on helping when support exists",
            )
    return findings


def redact_reality_graph(graph: RealityTransferGraph) -> dict[str, Any]:
    """Participant-safe projection: counts, never structure.

    A public surface must never let a participant reconstruct which hidden
    train task supports which hidden test task.
    """
    relation_counts: dict[str, int] = {}
    distance_counts: dict[str, int] = {}
    for edge in graph.edges:
        relation_counts[edge.relation] = relation_counts.get(edge.relation, 0) + 1
        cls = edge.distance_class
        if cls:
            distance_counts[cls] = distance_counts.get(cls, 0) + 1
    return {
        "ability_count": len(graph.abilities),
        "edge_count": len(graph.edges),
        "relations": dict(sorted(relation_counts.items())),
        "distance_classes": dict(sorted(distance_counts.items())),
        "digest": graph.digest,
        "statement": "The Reality Transfer Graph — Abilities, support edges, and oracle Skill content — is evaluator-only.",
    }
