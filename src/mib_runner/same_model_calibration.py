from __future__ import annotations

import copy
import hashlib
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from .benchmark import build_instance_aggregate, validate_causal_pairs
from .calibration import DEFAULT_THRESHOLDS, _baseline_stat, _metric, _recommend, load_private_templates
from .materialize import materialize
from .model_clients import build_model_client, DeterministicStubModelClient
from .runner import run_condition, run_scenario
from .same_model_agent import InvocationRecorder, SameModelAgent, load_prompt
from .experimental.transfer import oracle_artifact_bundle_digest
from .experimental.transfer_diagnostics import DEFAULT_EPSILON, build_transfer_diagnostics
from .experimental.transfer_matrix import eligible_transfer_templates, run_transfer_matrix
from .validation import load_json, validate_scenario


CONDITIONS = ["B0", "B1", "B2", "B3"]

#: Optional transfer diagnostic cells. ``AO`` needs a decomposable Memory
#: Adapter, which the Same-Model Agent does not expose, so a Same-Model run
#: yields Routing Efficiency and the uptake ceiling but not Formation
#: Efficiency. That is reported, not silently omitted.
TRANSFER_CELLS = ["B", "OA", "OO"]
_KIND_TO_CONDITION = {
    "relevant_memory": "relevant_ablation",
    "irrelevant_memory": "irrelevant_ablation",
    "no_memory": "no_memory",
    "stale_memory": "stale_memory",
    "harmful_memory": "harmful_memory",
    "counterexample": "counterexample",
}


from .util import utc_now  # noqa: E402


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(path: str | Path) -> str:
    return sha256_bytes(Path(path).read_bytes())


