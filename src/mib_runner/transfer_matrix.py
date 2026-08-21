"""The 2x2 transfer diagnostic matrix (M6.2).

Two axes, Content Formation and Routing, each either Automatic or Oracle:

                        ROUTING
                    Automatic    Oracle
    CONTENT  Auto      AA          AO
             Oracle    OA          OO

``AA`` is the ordinary ``full`` condition: the real deployed behaviour.
``AO`` asks whether the system forms useful content when routing is perfect.
``OA`` asks whether routing is the bottleneck when content quality is perfect.
``OO`` is an uptake ceiling — can the Agent use an ideal procedure at all? — and
is explicitly not a deployable method.

Cell construction, for one annotated Ability:

    B   supporting Experience removed, nothing supplied
    AA  supporting Experience present, nothing supplied
    AO  supporting Experience present, the system's own best-matching formed
        artifact surfaced at task time            (needs a Memory Adapter)
    OA  supporting Experience removed, the canonical oracle artifact placed in
        the past stream where the Experience was  (black-box compatible)
    OO  supporting Experience removed, the canonical oracle artifact surfaced
        at task time                              (black-box compatible)

OA and OO both carry oracle content and differ only in *when* it is available,
which is what isolates Routing.  AA and AO both carry automatic content and
differ only in routing, which is what isolates Formation.

Every cell keeps the same Scenario Instance, the same repetition, the same
future Probe, the same future world, and the same Agent seed as its ``full``
control, so the cells are paired.

Diagnostic runs are returned separately and are never merged into the report's
``results.runs``: they must not touch Template aggregation, the Causal Score,
Coverage, or the MIB Score.
"""

from __future__ import annotations

from typing import Any, Callable

from .memory_adapter import select_artifact_for_ability, supports_memory_adapter
from .runner import run_condition
from .transfer import RECALL_PREFIX, TransferAbility, TransferSupport, parse_transfer_support

CELL_CONDITIONS = {
    "B": "transfer_b",
    "AO": "transfer_ao",
    "OA": "transfer_oa",
    "OO": "transfer_oo",
}


