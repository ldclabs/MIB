"""Shared generated episode identity and completeness checks for all entry points."""
from __future__ import annotations

from collections import defaultdict
from typing import Any


def validate_seeds(seeds: list[int | str]) -> None:
    # The generators and Instance IDs both render seeds as text.
    if not seeds or len({str(seed) for seed in seeds}) != len(seeds):
        raise ValueError('episode plan needs distinct nonempty seeds')


def validate_instance_keys(instances: list[dict[str, Any]]) -> None:
    from .scoring import instance_key
    keys = [instance_key(instance) for instance in instances]
    if len(set(keys)) != len(keys):
        raise ValueError('duplicate Instance; use repetitions for an already materialized scenario')


def validate_generated_instances(profile: dict[str, Any], instances: list[dict[str, Any]], *,
                                 require_programs: bool = True) -> None:
    from .generate.base import template_id_for
    from .generate.registry import profile_program_configs
    configs = profile_program_configs(profile)
    by_template = {template_id_for(c['id']): c for c in configs}
    units: dict[tuple[str, Any], set[int]] = defaultdict(set)
    validate_instance_keys(instances)
    for instance in instances:
        inst = instance['instantiation']
        config = by_template.get(inst['template_id'])
        rung = inst['rung']
        if (config is None or type(rung) is not int or not 0 <= rung < len(config['ladder'])
                or inst.get('program') != config['id'] or inst.get('program_version') != config['version']
                or inst.get('interference_count') != config['ladder'][rung]):
            raise ValueError('generated Instance Program/ladder differs from the Profile')
        rungs = units[(inst['template_id'], inst['seed'])]
        if rung in rungs:
            raise ValueError('duplicate generated Instance')
        rungs.add(rung)
    if require_programs and {tid for tid, _ in units} != set(by_template):
        raise ValueError('generated pack must contain every Program')
    if any(rungs != set(range(len(by_template[tid]['ladder']))) for (tid, _), rungs in units.items()):
        raise ValueError('generated pack must contain every rung for every seed')


def materialize_episode_plan(profile: dict[str, Any], seeds: list[int | str], *,
                             static_templates: list[dict[str, Any]] | None = None):
    """Program IDs never include rung: rung belongs to the Instance identity."""
    validate_seeds(seeds)
    if profile.get('programs'):
        from .generate import generate_pack
        templates, instances = generate_pack(profile, seeds)
        validate_generated_instances(profile, instances)
        return templates, instances
    from .materialize import materialize
    templates = list(static_templates or [])
    if not templates:
        raise ValueError('static episode plan needs templates')
    instances = [materialize(t, seed) for t in templates for seed in seeds]
    validate_instance_keys(instances)
    return templates, instances
