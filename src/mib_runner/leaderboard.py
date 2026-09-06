from __future__ import annotations

import json
import math
import random
from pathlib import Path
from typing import Any

from .service_db import ServiceDB

#: Result families.  A leaderboard query must never produce one rank that mixes
#: the controlled synthetic laboratory with the realistic external-task track.
CORE_FAMILY = "core"
TRANSFER_FAMILY = "transfer_diagnostic"
REALITY_FAMILY = "reality"


def result_family(profile: dict[str, Any] | str) -> str:
    """Result family of a Profile, by declaration or by identity prefix."""
    if isinstance(profile, dict):
        declared = profile.get("result_family")
        if declared:
            return str(declared)
        pid = str(profile.get("id", ""))
    else:
        pid = str(profile)
    if pid.startswith("MIB-R-") or pid == "MIB-R":
        return REALITY_FAMILY
    if "Transfer" in pid:
        return TRANSFER_FAMILY
    return CORE_FAMILY


from .scoring import percentile  # noqa: E402


def leaderboard(db: ServiceDB, *, cycle_id: str | None = None, profile_id: str | None = None) -> dict[str, Any]:
    cycle = db.cycle(cycle_id) if cycle_id else db.active_cycle(profile_id)
    if not cycle:
        raise ValueError("no active evaluation cycle")
    rows = db.latest_results_for_cycle(cycle["id"])
    entries = []
    profile = _load_report(cycle['profile_path'])
    excluded = []
    for row in rows:
        from .report import verify_score
        report = _load_report(row['public_report_path'])
        score = report.get('aggregates', {}).get('mib_score', {})
        failures = float(report.get('execution', {}).get('execution_failure_rate', 0))
        if (not score.get('official') or score.get('partial') or row.get('track') != profile.get('track', 'integrated_agent')
                or report['benchmark']['profile'] != {'id': profile['id'], 'version': profile['version']}
                or failures > float(profile.get('max_execution_failure_rate', 0)) or not verify_score(report)['valid']):
            excluded.append(row['id'])
            continue
        entries.append({
            "rank": len(entries) + 1,
            "submission_id": row["submission_id"],
            "display_name": row["display_name"],
            "owner": row.get("owner"),
            "track": row.get("track"),
            "score": row["score"],
            "ci": {"lower": row["ci_lower"], "upper": row["ci_upper"]} if row.get("ci_lower") is not None else None,
            "result_id": row["id"],
            "public_report_ref": f"/results/{row['id']}/report",
            "attestation_ref": f"/results/{row['id']}/attestation",
            "attestation": json.loads(row["attestation_signature_json"]),
        })
    family = result_family(cycle["profile_id"])
    return {
        "mib": "0.1",
        "kind": "MIBLeaderboard",
        "cycle_id": cycle["id"],
        "profile_id": cycle["profile_id"],
        "result_family": family,
        "cross_family_ranking": False,
        "entries": entries,
        "excluded_ineligible_count": len(excluded),
    }


def _load_report(path: str) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _profile_weights(report: dict[str, Any]) -> dict[str, float]:
    return {d["dimension"]: float(d.get("weight", 0.0)) for d in report["aggregates"]["dimensions"]}


