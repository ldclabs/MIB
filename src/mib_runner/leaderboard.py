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
    for rank, row in enumerate(rows, 1):
        entries.append({
            "rank": rank,
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
    }


def _load_report(path: str) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _profile_weights(report: dict[str, Any]) -> dict[str, float]:
    return {d["dimension"]: float(d.get("weight", 0.0)) for d in report["aggregates"]["dimensions"]}


def _instance_map(report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {x["scenario_instance_id"]: x for x in report["aggregates"]["scenario_instances"]}


def paired_compare_reports(report_a: dict[str, Any], report_b: dict[str, Any], *, resamples: int = 5000, seed: int | str = 20260819, confidence_level: float = 0.95) -> dict[str, Any]:
    """Paired hierarchical comparison using public aggregate evidence.

    Public M4/M5 reports retain per-instance dimension scores but redact raw runs.
    We pair on opaque instance aliases, resample Templates then Instances, and
    preserve the same paired instance in both systems.
    """
    family_a = result_family(report_a["benchmark"]["profile"]["id"])
    family_b = result_family(report_b["benchmark"]["profile"]["id"])
    if family_a != family_b:
        raise ValueError(f"cannot compare across result families: {family_a} vs {family_b}")
    a = _instance_map(report_a); b = _instance_map(report_b)
    common_ids = sorted(set(a) & set(b))
    if not common_ids:
        raise ValueError("reports have no common paired Scenario Instance aliases")
    by_template: dict[str, list[str]] = {}
    for iid in common_ids:
        ta, tb = a[iid]["template_id"], b[iid]["template_id"]
        if ta != tb:
            continue
        by_template.setdefault(ta, []).append(iid)
    if not by_template:
        raise ValueError("reports have no common paired Template/Instance evidence")

    weights = _profile_weights(report_a)
    dims = sorted(weights)
    rng = random.Random(str(seed))

    def sampled_delta() -> tuple[float, dict[str, float]]:
        sampled_templates = [rng.choice(list(by_template)) for _ in range(len(by_template))]
        dim_values: dict[str, list[float]] = {d: [] for d in dims}
        for tid in sampled_templates:
            ids = by_template[tid]
            sampled_ids = [rng.choice(ids) for _ in range(len(ids))]
            for d in dims:
                vals=[]
                for iid in sampled_ids:
                    da=(a[iid].get("dimension_scores") or {}).get(d)
                    db=(b[iid].get("dimension_scores") or {}).get(d)
                    if da is not None and db is not None:
                        vals.append(100.0*(float(da)-float(db)))
                if vals:
                    dim_values[d].append(sum(vals)/len(vals))
        dd={d:(sum(v)/len(v) if v else 0.0) for d,v in dim_values.items()}
        denom=sum(weights.values()) or 1.0
        overall=sum(weights[d]*dd[d] for d in dims)/denom
        return overall,dd

    boot=[]; boot_dims={d:[] for d in dims}
    for _ in range(resamples):
        x, dd=sampled_delta(); boot.append(x)
        for d in dims: boot_dims[d].append(dd[d])
    alpha=1-confidence_level
    point=float(report_a["aggregates"]["mib_score"]["final_score"])-float(report_b["aggregates"]["mib_score"]["final_score"])
    ci={"lower":percentile(boot,alpha/2),"upper":percentile(boot,1-alpha/2),"level":confidence_level,"method":"paired_hierarchical_bootstrap_public_aggregates","resamples":resamples,"seed":seed}
    return {
        "kind":"MIBPairedSystemComparison",
        "profile_id":report_a["benchmark"]["profile"]["id"],
        "result_family":family_a,
        "cycle_compatible": report_a["benchmark"]["scenario_pack"]["id"] == report_b["benchmark"]["scenario_pack"]["id"],
        "paired_template_count":len(by_template),
        "paired_instance_count":sum(len(v) for v in by_template.values()),
        "mib_score_delta_a_minus_b":point,
        "paired_ci":ci,
        "statistically_distinguishable_95": not (ci["lower"] <= 0 <= ci["upper"]),
        "dimension_deltas":{
            d:{"mean_bootstrap_delta":sum(boot_dims[d])/len(boot_dims[d]),"ci":{"lower":percentile(boot_dims[d],alpha/2),"upper":percentile(boot_dims[d],1-alpha/2)}}
            for d in dims
        },
    }


def compare_results(db: ServiceDB, result_a: str, result_b: str, **kwargs) -> dict[str, Any]:
    ra=db.result(result_a); rb=db.result(result_b)
    if not ra or not rb: raise KeyError("unknown result id")
    if ra["cycle_id"] != rb["cycle_id"]: raise ValueError("paired comparison requires same evaluation cycle")
    return paired_compare_reports(_load_report(ra["public_report_path"]), _load_report(rb["public_report_path"]), **kwargs)