def eligible_transfer_templates(templates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Templates the diagnostic cells can actually run against.

    A Template is eligible only when it declares a Transfer Support Annotation,
    at least one annotated Probe, and at least one oracle Skill artifact.
    Without an oracle artifact there is no ceiling, and every efficiency ratio
    would be undefined rather than informative.
    """
    out = []
    for template in templates:
        support = parse_transfer_support(template)
        if support is None:
            continue
        if not annotated_probe_ids(support) or not abilities_with_oracle(support):
            continue
        out.append(template)
    return out


def annotated_probe_ids(support: TransferSupport) -> list[str]:
    return [r.probe_id for r in support.probe_relations]


def abilities_with_oracle(support: TransferSupport) -> list[TransferAbility]:
    return [a for a in support.abilities if a.oracle_artifact]


def baseline_excluded_event_ids(scenario: dict[str, Any], support: TransferSupport) -> set[str]:
    """Events whose removal takes the annotated support away.

    Every declared causal information set is removed, not just one: redundant
    support means ablating a single set may not degrade anything, and a
    baseline that still contains a surviving support set is not a baseline.
    """
    excluded: set[str] = set()
    for ability in support.abilities:
        for group in ability.causal_information_sets:
            excluded.update(group)
    if not excluded:
        # No Ability is declared (an unsupported-novel Template). The baseline is
        # then "no past at all": every Agent-visible past event is withheld.
        for event in scenario.get("timeline") or []:
            if event.get("visibility") in {"agent", "both"} and event.get("stage") != "pre_probe":
                excluded.add(str(event["id"]))
    return excluded


def _last_support_anchor(scenario: dict[str, Any], support: TransferSupport) -> str | None:
    """The Timeline event after which oracle content enters the past stream.

    Oracle content must occupy the same temporal slot as the Experience it
    replaces, or the OA cell would also change the retention interval.
    """
    excluded = baseline_excluded_event_ids(scenario, support)
    last = None
    for event in scenario.get("timeline") or []:
        if str(event.get("id")) in excluded:
            last = str(event["id"])
    return last


def _oracle_contents(support: TransferSupport, probe_id: str) -> list[str]:
    """Canonical artifact text for the Abilities this Probe expects to transfer."""
    relation = next((r for r in support.probe_relations if r.probe_id == probe_id), None)
    if relation is None:
        return []
    out = []
    for ability_id in relation.ability_ids:
        ability = support.ability(ability_id)
        artifact = ability.oracle_artifact if ability else None
        if artifact and artifact.get("content"):
            out.append(str(artifact["content"]))
    return out


def _pool_contents(support: TransferSupport) -> list[str]:
    return [str(a.oracle_artifact["content"]) for a in abilities_with_oracle(support)]


def _formed_contents(agent: Any, support: TransferSupport, probe_id: str) -> tuple[list[str], list[dict[str, Any]]]:
    """Oracle routing over the system's own formed artifacts."""
    export = agent.export_artifacts({"scope": "all"}) or {}
    artifacts = list(export.get("artifacts") or [])
    relation = next((r for r in support.probe_relations if r.probe_id == probe_id), None)
    contents: list[str] = []
    evidence: list[dict[str, Any]] = []
    for ability_id in (relation.ability_ids if relation else ()):
        ability = support.ability(ability_id)
        if ability is None:
            continue
        chosen, score = select_artifact_for_ability(artifacts, ability)
        evidence.append({
            "ability_id": ability_id,
            "matched": chosen is not None,
            "match_score": score,
            "candidate_count": len(artifacts),
        })
        if chosen and chosen.get("content"):
            contents.append(str(chosen["content"]))
    return contents, evidence


def _prefixed(contents: list[str]) -> list[str]:
    return [RECALL_PREFIX + c for c in contents]


def run_transfer_matrix(
    *,
    scenario: dict[str, Any],
    agent_factory: Callable[[], Any],
    repetition: int = 0,
    agent_seed: int | str | None = None,
    cells: tuple[str, ...] = ("B", "OA", "OO", "AO"),
) -> list[dict[str, Any]]:
    """Run the diagnostic cells for one Scenario Instance.

    Returns diagnostic run records.  ``AO`` is skipped when the Agent exposes no
    Memory Adapter, which is the normal case for a black-box Track B system:
    the remaining cells still yield Routing Efficiency and the uptake ceiling.
    """
    support = parse_transfer_support(scenario)
    if support is None:
        return []
    probe_ids = annotated_probe_ids(support)
    if not probe_ids:
        return []

    excluded = baseline_excluded_event_ids(scenario, support)
    anchor = _last_support_anchor(scenario, support)
    pool = _pool_contents(support)
    runs: list[dict[str, Any]] = []

    def execute(cell: str, **kwargs: Any) -> dict[str, Any]:
        run = run_condition(
            scenario=scenario,
            agent=agent_factory(),
            condition=CELL_CONDITIONS[cell],
            repetition=repetition,
            agent_seed=agent_seed,
            probe_ids=set(probe_ids),
            **kwargs,
        )
        run.setdefault("extensions", {})["mib.transfer.cell"] = cell
        return run

    if "B" in cells:
        runs.append(execute("B", excluded_event_ids=excluded))

    if "OA" in cells and pool and anchor is not None:
        # Oracle content in the pool, the system's own routing.
        runs.append(execute(
            "OA",
            excluded_event_ids=excluded,
            past_injections=[(anchor, c) for c in _prefixed(pool)],
        ))

    if "OO" in cells and pool:
        # Oracle content, oracle routing: the uptake ceiling.
        injections = {pid: _prefixed(_oracle_contents(support, pid)) for pid in probe_ids}
        injections = {k: v for k, v in injections.items() if v}
        if injections:
            runs.append(execute("OO", excluded_event_ids=excluded, pre_probe_injections=injections))

    if "AO" in cells:
        probe_agent = agent_factory()
        try:
            decomposable = supports_memory_adapter(probe_agent)
        finally:
            close = getattr(probe_agent, "close", None)
            if callable(close):
                try:
                    close()
                except TypeError:
                    pass
        if decomposable:
            runs.append(_run_ao_cell(
                scenario=scenario,
                agent_factory=agent_factory,
                support=support,
                probe_ids=probe_ids,
                repetition=repetition,
                agent_seed=agent_seed,
            ))
    return [r for r in runs if r is not None]


def _run_ao_cell(
    *,
    scenario: dict[str, Any],
    agent_factory: Callable[[], Any],
    support: TransferSupport,
    probe_ids: list[str],
    repetition: int,
    agent_seed: int | str | None,
) -> dict[str, Any] | None:
    """Automatic content under oracle routing.

    Formation runs first on the untouched past so the system forms whatever it
    forms; the evaluator then selects from those artifacts and surfaces the
    selection at task time in a second, paired run.
    """
    formation_agent = agent_factory()
    try:
        run_condition(
            scenario=scenario,
            agent=formation_agent,
            condition=CELL_CONDITIONS["AO"],
            repetition=repetition,
            agent_seed=agent_seed,
            probe_ids=set(),
        )
        contents_by_probe: dict[str, list[str]] = {}
        evidence: list[dict[str, Any]] = []
        for probe_id in probe_ids:
            contents, rows = _formed_contents(formation_agent, support, probe_id)
            evidence.extend({"probe_id": probe_id, **row} for row in rows)
            if contents:
                contents_by_probe[probe_id] = _prefixed(contents)
    finally:
        close = getattr(formation_agent, "close", None)
        if callable(close):
            try:
                close()
            except TypeError:
                pass

    run = run_condition(
        scenario=scenario,
        agent=agent_factory(),
        condition=CELL_CONDITIONS["AO"],
        repetition=repetition,
        agent_seed=agent_seed,
        probe_ids=set(probe_ids),
        pre_probe_injections=contents_by_probe,
    )
    run.setdefault("extensions", {})["mib.transfer.cell"] = "AO"
    run["extensions"]["mib.transfer.routing_evidence"] = evidence
    return run


def run_transfer_matrix_pack(
    *,
    instances: list[dict[str, Any]],
    agent_factory: Callable[[], Any],
    repetitions: int,
    seed_for: Callable[[dict[str, Any], int], int | str] | None = None,
) -> list[dict[str, Any]]:
    """Run the diagnostic cells across every annotated Scenario Instance."""
    out: list[dict[str, Any]] = []
    for instance in instances:
        if parse_transfer_support(instance) is None:
            continue
        seed_alias = (instance.get("instantiation") or {}).get("seed", "instance")
        for rep in range(repetitions):
            agent_seed = seed_for(instance, rep) if seed_for else f"{seed_alias}:{rep}"
            out.extend(run_transfer_matrix(
                scenario=instance,
                agent_factory=agent_factory,
                repetition=rep,
                agent_seed=agent_seed,
            ))
    return out
