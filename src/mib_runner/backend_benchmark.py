"""Evaluator-owned fixed-business-agent comparison over runtime memory backends.

This does not admit a backend to the official benchmark or replace the B0–B3
empirical calibration. Each arm retains a standard, independently verifiable
MIBReport; the outer report binds the shared business harness and backend costs.
"""
from __future__ import annotations

import argparse
import copy
import json
import hashlib
from pathlib import Path

from . import __version__
from .adapter_contract import CONTRACT_VERSION, digest
from .benchmark import build_pack_report
from .materialize import materialize
from .memory_backend import HttpMemoryBackend, NullMemoryBackend, check_backend_descriptor, validate_retrieval
from .model_clients import DeterministicStubModelClient, build_model_client
from .report import verify_score
from .runner import run_scenario
from .same_model_agent import InvocationRecorder, SameModelAgent, load_prompt
from .same_model_calibration import (build_experiment_lock, load_experiment, load_experiment_templates,
                                     _preflight_statelessness)
from .validation import load_json, validate_scenario

REPORT_VERSION = "0.1.0"
CONDITIONS = ("B0", "candidate")


def backend_factory(spec):
    allowed = {"base_url", "timeout_seconds", "api_key_env", "allow_remote_http"}
    if set(spec) - allowed:
        raise ValueError(f"unknown memory_backend fields: {sorted(set(spec) - allowed)}")
    return lambda: HttpMemoryBackend(**spec)


def build_backend_lock(cfg, paths, descriptor):
    check_backend_descriptor(descriptor)
    lock = build_experiment_lock(cfg, paths)
    lock.pop("digest")
    lock.update(kind="MIBMemoryBackendExperimentLock", version=REPORT_VERSION,
                adapter_contract_version=CONTRACT_VERSION,
                backend_protocol=descriptor["protocol"], backend_descriptor=descriptor)
    lock["conditions"] = {"B0": {"memory_backend": "NullMemoryBackend"},
                          "candidate": {"memory_backend": "HTTP", "descriptor_digest": digest(descriptor)}}
    lock["memory_runtime"] = copy.deepcopy(cfg["agent"])
    lock["execution"] = copy.deepcopy(cfg.get("execution", {}))
    lock["templates_digest"] = digest(load_experiment_templates(paths))
    lock["backend_transport"] = copy.deepcopy(cfg["memory_backend"])
    # Backend transport has only an environment-variable name, never a token.
    lock["allowed_condition_differences"] = ["memory_backend", "memory_context", "backend_internal_work_and_cost"]
    lock["condition_order_policy"] = "two_arm_alternating_by_instance_repetition_v1"
    lock["digest"] = digest(lock)
    return lock


def fairness_from_evidence(lock, calls, reports, preflight):
    parameters = lock["model"].get("parameters", {})
    checks = {"statelessness_preflight": preflight.get("passed") is True
                  and isinstance(preflight.get("first_a_digest"), str)
                  and preflight.get("first_a_digest") == preflight.get("second_a_digest")
                  and not preflight.get("error"),
              "deterministic_or_seeded_decoding": float(parameters.get("temperature", 0)) == 0
                  or "seed" in parameters or lock["model"].get("seed_policy") == "paired_per_call"}
    for key, expected in [("system_prompt_sha", lock["system_prompt_sha256"]),
                          ("reasoning_policy_sha", lock["reasoning_policy_sha256"])]:
        checks[key] = bool(all(calls.values())) and all(r.get(key) == expected for rows in calls.values() for r in rows)
    for key, expected in [("model_identity", lock.get("business_model_identity")),
                          ("decoding_fingerprint", lock.get("decoding_fingerprint")),
                          ("seed_policy", lock["model"].get("seed_policy"))]:
        checks[key] = bool(all(calls.values())) and all(r.get(key) == expected for rows in calls.values() for r in rows)
    checks["condition_label_hidden"] = all(not r.get("condition_label_visible") for rows in calls.values() for r in rows)
    checks["model_execution_clean"] = all(not r.get("error") for rows in calls.values() for r in rows)
    keyed = {}
    for arm, report in reports.items():
        keyed[arm] = {(r["scenario_instance_id"], r["repetition"], r["condition"], r.get("ablation_id")):
            (r.get("agent_seed"), r.get("validity", {}).get("instance_spec_digest"))
            for r in report["results"]["runs"]}
    checks["paired_program_and_seed"] = keyed.get("B0") == keyed.get("candidate") and bool(keyed.get("B0"))
    checks["lifecycle_valid"] = all(r.get("validity", {}).get("runner_valid") is True
        for report in reports.values() for r in report["results"]["runs"])
    return {"valid": all(checks.values()), "checks": checks,
            "scope": "fixed evaluator business agent/model/prompt/tools/sampling/budgets; backend internal models/work may differ"}