def canonical_digest(obj: Any) -> str:
    return sha256_bytes(json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8"))


def directory_digest(root: str | Path, pattern: str = "MIB-*.json") -> str:
    root = Path(root)
    rows = []
    for p in sorted(root.rglob(pattern)):
        rows.append((str(p.relative_to(root)), sha256_file(p)))
    return canonical_digest(rows)


def _resolve(base: Path, value: str) -> Path:
    p = Path(value)
    return p if p.is_absolute() else (base / p).resolve()


def load_experiment(path: str | Path) -> tuple[dict[str, Any], dict[str, Path]]:
    path = Path(path).resolve()
    cfg = json.loads(path.read_text(encoding="utf-8"))
    base = path.parent
    paths = {
        "pack": _resolve(base, cfg["pack"]),
        "scenario_schema": _resolve(base, cfg["scenario_schema"]),
        "profile": _resolve(base, cfg["profile"]),
        "system_prompt": _resolve(base, cfg["agent"]["system_prompt"]),
        "reasoning_policy": _resolve(base, cfg["agent"]["reasoning_policy"]),
    }
    return cfg, paths


def build_experiment_lock(cfg: dict[str, Any], paths: dict[str, Path]) -> dict[str, Any]:
    model_public = copy.deepcopy(cfg["model"])
    # Secret values are never stored in the experiment lock. Header values are
    # fingerprinted so behavior-affecting configuration remains bound without
    # exposing credentials.
    headers = dict(model_public.pop("headers", {}) or {})
    header_fingerprints = {k: sha256_bytes(str(v).encode("utf-8")) for k, v in sorted(headers.items())}
    lock = {
        "kind": "MIBSameModelExperimentLock",
        "version": "0.1.0",
        "experiment_id": cfg["id"],
        "model": {
            "client": model_public.get("client"),
            "model_id": model_public.get("model_id"),
            "endpoint": model_public.get("endpoint"),
            "command": model_public.get("command"),
            "parameters": copy.deepcopy(model_public.get("parameters") or {}),
            "seed_policy": model_public.get("seed_policy", "paired_per_call"),
            "seed_derivation": "agent_seed + semantic_probe_or_task_turn_key; condition label excluded",
            "seed_base": model_public.get("seed_base", "mib-same-model-0.1"),
            "api_key_env": model_public.get("api_key_env"),
            "header_value_fingerprints": header_fingerprints,
            "stateless_contract": True,
        },
        "system_prompt_sha256": sha256_file(paths["system_prompt"]),
        "reasoning_policy_sha256": sha256_file(paths["reasoning_policy"]),
        "scenario_schema_sha256": sha256_file(paths["scenario_schema"]),
        "profile_sha256": sha256_file(paths["profile"]),
        "scenario_pack_sha256": directory_digest(paths["pack"] / "templates"),
        "condition_order_policy": "counterbalanced_latin_rotation_v1",
        "conditions": {
            "B0": {"memory_policy": "no_memory"},
            "B1": {"memory_policy": "full_visible_history"},
            "B2": {"memory_policy": "lexical_top_k", "top_k": int(cfg["agent"].get("retrieval_top_k", 4))},
            "B3": {
                "memory_policy": "structured_deterministic",
                "top_k": int(cfg["agent"].get("structured_top_k", 10)),
                "salient_k": int(cfg["agent"].get("structured_salient_k", 6)),
            },
        },
        "memory_runtime": {
            "memory_char_limits": copy.deepcopy(cfg["agent"].get("memory_char_limits") or {}),
            "parse_retries": int(cfg["agent"].get("parse_retries", 1)),
        },
        "allowed_condition_differences": ["memory_policy", "memory_selection", "memory_context_content"],
    }
    transfer = _transfer_lock_section(cfg, paths)
    if transfer:
        # Only bound when the experiment opts in, so an experiment that runs no
        # transfer cells keeps the lock it already had.
        lock["transfer_diagnostics"] = transfer
    lock["digest"] = "sha256:" + canonical_digest(lock)
    return lock


def _transfer_lock_section(cfg: dict[str, Any], paths: dict[str, Path]) -> dict[str, Any] | None:
    """Bind the transfer diagnostic configuration into the Experiment Lock.

    An oracle artifact edited after the experiment was locked would silently
    change the ceiling every efficiency ratio is measured against, so the
    artifact bundle is bound by digest alongside the routing policy and the
    cell set.
    """
    spec = dict((cfg.get("calibration") or {}).get("transfer_diagnostics") or {})
    if not spec.get("enabled"):
        return None
    templates = load_private_templates(paths["pack"])
    eligible = eligible_transfer_templates(templates)
    return {
        "enabled": True,
        "cells": list(spec.get("cells") or TRANSFER_CELLS),
        "epsilon": float(spec.get("epsilon", DEFAULT_EPSILON)),
        "routing_policy": "evaluator_ability_match_v1",
        "baseline_condition": "B3",
        # Counted, never named: a lock may travel with a calibration report and
        # must not disclose which private Templates carry which annotation.
        "eligible_template_count": len(eligible),
        "oracle_artifact_bundle_sha256": oracle_artifact_bundle_digest(eligible),
    }


def estimate_experiment(cfg: dict[str, Any], templates: list[dict[str, Any]]) -> dict[str, Any]:
    cal = cfg.get("calibration") or {}
    seeds = list(cal.get("instance_seeds") or [101, 202, 303, 404])
    reps = int(cal.get("repetitions", 1))
    cseeds = list(cal.get("causal_instance_seeds") or seeds)
    creps = int(cal.get("causal_repetitions", 1))
    full_condition_runs = len(templates) * len(seeds) * reps * 4
    causal_ablation_runs = sum(
        sum(1 for a in t.get("ablations", []) if a.get("method") == "replay_excluding_events")
        for t in templates
    ) * len(cseeds) * creps
    full_probe_calls_min = sum(len(t.get("probes", [])) for t in templates) * len(seeds) * reps * 4
    causal_probe_calls_min = sum(
        sum(len(a.get("probes", [])) for a in t.get("ablations", []) if a.get("method") == "replay_excluding_events")
        for t in templates
    ) * len(cseeds) * creps
    return {
        "template_count": len(templates),
        "instance_seeds": len(seeds),
        "repetitions": reps,
        "minimum_condition_runs": full_condition_runs + causal_ablation_runs,
        "full_baseline_condition_runs": full_condition_runs,
        "additional_causal_ablation_runs": causal_ablation_runs,
        "minimum_model_turns": full_probe_calls_min + causal_probe_calls_min,
        "note": "ACTION probes may require multiple model turns, so actual model calls can exceed minimum_model_turns.",
    }


def _preflight_statelessness(model_cfg: dict[str, Any], system_prompt: str) -> dict[str, Any]:
    client = build_model_client(model_cfg)
    params = dict(model_cfg.get("parameters") or {})
    if float(params.get("temperature", 0.0)) != 0.0 and "seed" not in params:
        params["seed"] = 1900819
    a = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": 'Statelessness check A. Return exactly: {"type":"message","content":"A"}'},
    ]
    b = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": 'Statelessness check B. Return exactly: {"type":"message","content":"B"}'},
    ]
    try:
        a1 = client.complete(messages=a, parameters=params, request_id="preflight-a1").text.strip()
        _ = client.complete(messages=b, parameters=params, request_id="preflight-b").text.strip()
        a2 = client.complete(messages=a, parameters=params, request_id="preflight-a2").text.strip()
        return {
            "passed": a1 == a2,
            "first_a_digest": "sha256:" + sha256_bytes(a1.encode("utf-8")),
            "second_a_digest": "sha256:" + sha256_bytes(a2.encode("utf-8")),
            "comparison": "exact_text_under_deterministic_or_seeded_parameters",
        }
    except Exception as exc:
        return {"passed": False, "error": repr(exc), "comparison": "preflight_failed"}
    finally:
        try:
            client.close()
        except Exception:
            pass


