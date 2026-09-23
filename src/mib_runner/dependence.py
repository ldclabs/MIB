"""Fixed-opportunity joint twin evidence; repetitions stay inside Instances.

Conditional tracking remains a diagnostic in scoring.py. Admission never
selects its denominator using the participant's full-condition correctness.
"""
from __future__ import annotations

import random
from collections import defaultdict
from .scoring import mean, ci_percentile

METRIC = 'joint_twin_success'


def counterfactual_plan(scenario):
    probes = {p['id']: p for p in scenario.get('probes', [])}
    return [{'ablation_id': a['id'], 'probe_id': pid, 'dimensions': probes[pid].get('dimensions', [])}
            for a in scenario.get('ablations', [])
            if a['kind'] in {'counterfactual_content', 'counterfactual_policy'}
            for pid in sorted(set(a.get('probes', []))) if float(probes[pid].get('weight', 1)) > 0]


def joint_evidence(runs):
    rows = defaultdict(list)
    for full in (r for r in runs if r['condition'] == 'full'):
        plan = full.get('validity', {}).get('counterfactual_plan', [])
        base = {p['probe_id']: p for p in full.get('probe_results', [])}
        twins = {r.get('ablation_id'): r for r in runs
                 if r['condition'] == 'counterfactual_content' and r['repetition'] == full['repetition']}
        for opportunity in plan:
            twin = twins.get(opportunity['ablation_id'], {})
            probe = next((p for p in twin.get('probe_results', []) if p['probe_id'] == opportunity['probe_id']), {})
            original = base.get(opportunity['probe_id'], {})
            valid = (full.get('validity', {}).get('runner_valid') is True
                     and twin.get('validity', {}).get('runner_valid') is True
                     and twin.get('validity', {}).get('causal_pair_valid') is True
                     and original.get('outcome') == probe.get('outcome') == 'scored'
                     and float(probe.get('weight', 0)) > 0)
            success = valid and float(original.get('score', 0)) >= 1 and float(probe.get('score', 0)) >= 1
            for dimension in opportunity['dimensions']:
                rows[dimension].append((int(valid), int(success)))
    return [{'dimension': d, 'total_n': len(values), 'valid_n': sum(v for v, _ in values),
             'successes': sum(s for _, s in values), 'joint_score': mean([s for _, s in values])}
            for d, values in sorted(rows.items())]


def joint_dependence(instances, profile):
    policy = profile['memory_dependence']
    floor = float(policy.get('floor', .5))
    level = float(policy.get('confidence_level', .95))
    resamples = int(policy.get('bootstrap_resamples', 2000))
    if not 0 < level < 1 or resamples < 1:
        raise ValueError('invalid joint dependence confidence policy')
    dimensions = []
    for d, spec in profile.get('dimensions', {}).items():
        if float(spec.get('weight', 0)) <= 0:
            continue
        strata = defaultdict(list)
        total = valid = 0
        complete_instances = 0
        for inst in instances:
            row = next((r for r in inst.get('joint_dependence_evidence', []) if r['dimension'] == d), None)
            if row is None or not row['total_n']:
                continue
            strata[inst['template_id']].append(float(row['joint_score']))
            total += row['total_n']; valid += row['valid_n']
            complete_instances += int(row['valid_n'] == row['total_n'])
        n = sum(map(len, strata.values()))
        value = mean([mean(scores) for scores in strata.values()]) if n else None
        ci = None
        if n and valid:
            seed = str(policy.get('bootstrap_seed', 'joint-twin-v1')) + ':' + d
            rng = random.Random(seed)
            boot = [mean([mean([rng.choice(scores) for _ in scores]) for _, scores in sorted(strata.items())])
                    for _ in range(resamples)]
            ci = ci_percentile(boot, level, 'stratified_instance_cluster_percentile', resamples, seed)
            ci['degenerate'] = len(set(boot)) == 1
        coverage = valid / total if total else 0
        ok = None if not valid else (complete_instances >= int(policy.get('min_instances', 5))
             and coverage >= float(policy.get('min_coverage', 1)) and ci['lower'] >= floor)
        dimensions.append({'dimension': d, 'eligible': ok, 'eligible_n': valid, 'total_n': total,
            'coverage': coverage, 'eligible_instances': complete_instances, 'independent_instances': n,
            'joint_twin_success': value, 'instance_tracking_lower_bound': ci['lower'] if ci else None, 'ci': ci})
    assessable = any(d['eligible'] is not None for d in dimensions)
    return {'metric': METRIC, 'floor': floor,
        METRIC: mean([d[METRIC] for d in dimensions if d[METRIC] is not None]) if assessable else None,
        'eligible': all(d['eligible'] is True for d in dimensions) if assessable else None,
        'eligible_n': sum(d['eligible_n'] for d in dimensions), 'total_n': sum(d['total_n'] for d in dimensions),
        'dimensions': dimensions,
        'interval_scope': 'Fixed Program strata; empirical Instance bootstrap. Degenerate/small-sample intervals do not establish population certainty.'}


def assess_dependence(instances, metrics, profile):
    from .aggregation import canonical_instances, tracking_totals
    from .scoring import aggregate_dependence_evidence, memory_dependence
    units = canonical_instances(instances, profile)
    legacy = memory_dependence(metrics, profile, aggregate_dependence_evidence(units) if profile.get('programs') else None,
                               tracking_totals(units) if profile.get('programs') else None)
    if profile.get('memory_dependence', {}).get('metric') == METRIC:
        legacy.update(joint_dependence(units, profile))
    return legacy