def verify_backend_report(report):
    errors = []
    if report.get("kind") != "MIBMemoryBackendReport" or report.get("report_version") != REPORT_VERSION:
        return {"valid": False, "errors": ["unsupported memory backend report version"]}
    lock = report.get("experiment_lock", {})
    if lock.get("digest") != digest({k: v for k, v in lock.items() if k != "digest"}):
        errors.append("experiment lock digest mismatch")
    if lock.get("adapter_contract_version") != CONTRACT_VERSION or set(lock.get("conditions", {})) != set(CONDITIONS):
        errors.append("experiment lock contract/conditions mismatch")
    if report.get("evidence_digest") != digest({"calls": report.get("business_calls"), "backends": report.get("backend_runs")}):
        errors.append("runtime evidence digest mismatch")
    reports = report.get("reports", {})
    if set(reports) != set(CONDITIONS):
        errors.append("both backend arms are required")
    for arm, child in reports.items():
        result = verify_score(child)
        errors.extend(f"{arm}: {e}" for e in result["errors"])
        if child.get("benchmark", {}).get("track") != "memory_system":
            errors.append(f"{arm}: wrong Track A declaration")
    expected = fairness_from_evidence(lock, report.get("business_calls", {}), reports, report.get("preflight", {}))
    if report.get("fairness_audit") != expected:
        errors.append("fairness audit disagrees with runtime evidence")
    schedule = report.get("schedule", [])
    units = [(s.get("template_id"), str(s.get("seed")), s.get("repetition")) for s in schedule]
    expected_units = {(r["template_id"], str(r.get("instance_seed")), r["repetition"])
        for r in reports.get("B0", {}).get("results", {}).get("runs", []) if r.get("condition") == "full"}
    if len(units) != len(set(units)) or set(units) != expected_units or any(
        s.get("order") != list(CONDITIONS if i % 2 == 0 else tuple(reversed(CONDITIONS))) for i, s in enumerate(schedule)):
        errors.append("condition schedule differs from paired alternating execution policy")
    if report.get("total_cost") is not None or report.get("accounting_complete") is not False:
        errors.append("total cost must remain unknown while provider retries/pricing are unmeasured")
    if set(report.get("backend_runs", {})) != set(CONDITIONS) or set(report.get("business_calls", {})) != set(CONDITIONS):
        errors.append("backend and business evidence must cover both conditions")
    for arm, runs in report.get("backend_runs", {}).items():
        expected_ids = {r["run_id"] for r in reports.get(arm, {}).get("results", {}).get("runs", [])}
        if {r.get("agent_run_id") for r in runs} != expected_ids:
            errors.append(f"{arm}: backend run coverage mismatch")
        ids = [r.get("backend_run_id") for r in runs if r.get("backend_run_id") is not None]
        if len(ids) != len(set(ids)):
            errors.append(f"{arm}: backend run id reused")
        child_runs = {r["run_id"]: r for r in reports.get(arm, {}).get("results", {}).get("runs", [])}
        for run in runs:
            operations = run.get("operations", [])
            child = child_runs.get(run.get("agent_run_id"), {})
            failed = any(op.get("outcome") == "failure" for op in operations)
            if failed and child.get("validity", {}).get("runner_valid") is not False:
                errors.append(f"{arm}: failed backend operation must invalidate agent run")
            if run.get("cost_scope") != "cumulative_run":
                errors.append(f"{arm}: unsupported backend cost scope")
            if child.get("validity", {}).get("runner_valid") is True and (not operations or operations[0].get("operation") != "reset" or operations[-1].get("operation") != "close"):
                errors.append(f"{arm}: successful run requires reset through close lifecycle evidence")
            for op in operations:
                operation = op.get("operation")
                if operation not in {"reset", "observe", "retrieve", "maintain", "session_boundary", "close"} or op.get("outcome") not in {"success", "failure"}:
                    errors.append(f"{arm}: invalid backend operation evidence")
                if op.get("run_id") != run.get("backend_run_id"):
                    errors.append(f"{arm}: backend operation run correlation mismatch")
                if op.get("outcome") == "success":
                    if not isinstance(op.get("costs"), dict):
                        errors.append(f"{arm}: missing cumulative cost receipt")
                    if operation in {"reset", "observe", "maintain", "session_boundary"} and op.get("accepted") is not True:
                        errors.append(f"{arm}: missing terminal acknowledgement")
                    if operation == "close" and op.get("closed") is not True:
                        errors.append(f"{arm}: missing close acknowledgement")
                    if operation == "retrieve" and arm == "candidate":
                        retrieval = op.get("retrieval", {})
                        try:
                            validate_retrieval(retrieval, int(lock["memory_runtime"].get("max_memory_chars", 32768)))
                            if retrieval.get("limit_chars") != int(lock["memory_runtime"].get("max_memory_chars", 32768)):
                                raise ValueError("memory budget mismatch")
                        except Exception:
                            errors.append(f"{arm}: invalid retrieval/budget evidence")
                costs = op.get("costs")
                if costs is not None:
                    if op.get("cost_scope") != "cumulative_run":
                        errors.append(f"{arm}: cost snapshot lacks cumulative_run scope")
                    if not isinstance(costs, dict) or type(costs.get("accounting_complete")) is not bool or not isinstance(costs.get("receipts"), list) or not isinstance(costs.get("unreported_stages"), list):
                        errors.append(f"{arm}: invalid CostSummary")
            snapshots = [op["costs"] for op in run.get("operations", [])
                         if "costs" in op and op.get("cost_scope") == "cumulative_run"]
            if run.get("costs") != (snapshots[-1] if snapshots else None):
                errors.append(f"{arm}: cumulative costs must use the last snapshot exactly once")
    return {"valid": not errors, "verification_level": "backend_contract_and_full_child_scores", "errors": errors}