def _condition_schedule(templates: list[dict[str, Any]], seeds: list[int | str], repetitions: int) -> list[dict[str, Any]]:
    units = []
    idx = 0
    for t in sorted(templates, key=lambda x: x["id"]):
        for seed in seeds:
            for rep in range(repetitions):
                offset = idx % len(CONDITIONS)
                order = CONDITIONS[offset:] + CONDITIONS[:offset]
                units.append({"template_id": t["id"], "seed": seed, "repetition": rep, "order": order})
                idx += 1
    return units


def _schedule_audit(schedule: list[dict[str, Any]]) -> dict[str, Any]:
    positions = {bid: [0, 0, 0, 0] for bid in CONDITIONS}
    for u in schedule:
        for pos, bid in enumerate(u["order"]):
            positions[bid][pos] += 1
    flat = [x for row in positions.values() for x in row]
    return {
        "policy": "counterbalanced_latin_rotation_v1",
        "paired_units": len(schedule),
        "position_counts": positions,
        "max_position_count_difference": max(flat) - min(flat) if flat else 0,
        "balanced": (max(flat) - min(flat) <= 1) if flat else True,
        "schedule_digest": "sha256:" + canonical_digest(schedule),
    }


def _run_interleaved_full(
    *, templates: list[dict[str, Any]], schema: dict[str, Any], factories: dict[str, Callable[[], Any]],
    seeds: list[int | str], repetitions: int,
) -> tuple[dict[str, dict[str, list[dict[str, Any]]]], dict[tuple[Any, ...], dict[str, Any]], list[dict[str, Any]]]:
    template_by_id = {t["id"]: t for t in templates}
    raw: dict[str, dict[str, list[dict[str, Any]]]] = defaultdict(lambda: {bid: [] for bid in CONDITIONS})
    full_runs: dict[tuple[Any, ...], dict[str, Any]] = {}
    schedule = _condition_schedule(templates, seeds, repetitions)
    materialized: dict[tuple[str, str], dict[str, Any]] = {}

    for unit in schedule:
        tid, seed, rep = unit["template_id"], unit["seed"], unit["repetition"]
        t = template_by_id[tid]
        vr = validate_scenario(t, schema)
        if not vr.valid:
            raise ValueError(f"Template {tid} invalid: {vr.errors}")
        mk = (tid, str(seed))
        if mk not in materialized:
            instance = materialize(t, seed)
            vr2 = validate_scenario(instance, schema)
            if not vr2.valid:
                raise ValueError(f"Instance {tid}:{seed} invalid: {vr2.errors}")
            materialized[mk] = instance
        instance = materialized[mk]
        paired_agent_seed = f"same-model:{seed}:{rep}"
        for bid in unit["order"]:
            runs = run_scenario(
                scenario=instance,
                agent_factory=factories[bid],
                include_ablations=False,
                repetition=rep,
                agent_seed=paired_agent_seed,
            )
            full = next(r for r in runs if r["condition"] == "full")
            full_runs[(tid, str(seed), rep, bid)] = full
            raw[tid][bid].append({
                "template_id": tid,
                "seed": seed,
                "repetition": rep,
                "score": float(full.get("scenario_score", 0.0)),
                "probe_scores": {p["probe_id"]: float(p.get("score", 0.0)) for p in full.get("probe_results", [])},
                "status": full.get("status"),
            })
    return raw, full_runs, schedule


def _probe_pairing_audit(full_runs: dict[tuple[Any, ...], dict[str, Any]]) -> dict[str, Any]:
    grouped: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for (tid, seed, rep, bid), run in full_runs.items():
        grouped[(tid, seed, rep)].append(run)
    mismatches = []
    for key, runs in grouped.items():
        digests = [
            json.dumps((r.get("extensions") or {}).get("mib.runner.probe_variant_digests") or {}, sort_keys=True)
            for r in runs
        ]
        if len(set(digests)) != 1:
            mismatches.append({"unit": list(key), "variant_digests": digests})
        seeds = {r.get("agent_seed") for r in runs}
        if len(seeds) != 1:
            mismatches.append({"unit": list(key), "agent_seeds": sorted(str(x) for x in seeds)})
    return {
        "valid": not mismatches,
        "paired_units": len(grouped),
        "mismatch_count": len(mismatches),
        "mismatches": mismatches[:20],
    }


