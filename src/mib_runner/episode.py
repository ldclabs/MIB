"""Shared generated episode identity and completeness checks for all entry points."""
from __future__ import annotations

from collections import defaultdict
from typing import Any


def validate_generated_instances(profile: dict[str, Any], instances: list[dict[str, Any]], *,
                                 require_programs: bool = True) -> None:
    from .generate.base import template_id_for
    from .generate.registry import resolve_program_config
    configs = [resolve_program_config(e, profile.get('ladder')) for e in profile['programs']]
    by_template = {template_id_for(c['id']): c for c in configs}
    if len(by_template) != len(configs):
        raise ValueError('duplicate generated Program')
    units: dict[tuple[str, Any], set[int]] = defaultdict(set)
    seen = set()
    for instance in instances:
        inst = instance['instantiation']
        config = by_template.get(inst['template_id'])
        rung = inst['rung']
        if (config is None or type(rung) is not int or not 0 <= rung < len(config['ladder'])
                or inst.get('program') != config['id'] or inst.get('program_version') != config['version']
                or inst.get('interference_count') != config['ladder'][rung]):
            raise ValueError('generated Instance Program/ladder differs from the Profile')
        key = (inst['template_id'], inst['seed'], rung)
        if key in seen:
            raise ValueError('duplicate generated Instance')
        seen.add(key)
        units[key[:2]].add(rung)
    if require_programs and {tid for tid, _ in units} != set(by_template):
        raise ValueError('generated pack must contain every Program')
    if any(rungs != set(range(len(by_template[tid]['ladder']))) for (tid, _), rungs in units.items()):
        raise ValueError('generated pack must contain every rung for every seed')


def materialize_episode_plan(profile: dict[str, Any], seeds: list[int | str], *,
                             static_templates: list[dict[str, Any]] | None = None):
    """Program IDs never include rung: rung belongs to the Instance identity."""
    if not seeds or len(set(seeds)) != len(seeds):
        raise ValueError('episode plan needs distinct nonempty seeds')
    if profile.get('programs'):
        from .generate import generate_pack
        templates, instances = generate_pack(profile, seeds)
        validate_generated_instances(profile, instances)
        return templates, instances
    from .materialize import materialize
    templates = list(static_templates or [])
    if not templates:
        raise ValueError('static episode plan needs templates')
    from .scoring import instance_key
    instances = [materialize(t, seed) for t in templates for seed in seeds]
    keys = [instance_key(instance) for instance in instances]
    if len(keys) != len(set(keys)):
        raise ValueError('duplicate static Instance; use repetitions for an already materialized scenario')
    return templates, instances
