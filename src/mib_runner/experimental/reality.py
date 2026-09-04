"""MIB-R — Memory Intelligence Benchmark, Reality Track (M6.4).

MIB-Core is the controlled synthetic laboratory: it establishes causal
validity.  MIB-R asks whether the same memory intelligence survives in a
realistic external task environment:

    Can past experience causally improve performance on real, held-out tasks
    that share verified procedural support?

The MIB-specific contribution is not the tasks; it is that every condition is
paired on the same source task, target task, environment revision, Agent,
model, tools, timeout, task seed, and verifier.  Only memory state varies.

    Phase A   train task -> Agent acts -> trajectory -> verifier -> Experience
    Phase B   held-out task, same base Agent, memory condition varies

This module is a prototype.  MIB-R is not official, its results are their own
result family, and they are never ranked against MIB-Core.
"""

from __future__ import annotations

import hashlib
import importlib
import json
import math
import random
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Protocol

from .. import __version__
from .reality_graph import (
    RealityTransferGraph,
    load_reality_graph,
    redact_reality_graph,
    validate_reality_graph,
)
from ..service_signing import derive_ed25519_private_key, digest_json, sign_json_ed25519, verify_json_ed25519
from .transfer import (
    DISTANCE_CLASSES,
    DISTANCE_LABEL,
    POSITIVE_RELATIONS,
    RECALL_PREFIX,
)
from ..types import Observation

REALITY_EXTENSION = "mib.reality.v1"

#: Paired memory conditions.  ``natural_memory`` is the deployed behaviour;
#: everything else is an intervention on memory alone.
CONDITIONS = (
    "no_memory",
    "natural_memory",
    "relevant_ability_ablated",
    "irrelevant_ability_ablated",
    "wrong_ability_injected",
    "oracle_skill",
    "oracle_routing",
)

DEFAULT_CONDITIONS = (
    "no_memory",
    "natural_memory",
    "relevant_ability_ablated",
    "irrelevant_ability_ablated",
    "wrong_ability_injected",
)

#: Injected near-match instruction for the wrong-ability condition.  It is a
#: plausible over-generalization of a real convention, never a hidden answer.
WRONG_ABILITY_TEXT = (
    RECALL_PREFIX + "Every record class, legacy classes included, uses the modulo 97 convention."
)


class RealityPackError(ValueError):
    pass


class RealityTaskAdapter(Protocol):
    """A realistic task environment plus its upstream verifier."""

    def describe(self) -> dict[str, Any]: ...

    def load_task(self, task_ref: dict[str, Any]) -> dict[str, Any]: ...

    def run_task(
        self,
        task: dict[str, Any],
        agent: Any,
        *,
        run_id: str,
        seed: int | str,
        request_id: str,
    ) -> dict[str, Any]: ...

    def normalize_score(self, result: dict[str, Any]) -> float: ...

    def collect_trajectory(self, result: dict[str, Any]) -> list[dict[str, Any]]: ...

    def feedback(self, task: dict[str, Any], result: dict[str, Any], *, score: float) -> list[str]:
        """Verifier verdict, plus any reviewer correction, as observation lines.

        Phase A delivers these back to the Agent, which is what makes the
        acquisition an Experience rather than a document dump.  It is part of
        the contract, not an optional extra.
        """
        ...


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def mean(values: list[float]) -> float | None:
    return math.fsum(values) / len(values) if values else None


def load_reality_pack(path: str | Path) -> dict[str, Any]:
    pack = json.loads(Path(path).read_text(encoding="utf-8"))
    if pack.get("kind") != "MIBRealityPack":
        raise RealityPackError(f"not a MIBRealityPack: {pack.get('kind')!r}")
    return pack


def load_adapter(pack: dict[str, Any]) -> RealityTaskAdapter:
    spec = pack.get("environment_adapter")
    if not spec or ":" not in spec:
        raise RealityPackError("environment_adapter must be module:Class")
    module_name, class_name = spec.split(":", 1)
    return getattr(importlib.import_module(module_name), class_name)()


