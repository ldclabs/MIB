from __future__ import annotations

import copy
import hashlib
import json
import math
import time
import uuid

import jsonschema
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any

from .evaluator import evaluate_probe
from .late_sampling import sample_probe_for_delivery
from .types import AgentAdapter, AgentOutput, Observation, ActStep
from .world import WorldState

_EVENT_TYPE_MAP = {
    "interaction": "user_message",
    "observation": "environment_event",
    "tool_result": "tool_result",
    "distractor": "user_message",
    "document": "document",
    "feedback": "feedback",
    "time_advance": "time_event",
    "maintenance_window": "system_event",
    "system_event": "system_event",
    "custom": "custom",
}


class RunnerError(RuntimeError):
    pass


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _opaque(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:16]}"


def _actor_map(scenario: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {a["id"]: a for a in scenario.get("actors", [])}


def _project_observation(event: dict[str, Any], actors: dict[str, dict[str, Any]], virtual_time: str | None) -> Observation:
    actor = None
    if event.get("actor"):
        src = actors[event["actor"]]
        actor = {"id": src["id"], "kind": src.get("kind"), "display_name": src.get("display_name")}
    obs_type = _EVENT_TYPE_MAP.get(event["type"], event["type"])
    return Observation(
        observation_id=f"obs_{event['id']}",
        type=obs_type,
        virtual_time=virtual_time,
        actor=actor,
        content=event.get("content"),
        payload=copy.deepcopy(event.get("payload")),
        tool_call_id=event.get("tool_call_id"),
        tool=event.get("tool"),
    )


def _scenario_score(probe_results: list[dict[str, Any]]) -> float:
    scored = [p for p in probe_results if p.get("outcome") == "scored"]
    if not scored:
        return 0.0
    total_w = math.fsum(float(p.get("weight", 1.0)) for p in scored)
    if total_w <= 0:
        return 0.0
    return math.fsum(float(p["score"]) * float(p.get("weight", 1.0)) for p in scored) / total_w


def _virtual_time_for_event(event: dict[str, Any], current: str | None) -> str | None:
    at = event.get("at") or {}
    return at.get("time") or current


def _tool_result_observation(call_id: str, tool: str, payload: dict[str, Any], virtual_time: str | None) -> Observation:
    return Observation(
        observation_id=f"obs_tool_{call_id}",
        type="tool_result",
        virtual_time=virtual_time,
        payload=copy.deepcopy(payload),
        tool_call_id=call_id,
        tool=tool,
    )


def run_condition(
    *,
    scenario: dict[str, Any],
    agent: AgentAdapter,
    condition: str = "full",
    ablation: dict[str, Any] | None = None,
    repetition: int = 0,
    agent_seed: int | str | None = None,
) -> dict[str, Any]:
    if condition != "full" and not ablation:
        raise RunnerError("non-full condition requires ablation")

    run_id = _opaque("run")
    started = utc_now()
    actor_by_id = _actor_map(scenario)
    evaluator_map = {e["id"]: e for e in scenario.get("evaluators", [])}
    world = WorldState.from_scenario(scenario.get("world") or {})
    virtual_time = ((scenario.get("world") or {}).get("clock") or {}).get("start")
    execution = scenario.get("execution") or {}
    max_agent_turns = int(execution.get("max_agent_turns", 20))
    max_tool_calls = int(execution.get("max_tool_calls", 20))

    seed = agent_seed if agent_seed is not None else repetition
    agent.reset(run_id=run_id, seed=seed, virtual_time=virtual_time)

    removed_ids: set[str] = set()
    selected_probe_ids: set[str] | None = None
    ablation_id = None
    ablation_method = None
    if ablation:
        ablation_id = ablation["id"]
        ablation_method = ablation.get("method")
        if ablation_method != "replay_excluding_events":
            raise NotImplementedError(f"Milestone 4 implements replay_excluding_events only, got {ablation_method!r}")
        removed_ids = set((ablation.get("targets") or {}).get("event_ids", []))
        selected_probe_ids = set(ablation.get("probes", []))

    probes_by_trigger: dict[str, list[dict[str, Any]]] = {}
    for p in scenario.get("probes", []):
        if selected_probe_ids is not None and p["id"] not in selected_probe_ids:
            continue
        trigger = p.get("trigger") or {}
        if "after_event" not in trigger:
            raise NotImplementedError(f"Milestone 4 only implements after_event trigger: {p['id']}")
        probes_by_trigger.setdefault(trigger["after_event"], []).append(p)

    probe_results: list[dict[str, Any]] = []
    run_action_trace: list[dict[str, Any]] = []
    probe_variant_digests: dict[str, str] = {}
    request_counter = 0

    def req_id() -> str:
        nonlocal request_counter
        request_counter += 1
        return f"req_{request_counter:06d}"

    def deliver_observation(obs: Observation) -> None:
        agent.observe(run_id=run_id, request_id=req_id(), observation=obs)

    def append_probe_result(p: dict[str, Any], output: AgentOutput, score: float, eval_results: list[dict[str, Any]], latency_ms: float, action_trace: list[dict[str, Any]] | None = None) -> None:
        failures = sorted({fc for e in eval_results for fc in e.get("failure_codes", [])})
        payload = asdict(output)
        probe_results.append({
            "probe_id": p["id"],
            "probe_kind": p.get("kind"),
            "condition": condition,
            "repetition": repetition,
            "outcome": "scored",
            "score": score,
            "weight": float(p.get("weight", 1.0)),
            "dimensions": list(p.get("dimensions") or []),
            "evaluator_results": eval_results,
            "failure_codes": failures,
            "latency_ms": latency_ms,
            "output_digest": hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest(),
            **({"extensions": {"mib.runner.action_trace": copy.deepcopy(action_trace)}} if action_trace is not None else {}),
        })

    def execute_respond_probe(p: dict[str, Any]) -> None:
        started_ns = time.perf_counter_ns()
        output = agent.respond(
            run_id=run_id,
            request_id=req_id(),
            interaction_id=f"interaction_{p['id']}",
            input_data=copy.deepcopy(p.get("input") or {}),
            virtual_time=virtual_time,
        )
        score, eval_results = evaluate_probe(output, p, evaluator_map, {"world": world, "action_trace": []})
        append_probe_result(p, output, score, eval_results, (time.perf_counter_ns() - started_ns) / 1_000_000)

    def execute_act_probe(p: dict[str, Any]) -> None:
        started_ns = time.perf_counter_ns()
        inp = copy.deepcopy(p.get("input") or {})
        goal = inp.get("goal") or inp.get("content")
        allowed = inp.get("available_tools")
        tool_defs = world.exposed_tools(allowed)
        available_names = {t["name"] for t in tool_defs}
        if allowed:
            missing = set(allowed) - available_names
            if missing:
                raise RunnerError(f"probe {p['id']} references unavailable tools: {sorted(missing)}")
        constraints = list(inp.get("constraints") or [])
        task_id = f"task_{p['id']}"
        trace: list[dict[str, Any]] = []
        seen_calls: set[str] = set()
        final_step: ActStep | None = None

        for turn in range(max_agent_turns):
            step = agent.act(
                run_id=run_id,
                request_id=req_id(),
                task_id=task_id,
                goal=goal if turn == 0 else None,
                constraints=constraints if turn == 0 else [],
                tools=tool_defs if turn == 0 else [],
                continuation=turn > 0,
                virtual_time=virtual_time,
            )
            if step.type == "tool_call":
                if not step.tool or not step.tool_call_id:
                    raise RunnerError("tool_call requires tool and tool_call_id")
                if step.tool not in available_names:
                    raise RunnerError(f"Agent called unavailable benchmark tool: {step.tool}")
                if step.tool_call_id in seen_calls:
                    raise RunnerError(f"duplicate tool_call_id: {step.tool_call_id}")
                seen_calls.add(step.tool_call_id)
                if len(seen_calls) > max_tool_calls:
                    raise RunnerError("max_tool_calls exceeded")
                tool_spec = next(t for t in tool_defs if t["name"] == step.tool)
                jsonschema.Draft202012Validator(tool_spec.get("input_schema") or {}).validate(step.arguments or {})
                execution_result = world.execute_tool(step.tool, step.arguments or {})
                row = {
                    "sequence": len(trace) + 1,
                    "kind": "tool_call",
                    "tool_call_id": step.tool_call_id,
                    "tool": step.tool,
                    "arguments": copy.deepcopy(step.arguments or {}),
                    "result": copy.deepcopy(execution_result.result),
                }
                trace.append(row)
                run_action_trace.append({"probe_id": p["id"], **copy.deepcopy(row)})
                deliver_observation(_tool_result_observation(step.tool_call_id, step.tool, execution_result.result, virtual_time))
                continue
            if step.type in {"final", "abstention"}:
                final_step = step
                break
            raise RunnerError(f"unsupported ActStep type: {step.type!r}")

        if final_step is None:
            raise RunnerError("act probe did not terminate within max_agent_turns")
        output = AgentOutput(
            type="abstention" if final_step.type == "abstention" else ("structured" if final_step.value is not None else "message"),
            content=final_step.content,
            value=final_step.value,
            attribution=final_step.attribution,
        )
        score, eval_results = evaluate_probe(output, p, evaluator_map, {"world": world, "action_trace": trace})
        append_probe_result(p, output, score, eval_results, (time.perf_counter_ns() - started_ns) / 1_000_000, trace)

    def execute_probe(p: dict[str, Any]) -> None:
        sampled, variant_digest = sample_probe_for_delivery(scenario=scenario, probe=p, repetition=repetition)
        if variant_digest:
            probe_variant_digests[p["id"]] = variant_digest
        try:
            if sampled.get("delivery") == "respond":
                execute_respond_probe(sampled)
            elif sampled.get("delivery") == "act":
                execute_act_probe(sampled)
            else:
                raise NotImplementedError(f"Milestone 4 implements respond/act probes, got {sampled.get('delivery')!r}")
        except Exception as exc:
            probe_results.append({
                "probe_id": sampled["id"],
                "probe_kind": sampled.get("kind"),
                "condition": condition,
                "repetition": repetition,
                "outcome": "execution_failure",
                "score": 0.0,
                "weight": float(sampled.get("weight", 1.0)),
                "dimensions": list(sampled.get("dimensions") or []),
                "failure_codes": ["execution_failure"],
                "latency_ms": 0.0,
                "evaluator_results": [],
                "output_digest": hashlib.sha256(repr(exc).encode()).hexdigest(),
                "extensions": {"mib.runner.error": repr(exc)},
            })

    for event in scenario.get("timeline", []):
        virtual_time = _virtual_time_for_event(event, virtual_time)
        for update in event.get("world_updates", []):
            world.apply(update)
        if event["id"] not in removed_ids and event.get("visibility") in {"agent", "both"}:
            if event["type"] not in {"checkpoint", "world_update"}:
                deliver_observation(_project_observation(event, actor_by_id, virtual_time))
        for p in probes_by_trigger.get(event["id"], []):
            execute_probe(p)

    expected_probe_ids = {p["id"] for p in scenario.get("probes", []) if selected_probe_ids is None or p["id"] in selected_probe_ids}
    executed_probe_ids = {p["probe_id"] for p in probe_results}
    missing = expected_probe_ids - executed_probe_ids
    if missing:
        raise RunnerError(f"untriggered probes: {sorted(missing)}")

    completed = utc_now()
    status = "failed" if any(p["outcome"] == "execution_failure" for p in probe_results) else "succeeded"
    instance = scenario.get("instantiation") or {}
    result = {
        "run_id": run_id,
        "scenario_instance_id": f"{scenario['id']}:{instance.get('seed', 'instance')}",
        "scenario_instance_version": scenario.get("version"),
        "template_id": instance.get("template_id", scenario["id"]),
        "template_version": instance.get("template_version", scenario.get("version")),
        "instance_seed": instance.get("seed"),
        "condition": condition,
        **({"ablation_id": ablation_id, "ablation_method": ablation_method} if ablation else {}),
        "repetition": repetition,
        "agent_seed": seed,
        "status": status,
        "started_at": started,
        "completed_at": completed,
        "scenario_score": _scenario_score(probe_results),
        "probe_results": probe_results,
        "validity": {"causal_pair_valid": True, "runner_valid": True, "notes": []},
        "extensions": {
            "mib.runner.world_state": copy.deepcopy(world.state),
            "mib.runner.world_state_digest": hashlib.sha256(json.dumps(world.state, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest(),
            "mib.runner.action_trace": run_action_trace,
            "mib.runner.probe_variant_digests": probe_variant_digests,
        },
    }
    # A transport-backed Adapter may own one subprocess per condition.  Close it
    # only after all observations, Probes, and result traces are complete.
    close = getattr(agent, "close", None)
    if callable(close):
        try:
            close(run_id=run_id)
        except TypeError:
            close()
    return result


def run_scenario(*, scenario: dict[str, Any], agent_factory, include_ablations: bool = True, repetition: int = 0, agent_seed: int | str | None = None) -> list[dict[str, Any]]:
    runs = [run_condition(scenario=scenario, agent=agent_factory(), condition="full", repetition=repetition, agent_seed=agent_seed)]
    if include_ablations:
        kind_to_condition = {
            "relevant_memory": "relevant_ablation",
            "irrelevant_memory": "irrelevant_ablation",
            "no_memory": "no_memory",
            "stale_memory": "stale_memory",
            "harmful_memory": "harmful_memory",
            "counterexample": "counterexample",
        }
        for a in scenario.get("ablations", []):
            if a.get("method") != "replay_excluding_events":
                continue
            runs.append(run_condition(
                scenario=scenario,
                agent=agent_factory(),
                condition=kind_to_condition.get(a["kind"], "custom"),
                ablation=a,
                repetition=repetition,
                agent_seed=agent_seed,
            ))
    return runs
