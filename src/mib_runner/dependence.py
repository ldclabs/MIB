"""Fixed-opportunity twin evidence; repetitions stay inside Instances.

Measurement 0.5.0 gates on the content-following effect: for every frozen
changed-probe opportunity, whether the output carries the twin value under
the twin history minus whether it already carried that value under the
original history. The denominator is fixed, correctness never selects it,
and a system with no memory or a constant answer has an expected effect of
zero, independent of its accuracy. Joint twin success (both answers fully
correct) remains a diagnostic; it approximates accuracy squared and is not a
dependence test. Conditional tracking remains a diagnostic in scoring.py.
"""
from __future__ import annotations

import random
from collections import defaultdict
from .scoring import mean, ci_percentile

METRIC = 'joint_twin_success'
CFE_METRIC = 'content_following_effect'


def counterfactual_plan(scenario):
    probes = {p['id']: p for p in scenario.get('probes', [])}
    return [{'ablation_id': a['id'], 'probe_id': pid, 'dimensions': probes[pid].get('dimensions', [])}
            for a in scenario.get('ablations', [])
            if a['kind'] in {'counterfactual_content', 'counterfactual_policy'}
            for pid in sorted(set(a.get('probes', []))) if float(probes[pid].get('weight', 1)) > 0]


def joint_evidence(runs):
    rows = defaultdict(list)
    # Runs from measurement 0.5.0 carry cross-oracle matches; older reports
    # keep exactly their original evidence rows.
    with_cross = any('counterfactual_cross' in p for r in runs if r['condition'] == 'full' for p in r.get('probe_results', []))
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
            follows_twin = valid and bool((probe.get('counterfactual') or {}).get('follows'))
            follows_full = valid and bool((original.get('counterfactual_cross') or {}).get(opportunity['ablation_id']))
            for dimension in opportunity['dimensions']:
                rows[dimension].append((int(valid), int(success), int(follows_twin), int(follows_full)))
    out = []
    for d, values in sorted(rows.items()):
        row = {'dimension': d, 'total_n': len(values), 'valid_n': sum(v[0] for v in values),
               'successes': sum(v[1] for v in values), 'joint_score': mean([v[1] for v in values])}
        if with_cross:
            row.update(twin_follow_n=sum(v[2] for v in values), full_follow_n=sum(v[3] for v in values),
                       content_following_effect=mean([v[2] - v[3] for v in values]))
        out.append(row)
    return out


def joint_dependence(instances, profile, field='joint_score', metric=METRIC):
    """Stratified Instance-cluster gate for one per-Instance evidence field."""
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
            if row is None or not row['total_n'] or field not in row:
                continue
            strata[inst['template_id']].append(float(row[field]))
            total += row['total_n']; valid += row['valid_n']
            complete_instances += int(row['valid_n'] == row['total_n'])
        n = sum(map(len, strata.values()))
        value = mean([mean(scores) for scores in strata.values()]) if n else None
        ci = None
        if n and valid:
            seed = str(policy.get('bootstrap_seed', 'joint-twin-v1' if metric == METRIC else 'content-following-v1')) + ':' + d
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
            metric: value, 'instance_tracking_lower_bound': ci['lower'] if ci else None, 'ci': ci})
    assessable = any(d['eligible'] is not None for d in dimensions)
    return {'metric': metric, 'floor': floor,
        metric: mean([d[metric] for d in dimensions if d[metric] is not None]) if assessable else None,
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
    metric = profile.get('memory_dependence', {}).get('metric')
    if metric == METRIC:
        legacy.update(joint_dependence(units, profile))
    elif metric == CFE_METRIC:
        joint = joint_dependence(units, profile)
        legacy.update(joint_dependence(units, profile, field=CFE_METRIC, metric=CFE_METRIC))
        legacy[METRIC] = joint[METRIC]
        for row in legacy['dimensions']:
            row[METRIC] = next((j[METRIC] for j in joint['dimensions'] if j['dimension'] == row['dimension']), None)
    return legacy