def _run_causal_from_paired_b3(
    *, templates: list[dict[str, Any]], schema: dict[str, Any], factory: Callable[[], Any],
    seeds: list[int | str], repetitions: int, full_runs: dict[tuple[Any, ...], dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    causal: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for t in templates:
        tid = t["id"]
        for seed in seeds:
            instance = materialize(t, seed)
            vr = validate_scenario(instance, schema)
            if not vr.valid:
                raise ValueError(f"Instance {tid}:{seed} invalid: {vr.errors}")
            for rep in range(repetitions):
                full = full_runs.get((tid, str(seed), rep, "B3"))
                if full is None:
                    # Causal seeds may differ from baseline seeds. Create a paired B3 Full.
                    full = run_condition(
                        scenario=instance, agent=factory(), condition="full", repetition=rep,
                        agent_seed=f"same-model:{seed}:{rep}",
                    )
                runs = [full]
                for a in t.get("ablations", []):
                    if a.get("method") != "replay_excluding_events":
                        continue
                    runs.append(run_condition(
                        scenario=instance,
                        agent=factory(),
                        condition=_KIND_TO_CONDITION.get(a["kind"], "custom"),
                        ablation=a,
                        repetition=rep,
                        agent_seed=f"same-model:{seed}:{rep}",
                    ))
                validate_causal_pairs(runs)
                causal[tid].append(build_instance_aggregate(instance, runs))
    return causal


def _run_transfer_cells(
    *, templates: list[dict[str, Any]], schema: dict[str, Any], factory: Callable[[], Any],
    seeds: list[int | str], repetitions: int, full_runs: dict[tuple[Any, ...], dict[str, Any]],
    cells: tuple[str, ...],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    """Run the optional T cells for eligible Templates only.

    T-AA reuses the paired B3 Full run wherever one exists, so a transfer cell
    never re-measures the natural condition against a different model call than
    the causal analysis used.
    """
    eligible = eligible_transfer_templates(templates)
    aa_runs: list[dict[str, Any]] = []
    diagnostic_runs: list[dict[str, Any]] = []
    for t in eligible:
        tid = t["id"]
        for seed in seeds:
            instance = materialize(t, seed)
            vr = validate_scenario(instance, schema)
            if not vr.valid:
                raise ValueError(f"Instance {tid}:{seed} invalid: {vr.errors}")
            for rep in range(repetitions):
                agent_seed = f"same-model:{seed}:{rep}"
                full = full_runs.get((tid, str(seed), rep, "B3"))
                if full is None:
                    full = run_condition(
                        scenario=instance, agent=factory(), condition="full",
                        repetition=rep, agent_seed=agent_seed,
                    )
                aa_runs.append(full)
                diagnostic_runs.extend(run_transfer_matrix(
                    scenario=instance, agent_factory=factory, repetition=rep,
                    agent_seed=agent_seed, cells=cells,
                ))
    return eligible, aa_runs, diagnostic_runs


def _aggregate_calibration(
    *, templates: list[dict[str, Any]], profile: dict[str, Any], raw: dict[str, dict[str, list[dict[str, Any]]]],
    causal: dict[str, list[dict[str, Any]]], factories: dict[str, Callable[[], Any]],
    thresholds: dict[str, float], bootstrap_resamples: int, bootstrap_seed: str | int,
    configuration: dict[str, Any],
) -> dict[str, Any]:
    templates_by_id = {t["id"]: t for t in templates}
    cards = []
    for t in templates:
        tid = t["id"]
        stats_by_b = {
            bid: _baseline_stat(raw[tid][bid], bootstrap_resamples=bootstrap_resamples,
                                bootstrap_seed=f"{bootstrap_seed}:{tid}:{bid}")
            for bid in CONDITIONS
        }
        b0, b1, b2, b3 = [stats_by_b[x]["mean"] for x in CONDITIONS]
        mdi = b1 - b0
        denom = mdi
        mgc_b2 = (b2 - b0) / denom if abs(denom) > 1e-12 else None
        mgc_b3 = (b3 - b0) / denom if abs(denom) > 1e-12 else None
        baseline_means = [b0, b1, b2, b3]
        caggs = causal.get(tid, [])
        cdiag = {
            "memory_benefit": _metric(caggs, "memory_benefit"),
            "headroom_normalized_memory_benefit": _metric(caggs, "headroom_normalized_memory_benefit"),
            "irrelevant_memory_stability": _metric(caggs, "irrelevant_memory_stability"),
            "memory_harm": _metric(caggs, "memory_harm"),
            "harm_resistance": _metric(caggs, "harm_resistance"),
            "net_memory_gain": _metric(caggs, "net_memory_gain"),
        }
        card = {
            "template_id": tid,
            "title": t.get("title"),
            "suite": t.get("suite"),
            "visibility": (t.get("metadata") or {}).get("visibility"),
            "dimensions": list(t.get("dimensions") or []),
            "baseline_scores": stats_by_b,
            "metrics": {
                "full_context": b1,
                "no_memory": b0,
                "memory_discriminativeness_index": mdi,
                "simple_retrieval": b2,
                "structured_agentic": b3,
                "memory_gap_closure_b2": mgc_b2,
                "memory_gap_closure_b3": mgc_b3,
                "baseline_span": max(baseline_means) - min(baseline_means),
                "structured_over_retrieval": b3 - b2,
            },
            "causal_diagnostics": cdiag,
            "gates": {
                "full_context": b1 >= thresholds["full_context_min"],
                "no_memory": b0 <= thresholds["no_memory_max"],
                "mdi": mdi >= thresholds["mdi_min"],
                "baseline_span": (max(baseline_means) - min(baseline_means)) >= thresholds["baseline_span_min"],
                "irrelevant_stability": cdiag["irrelevant_memory_stability"] is None or cdiag["irrelevant_memory_stability"] >= thresholds["irrelevant_stability_min"],
                "causal_sensitivity": cdiag["memory_benefit"] is None or cdiag["memory_benefit"] >= thresholds["causal_memory_benefit_min"],
            },
        }
        rec, reasons = _recommend(card, thresholds)
        risks = []
        if cdiag["memory_benefit"] is not None and cdiag["memory_benefit"] < thresholds["causal_memory_benefit_min"]:
            risks.append("relevant_ablation_low_effect")
        if cdiag["irrelevant_memory_stability"] is not None and cdiag["irrelevant_memory_stability"] < thresholds["irrelevant_stability_min"]:
            risks.append("irrelevant_ablation_unstable")
        card["recommendation"] = rec
        card["reasons"] = reasons
        card["causal_risks"] = risks
        cards.append(card)

    dimension_matrix = []
    for d, spec in (profile.get("dimensions") or {}).items():
        row = {"dimension": d, "weight": float(spec["weight"]), "baselines": {}}
        for bid in CONDITIONS:
            vals = []
            for card in cards:
                t = templates_by_id[card["template_id"]]
                w = float(((t.get("scoring") or {}).get("dimension_weights") or {}).get(d, 0.0))
                if w > 0:
                    vals.append((float(card["baseline_scores"][bid]["mean"]), w))
            den = sum(w for _, w in vals)
            row["baselines"][bid] = sum(v*w for v, w in vals) / den if den else 0.0
        dimension_matrix.append(row)

    rec_counts: dict[str, int] = defaultdict(int)
    gate_counts: dict[str, int] = defaultdict(int)
    risk_counts: dict[str, int] = defaultdict(int)
    for c in cards:
        rec_counts[c["recommendation"]] += 1
        for g, ok in c["gates"].items():
            if ok:
                gate_counts[g] += 1
        for risk in c["causal_risks"]:
            risk_counts[risk] += 1
    ordering = {
        "B1_ge_B3": sum(1 for c in cards if c["baseline_scores"]["B1"]["mean"] + 1e-12 >= c["baseline_scores"]["B3"]["mean"]),
        "B3_ge_B2": sum(1 for c in cards if c["baseline_scores"]["B3"]["mean"] + 1e-12 >= c["baseline_scores"]["B2"]["mean"]),
        "B2_ge_B0": sum(1 for c in cards if c["baseline_scores"]["B2"]["mean"] + 1e-12 >= c["baseline_scores"]["B0"]["mean"]),
        "template_count": len(cards),
    }
    actual_baselines = []
    for bid in CONDITIONS:
        d = factories[bid]().describe()
        ext = (d.get("extensions") or {}).get("mib.calibration") or {}
        actual_baselines.append({
            "id": bid,
            "name": (d.get("implementation") or {}).get("name", bid),
            "role": ext.get("role", bid),
            "release_calibration_eligible": bool(ext.get("release_calibration_eligible", False)),
        })
    return {
        "mib": "0.1",
        "kind": "MIBCalibrationReport",
        "report_version": "0.1.0",
        "generated_at": utc_now(),
        "profile": {"id": profile["id"], "version": profile["version"]},
        "scenario_pack": copy.deepcopy(profile.get("scenario_pack") or {}),
        "calibration_mode": "same_model_empirical",
        "release_calibration_eligible": False,
        "release_note": "Final release eligibility is decided by the enclosing Same-Model fairness and empirical release gate.",
        "configuration": configuration,
        "baselines": actual_baselines,
        "summary": {
            "template_count": len(cards),
            "recommendations": dict(sorted(rec_counts.items())),
            "gate_pass_counts": {k: gate_counts[k] for k in sorted(gate_counts)},
            "ordering_diagnostics": ordering,
            "causal_risk_counts": dict(sorted(risk_counts.items())),
            "provisional_gate_pass_all_three": sum(1 for c in cards if c["gates"]["full_context"] and c["gates"]["no_memory"] and c["gates"]["mdi"]),
            "provisional_full_gate_including_causal": sum(1 for c in cards if c["gates"]["full_context"] and c["gates"]["no_memory"] and c["gates"]["mdi"] and c["gates"]["causal_sensitivity"] and c["gates"]["irrelevant_stability"]),
        },
        "dimension_matrix": dimension_matrix,
        "templates": sorted(cards, key=lambda x: x["template_id"]),
    }


def run_same_model_calibration(experiment_path: str | Path) -> dict[str, Any]:
    cfg, paths = load_experiment(experiment_path)
    experiment_lock = build_experiment_lock(cfg, paths)
    schema = load_json(paths["scenario_schema"])
    profile = load_json(paths["profile"])
    templates = load_private_templates(paths["pack"])
    system_prompt = load_prompt(paths["system_prompt"])
    reasoning_policy = load_prompt(paths["reasoning_policy"])
    execution_plan = estimate_experiment(cfg, templates)

    # Statelessness preflight uses a disposable client, then the actual experiment
    # starts with a fresh client process/connection context.
    preflight = _preflight_statelessness(cfg["model"], system_prompt)
    model_client = build_model_client(cfg["model"])
    model_identity = model_client.identity()
    empirical_client = not isinstance(model_client, DeterministicStubModelClient)
    recorders = {bid: InvocationRecorder() for bid in CONDITIONS}

    common_memory = {
        "retrieval_top_k": int(cfg["agent"].get("retrieval_top_k", 4)),
        "structured_top_k": int(cfg["agent"].get("structured_top_k", 10)),
        "structured_salient_k": int(cfg["agent"].get("structured_salient_k", 6)),
        "parse_retries": int(cfg["agent"].get("parse_retries", 1)),
    }
    memory_limits = dict(cfg["agent"].get("memory_char_limits") or {})
    model_cfg = copy.deepcopy(cfg["model"])

    factories: dict[str, Callable[[], SameModelAgent]] = {}
    for bid in CONDITIONS:
        def make_factory(condition: str = bid):
            mem = dict(common_memory)
            if condition in memory_limits and memory_limits[condition] is not None:
                mem["max_memory_chars"] = memory_limits[condition]
            return SameModelAgent(
                condition=condition,
                model_client=model_client,
                system_prompt=system_prompt,
                reasoning_policy=reasoning_policy,
                model_parameters=copy.deepcopy(model_cfg.get("parameters") or {}),
                recorder=recorders[condition],
                memory_config=mem,
                empirical_eligible=empirical_client,
                seed_policy=str(model_cfg.get("seed_policy", "paired_per_call")),
                seed_base=str(model_cfg.get("seed_base", "mib-same-model-0.1")),
            )
        factories[bid] = make_factory

    cal_cfg = cfg.get("calibration") or {}
    seeds = list(cal_cfg.get("instance_seeds") or [101, 202, 303, 404])
    reps = int(cal_cfg.get("repetitions", 1))
    cseeds = list(cal_cfg.get("causal_instance_seeds") or seeds)
    creps = int(cal_cfg.get("causal_repetitions", 1))
    thresholds = {**DEFAULT_THRESHOLDS, **dict(cal_cfg.get("thresholds") or {})}

    try:
        raw, full_runs, schedule = _run_interleaved_full(
            templates=templates, schema=schema, factories=factories, seeds=seeds, repetitions=reps,
        )
        causal = _run_causal_from_paired_b3(
            templates=templates, schema=schema, factory=factories["B3"], seeds=cseeds,
            repetitions=creps, full_runs=full_runs,
        )
        transfer_spec = dict(cal_cfg.get("transfer_diagnostics") or {})
        transfer_body = None
        transfer_summary = {"enabled": False}
        if transfer_spec.get("enabled"):
            cells = tuple(transfer_spec.get("cells") or TRANSFER_CELLS)
            tseeds = list(transfer_spec.get("instance_seeds") or cseeds)
            treps = int(transfer_spec.get("repetitions", creps))
            eligible, aa_runs, diagnostic_runs = _run_transfer_cells(
                templates=templates, schema=schema, factory=factories["B3"],
                seeds=tseeds, repetitions=treps, full_runs=full_runs, cells=cells,
            )
            transfer_body = build_transfer_diagnostics(
                templates=eligible, runs=aa_runs, diagnostic_runs=diagnostic_runs,
                epsilon=float(transfer_spec.get("epsilon", DEFAULT_EPSILON)),
                bootstrap_resamples=int(transfer_spec.get("bootstrap_resamples", 0)),
                bootstrap_seed=cal_cfg.get("bootstrap_seed", "mib-same-model-0.1"),
            )
            transfer_summary = {
                "enabled": True,
                "cells": list(cells),
                "baseline_condition": "B3",
                "eligible_template_count": len(eligible),
                "instance_seeds": tseeds,
                "repetitions": treps,
                "formation_efficiency_available": "AO" in cells,
                "note": (
                    "The AO cell is configured, so Formation Efficiency is measurable for any Agent "
                    "that exposes a decomposable Memory Adapter."
                    if "AO" in cells else
                    "The Same-Model Agent exposes no decomposable Memory Adapter, so the AO cell is "
                    "not run and Formation Efficiency is unavailable. Routing Efficiency and the "
                    "uptake ceiling remain measurable."
                ),
            }

        base_report = _aggregate_calibration(
            templates=templates, profile=profile, raw=raw, causal=causal, factories=factories,
            thresholds=thresholds,
            bootstrap_resamples=int(cal_cfg.get("bootstrap_resamples", 2000)),
            bootstrap_seed=cal_cfg.get("bootstrap_seed", "mib-same-model-0.1"),
            configuration={
                "instance_seeds": seeds,
                "repetitions": reps,
                "baseline_ids": CONDITIONS,
                "bootstrap_resamples": int(cal_cfg.get("bootstrap_resamples", 2000)),
                "causal_baseline_id": "B3",
                "causal_instance_seeds": cseeds,
                "causal_repetitions": creps,
                "thresholds": thresholds,
                "condition_order_policy": "counterbalanced_latin_rotation_v1",
            },
        )
    finally:
        try:
            model_client.close()
        except Exception:
            pass

    schedule_audit = _schedule_audit(schedule)
    pairing_audit = _probe_pairing_audit(full_runs)
    telemetry = {bid: recorders[bid].summary() for bid in CONDITIONS}
    model_errors = sum(int(x.get("model_errors", 0)) for x in telemetry.values())
    b1_truncations = int(telemetry["B1"].get("memory_truncations", 0))
    params = dict(model_cfg.get("parameters") or {})
    seed_policy = str(model_cfg.get("seed_policy", "paired_per_call"))
    deterministic_decoding = float(params.get("temperature", 0.0)) == 0.0 or "seed" in params or seed_policy == "paired_per_call"

    # The audit is computed from what the run actually sent to the model, not
    # asserted from configuration.  Each fingerprint set must collapse to one
    # value across every condition; the memory policy is the only thing allowed
    # to differ.
    def _union(field: str) -> set[str]:
        out: set[str] = set()
        for t in telemetry.values():
            out.update(t.get(field) or [])
        return out

    model_identities = _union("model_identities")
    system_prompt_shas = _union("system_prompt_shas")
    reasoning_policy_shas = _union("reasoning_policy_shas")
    decoding_fingerprints = _union("decoding_fingerprints")
    memory_policy_ids = _union("memory_policy_ids")
    condition_label_leaks = sum(int(t.get("condition_label_visible_calls", 0)) for t in telemetry.values())
    observed_calls = sum(int(t.get("model_calls", 0)) for t in telemetry.values())
    # With no calls there is no evidence, so nothing may be reported as verified.
    have_evidence = observed_calls > 0

    fairness_checks = {
        "single_model_identity": have_evidence and len(model_identities) == 1,
        "single_model_client_configuration": have_evidence and len(decoding_fingerprints) == 1,
        "identical_system_prompt": have_evidence and len(system_prompt_shas) == 1,
        "identical_reasoning_policy": have_evidence and len(reasoning_policy_shas) == 1,
        "identical_tool_interface": True,  # Tools come from the Scenario, not the condition.
        "identical_decoding_parameters": have_evidence and len(decoding_fingerprints) == 1,
        "deterministic_or_seeded_decoding": deterministic_decoding,
        "stateless_model_contract": bool(preflight.get("passed")),
        "statelessness_preflight": bool(preflight.get("passed")),
        # One memory policy per executed condition, and nothing else varying.
        "only_memory_policy_varies": (
            have_evidence
            and len(memory_policy_ids) == len([b for b in CONDITIONS if telemetry.get(b, {}).get("model_calls")])
            and len(system_prompt_shas) == 1
            and len(decoding_fingerprints) == 1
        ),
        "condition_label_not_model_visible": have_evidence and condition_label_leaks == 0,
        "counterbalanced_condition_order": bool(schedule_audit["balanced"]),
        "paired_agent_seed_and_future_probe": bool(pairing_audit["valid"]),
        "b1_full_context_not_truncated": b1_truncations == 0,
        "no_model_transport_or_parse_errors": model_errors == 0,
    }
    fairness_evidence = {
        "observed_model_calls": observed_calls,
        "distinct_model_identities": len(model_identities),
        "distinct_system_prompts": len(system_prompt_shas),
        "distinct_reasoning_policies": len(reasoning_policy_shas),
        "distinct_decoding_fingerprints": len(decoding_fingerprints),
        "memory_policy_ids": sorted(memory_policy_ids),
        "condition_label_visible_calls": condition_label_leaks,
        "transport_errors": sum(int(t.get("transport_errors", 0)) for t in telemetry.values()),
        "parse_errors": sum(int(t.get("parse_errors", 0)) for t in telemetry.values()),
        "verification": "computed from recorded model invocations",
    }
    fairness_valid = all(fairness_checks.values())
    n = int(base_report["summary"]["template_count"])
    empirical_gate_count = int(base_report["summary"]["provisional_full_gate_including_causal"])
    all_templates_pass = empirical_gate_count == n
    release_eligible = bool(empirical_client and fairness_valid and all_templates_pass)
    base_report["calibration_mode"] = "same_model_empirical" if empirical_client else "same_model_engineering_stub"
    base_report["release_calibration_eligible"] = release_eligible
    base_report["release_note"] = (
        "Release-grade same-model calibration completed with a non-stub fixed model and all fairness/admission gates passed."
        if release_eligible else
        "Harness execution is valid, but leaderboard release eligibility remains false until a non-stub fixed model completes the full pack with all fairness and admission gates passing."
    )

    return {
        "mib": "0.1",
        "kind": "MIBSameModelCalibrationReport",
        "report_version": "0.1.0",
        "generated_at": utc_now(),
        "experiment": {
            "id": cfg["id"],
            "status": "completed" if empirical_client else "engineering_stub_completed",
            "experiment_lock": experiment_lock,
            "execution_plan": execution_plan,
        },
        "model_identity": model_identity,
        "statelessness_preflight": preflight,
        "condition_order_audit": schedule_audit,
        "pairing_audit": pairing_audit,
        "fairness_audit": {"valid": fairness_valid, "checks": fairness_checks, "evidence": fairness_evidence},
        "telemetry": telemetry,
        "empirical_release_gate": {
            "eligible": release_eligible,
            "non_stub_model": empirical_client,
            "template_full_gate": {"passed": empirical_gate_count, "total": n, "all_pass": all_templates_pass},
            "fairness_valid": fairness_valid,
            "requirements": [
                "same model identity across B0-B3",
                "same system/reasoning/tool/decoding policy across B0-B3",
                "only memory context/policy varies",
                "counterbalanced condition order",
                "paired Agent seed and future Probe",
                "statelessness preflight passes",
                "B1 full history is not truncated",
                "zero model transport/parse failures",
                "all official Templates pass FC/NM/MDI and causal sensitivity/stability gates",
            ],
        },
        "calibration": base_report,
        # Supplemental. Transfer diagnostics never enter a calibration gate or
        # the release-eligibility decision.
        "transfer_diagnostics": {
            **transfer_summary,
            **({"result": transfer_body} if transfer_body else {}),
        },
    }


def write_same_model_markdown(report: dict[str, Any]) -> str:
    cal = report["calibration"]
    gate = report["empirical_release_gate"]
    fa = report["fairness_audit"]
    sched = report["condition_order_audit"]
    lines = [
        "# MIB v0.1 Same-Model Empirical Calibration Report",
        "",
        f"**Experiment:** `{report['experiment']['id']}`  ",
        f"**Mode:** `{cal['calibration_mode']}`  ",
        f"**Model:** `{report['model_identity'].get('model_id')}`  ",
        f"**Experiment lock:** `{report['experiment']['experiment_lock']['digest']}`  ",
        f"**Fairness audit:** `{'PASS' if fa['valid'] else 'FAIL'}`  ",
        f"**Leaderboard release eligible:** `{str(gate['eligible']).lower()}`",
        "",
        "## Experimental Variable",
        "",
        "The base model, system prompt, reasoning policy, tool interface, decoding parameters, Scenario instances, and pairing policy are locked. Only long-term memory policy/context varies:",
        "",
        "- **B0** — No Memory",
        "- **B1** — Full Visible History",
        "- **B2** — Simple Lexical Retrieval",
        "- **B3** — Structured Deterministic Memory",
        "",
        "## Release Gate",
        "",
        f"- Official Templates passing full gate: **{gate['template_full_gate']['passed']} / {gate['template_full_gate']['total']}**",
        f"- Non-stub fixed model: **{gate['non_stub_model']}**",
        f"- Fairness valid: **{gate['fairness_valid']}**",
        f"- Release eligible: **{gate['eligible']}**",
        "",
        "## Condition Order",
        "",
        f"- Policy: `{sched['policy']}`",
        f"- Paired units: **{sched['paired_units']}**",
        f"- Balanced: **{sched['balanced']}**",
        f"- Schedule digest: `{sched['schedule_digest']}`",
        "",
        "## Dimension Matrix",
        "",
        "| Dimension | B0 | B1 | B2 | B3 |",
        "|---|---:|---:|---:|---:|",
    ]
    for row in cal["dimension_matrix"]:
        b = row["baselines"]
        lines.append(f"| {row['dimension']} | {100*b.get('B0',0):.1f} | {100*b.get('B1',0):.1f} | {100*b.get('B2',0):.1f} | {100*b.get('B3',0):.1f} |")
    lines += ["", "## Fairness Checks", ""]
    for k, v in fa["checks"].items():
        lines.append(f"- `{k}`: **{'PASS' if v else 'FAIL'}**")
    lines += ["", "## Model / Memory Telemetry", "", "| Condition | Calls | Errors | Memory selections | Selected records | Truncations |", "|---|---:|---:|---:|---:|---:|"]
    for bid in CONDITIONS:
        t = report["telemetry"][bid]
        lines.append(f"| {bid} | {t['model_calls']} | {t['model_errors']} | {t['memory_selections']} | {t['memory_records_selected_total']} | {t['memory_truncations']} |")
    lines += [
        "",
        "## Interpretation",
        "",
        "A result is release-eligible only when a real fixed model—not the engineering stub—runs all four memory conditions under the same experiment lock, the condition schedule is balanced, paired seeds/Probes are intact, B1 is complete rather than truncated, statelessness checks pass, transport/parsing is clean, and every official Template passes the empirical admission gates.",
    ]
    return "\n".join(lines) + "\n"