def _instance_map(report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {x["scenario_instance_id"]: x for x in report["aggregates"]["scenario_instances"]}


def paired_compare_reports(report_a: dict[str, Any], report_b: dict[str, Any], *, resamples: int = 5000, seed: int | str = 20260819, confidence_level: float = 0.95) -> dict[str, Any]:
    """Bootstrap the same canonical score functional used to publish the points."""
    from .aggregation import canonical_instances, score_aggregates
    import copy
    if resamples < 1 or not 0 < confidence_level < 1:
        raise ValueError("positive resamples and a confidence level inside (0, 1) are required")
    family_a = result_family(report_a['benchmark']['profile']['id'])
    family_b = result_family(report_b['benchmark']['profile']['id'])
    if family_a != family_b:
        raise ValueError(f"cannot compare across result families: {family_a} vs {family_b}")
    for key in ['profile', 'track', 'scale', 'scenario_pack', 'scoring_spec_version']:
        if report_a['benchmark'].get(key) != report_b['benchmark'].get(key):
            raise ValueError(f"paired comparison requires identical {key}")
    if report_a.get('evaluation_policy') != report_b.get('evaluation_policy'):
        raise ValueError('paired comparison requires identical evaluation policies')
    if _profile_weights(report_a) != _profile_weights(report_b):
        raise ValueError('paired comparison requires identical dimension weights')
    if report_a.get('retention') or report_b.get('retention'):
        canonical_a = {x['template_id']: x.get('canonical_rung') for x in report_a.get('retention', [])}
        canonical_b = {x['template_id']: x.get('canonical_rung') for x in report_b.get('retention', [])}
        if canonical_a != canonical_b or len(set(canonical_a.values())) != 1:
            raise ValueError('paired comparison requires identical canonical rungs')
        canonical = next(iter(canonical_a.values()))
    else:
        canonical = None
    policy = report_a.get('evaluation_policy') or {}
    profile = copy.deepcopy(policy.get('profile') or {'dimensions': {d: {'weight': w} for d, w in _profile_weights(report_a).items()}})
    profile['canonical_rung'] = canonical
    generated = bool(profile.get('programs')) or canonical is not None
    templates = policy.get('templates') or [{'id': t['template_id'], 'version': t.get('template_version'),
                  'scoring': {'dimension_weights': t.get('dimension_weights', {})}}
                 for t in report_a['aggregates']['templates']]
    a = {x['scenario_instance_id']: x for x in canonical_instances(report_a['aggregates']['scenario_instances'], profile)}
    b = {x['scenario_instance_id']: x for x in canonical_instances(report_b['aggregates']['scenario_instances'], profile)}
    if not a or set(a) != set(b):
        raise ValueError('paired comparison requires complete identical Scenario Instance coverage')
    by_template = {}
    for iid in sorted(a):
        if a[iid]['template_id'] != b[iid]['template_id']:
            raise ValueError('paired Template mismatch')
        by_template.setdefault(a[iid]['template_id'], []).append(iid)
    tids = [t['id'] for t in templates]
    if set(tids) != set(by_template):
        raise ValueError('paired comparison requires every required Template')
    template_map = {t['id']: t for t in templates}
    def score(rows, ts):
        return score_aggregates(rows, ts, profile)
    point_a, point_b = score(list(a.values()), templates), score(list(b.values()), templates)
    for report, point in [(report_a, point_a), (report_b, point_b)]:
        if not math.isclose(point['score'], float(report['aggregates']['mib_score']['final_score']), abs_tol=1e-9):
            raise ValueError('published score does not match paired evidence')
    rng = random.Random(str(seed))
    boot, boot_dims = [], {d: [] for d in _profile_weights(report_a)}
    attempts = 0
    while len(boot) < resamples and attempts < resamples * 1000:
        attempts += 1
        chosen = tids if generated else [rng.choice(tids) for _ in tids]
        ts, ra, rb = [], [], []
        for index, tid in enumerate(chosen):
            alias = f'draw-{index}'
            ts.append({**template_map[tid], 'id': alias})
            for iid in [rng.choice(by_template[tid]) for _ in by_template[tid]]:
                ra.append({**a[iid], 'template_id': alias})
                rb.append({**b[iid], 'template_id': alias})
        sa, sb = score(ra, ts), score(rb, ts)
        if any(d['weight'] > 0 and d['coverage'] == 0 for d in sa['dimensions']):
            continue
        boot.append(sa['score'] - sb['score'])
        db = {d['dimension']: d['score'] for d in sb['dimensions']}
        for d in sa['dimensions']:
            boot_dims[d['dimension']].append(d['score'] - db[d['dimension']])
    if len(boot) != resamples:
        raise ValueError('insufficient complete bootstrap draws')
    alpha = 1 - confidence_level
    ci = {'lower': percentile(boot, alpha/2), 'upper': percentile(boot, 1-alpha/2), 'level': confidence_level,
          'method': 'paired_canonical_instance_bootstrap' if generated else 'paired_hierarchical_bootstrap_public_aggregates',
          'resamples': resamples, 'seed': seed}
    return {'kind': 'MIBPairedSystemComparison', 'profile_id': report_a['benchmark']['profile']['id'],
            'result_family': family_a, 'cycle_compatible': True, 'paired_template_count': len(tids),
            'paired_instance_count': len(a), 'mib_score_delta_a_minus_b': point_a['score'] - point_b['score'],
            'paired_ci': ci, 'statistically_distinguishable': not(ci['lower'] <= 0 <= ci['upper']),
            **({'statistically_distinguishable_95': not(ci['lower'] <= 0 <= ci['upper'])} if confidence_level == 0.95 else {}),
            'dimension_deltas': {d: {'mean_bootstrap_delta': sum(v)/len(v),
                'ci': {'lower': percentile(v, alpha/2), 'upper': percentile(v, 1-alpha/2)}} for d, v in boot_dims.items()}}


def compare_results(db: ServiceDB, result_a: str, result_b: str, **kwargs) -> dict[str, Any]:
    ra=db.result(result_a); rb=db.result(result_b)
    if not ra or not rb: raise KeyError("unknown result id")
    if ra["cycle_id"] != rb["cycle_id"]: raise ValueError("paired comparison requires same evaluation cycle")
    return paired_compare_reports(_load_report(ra["public_report_path"]), _load_report(rb["public_report_path"]), **kwargs)
