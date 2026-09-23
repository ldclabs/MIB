"""Three-arm, fixed-horizon executable harness with independent replay checks."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import secrets
from pathlib import Path

from .. import __version__
from ..adapter_contract import digest
from .workflow import CONTRACT, CONTRACT_DIGEST, TOOLS
from ..runner import run_condition
from ..submission import build_submission_runtime, load_submission_spec
from ..validation import load_json, validate_scenario
from .contract import AuditedAgent, CONDITIONS, EXTENSION, check_learning_descriptor
from .programs import MEASUREMENT_REVISION, PROGRAMS, generate
from .scoring import aggregate, score_unit

REPORT_VERSION = "0.2.0"


def validate_profile(profile):
    if profile.get("kind") != "MIBLearningLongitudinalProfile" or profile.get("measurement_revision") != MEASUREMENT_REVISION:
        raise ValueError("unsupported longitudinal measurement revision")
    if profile.get("conditions") != list(CONDITIONS) or profile.get("programs") != list(PROGRAMS):
        raise ValueError("all three conditions and all three programs are mandatory")
    seeds = profile.get("seeds")
    if not isinstance(seeds, list) or not seeds or len(seeds) > 16 or any(type(seed) is not int for seed in seeds) or len(set(seeds)) != len(seeds):
        raise ValueError("seeds must contain 1..16 distinct integers")
    if type(profile.get("repetitions")) is not int or not 1 <= profile["repetitions"] <= 16:
        raise ValueError("repetitions must be in 1..16")
    phases = profile.get("phases", {})
    for field in ("early", "late", "retrial"):
        if type(phases.get(field)) is not int or not 2 <= phases[field] <= 32:
            raise ValueError("phase lengths must be frozen integers in 2..32")
    execution = profile.get("execution", {})
    for field in ("max_agent_turns", "max_tool_calls"):
        if type(execution.get(field)) is not int or not 1 <= execution[field] <= 32:
            raise ValueError("task execution limits must be fixed in 1..32")
    attempt = execution.get("attempt_budget", {})
    bounds = {"tool_calls": 64, "elapsed_ms": 3600000, "input_tokens": 1000000, "output_tokens": 1000000}
    if set(attempt) != set(bounds) or any(type(attempt[key]) is not int or not 1 <= attempt[key] <= limit for key, limit in bounds.items()) or attempt["tool_calls"] != execution["max_tool_calls"]:
        raise ValueError("complete frozen P0 per-attempt budgets are required")
    if phases["retrial"] < 3:
        raise ValueError("retrial cohort must cover all three P0 requirements")
    if execution.get("maintenance_budget") != "PT1M" or profile.get("stopping") != "fixed_horizon_keep_all_failures_v1":
        raise ValueError("unsupported maintenance/stopping policy")
    stats = profile.get("statistics", {})
    if stats.get("confidence") != .95 or type(stats.get("bootstrap_seed")) is not int or type(stats.get("bootstrap_repetitions")) is not int or not 200 <= stats["bootstrap_repetitions"] <= 10000:
        raise ValueError("fixed 95% paired bootstrap with 200..10000 resamples required")
    if profile.get("metrics") != ["first_success", "final_success", "late_damage", "negative_transfer", "candidate_retained_unproven", "question_contamination", "revocation_latency", "use_after_revoke", "retrial"]:
        raise ValueError("metric denominator/definitions must match the measurement revision")
    return profile


def build_lock(profile, descriptors, fixture):
    validate_profile(profile)
    schedule = []
    for program in profile["programs"]:
        for seed in profile["seeds"]:
            for repetition in range(profile["repetitions"]):
                index = len(schedule)
                order = list(CONDITIONS[index % 3:] + CONDITIONS[:index % 3])
                schedule.append({"pair_id": digest([program, seed, repetition]), "program": program,
                    "seed": seed, "repetition": repetition, "order": order,
                    # The learner receives an opaque common business seed,
                    # never the seed that reconstructs the hidden world.
                    "agent_seed": secrets.randbits(63)})
    lock = {"kind": "MIBLearningLongitudinalLock", "report_version": REPORT_VERSION,
        "measurement_revision": MEASUREMENT_REVISION, "implementation_version": __version__,
        "profile": copy.deepcopy(profile), "conditions": list(CONDITIONS), "programs": list(PROGRAMS),
        "statistics": profile["statistics"], "schedule": schedule, "descriptors": descriptors,
        "evidence_kind": "engineering_fixture" if fixture else "external_adapter",
        "scope": "Track B integrated-agent behavioral comparison; host audit is read-only attestation, not a native verdict",
        "cost_policy": "last_cumulative_snapshot_only_unknown_is_not_zero",
        "task_contract": task_contract(),
        "world_simulator": "tool_workflow.precondition.v1; failed commits and unsafe preparations remain in executor journal"}
    lock["digest"] = digest(lock)
    return lock


def task_contract():
    return {"task_family": CONTRACT["task_family"], "version": CONTRACT["version"],
            "workflow_contract_digest": CONTRACT_DIGEST, "tool_definition_digest": digest(TOOLS)}


def fairness(lock, units):
    reasons = []
    extensions = []
    for condition in CONDITIONS:
        try:
            extensions.append(check_learning_descriptor(lock["descriptors"][condition], condition))
        except Exception as exc:
            reasons.append(f"{condition}: {exc}")
    if len(extensions) == 3:
        for field in ("business_identity", "execution_guard_digest", "recall_budget"):
            if any(ext[field] != extensions[0][field] for ext in extensions[1:]):
                reasons.append(f"three-arm {field} differs")
    for unit in units:
        if unit["evidence"]["descriptor"] != lock["descriptors"][unit["condition"]]:
            reasons.append("runtime descriptor changed after experiment lock")
        if not unit["metrics"]["runner_valid"]:
            reasons.append(f"invalid run {unit['run']['run_id']}")
    return {"valid": not reasons, "reasons": reasons,
        "claim": "same attested business model/prompt/tools/sampling/Recall budgets and native execution guard; only memory/adoption gating differs"}


class FailedFactory:
    def __init__(self, error): self.error = error
    def describe(self): raise RuntimeError(self.error)
    def close(self, **_): pass


def persist_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as handle:
        handle.write(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def validate_lock(lock, profile):
    if lock.get("profile") != profile or lock.get("digest") != digest({k:v for k,v in lock.items() if k != "digest"}):
        raise ValueError("frozen lock does not match this profile or digest")
    if lock.get("kind") != "MIBLearningLongitudinalLock" or lock.get("report_version") != REPORT_VERSION or lock.get("measurement_revision") != MEASUREMENT_REVISION or lock.get("implementation_version") != __version__:
        raise ValueError("unsupported frozen experiment identity")
    if lock.get("task_contract") != task_contract() or lock.get("conditions") != list(CONDITIONS) or lock.get("programs") != list(PROGRAMS) or lock.get("statistics") != profile["statistics"]:
        raise ValueError("frozen task/condition/statistics mismatch")
    expected = [(program, seed, rep) for program in PROGRAMS for seed in profile["seeds"] for rep in range(profile["repetitions"])]
    schedule=lock.get("schedule", [])
    if [(e.get("program"), e.get("seed"), e.get("repetition")) for e in schedule] != expected:
        raise ValueError("frozen pair schedule mismatch")
    for index, entry in enumerate(schedule):
        if type(entry.get("agent_seed")) is not int or not 0 <= entry["agent_seed"] < 2**63 or entry.get("order") != list(CONDITIONS[index%3:]+CONDITIONS[:index%3]) or entry.get("pair_id") != digest(list(expected[index])):
            raise ValueError("frozen business seed/condition order mismatch")


def run_experiment(profile, factories, *, engineering_fixture=False, schema=None, lock_path=None, frozen_lock=None, progress_path=None):
    validate_profile(profile)
    if set(factories) != set(CONDITIONS):
        raise ValueError("one independent submission factory per condition is required")
    descriptors = {}
    for condition in CONDITIONS:
        instance = None
        try:
            instance = factories[condition]()
            descriptors[condition] = instance.describe()
        except Exception as exc:
            descriptors[condition] = {"unavailable": repr(exc)}
        finally:
            if instance is not None:
                try: instance.close()
                except Exception: pass
    # Freeze every seed, repetition, condition order, identity and stopping rule
    # before any lived task. No successful-outcome filtering is permitted.
    lock = copy.deepcopy(frozen_lock) if frozen_lock is not None else build_lock(profile, descriptors, engineering_fixture)
    validate_lock(lock, profile)
    if lock.get("evidence_kind") != ("engineering_fixture" if engineering_fixture else "external_adapter"):
        raise ValueError("cannot relabel engineering fixtures as external model evidence")
    if lock_path is not None:
        persist_json(lock_path, lock)
    elif not engineering_fixture:
        raise ValueError("external experiments require a durable pre-execution lock path")
    if progress_path is not None:
        Path(progress_path).touch(exist_ok=False)
    units = []
    for entry in lock["schedule"]:
        scenario = generate(entry["program"], entry["seed"], profile["phases"], profile["execution"])
        if schema is not None:
            validation = validate_scenario(scenario, schema)
            if not validation.valid:
                raise ValueError("; ".join(validation.errors))
        for condition in entry["order"]:
            try: instance = factories[condition]()
            except Exception as exc: instance = FailedFactory(repr(exc))
            agent = AuditedAgent(instance, condition, lock["descriptors"][condition])
            row = run_condition(scenario=scenario, agent=agent, repetition=entry["repetition"], agent_seed=entry["agent_seed"])
            unit = {"pair_id": entry["pair_id"], "program": entry["program"], "seed": entry["seed"],
                "repetition": entry["repetition"], "condition": condition, "run": row, "evidence": agent.evidence()}
            unit["metrics"] = score_unit(unit, scenario)
            units.append(unit)
            if progress_path is not None:
                with Path(progress_path).open("a", encoding="utf-8") as handle:
                    handle.write(json.dumps(unit, ensure_ascii=False) + "\n")
                    handle.flush()
                    os.fsync(handle.fileno())
    report = {"kind": "MIBLearningLongitudinalReport", "report_version": REPORT_VERSION,
        "measurement_revision": MEASUREMENT_REVISION, "experiment_lock": lock, "units": units,
        "fairness_audit": fairness(lock, units), "aggregates": aggregate(units, lock),
        "accounting_complete": False, "total_cost": None}
    report["evidence_digest"] = digest(units)
    return report


def verify_report(report):
    try:
        if report.get("kind") != "MIBLearningLongitudinalReport" or report.get("report_version") != REPORT_VERSION or report.get("measurement_revision") != MEASUREMENT_REVISION:
            raise ValueError("unsupported longitudinal report/measurement revision")
        lock = report["experiment_lock"]
        if lock["digest"] != digest({k: v for k, v in lock.items() if k != "digest"}):
            raise ValueError("experiment lock digest mismatch")
        validate_profile(lock["profile"])
        validate_lock(lock, lock["profile"])
        if lock.get("kind") != "MIBLearningLongitudinalLock" or lock.get("report_version") != REPORT_VERSION or lock.get("implementation_version") != __version__ or lock.get("evidence_kind") not in {"engineering_fixture", "external_adapter"}:
            raise ValueError("unsupported frozen implementation/lock/evidence identity")
        if lock.get("task_contract") != task_contract():
            raise ValueError("workflow measurement contract mismatch")
        if lock["measurement_revision"] != MEASUREMENT_REVISION or lock["conditions"] != list(CONDITIONS) or lock["programs"] != list(PROGRAMS) or lock["statistics"] != lock["profile"]["statistics"]:
            raise ValueError("lock measurement contract mismatch")
        expected = [(program, seed, repetition) for program in PROGRAMS for seed in lock["profile"]["seeds"] for repetition in range(lock["profile"]["repetitions"])]
        if [(e["program"], e["seed"], e["repetition"]) for e in lock["schedule"]] != expected:
            raise ValueError("predeclared pair schedule changed")
        expected_units = []
        for index, entry in enumerate(lock["schedule"]):
            order = list(CONDITIONS[index % 3:] + CONDITIONS[:index % 3])
            if entry["order"] != order or entry["pair_id"] != digest([entry["program"], entry["seed"], entry["repetition"]]):
                raise ValueError("paired condition order/identity mismatch")
            expected_units.extend((entry, condition) for condition in order)
        if len(report["units"]) != len(expected_units) or report["evidence_digest"] != digest(report["units"]):
            raise ValueError("evidence denominator/digest mismatch")
        run_ids = set()
        rebuilt = []
        for unit, (entry, condition) in zip(report["units"], expected_units):
            if any(unit[field] != entry[field] for field in ("pair_id", "program", "seed", "repetition")) or unit["condition"] != condition or unit["run"]["agent_seed"] != entry["agent_seed"]:
                raise ValueError("condition pairing mismatch")
            if unit["run"]["run_id"] in run_ids:
                raise ValueError("isolated run id reused")
            run_ids.add(unit["run"]["run_id"])
            scenario = generate(entry["program"], entry["seed"], lock["profile"]["phases"], lock["profile"]["execution"])
            metrics = score_unit(unit, scenario)
            if metrics != unit["metrics"]:
                raise ValueError("longitudinal metrics differ from replayed observations")
            snapshots = unit["evidence"].get("cost_snapshots", [])
            if any(s.get("run_id") != unit["run"]["run_id"] or s.get("cost_scope") != "cumulative_run" for s in snapshots):
                raise ValueError("cost snapshot run/scope mismatch")
            for snapshot in snapshots:
                costs=snapshot.get("costs")
                if not isinstance(costs,dict) or type(costs.get("accounting_complete")) is not bool or not isinstance(costs.get("receipts"),list) or not isinstance(costs.get("unreported_stages"),list):
                    raise ValueError("invalid cumulative CostSummary")
            rebuilt.append({**unit, "metrics": metrics})
        if report["aggregates"] != aggregate(rebuilt, lock) or report["fairness_audit"] != fairness(lock, rebuilt):
            raise ValueError("aggregate/fairness claim does not replay")
        if report.get("total_cost") is not None or report.get("accounting_complete") is not False:
            raise ValueError("unmeasured provider/retry cost cannot become zero or complete")
        return {"valid": True, "verification_level": "longitudinal_world_replay_and_host_audit", "errors": [],
            "learning_status": report["aggregates"]["learning_evaluation"]["status"]}
    except Exception as exc:
        return {"valid": False, "verification_level": "longitudinal_world_replay_and_host_audit", "errors": [str(exc)]}


def run_config(path, *, allow_remote_http=False, lock_path=None, resume_lock=None, progress_path=None):
    path = Path(path).resolve()
    cfg = load_json(path)
    profile_path = (path.parent / cfg["profile"]).resolve()
    profile = load_json(profile_path)
    submission_paths = {mode: (path.parent / cfg["submissions"][mode]).resolve() for mode in CONDITIONS}
    hidden_paths = [str(path), str(profile_path), *[str(p) for p in submission_paths.values()],
        *[str(Path(p).resolve()) for p in (lock_path, progress_path, resume_lock) if p]]
    factories = {}
    for mode in CONDITIONS:
        submission_path = submission_paths[mode]
        spec = load_submission_spec(submission_path)
        factories[mode] = build_submission_runtime(spec, allow_remote_http=allow_remote_http,
            hide_paths=hidden_paths, network="disabled_strict", confine_stage_to_spec_dir=True).factory
    if cfg.get("evidence_kind", "external_adapter") not in {"external_adapter", "engineering_fixture"}:
        raise ValueError("unsupported evidence kind")
    return run_experiment(profile, factories, engineering_fixture=cfg.get("evidence_kind") == "engineering_fixture", lock_path=lock_path,
        frozen_lock=load_json(resume_lock) if resume_lock else None, progress_path=progress_path)


def main(argv=None):
    parser = argparse.ArgumentParser(description="P6 three-arm longitudinal engineering/behavioral experiment")
    parser.add_argument("config")
    parser.add_argument("--output", required=True)
    parser.add_argument("--allow-remote-http", action="store_true")
    parser.add_argument("--resume-lock", help="Reuse the exact predeclared world/business seeds with fresh isolated runs")
    args = parser.parse_args(argv)
    # Reserve all output names before descriptor reads or any lived task. A
    # rerun uses a new output path and the explicit previous lock as input.
    for path in (args.output, args.output + ".lock.json", args.output + ".units.jsonl"):
        if Path(path).exists():
            raise FileExistsError(f"refusing existing experiment output: {path}")
    report = run_config(args.config, allow_remote_http=args.allow_remote_http,
        lock_path=args.output + ".lock.json", resume_lock=args.resume_lock, progress_path=args.output + ".units.jsonl")
    persist_json(args.output, report)
    verification = verify_report(report)
    print(json.dumps({"report": args.output, **verification, "fairness_valid": report["fairness_audit"]["valid"]}, indent=2))
    return 0 if verification["valid"] and report["fairness_audit"]["valid"] else 3