def pack_digest(pack: dict[str, Any]) -> str:
    blob = json.dumps(pack, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _observe(agent: Any, run_id: str, counter: list[int], content: str, obs_type: str = "environment_event") -> None:
    counter[0] += 1
    agent.observe(
        run_id=run_id,
        request_id=f"req_{counter[0]:06d}",
        observation=Observation(
            observation_id=f"obs_{counter[0]:06d}",
            type=obs_type,
            virtual_time=None,
            content=content,
        ),
    )


def _training_task_ids(
    *,
    condition: str,
    train_ids: list[str],
    supporting: set[str],
    causal: set[str],
) -> list[str]:
    """Which acquisition tasks this condition is allowed to experience."""
    if condition == "no_memory":
        return []
    if condition in {"relevant_ability_ablated", "oracle_skill", "oracle_routing"}:
        # The oracle conditions replace the Experience they stand in for, so
        # they withhold the same support the relevant ablation does.
        return [t for t in train_ids if t not in supporting]
    if condition == "irrelevant_ability_ablated":
        # Withhold as much past as the relevant ablation does, chosen only from
        # tasks the target's answer does not depend on. The two conditions then
        # differ in *which* past was removed, not in how much.
        irrelevant = [t for t in train_ids if t not in causal]
        drop = set(irrelevant[: len(supporting)])
        return [t for t in train_ids if t not in drop]
    return list(train_ids)


def _oracle_contents(graph: RealityTransferGraph, target_task_id: str) -> list[str]:
    out = []
    for ability in graph.abilities_for(target_task_id):
        if ability.oracle_artifact and ability.oracle_artifact.get("content"):
            out.append(RECALL_PREFIX + str(ability.oracle_artifact["content"]))
    return out


def run_reality_pair(
    *,
    adapter: RealityTaskAdapter,
    graph: RealityTransferGraph,
    agent_factory: Callable[[], Any],
    train_tasks: dict[str, dict[str, Any]],
    test_task: dict[str, Any],
    condition: str,
    seed: int | str,
    repetition: int,
) -> dict[str, Any]:
    """One paired cell: Phase A under a memory condition, then Phase B.

    Everything except memory state is held fixed — same target task, same
    environment revision, same Agent, same seed, same verifier.
    """
    target_id = test_task["task_id"]
    supporting = set(graph.supporting_task_ids(target_id))
    causal = set(graph.causal_task_ids(target_id)) or supporting
    train_ids = list(train_tasks)
    allowed = _training_task_ids(
        condition=condition, train_ids=train_ids, supporting=supporting, causal=causal,
    )
    withheld = len(train_ids) - len(allowed)

    agent = agent_factory()
    run_id = f"reality_{uuid.uuid4().hex[:16]}"
    counter = [0]
    started = utc_now()
    agent.reset(run_id=run_id, seed=seed, virtual_time=None)

    allowed_set = set(allowed)
    contents = _oracle_contents(graph, target_id) if condition in {"oracle_skill", "oracle_routing"} else []
    # Oracle content must occupy the temporal slot of the Experience it replaces:
    # the acquisition tasks that followed that Experience have to follow it here
    # too, or the retention interval changes as well.  Emitting it after Phase A
    # instead would make oracle_skill and oracle_routing byte-identical streams
    # and the Routing axis would not be isolated at all.
    withheld_ids = [t for t in train_ids if t not in allowed_set]
    pool_anchor = withheld_ids[-1] if (condition == "oracle_skill" and withheld_ids) else None

    acquisition: list[dict[str, Any]] = []
    try:
        # --- Phase A: experience acquisition ---------------------------
        for task_id in train_ids:
            if task_id not in allowed_set:
                if task_id == pool_anchor:
                    # Perfect content in the pool; the system's own routing decides.
                    for content in contents:
                        _observe(agent, run_id, counter, content)
                continue
            task = train_tasks[task_id]
            counter[0] += 1
            result = adapter.run_task(
                task,
                agent,
                run_id=run_id,
                seed=seed,
                request_id=f"req_{counter[0]:06d}",
            )
            score = adapter.normalize_score(result)
            acquisition.append({"task_id": task_id, "score": score})
            for line in adapter.feedback(task, result, score=score):
                _observe(agent, run_id, counter, line, obs_type="feedback")

        if condition == "oracle_skill" and pool_anchor is None:
            # Nothing was withheld, so there is no earlier slot to occupy.
            for content in contents:
                _observe(agent, run_id, counter, content)
        if condition == "wrong_ability_injected":
            _observe(agent, run_id, counter, WRONG_ABILITY_TEXT)

        # --- Phase B: held-out transfer --------------------------------
        if condition == "oracle_routing":
            for content in contents:
                _observe(agent, run_id, counter, content)

        counter[0] += 1
        result = adapter.run_task(
            test_task,
            agent,
            run_id=run_id,
            seed=seed,
            request_id=f"req_{counter[0]:06d}",
        )
        score = adapter.normalize_score(result)
        trajectory = adapter.collect_trajectory(result)
    finally:
        close = getattr(agent, "close", None)
        if callable(close):
            try:
                close(run_id=run_id)
            except TypeError:
                close()

    edge = graph.edge_for(target_id)
    return {
        "run_id": run_id,
        "condition": condition,
        "repetition": repetition,
        "seed": seed,
        "target_task_id": target_id,
        "task_content_digest": test_task.get("content_digest"),
        "relation": edge.relation if edge else None,
        "support_expected": edge.support_expected if edge else None,
        "distance_class": edge.distance_class if edge else None,
        "acquisition_task_count": len(allowed),
        "withheld_task_count": withheld,
        "acquisition_score": mean([r["score"] for r in acquisition]),
        "score": score,
        "answer_digest": hashlib.sha256(str(result.get("answer", "")).encode("utf-8")).hexdigest(),
        "trajectory_steps": len(trajectory),
        "started_at": started,
        "completed_at": utc_now(),
    }


def run_reality_benchmark(
    *,
    pack: dict[str, Any],
    pack_path: str | Path,
    agent_factory: Callable[[], Any],
    seeds: list[int | str] | None = None,
    repetitions: int = 1,
    conditions: tuple[str, ...] | None = None,
    adapter: RealityTaskAdapter | None = None,
    graph: RealityTransferGraph | None = None,
    bootstrap_resamples: int = 0,
    bootstrap_seed: int | str = 20260819,
    confidence_level: float = 0.95,
) -> tuple[dict[str, Any], dict[str, Any]]:
    adapter = adapter or load_adapter(pack)
    graph = graph or load_reality_graph(pack_path, pack)
    conditions = tuple(conditions or pack.get("conditions") or DEFAULT_CONDITIONS)
    unknown = [c for c in conditions if c not in CONDITIONS]
    if unknown:
        raise RealityPackError(f"unknown MIB-R conditions: {unknown}")
    seeds = list(seeds or pack.get("task_seeds") or [101])

    train_tasks = {
        ref["task_id"]: adapter.load_task(ref) for ref in pack.get("train_tasks") or []
    }
    test_tasks = {
        ref["task_id"]: adapter.load_task(ref) for ref in pack.get("test_tasks") or []
    }
    findings = validate_reality_graph(graph, train_task_ids=set(train_tasks), test_task_ids=set(test_tasks))
    errors = [f for f in findings if f["severity"] == "error"]
    if errors:
        raise RealityPackError(f"Reality Transfer Graph invalid: {errors}")

    runs: list[dict[str, Any]] = []
    for test_id in sorted(test_tasks):
        for seed in seeds:
            for rep in range(repetitions):
                for condition in conditions:
                    runs.append(run_reality_pair(
                        adapter=adapter, graph=graph, agent_factory=agent_factory,
                        train_tasks=train_tasks, test_task=test_tasks[test_id],
                        condition=condition, seed=seed, repetition=rep,
                    ))

    metrics = reality_metrics(runs)
    findings = findings + _magnitude_warnings(runs)
    report = build_reality_report(
        pack=pack,
        adapter=adapter,
        graph=graph,
        runs=runs,
        metrics=metrics,
        warnings=[f for f in findings if f["severity"] == "warning"],
        agent_descriptor=_describe(agent_factory),
        statistics=(
            reality_bootstrap(runs, resamples=bootstrap_resamples, seed=bootstrap_seed, confidence_level=confidence_level)
            if bootstrap_resamples > 0 else None
        ),
    )
    summary = {
        "pack": pack["id"],
        "domain": pack.get("domain"),
        "train_task_count": len(train_tasks),
        "test_task_count": len(test_tasks),
        "conditions": list(conditions),
        "run_count": len(runs),
        "metrics": {k: v for k, v in metrics["overall"].items()},
    }
    return report, summary


def _magnitude_warnings(runs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Flag targets where the two ablations could not withhold equal amounts.

    The irrelevant-ablation control is chosen only from tasks the target does
    not depend on.  When fewer such tasks exist than the relevant ablation
    withholds, the two conditions differ in magnitude as well as in content,
    and the stability reading is correspondingly weaker.  Say so rather than
    quietly reporting it as a clean control.
    """
    withheld: dict[str, dict[str, int]] = defaultdict(dict)
    for row in runs:
        withheld[row["target_task_id"]][row["condition"]] = int(row.get("withheld_task_count", 0))
    capped = sorted(
        target for target, byc in withheld.items()
        if byc.get("irrelevant_ability_ablated", 0) < byc.get("relevant_ability_ablated", 0)
    )
    if not capped:
        return []
    return [{
        "severity": "warning",
        "code": "reality.ablation_magnitude_mismatch",
        "message": (
            f"{len(capped)} target task(s) have fewer non-load-bearing acquisition tasks than the "
            "relevant ablation withholds, so the irrelevant-ablation control withholds less past "
            "than the relevant one: " + ", ".join(capped)
        ),
    }]


def _describe(agent_factory: Callable[[], Any]) -> dict[str, Any]:
    agent = agent_factory()
    try:
        return agent.describe()
    finally:
        close = getattr(agent, "close", None)
        if callable(close):
            try:
                close()
            except TypeError:
                pass


def _by_condition(rows: list[dict[str, Any]]) -> dict[str, float]:
    buckets: dict[str, list[float]] = defaultdict(list)
    for row in rows:
        buckets[row["condition"]].append(float(row["score"]))
    return {k: math.fsum(v) / len(v) for k, v in buckets.items()}


def _paired_delta(rows: list[dict[str, Any]], left: str, right: str) -> float | None:
    """Signed ``left - right``, paired on task, seed, and repetition.

    Signed on purpose: a negative delta is harmful memory, not a smaller
    positive number, and taking an absolute value would hide exactly the
    finding MIB-R exists to surface.
    """
    index: dict[tuple[Any, ...], dict[str, float]] = defaultdict(dict)
    for row in rows:
        key = (row["target_task_id"], row["seed"], row["repetition"])
        index[key][row["condition"]] = float(row["score"])
    deltas = [v[left] - v[right] for v in index.values() if left in v and right in v]
    return mean(deltas)


def reality_metrics(runs: list[dict[str, Any]]) -> dict[str, Any]:
    """Diagnostic metrics only.

    There is deliberately no single official MIB-R Score: hiding domain
    behaviour inside one mean this early would destroy the information the
    track exists to produce.
    """
    supported = [r for r in runs if r.get("relation") in POSITIVE_RELATIONS]
    near_match = [r for r in runs if r.get("relation") == "near_match_non_applicable"]
    unsupported = [r for r in runs if r.get("relation") == "unsupported_novel"]

    def block(rows: list[dict[str, Any]]) -> dict[str, Any]:
        if not rows:
            return {}
        conditions = _by_condition(rows)
        out: dict[str, Any] = {"condition_scores": conditions, "task_count": len({r["target_task_id"] for r in rows})}
        for name, left, right in (
            ("natural_transfer_gain", "natural_memory", "no_memory"),
            ("relevant_ablation_delta", "natural_memory", "relevant_ability_ablated"),
            ("irrelevant_ablation_delta", "natural_memory", "irrelevant_ability_ablated"),
            ("wrong_ability_delta", "natural_memory", "wrong_ability_injected"),
            ("oracle_skill_gain", "oracle_skill", "no_memory"),
            ("oracle_routing_gain", "oracle_routing", "no_memory"),
        ):
            value = _paired_delta(rows, left, right)
            if value is not None:
                out[name] = value
        if "irrelevant_ablation_delta" in out:
            out["irrelevant_stability"] = max(0.0, 1.0 - abs(out["irrelevant_ablation_delta"]))
        if "wrong_ability_delta" in out:
            out["memory_harm"] = max(0.0, out["wrong_ability_delta"])
        return out

    per_task = []
    for task_id in sorted({r["target_task_id"] for r in runs}):
        rows = [r for r in runs if r["target_task_id"] == task_id]
        entry = {
            "target_task_id": task_id,
            "relation": rows[0].get("relation"),
            "distance_class": rows[0].get("distance_class"),
            **block(rows),
        }
        per_task.append(entry)

    distance: list[dict[str, Any]] = []
    for cls in DISTANCE_CLASSES:
        rows = [r for r in runs if r.get("distance_class") == cls]
        if not rows:
            continue
        entry = {"class": cls, "label": DISTANCE_LABEL[cls], **block(rows)}
        distance.append(entry)

    negative_rows = [
        r for r in per_task
        if r.get("natural_transfer_gain") is not None and r["natural_transfer_gain"] < -1e-9
    ]
    overall = block(runs)
    if per_task:
        overall["negative_transfer_rate"] = len(negative_rows) / len(per_task)
    if near_match:
        overall["near_match_resistance"] = _by_condition(near_match).get("natural_memory")
    if unsupported:
        delta = _paired_delta(unsupported, "natural_memory", "no_memory")
        if delta is not None:
            overall["unsupported_memory_delta"] = delta
            overall["unsupported_memory_neutrality"] = max(0.0, 1.0 - abs(delta))
    if supported:
        overall["supported_transfer_success_rate"] = _by_condition(supported).get("natural_memory")

    return {
        "overall": overall,
        "by_relation": {
            "supported": block(supported),
            "near_match_non_applicable": block(near_match),
            "unsupported_novel": block(unsupported),
        },
        "by_distance": distance,
        "by_task": per_task,
    }


def reality_bootstrap(
    runs: list[dict[str, Any]],
    *,
    resamples: int,
    seed: int | str,
    confidence_level: float,
) -> dict[str, Any]:
    """Paired bootstrap over target tasks, preserving each task's condition set."""
    by_task: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in runs:
        by_task[row["target_task_id"]].append(row)
    task_ids = sorted(by_task)
    if len(task_ids) < 2:
        return {}
    rng = random.Random(str(seed))
    draws: dict[str, list[float]] = defaultdict(list)
    for _ in range(resamples):
        sample: list[dict[str, Any]] = []
        # Each draw gets its own target id.  ``_paired_delta`` and the per-task
        # rows key on ``target_task_id``, so a task drawn twice under its own id
        # would collapse into one observation and every replicate would be a
        # random subsample rather than a bootstrap resample.
        for draw, _ in enumerate(task_ids):
            picked = task_ids[rng.randrange(len(task_ids))]
            sample.extend(
                {**row, "target_task_id": f"{row['target_task_id']}#{draw}"}
                for row in by_task[picked]
            )
        for name, value in reality_metrics(sample)["overall"].items():
            if isinstance(value, (int, float)):
                draws[name].append(float(value))
    alpha = 1.0 - confidence_level

    def ci(values: list[float]) -> dict[str, Any]:
        xs = sorted(values)

        def q(p: float) -> float:
            pos = (len(xs) - 1) * p
            lo, hi = int(math.floor(pos)), int(math.ceil(pos))
            return xs[lo] if lo == hi else xs[lo] * (1 - (pos - lo)) + xs[hi] * (pos - lo)

        return {
            "level": confidence_level,
            "lower": q(alpha / 2.0),
            "upper": q(1.0 - alpha / 2.0),
            "method": "paired_task_bootstrap_percentile",
            "resamples": resamples,
            "seed": seed,
        }

    return {"overall": {k: ci(v) for k, v in draws.items() if len(v) > 1}}


def build_reality_report(
    *,
    pack: dict[str, Any],
    adapter: RealityTaskAdapter,
    graph: RealityTransferGraph,
    runs: list[dict[str, Any]],
    metrics: dict[str, Any],
    warnings: list[dict[str, Any]],
    agent_descriptor: dict[str, Any],
    statistics: dict[str, Any] | None = None,
) -> dict[str, Any]:
    profile = pack.get("profile") or {"id": "MIB-R-0.1-Dev", "version": "0.1.0"}
    report = {
        "mib": "0.1",
        "kind": "MIBRealityReport",
        "report_version": "0.1.0",
        "report_id": f"reality_{uuid.uuid4().hex[:16]}",
        "generated_at": utc_now(),
        "scope": "internal",
        "benchmark": {
            "mib_version": "0.1",
            "profile": profile,
            "result_family": "reality",
            "official": False,
            "track": pack.get("track", "integrated_agent"),
            "reality_pack": {"id": pack["id"], "version": pack.get("version"), "digest": pack_digest(pack)},
        },
        "system": {
            "agent": {
                "name": (agent_descriptor.get("implementation") or {}).get("name", "Unknown Agent"),
                "version": (agent_descriptor.get("implementation") or {}).get("version", "0.0.0"),
                "vendor": (agent_descriptor.get("implementation") or {}).get("vendor", "Unknown"),
            }
        },
        "environment": {
            "runner": {"name": "MIB Reference Runner", "version": __version__},
            "reality_adapter": adapter.describe(),
        },
        "execution": {
            "started_at": min(r["started_at"] for r in runs) if runs else utc_now(),
            "completed_at": max(r["completed_at"] for r in runs) if runs else utc_now(),
            "runs": len(runs),
            "paired_on": [
                "target_task", "source_task_set", "environment_revision", "agent",
                "model", "tools", "timeout", "task_seed", "verifier",
            ],
        },
        "results": {"runs": runs, "redacted": False},
        "warnings": [
            {"code": w["code"], "severity": "warning", "message": w["message"], "scope": "report"}
            for w in warnings
        ] + [{
            "code": "reality.prototype",
            "severity": "info",
            "message": (
                "MIB-R-0.1-Dev is a prototype. Its results are their own result family and are "
                "never ranked against MIB-Core."
            ),
            "scope": "report",
        }],
        "extensions": {
            REALITY_EXTENSION: {
                "version": "1.0.0",
                "domain": pack.get("domain"),
                "upstream_benchmark": pack.get("source_benchmark"),
                "transfer_metrics": metrics["overall"],
                "by_relation": metrics["by_relation"],
                "distance_profile": metrics["by_distance"],
                "by_task": metrics["by_task"],
                "transfer_graph": redact_reality_graph(graph),
            }
        },
        "provenance": {
            "generated_by": "MIB Reference Runner",
            "generator_version": __version__,
            "score_recomputed": True,
        },
    }
    if statistics:
        report["statistics"] = statistics
    return report


def redact_reality_report(report: dict[str, Any], *, redaction_key: str = "") -> dict[str, Any]:
    """Public projection.

    Immediate: domain-level aggregates, the distance profile, attestation.
    Withheld: per-task score, per-Ability score, the specific support relation,
    and which wrong Skill produced which failure.  Transfer graphs are
    especially vulnerable to adaptive reverse engineering, so per-task feedback
    is deliberately not part of the immediate public surface.
    """
    out = json.loads(json.dumps(report))
    out["scope"] = "public"
    out["results"] = {"runs": [], "redacted": True, "raw_output_policy": "withheld"}
    body = out.get("extensions", {}).get(REALITY_EXTENSION)
    if body is not None:
        body.pop("by_task", None)
        body.pop("by_relation", None)
        graph = body.get("transfer_graph") or {}
        body["transfer_graph"] = {
            "ability_count": graph.get("ability_count"),
            "edge_count": graph.get("edge_count"),
            "digest": graph.get("digest"),
            "statement": graph.get("statement"),
        }
        for entry in body.get("distance_profile") or []:
            entry.pop("condition_scores", None)
    out.setdefault("provenance", {})["notes"] = (
        "Per-task scores, per-Ability results, and support relations are withheld from the "
        "immediate public surface to prevent adaptive reverse engineering of the transfer graph."
    )
    return out


def render_reality_card(report: dict[str, Any]) -> str:
    body = (report.get("extensions") or {}).get(REALITY_EXTENSION) or {}
    metrics = body.get("transfer_metrics") or {}
    agent = (report.get("system") or {}).get("agent", {})
    conditions = metrics.get("condition_scores") or {}
    lines = [
        "# MIB-R Reality Card",
        "",
        "```text",
        "MIB-R — Memory Intelligence Benchmark, Reality Track",
        "══════════════════════════════════════════════════════",
        "",
        f"Profile   {report['benchmark']['profile']['id']} {report['benchmark']['profile'].get('version', '')}".rstrip(),
        f"Domain    {body.get('domain', 'unknown')}",
        f"Agent     {agent.get('name', 'Unknown')} {agent.get('version', '')}".rstrip(),
        "",
        "Condition Scores",
    ]
    for name in CONDITIONS:
        if name in conditions:
            lines.append(f"  {name:28s} {100*float(conditions[name]):5.1f}")
    lines += ["", "Transfer Metrics"]
    for key, label, fmt in [
        ("natural_transfer_gain", "Natural Transfer Gain", "pp"),
        ("relevant_ablation_delta", "Relevant-Ablation Delta", "pp"),
        ("irrelevant_stability", "Irrelevant Stability", "score"),
        ("memory_harm", "Memory Harm", "pp"),
        ("negative_transfer_rate", "Negative Transfer Rate", "rate"),
        ("supported_transfer_success_rate", "Supported Transfer", "score"),
        ("near_match_resistance", "Near-Match Resistance", "score"),
        ("unsupported_memory_neutrality", "Unsupported Neutrality", "score"),
        ("oracle_routing_gain", "Oracle-Routed Gain", "pp"),
    ]:
        if metrics.get(key) is None:
            continue
        v = float(metrics[key])
        if fmt == "pp":
            lines.append(f"  {label:28s} {100*v:+5.1f} pp")
        elif fmt == "rate":
            lines.append(f"  {label:28s} {100*v:5.1f}%")
        else:
            lines.append(f"  {label:28s} {100*v:5.1f}")
    profile = body.get("distance_profile") or []
    if profile:
        lines += ["", "Transfer Profile"]
        for entry in profile:
            score = (entry.get("condition_scores") or {}).get("natural_memory")
            if score is None:
                continue
            lines.append(f"  {entry['class']} {entry.get('label', ''):24s} {100*float(score):5.1f}")
    lines += [
        "",
        "MIB-R-0.1-Dev is a prototype. It has no official MIB-R Score and is",
        "never ranked against MIB-Core.",
        "```",
        "",
    ]
    return "\n".join(lines)


#: Signature context for MIB-R result attestations.  Distinct from the core
#: evaluation-service context, so a Reality attestation can never be mistaken
#: for, or replayed as, an official MIB-Core result.
ATTESTATION_CONTEXT = "mib-reality-result-attestation/v1"


def attest_reality_result(
    *,
    report: dict[str, Any],
    public_report: dict[str, Any],
    root_secret: str,
    result_id: str | None = None,
) -> dict[str, Any]:
    """Sign what a MIB-R run was measured against.

    The attestation binds the Reality Pack digest, the private transfer graph
    digest, the environment adapter identity, and both report digests, so a
    published MIB-R result cannot be silently reattributed to a different pack,
    a different graph, or a different environment revision.

    It carries no score: MIB-R has no official Score, and inventing one here
    would be exactly the cross-ranking the track is separated to prevent.
    """
    body = (report.get("extensions") or {}).get(REALITY_EXTENSION) or {}
    benchmark = report.get("benchmark") or {}
    attestation = {
        "mib": "0.1",
        "kind": "MIBRealityResultAttestation",
        "version": "0.1.0",
        "result_id": result_id or f"realityres_{uuid.uuid4().hex[:16]}",
        "report_id": report.get("report_id"),
        "profile_id": (benchmark.get("profile") or {}).get("id"),
        "result_family": "reality",
        "official": False,
        "reality_pack": benchmark.get("reality_pack"),
        "transfer_graph_digest": (body.get("transfer_graph") or {}).get("digest"),
        "environment_adapter": (report.get("environment") or {}).get("reality_adapter", {}).get("adapter"),
        "conditions": sorted({r["condition"] for r in report.get("results", {}).get("runs", [])}),
        "internal_report_digest": digest_json(report),
        "public_report_digest": digest_json(public_report),
        "started_at": (report.get("execution") or {}).get("started_at"),
        "completed_at": (report.get("execution") or {}).get("completed_at"),
        "attestation_type": "reality_prototype_attestation",
        "statement": (
            "MIB-R-0.1-Dev prototype result. It has no official MIB-R Score and is never ranked "
            "against MIB-Core. This attestation binds the Reality Pack, the evaluator-private "
            "transfer graph digest, and the environment adapter this result was produced against."
        ),
    }
    key = derive_ed25519_private_key(root_secret, "reality-result-attestation")
    signature = sign_json_ed25519(attestation, key, context=ATTESTATION_CONTEXT)
    return {"attestation": attestation, "signature": signature}


def verify_reality_attestation(signed: dict[str, Any], *, root_secret: str | None = None) -> bool:
    expected = None
    if root_secret is not None:
        from ..service_signing import public_key_b64

        expected = public_key_b64(derive_ed25519_private_key(root_secret, "reality-result-attestation"))
    return verify_json_ed25519(
        signed.get("attestation"),
        signed.get("signature") or {},
        expected_context=ATTESTATION_CONTEXT,
        expected_public_key=expected,
    )
