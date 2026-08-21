"""Transfer Support Annotation (``mib.transfer_support.v1``).

The annotation makes the evaluator's latent transfer hypothesis explicit:

    which past Experience supports which future Probe,
    through which reusable Ability,
    under which applicability boundary?

It is evaluator-only diagnostic metadata.  It is carried inside the Scenario
``extensions`` map so that every existing v0.1 Scenario stays valid and every
existing v0.1 parser can ignore it, and it never reaches the Agent: the Runner
projects Timeline events and Probe inputs, never Scenario extensions.

Parsing here is side-effect free.  Nothing in this module changes a MIB Score.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

TRANSFER_EXTENSION = "mib.transfer_support.v1"
TRANSFER_DIAGNOSTICS_EXTENSION = "mib.transfer_diagnostics.v1"

#: Qualitative support relations.  A relation is *not* a distance: negative
#: controls are a different causal class, not farther positive transfer.
RELATIONS = (
    "exact_replay",
    "supported_transfer",
    "surface_shift",
    "structural_transfer",
    "compositional_transfer",
    "near_match_non_applicable",
    "unsupported_novel",
    "stale_support",
    "harmful_support",
    "historical_only",
    "custom",
)

#: Relations that describe expected positive transfer.
POSITIVE_RELATIONS = frozenset(
    {"exact_replay", "supported_transfer", "surface_shift", "structural_transfer", "compositional_transfer"}
)

#: Relations that are negative controls: memory influence must be withheld.
NEGATIVE_CONTROL_RELATIONS = frozenset(
    {"near_match_non_applicable", "unsupported_novel", "stale_support", "harmful_support"}
)

#: Relations for which an Ability reference is meaningless.
ABILITY_OPTIONAL_RELATIONS = frozenset({"unsupported_novel", "custom"})

#: Canonical positive-transfer distance class per relation.  ``supported_transfer``
#: is the generic positive relation and accepts any class.
RELATION_DISTANCE_CLASS = {
    "exact_replay": "D0",
    "surface_shift": "D1",
    "structural_transfer": "D2",
    "compositional_transfer": "D3",
}

DISTANCE_CLASSES = ("D0", "D1", "D2", "D3")

#: Display-only normalization of the positive-transfer distance ladder.
DISTANCE_NORMALIZED = {"D0": 0.0, "D1": 1.0 / 3.0, "D2": 2.0 / 3.0, "D3": 1.0}

DISTANCE_LABEL = {
    "D0": "Exact Replay",
    "D1": "Surface Shift",
    "D2": "Structural",
    "D3": "Compositional",
}

_ABILITY_DIMENSIONS = frozenset({"skill_learning_transfer", "experience_memory"})


class TransferAnnotationError(ValueError):
    """Raised when an annotation is structurally unusable."""


@dataclass(frozen=True)
class TransferAbility:
    id: str
    kind: str
    support_event_ids: tuple[str, ...]
    counterexample_event_ids: tuple[str, ...]
    raw: dict[str, Any]

    @property
    def label(self) -> str:
        return str(self.raw.get("label") or self.id)

    @property
    def oracle_artifact(self) -> dict[str, Any] | None:
        artifact = self.raw.get("oracle_artifact")
        return dict(artifact) if isinstance(artifact, dict) else None

    @property
    def causal_information_sets(self) -> tuple[tuple[str, ...], ...]:
        """Redundant support sets, defaulting to the single declared support set."""
        sets = self.raw.get("causal_information_sets")
        if not sets:
            return (self.support_event_ids,) if self.support_event_ids else ()
        return tuple(tuple(str(x) for x in s) for s in sets)

    @property
    def minimum_sets_required(self) -> int:
        return int(self.raw.get("minimum_sets_required", 1))


@dataclass(frozen=True)
class ProbeTransferRelation:
    probe_id: str
    ability_ids: tuple[str, ...]
    relation: str
    support_expected: bool
    raw: dict[str, Any]

    @property
    def distance_class(self) -> str | None:
        declared = (self.raw.get("transfer_distance") or {}).get("class")
        if declared:
            return str(declared)
        return RELATION_DISTANCE_CLASS.get(self.relation)

    @property
    def distance_normalized(self) -> float | None:
        cls = self.distance_class
        if cls is None or not self.support_expected:
            return None
        declared = (self.raw.get("transfer_distance") or {}).get("normalized")
        if declared is not None:
            return float(declared)
        return DISTANCE_NORMALIZED.get(cls)

    @property
    def minimum_required_ability_count(self) -> int:
        return int(self.raw.get("minimum_required_ability_count", 1))

    @property
    def expected_behaviour(self) -> str:
        declared = self.raw.get("expected_behaviour")
        if declared:
            return str(declared)
        return "apply" if self.support_expected else "withhold"


@dataclass(frozen=True)
class TransferSupport:
    abilities: tuple[TransferAbility, ...]
    probe_relations: tuple[ProbeTransferRelation, ...]
    raw: dict[str, Any]

    def ability(self, ability_id: str) -> TransferAbility | None:
        return next((a for a in self.abilities if a.id == ability_id), None)

    @property
    def version(self) -> str:
        return str(self.raw.get("version", "1.0.0"))


def _finding(severity: str, code: str, message: str, **scope: Any) -> dict[str, Any]:
    out = {"severity": severity, "code": code, "message": message}
    out.update({k: v for k, v in scope.items() if v is not None})
    return out


def parse_transfer_support(scenario: dict[str, Any]) -> TransferSupport | None:
    """Return the parsed annotation, or ``None`` when the Scenario carries none."""
    raw = (scenario.get("extensions") or {}).get(TRANSFER_EXTENSION)
    if raw is None:
        return None
    if not isinstance(raw, dict):
        raise TransferAnnotationError(f"{TRANSFER_EXTENSION} must be an object")

    abilities = []
    for entry in raw.get("abilities") or []:
        if not isinstance(entry, dict) or "id" not in entry:
            raise TransferAnnotationError("each ability requires an id")
        abilities.append(
            TransferAbility(
                id=str(entry["id"]),
                kind=str(entry.get("kind", "custom")),
                support_event_ids=tuple(str(x) for x in entry.get("support_event_ids") or ()),
                counterexample_event_ids=tuple(str(x) for x in entry.get("counterexample_event_ids") or ()),
                raw=entry,
            )
        )

    relations = []
    for entry in raw.get("probe_relations") or []:
        if not isinstance(entry, dict) or "probe_id" not in entry:
            raise TransferAnnotationError("each probe relation requires a probe_id")
        relations.append(
            ProbeTransferRelation(
                probe_id=str(entry["probe_id"]),
                ability_ids=tuple(str(x) for x in entry.get("ability_ids") or ()),
                relation=str(entry.get("relation", "custom")),
                support_expected=bool(entry.get("support_expected", False)),
                raw=entry,
            )
        )
    return TransferSupport(abilities=tuple(abilities), probe_relations=tuple(relations), raw=raw)


def relation_for_probe(support: TransferSupport, probe_id: str) -> ProbeTransferRelation | None:
    return next((r for r in support.probe_relations if r.probe_id == probe_id), None)


def abilities_for_probe(support: TransferSupport, probe_id: str) -> tuple[TransferAbility, ...]:
    relation = relation_for_probe(support, probe_id)
    if relation is None:
        return ()
    return tuple(a for a in (support.ability(aid) for aid in relation.ability_ids) if a is not None)


def transfer_support_digest(support: TransferSupport | dict[str, Any]) -> str:
    """Stable digest of the annotation, including oracle artifacts.

    Binding this into the private evaluation store means that changing Ability
    support, an oracle artifact, or a transfer relation invalidates a signed
    evaluation cycle instead of silently changing what a diagnostic measured.
    """
    raw = support.raw if isinstance(support, TransferSupport) else support
    payload = json.dumps(raw, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _event_text(scenario: dict[str, Any]) -> dict[str, str]:
    out: dict[str, str] = {}
    for event in scenario.get("timeline") or []:
        parts = [str(event.get("content") or "")]
        payload = event.get("payload")
        if payload is not None:
            parts.append(json.dumps(payload, ensure_ascii=False))
        out[str(event.get("id"))] = " ".join(parts)
    return out


def _secret_strings(scenario: dict[str, Any]) -> list[tuple[str, str]]:
    """Values an oracle artifact must never restate verbatim."""
    out: list[tuple[str, str]] = []
    for probe in scenario.get("probes") or []:
        oracle = probe.get("oracle") or {}
        for value in oracle.get("accepted") or []:
            out.append((f"probe {probe.get('id')} accepted value", str(value)))
        for assertion in oracle.get("world_assertions") or []:
            value = assertion.get("value")
            if isinstance(value, str):
                out.append((f"probe {probe.get('id')} world assertion", value))
    hidden = (scenario.get("world") or {}).get("hidden_ground_truth") or {}
    for key, value in hidden.items():
        if isinstance(value, str):
            out.append((f"hidden_ground_truth.{key}", value))
    return out


def validate_transfer_support(
    scenario: dict[str, Any],
    support: TransferSupport,
) -> list[dict[str, Any]]:
    """Semantic validation of one annotation against its Scenario.

    Returns findings; each carries ``severity`` of ``error`` or ``warning``.
    Schema-shape validation is a separate concern handled by
    ``schemas/mib-transfer-support.schema.json``.
    """
    findings: list[dict[str, Any]] = []
    timeline_ids = {str(e.get("id")) for e in scenario.get("timeline") or []}
    probes = scenario.get("probes") or []
    probe_ids = {str(p.get("id")) for p in probes}
    probes_by_id = {str(p.get("id")): p for p in probes}
    ablations = scenario.get("ablations") or []

    # --- Abilities -------------------------------------------------------
    seen_ability_ids: set[str] = set()
    for ability in support.abilities:
        if ability.id in seen_ability_ids:
            findings.append(_finding("error", "transfer.duplicate_ability", f"duplicate Ability id {ability.id}", ability_id=ability.id))
        seen_ability_ids.add(ability.id)

        if not ability.support_event_ids:
            findings.append(_finding("error", "transfer.empty_support", f"Ability {ability.id} declares no support event", ability_id=ability.id))
        for eid in ability.support_event_ids:
            if eid not in timeline_ids:
                findings.append(_finding("error", "transfer.unknown_event", f"Ability {ability.id} references unknown support event {eid}", ability_id=ability.id))
        for eid in ability.counterexample_event_ids:
            if eid not in timeline_ids:
                findings.append(_finding("error", "transfer.unknown_event", f"Ability {ability.id} references unknown counterexample event {eid}", ability_id=ability.id))
        for index, group in enumerate(ability.raw.get("causal_information_sets") or ()):
            for eid in group:
                if str(eid) not in timeline_ids:
                    findings.append(_finding(
                        "error", "transfer.unknown_event",
                        f"Ability {ability.id} causal_information_sets[{index}] references unknown event {eid}",
                        ability_id=ability.id,
                    ))
        declared_sets = ability.raw.get("causal_information_sets") or ()
        if declared_sets and ability.minimum_sets_required > len(declared_sets):
            findings.append(_finding(
                "error", "transfer.minimum_sets_exceeds_declared",
                f"Ability {ability.id} requires {ability.minimum_sets_required} causal information sets but declares {len(declared_sets)}",
                ability_id=ability.id,
            ))

        overlap = set(ability.counterexample_event_ids) & set(ability.support_event_ids)
        if overlap and overlap == set(ability.support_event_ids):
            findings.append(_finding(
                "error", "transfer.counterexample_is_support",
                f"Ability {ability.id} declares its entire support set as counterexample; the applicability boundary is undefined",
                ability_id=ability.id,
            ))
        elif overlap:
            findings.append(_finding(
                "warning", "transfer.counterexample_overlaps_support",
                f"Ability {ability.id} counterexample events {sorted(overlap)} also appear in its support set",
                ability_id=ability.id,
            ))

        artifact = ability.oracle_artifact
        if artifact:
            content = str(artifact.get("content") or "")
            folded = content.casefold()
            for where, secret in _secret_strings(scenario):
                needle = secret.strip()
                if len(needle) < 3 or needle.startswith("${"):
                    continue
                if needle.casefold() in folded:
                    findings.append(_finding(
                        "error", "transfer.oracle_artifact_leak",
                        f"Ability {ability.id} oracle artifact restates {where} ({needle!r}); an oracle Skill states a reusable procedure, not the answer",
                        ability_id=ability.id,
                    ))

    # --- Probe relations -------------------------------------------------
    seen_relation_probes: set[str] = set()
    for relation in support.probe_relations:
        scope = {"probe_id": relation.probe_id}
        if relation.probe_id in seen_relation_probes:
            findings.append(_finding("error", "transfer.duplicate_relation", f"duplicate Probe relation for {relation.probe_id}", **scope))
        seen_relation_probes.add(relation.probe_id)

        if relation.probe_id not in probe_ids:
            findings.append(_finding("error", "transfer.unknown_probe", f"relation references unknown Probe {relation.probe_id}", **scope))

        for aid in relation.ability_ids:
            if aid not in seen_ability_ids:
                findings.append(_finding("error", "transfer.unknown_ability", f"Probe {relation.probe_id} references unknown Ability {aid}", **scope))

        if relation.relation not in RELATIONS:
            findings.append(_finding("error", "transfer.unknown_relation", f"Probe {relation.probe_id} declares unknown relation {relation.relation}", **scope))

        if relation.support_expected and not relation.ability_ids:
            findings.append(_finding(
                "error", "transfer.support_without_ability",
                f"Probe {relation.probe_id} expects support but declares no Ability",
                **scope,
            ))
        if not relation.ability_ids and relation.relation not in ABILITY_OPTIONAL_RELATIONS:
            findings.append(_finding(
                "error", "transfer.relation_without_ability",
                f"Probe {relation.probe_id} relation {relation.relation} requires at least one Ability reference",
                **scope,
            ))
        declares_minimum = "minimum_required_ability_count" in relation.raw
        if (declares_minimum or relation.ability_ids) and relation.minimum_required_ability_count > len(relation.ability_ids):
            findings.append(_finding(
                "error", "transfer.minimum_ability_count",
                f"Probe {relation.probe_id} requires {relation.minimum_required_ability_count} Abilities but declares {len(relation.ability_ids)}",
                **scope,
            ))

        if relation.support_expected and relation.relation == "unsupported_novel":
            findings.append(_finding("error", "transfer.relation_conflict", f"Probe {relation.probe_id} cannot be unsupported_novel with support_expected=true", **scope))
        if not relation.support_expected and relation.relation == "exact_replay":
            findings.append(_finding("error", "transfer.relation_conflict", f"Probe {relation.probe_id} cannot be exact_replay with support_expected=false", **scope))
        if relation.support_expected and relation.relation in NEGATIVE_CONTROL_RELATIONS:
            findings.append(_finding(
                "error", "transfer.relation_conflict",
                f"Probe {relation.probe_id} relation {relation.relation} is a negative control and cannot expect support",
                **scope,
            ))
        if not relation.support_expected and relation.relation in POSITIVE_RELATIONS:
            findings.append(_finding(
                "error", "transfer.relation_conflict",
                f"Probe {relation.probe_id} relation {relation.relation} is a positive transfer class and requires support_expected=true",
                **scope,
            ))

        declared_distance = relation.raw.get("transfer_distance") or {}
        if declared_distance:
            if not relation.support_expected:
                findings.append(_finding(
                    "error", "transfer.distance_on_negative_control",
                    f"Probe {relation.probe_id} is a negative control; a negative control is a different causal class, not a farther distance",
                    **scope,
                ))
            expected_class = RELATION_DISTANCE_CLASS.get(relation.relation)
            declared_class = str(declared_distance.get("class"))
            if expected_class and declared_class != expected_class:
                findings.append(_finding(
                    "error", "transfer.distance_relation_mismatch",
                    f"Probe {relation.probe_id} relation {relation.relation} implies {expected_class} but declares {declared_class}",
                    **scope,
                ))
            normalized = declared_distance.get("normalized")
            canonical = DISTANCE_NORMALIZED.get(declared_class)
            if normalized is not None and canonical is not None and abs(float(normalized) - canonical) > 0.01:
                findings.append(_finding(
                    "warning", "transfer.distance_normalization",
                    f"Probe {relation.probe_id} declares normalized={normalized} for {declared_class}; canonical value is {canonical:.2f}",
                    **scope,
                ))
        elif relation.support_expected and relation.relation == "supported_transfer":
            findings.append(_finding(
                "warning", "transfer.distance_unspecified",
                f"Probe {relation.probe_id} uses the generic supported_transfer relation without a transfer_distance class",
                **scope,
            ))

        if relation.relation == "compositional_transfer" and len(relation.ability_ids) < 2:
            findings.append(_finding(
                "warning", "transfer.composition_needs_two",
                f"Probe {relation.probe_id} declares compositional transfer with fewer than two Abilities",
                **scope,
            ))

        if relation.support_expected:
            covered = any(
                a.get("kind") == "relevant_memory" and relation.probe_id in (a.get("probes") or [])
                for a in ablations
            )
            if not covered:
                findings.append(_finding(
                    "warning", "transfer.no_relevant_ablation",
                    f"Probe {relation.probe_id} expects positive transfer but no relevant_memory Ablation targets it",
                    **scope,
                ))

        if relation.relation == "near_match_non_applicable":
            has_counterexample = any(
                (support.ability(aid).counterexample_event_ids if support.ability(aid) else ())
                for aid in relation.ability_ids
            )
            has_control = any(
                a.get("kind") in {"counterexample", "harmful_memory"} and relation.probe_id in (a.get("probes") or [])
                for a in ablations
            )
            if not has_counterexample and not has_control:
                findings.append(_finding(
                    "warning", "transfer.near_match_without_boundary",
                    f"Probe {relation.probe_id} is a near-match trap but no counterexample event or counterexample/harmful Ablation defines the boundary",
                    **scope,
                ))

    # --- Coverage --------------------------------------------------------
    for pid, probe in probes_by_id.items():
        if pid in seen_relation_probes:
            continue
        dims = set(probe.get("dimensions") or [])
        if dims & _ABILITY_DIMENSIONS:
            findings.append(_finding(
                "warning", "transfer.unannotated_probe",
                f"Probe {pid} carries {sorted(dims & _ABILITY_DIMENSIONS)} but has no transfer relation",
                probe_id=pid,
            ))

    return findings


def inspect_transfer(scenario: dict[str, Any], *, schema: dict[str, Any] | None = None) -> dict[str, Any]:
    """Summarize the annotation of one Scenario.

    The output names Ability IDs, so it is evaluator-internal for Hidden and
    Private Holdout content.
    """
    out: dict[str, Any] = {
        "scenario_id": scenario.get("id"),
        "annotated": False,
        "abilities": 0,
        "annotated_probes": 0,
        "relations": {},
        "distance_classes": {},
        "oracle_artifacts": 0,
        "errors": [],
        "warnings": [],
    }
    try:
        support = parse_transfer_support(scenario)
    except TransferAnnotationError as exc:
        out["errors"].append(str(exc))
        return out
    if support is None:
        return out

    out["annotated"] = True
    out["annotation_version"] = support.version
    out["abilities"] = len(support.abilities)
    out["annotated_probes"] = len(support.probe_relations)
    out["oracle_artifacts"] = sum(1 for a in support.abilities if a.oracle_artifact)
    out["digest"] = transfer_support_digest(support)

    relations: dict[str, int] = {}
    distances: dict[str, int] = {}
    for relation in support.probe_relations:
        relations[relation.relation] = relations.get(relation.relation, 0) + 1
        cls = relation.distance_class if relation.support_expected else None
        if cls:
            distances[cls] = distances.get(cls, 0) + 1
    out["relations"] = dict(sorted(relations.items()))
    out["distance_classes"] = dict(sorted(distances.items()))

    if schema is not None:
        import jsonschema

        validator = jsonschema.Draft202012Validator(schema)
        for err in sorted(validator.iter_errors(support.raw), key=lambda e: list(e.path)):
            where = "/".join(str(x) for x in err.path)
            out["errors"].append(f"schema:{where or '$'}: {err.message}")

    for finding in validate_transfer_support(scenario, support):
        bucket = "errors" if finding["severity"] == "error" else "warnings"
        out[bucket].append(f"{finding['code']}: {finding['message']}")
    return out


def transfer_coverage(scenarios: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate annotation coverage across a Template pack."""
    annotated_templates = 0
    annotated_probes = 0
    relations: dict[str, int] = {}
    distances: dict[str, int] = {}
    for scenario in scenarios:
        support = parse_transfer_support(scenario)
        if support is None:
            continue
        annotated_templates += 1
        annotated_probes += len(support.probe_relations)
        for relation in support.probe_relations:
            relations[relation.relation] = relations.get(relation.relation, 0) + 1
            cls = relation.distance_class if relation.support_expected else None
            if cls:
                distances[cls] = distances.get(cls, 0) + 1
    return {
        "annotated_templates": annotated_templates,
        "annotated_probes": annotated_probes,
        "relations": dict(sorted(relations.items())),
        "distance_classes": dict(sorted(distances.items())),
    }


def check_profile_transfer_coverage(profile: dict[str, Any], coverage: dict[str, Any]) -> list[dict[str, Any]]:
    """Compare declared ``transfer_coverage.required_relations`` against a pack."""
    required = ((profile.get("transfer_coverage") or {}).get("required_relations")) or {}
    observed = coverage.get("relations") or {}
    findings: list[dict[str, Any]] = []
    for relation, minimum in sorted(required.items()):
        have = int(observed.get(relation, 0))
        if have < int(minimum):
            findings.append(_finding(
                "error", "transfer.coverage_shortfall",
                f"profile requires {minimum} '{relation}' relation(s); pack declares {have}",
                relation=relation,
            ))
    return findings
