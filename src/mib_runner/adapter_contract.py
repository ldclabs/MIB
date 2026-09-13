"""Evaluator evidence for lifecycle success, separate from cognitive scoring."""
from __future__ import annotations

import hashlib
import json
from typing import Any

CONTRACT_VERSION = "1.0.0"
ACKNOWLEDGED = {"reset", "observe", "maintain", "session_boundary"}


class AdapterLifecycleError(RuntimeError):
    """A condition's memory/session state is no longer known to be usable."""


def digest(value: Any) -> str:
    return "sha256:" + hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
        separators=(",", ":")).encode()).hexdigest()


def required_capabilities(scenario: dict[str, Any]) -> list[str]:
    required = set((scenario.get("requirements") or {}).get("capabilities") or [])
    required = {"runner_managed_tools" if c == "tools" else c for c in required}
    for p in scenario.get("probes", []):
        delivery = p.get("delivery")
        if delivery in {"respond", "act"}:
            required.add(delivery)
        elif delivery == "observe_only":
            required.add("spontaneous_emissions")
    for e in scenario.get("timeline", []):
        if e.get("visibility") in {"agent", "both"}:
            if e.get("type") == "task":
                required.update({"act", "runner_managed_tools"})
            elif e.get("type") not in {"checkpoint", "world_update"}:
                required.add("observe")
            if e.get("type") == "session_boundary":
                required.add("session_boundary")
    return sorted(required)


def check_descriptor(descriptor: Any, required: list[str]) -> dict[str, bool]:
    if not isinstance(descriptor, dict) or descriptor.get("protocol") != "mib-agent/0.1":
        raise AdapterLifecycleError("describe must declare protocol mib-agent/0.1")
    caps = descriptor.get("capabilities")
    if not isinstance(caps, dict):
        raise AdapterLifecycleError("describe must declare capabilities")
    missing = [c for c in required if caps.get(c) is not True]
    if missing:
        raise AdapterLifecycleError(f"required capabilities not explicitly true: {missing}")
    return caps


def require_accepted(operation: str, result: Any) -> None:
    if not isinstance(result, dict) or result.get("accepted") is not True or result.get("error") is not None:
        raise AdapterLifecycleError(f"{operation} did not acknowledge successful completion: {result!r}")


def verify_run_contract(run: dict[str, Any], *, required: bool = False) -> list[str]:
    evidence = run.get("adapter_contract")
    prefix = f"run {run.get('run_id')} adapter_contract"
    if evidence is None:
        return [prefix + ": missing"] if required else []
    errors = []
    if not isinstance(evidence, dict) or evidence.get("version") != CONTRACT_VERSION:
        return [prefix + ": unsupported version"]
    core = {k: v for k, v in evidence.items() if k != "digest"}
    if evidence.get("digest") != digest(core):
        errors.append(prefix + ": digest mismatch")
    snapshots = evidence.get("reported_cost_snapshots", [])
    if any(s.get("cost_scope") not in {None, "cumulative_run"} for s in snapshots):
        errors.append(prefix + ": unsupported cost scope")
    if snapshots and (evidence.get("reported_costs_last") != snapshots[-1] or any(s.get("run_id") != run.get("run_id") for s in snapshots)):
        errors.append(prefix + ": cost snapshot/run mismatch")
    receipts = evidence.get("operations", [])
    if not isinstance(receipts, list) or not receipts:
        return errors + [prefix + ": missing operation evidence"]
    failed = any(r.get("outcome") == "failure" for r in receipts)
    for i, r in enumerate(receipts):
        if r.get("sequence") != i or r.get("outcome") not in {"success", "failure", "skipped"}:
            errors.append(prefix + ": invalid operation sequence/outcome")
        if r.get("operation") in ACKNOWLEDGED and r.get("outcome") == "success" and r.get("accepted") is not True:
            errors.append(prefix + ": successful lifecycle receipt lacks accepted=true")
        if r.get("outcome") == "skipped" and (r.get("operation") != "maintain" or evidence.get("capabilities", {}).get("maintenance") is not False):
            errors.append(prefix + ": unsupported lifecycle skip")
    if receipts[0].get("operation") != "describe":
        errors.append(prefix + ": describe must begin the lifecycle")
    if required and receipts[-1].get("operation") != "close":
        errors.append(prefix + ": close must end the lifecycle")
    if evidence.get("valid") is not (not failed):
        errors.append(prefix + ": validity disagrees with receipts")
    if not failed:
        try:
            check_descriptor({"protocol": evidence.get("protocol"), "capabilities": evidence.get("capabilities")}, evidence.get("required_capabilities", []))
        except AdapterLifecycleError:
            errors.append(prefix + ": capability evidence is incomplete")
        if receipts[0].get("operation") == "describe" and receipts[0].get("outcome") != "success":
            errors.append(prefix + ": describe did not succeed")
        if len(receipts) < 2 or receipts[1].get("operation") != "reset" or receipts[1].get("outcome") != "success":
            errors.append(prefix + ": reset success must follow describe")
        if required and receipts[-1].get("operation") == "close" and receipts[-1].get("outcome") != "success":
            errors.append(prefix + ": close did not succeed")
    if run.get("validity", {}).get("runner_valid") is not (not failed):
        errors.append(prefix + ": runner_valid disagrees with receipts")
    scheduled = evidence.get("scheduled_probes", [])
    actual = run.get("probe_results", [])
    if [(p.get("probe_id"), p.get("weight")) for p in actual] != [(p.get("probe_id"), p.get("weight")) for p in scheduled]:
        # Chronological execution order can differ from declaration order.
        if sorted((p.get("probe_id"), p.get("weight")) for p in actual) != sorted((p.get("probe_id"), p.get("weight")) for p in scheduled):
            errors.append(prefix + ": scheduled probe denominator changed")
    if failed:
        if run.get("status") != "invalid" or any(p.get("outcome") != "execution_failure" or p.get("score") != 0 for p in actual):
            errors.append(prefix + ": failed lifecycle must invalidate every scheduled probe")
    elif run.get("status") != ("failed" if any(p.get("outcome") == "execution_failure" for p in actual) else "succeeded"):
        errors.append(prefix + ": status disagrees with probe outcomes")
    return errors