def run_backend_benchmark(experiment_path, *, model_client=None, candidate_factory=None):
    cfg, paths = load_experiment(experiment_path)
    agent_cfg = cfg["agent"]
    unsupported = set(agent_cfg) - {"system_prompt", "reasoning_policy", "max_memory_chars", "parse_retries", "observe_decisions", "maintenance_decisions"}
    if unsupported:
        raise ValueError(f"backend comparison requires a common budget, unsupported agent fields: {sorted(unsupported)}")
    if int(agent_cfg.get("max_memory_chars", 32768)) <= 0:
        raise ValueError("max_memory_chars must be positive")
    factory = candidate_factory or backend_factory(cfg["memory_backend"])
    descriptor = check_backend_descriptor(factory().describe())
    lock = build_backend_lock(cfg, paths, descriptor)
    schema = load_json(paths["scenario_schema"])
    profile = load_json(paths["profile"])
    # This is a development experiment until fixed-model empirical admission is complete.
    profile = {**profile, "track": "memory_system", "official": False}
    templates = load_experiment_templates(paths)
    system = load_prompt(paths["system_prompt"])
    policy = load_prompt(paths["reasoning_policy"])
    owned = model_client is None
    if owned:
        preflight = _preflight_statelessness(cfg["model"], system)
    else:
        # Test clients are explicitly injected, but never exempt from the
        # consistency check used by the executable harness.
        parameters = copy.deepcopy(cfg["model"].get("parameters", {}))
        parameters.setdefault("seed", 1900819)
        answers = []
        try:
            for index, letter in enumerate(("A", "B", "A")):
                out = model_client.complete(messages=[{"role": "system", "content": system},
                    {"role": "user", "content": "Statelessness check. Return exactly " + letter}],
                    parameters=parameters, request_id=f"preflight-test-{index}")
                answers.append(out.text.strip())
            preflight = {"passed": answers[0] == answers[2], "first_a_digest": digest(answers[0]),
                         "second_a_digest": digest(answers[2]), "injected_engineering_client": True}
        except Exception as exc:
            preflight = {"passed": False, "error": repr(exc), "injected_engineering_client": True}
    model = model_client or build_model_client(cfg["model"])
    lock.pop("digest")
    lock["business_model_identity"] = copy.deepcopy(model.identity())
    lock["decoding_fingerprint"] = hashlib.sha256(json.dumps(
        {k: v for k, v in sorted(cfg["model"].get("parameters", {}).items()) if k != "seed"},
        sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    lock["digest"] = digest(lock)
    recorders = {arm: InvocationRecorder() for arm in CONDITIONS}
    all_runs = {arm: [] for arm in CONDITIONS}
    backends = {arm: [] for arm in CONDITIONS}
    descriptors = {}
    instances = []
    schedule = []
    settings = cfg.get("execution") or {}
    seeds = settings.get("instance_seeds", [101])
    repetitions = int(settings.get("repetitions", 1))
    if not seeds or repetitions < 1:
        raise ValueError("at least one instance seed and repetition is required")
    try:
        index = 0
        for template in templates:
            for seed in seeds:
                scenario = materialize(template, seed)
                validation = validate_scenario(scenario, schema)
                if not validation.valid:
                    raise ValueError(f"invalid scenario: {validation.errors}")
                instances.append(scenario)
                for rep in range(repetitions):
                    order = CONDITIONS if index % 2 == 0 else tuple(reversed(CONDITIONS))
                    schedule.append({"template_id": template["id"], "seed": seed, "repetition": rep, "order": list(order)})
                    index += 1
                    for arm in order:
                        made = []
                        def make_agent():
                            backend = NullMemoryBackend() if arm == "B0" else factory()
                            # Pin identity on every fresh backend, not only the preflight descriptor.
                            if arm == "candidate":
                                backend.expected_descriptor_digest = digest(descriptor)
                            a = SameModelAgent(condition=arm if arm == "B0" else "MIB_BACKEND_CANDIDATE", model_client=model, system_prompt=system, reasoning_policy=policy,
                                model_parameters=copy.deepcopy(cfg["model"].get("parameters", {})), recorder=recorders[arm],
                                memory_backend=backend, memory_config={k: v for k, v in agent_cfg.items() if k not in {"system_prompt", "reasoning_policy"}},
                                seed_policy=cfg["model"].get("seed_policy", "paired_per_call"), seed_base=cfg["model"].get("seed_base", "mib-backend-0.1"),
                                empirical_eligible=not isinstance(model, DeterministicStubModelClient))
                            descriptors.setdefault(arm, {"protocol": "mib-agent/0.1",
                                "implementation": {"name": f"MIB Same-Model Agent {arm}", "version": __version__, "vendor": "MIB"},
                                "track_support": ["memory_system"],
                                "extensions": {"mib.backend": descriptor if arm == "candidate" else NullMemoryBackend().describe()}})
                            made.append(a)
                            return a
                        runs = run_scenario(scenario=scenario, agent_factory=make_agent,
                            include_ablations=settings.get("include_ablations", True), repetition=rep, agent_seed=f"backend:{seed}:{rep}")
                        all_runs[arm].extend(runs)
                        for a, run in zip(made, runs):
                            operations = copy.deepcopy(a.backend.operations)
                            snapshots = [op["costs"] for op in operations
                                         if "costs" in op and op.get("cost_scope") == "cumulative_run"]
                            backends[arm].append({"agent_run_id": run["run_id"], "backend_run_id": a.backend.run_id,
                                "operations": operations, "cost_scope": "cumulative_run", "costs": snapshots[-1] if snapshots else None})
    finally:
        if owned:
            model.close()
    reports = {arm: build_pack_report(templates=templates, instances=instances, all_runs=all_runs[arm], profile=profile,
                agent_descriptor=descriptors[arm]) for arm in CONDITIONS}
    calls = {arm: recorders[arm].rows for arm in CONDITIONS}
    result = {"kind": "MIBMemoryBackendReport", "report_version": REPORT_VERSION, "runner_version": __version__,
        "experiment_lock": lock, "reports": reports, "schedule": schedule,
        "business_calls": calls, "business_telemetry": {arm: recorders[arm].summary() for arm in CONDITIONS},
        "backend_runs": backends, "preflight": preflight,
        "fairness_audit": fairness_from_evidence(lock, calls, reports, preflight),
        "accounting_complete": False, "total_cost": None,
        "empirical_admission": False,
        "limitations": ["Development pipeline evidence; no official release admission or empirical memory superiority is claimed.",
            "Only the business agent/model/prompt/tools/sampling/budgets are shared. Brain may use additional Formation, Recall and Maintenance models.",
            "Recall items are summarized context with receipt identifiers, not source-element citations.",
            "Backend costs are cumulative snapshots per run. Provider retries, pricing and unreported stages keep total cost unknown."]}
    result["evidence_digest"] = digest({"calls": calls, "backends": backends})
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description="Evaluator-owned same-model memory backend development benchmark")
    parser.add_argument("experiment")
    parser.add_argument("--output-json", required=True)
    args = parser.parse_args(argv)
    report = run_backend_benchmark(args.experiment)
    Path(args.output_json).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    verified = verify_backend_report(report)
    print(json.dumps({"report": args.output_json, "verification": verified, "fairness_audit": report["fairness_audit"]}, indent=2))
    return 0 if verified["valid"] and report["fairness_audit"]["valid"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
