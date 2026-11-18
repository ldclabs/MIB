"""Program registry and pack generation."""

from __future__ import annotations

import copy
from typing import Any

from .base import ScenarioBuilder, template_id_for
from .surface import validate_bank
from .programs import PROGRAM_CLASSES, Program
from .extended import EXTENDED_PROGRAM_CLASSES
from .products import PRODUCT_PROGRAM_CLASSES
from .challenges import CHALLENGE_PROGRAM_CLASSES

PROGRAMS: dict[str, type[Program]] = {cls.ID: cls for cls in PROGRAM_CLASSES + EXTENDED_PROGRAM_CLASSES + PRODUCT_PROGRAM_CLASSES + CHALLENGE_PROGRAM_CLASSES}


class UnknownProgram(KeyError):
    pass


def _program(program_id: str) -> Program:
    try:
        return PROGRAMS[program_id]()
    except KeyError as exc:
        raise UnknownProgram(f"unknown program {program_id!r}; known: {sorted(PROGRAMS)}") from exc


def program_descriptor(program_id: str) -> dict[str, Any]:
    """The Template-shaped descriptor a pack report aggregates a program under."""
    p = _program(program_id)
    return {
        "mib": "0.2",
        "kind": "MemoryEpisodeProgram",
        "id": template_id_for(p.ID),
        "version": p.VERSION,
        "title": p.TITLE,
        "suite": p.SUITE,
        "dimensions": list(p.DIMENSIONS),
        "requirements": {"black_box_compatible": True, "capabilities": list(p.CAPABILITIES)},
        "template": {"program": {"id": p.ID, "version": p.VERSION, "ladder": list(p.LADDER)}},
        "world": {"clock": {"mode": "virtual", "start": "2026-01-01T09:00:00Z", "timezone": "UTC"}, "state": {}},
        "timeline": [],
        "probes": [],
        "evaluators": [],
        "scoring": {"probe_aggregation": "weighted_mean", "score_range": {"min": 0, "max": 100}, "dimension_weights": dict(p.WEIGHTS)},
    }


def resolve_program_config(entry: str | dict[str, Any], default_ladder: list[int] | None = None) -> dict[str, Any]:
    """Resolve the same Program overrides for public, private and calibration packs."""
    entry = entry if isinstance(entry, dict) else {'id': entry}
    p = _program(entry['id'])
    steps = list(entry.get('ladder', default_ladder if default_ladder is not None else p.LADDER))
    if not steps or any(type(step) is not int or step < 0 for step in steps):
        raise ValueError('Program ladder must contain nonnegative integer counts')
    return {'id': p.ID, 'version': p.VERSION, 'ladder': steps, 'params': dict(entry.get('params') or {})}


def profile_program_configs(profile: dict[str, Any]) -> list[dict[str, Any]]:
    configs = [resolve_program_config(entry, profile.get("ladder")) for entry in profile["programs"]]
    if len({c["id"] for c in configs}) != len(configs):
        raise ValueError("duplicate generated Program")
    canonical = profile.get("canonical_rung")
    if canonical is not None and any(type(canonical) is not int or not 0 <= canonical < len(c["ladder"]) for c in configs):
        raise ValueError("the canonical rung must exist on every Program ladder")
    return configs


def generate_instance(program_id: str, seed: int | str, *, rung: int = 0, ladder: list[int] | None = None,
                      session_boundary: bool = False, parameters: dict[str, Any] | None = None,
                      surface_bank: dict[str, Any] | None = None) -> dict[str, Any]:
    """Materialize one Instance.

    ``surface_bank`` is an evaluator-private surface realization (see
    ``generate.surface.templates_for``). It changes wording only; semantic
    sampling, world-model assertions and Oracles are unchanged.
    """
    if surface_bank is not None:
        validate_bank(surface_bank)
    p = _program(program_id)
    steps = resolve_program_config(program_id, ladder)['ladder']
    if rung < 0 or rung >= len(steps):
        raise ValueError(f"rung {rung} outside ladder {steps}")
    builder = ScenarioBuilder(
        program_id=p.ID, program_version=p.VERSION, seed=seed, rung=rung, interference_count=int(steps[rung]),
        title=p.TITLE, suite=p.SUITE, dimensions=list(p.DIMENSIONS), dimension_weights=dict(p.WEIGHTS),
        capabilities=list(p.CAPABILITIES), session_boundary=session_boundary, parameters=parameters,
        surface_bank=surface_bank,
    )
    p.build(builder)
    return builder.finalize()


def generate_pack(profile: dict[str, Any], seeds: list[int | str] | None = None) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Materialize every (program, seed, rung) of a Profile: returns (descriptors, instances)."""
    if not profile.get("programs"):
        raise ValueError("profile declares no programs")
    from ..episode import validate_seeds
    seeds = list(seeds if seeds is not None else profile.get("instance_seeds", [101, 202]))
    validate_seeds(seeds)
    descriptors, instances = [], []
    for config in profile_program_configs(profile):
        pid, steps, parameters = config['id'], config['ladder'], config['params']
        descriptor = program_descriptor(pid)
        boundary = bool(profile.get('measurement_regime', {}).get('session_boundary'))
        descriptor['template']['program'].update(config, session_boundary=boundary)
        if profile.get("surface_bank") is not None:
            descriptor['template']['program']['surface_bank'] = copy.deepcopy(profile['surface_bank'])
        if boundary:
            descriptor['requirements']['capabilities'].append('session_boundary')
        descriptors.append(descriptor)
        for seed in seeds:
            for rung in range(len(steps)):
                instances.append(generate_instance(pid, seed, rung=rung, ladder=steps, session_boundary=boundary, parameters=parameters, surface_bank=profile.get("surface_bank")))
    return descriptors, instances
