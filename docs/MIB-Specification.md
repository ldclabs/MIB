# MIB Specification

## Memory Intelligence Benchmark — v0.1 normative specification

**Version:** 0.1 (implementation 0.8.0)
**Status:** Normative. This document describes what the reference implementation in `src/mib_runner/` executes and scores. Everything that was designed but is not executed lives in Appendix A (Roadmap), not in the body.

The earlier design drafts (`MIB-Architecture.md`, `MIB-Scenario-Model.md`, `MIB-Scoring.md`) are archived under `docs/archive/` for rationale and history. Where they and this document differ, this document and the code win. The Agent Adapter wire protocol is specified separately in `MIB-Agent-Adapter.md`; the hosted evaluation service in `MIB-Leaderboard-Evaluation-Service.md`; the supplemental Transfer Intelligence and MIB-R layers in `docs/experimental/`.

Normative words **MUST**, **MUST NOT**, **SHOULD**, and **MAY** carry their usual meaning. Section numbers are stable and are cited from code comments.

---

# 0. Scope

MIB measures how effectively an Agent plus its long-term memory system uses the past to improve future cognition and behavior. It does not primarily measure how much of the past the system can retrieve.

The evaluated object is:

```text
Agent + Long-Term Memory System, observed across time
```

MIB v0.1 is architecture-neutral: a participant needs only a black-box Agent that implements `reset`, `observe`, `respond`, and `act`. No memory representation, memory API, or KIP conformance is required, and none earns points.

---

# 1. Thesis and Principles

## 1.1 Thesis

> A memory system should not be judged by how much of the past it can retrieve, but by whether the right parts of the past change the future in the right way.

Three requirements follow:

1. **Memory must have causal consequences.** If removing a supposedly relevant memory does not change a relevant future decision, that item was stored history, not functioning memory.
2. **Memory must be context-sensitive.** A memory that helps in one context and harms unrelated contexts is weak memory intelligence.
3. **Memory must preserve distinctions.** Current vs historical truth, statement vs accepted belief, source vs provenance, event vs experience, knowledge vs skill, unknown vs false.

## 1.2 What a Scenario tests

Every Scenario exists to test one proposition:

> The past should change the future when relevant, should not control the future when irrelevant, and should be resisted when stale or harmful.

## 1.3 What v0.1 can and cannot claim

Every v0.1 Scenario is **MIB-S** scale: a few dozen events, far below any model's context window. At this scale MIB measures whether an Agent uses memory *semantics* correctly in context. It does not yet discriminate memory *systems*: a stateless full-context model saturates the relevant-memory ablation, because removing an event from the replay removes the information, not a retrieval step. That discrimination needs the larger history scales listed in Appendix A.

---

# 2. Benchmark Structure

## 2.1 Tracks

**Track A — Memory System.** Base model, agent prompt, reasoning policy, tools, environment, and Runner are fixed; only the memory system varies. Preferred for comparing memory architectures.

**Track B — Integrated Agent.** Model, agent policy, memory, orchestration, and tool strategy may all vary. Measures the complete Agent's memory-enabled capability and is intentionally not model-normalized.

Track A and Track B **MUST NOT** share one ranking.

## 2.2 Dimensions

MIB-Core-0.1 scores six capability dimensions:

| id | Dimension | What it asks |
|---|---|---|
| `retention_retrieval` | Retention & Retrieval | Can relevant past information be recovered under indirect cues and interference? |
| `temporal_memory` | Temporal Memory | Can current state, historical state, transitions, and stale information be distinguished? |
| `epistemic_memory` | Epistemic Memory | Who said what, correction vs contradiction, unknown vs false, source authority? |
| `experience_memory` | Experience Memory | Is the goal / action / failure / recovery structure of past experience preserved and reused? |
| `skill_learning_transfer` | Skill Learning & Transfer | Does repeated experience become reusable policy, including knowing when *not* to apply it? |
| `causal_memory_impact` | Causal Memory Impact | Does relevant memory measurably improve behavior while irrelevant and harmful memory do not control it? |

Two further dimensions (`selective_forgetting`, `prospective_self_memory`) are reserved in the schema and are roadmap (Appendix A).

## 2.3 Profiles

A **Profile** is a versioned JSON policy object that fixes: `id`, `version`, `track`, `scale`, `official`, `required_templates`, `required_coverage`, `repetitions`, `instance_seeds`, per-dimension `weight`, and `statistics` (confidence level, bootstrap resamples, `min_templates_per_dimension`). Every published score is identified by its Profile; weights from different Profiles **MUST NOT** be mixed.

The executed pack is exactly `required_templates` (§5.1). Profiles with `official: false` produce development scores that are never leaderboard scores.

## 2.4 Packs and visibility

MIB v0.1 defines 60 canonical Scenario Templates: 24 Public Dev, 30 Hidden Eval, 6 Private Holdout. Public Dev Templates are for integration, debugging, and regression testing. Official evaluation uses Hidden and Holdout instantiations that participants never see (§11).

---

# 3. Roles

```text
Scenario Template ──materialize──▶ Scenario Instance
                                        │
                              ┌─────────▼──────────┐
                              │       Runner       │  owns the timeline, the virtual
                              │  + World Simulator │  clock, hidden ground truth, tools
                              └───┬────────────┬───┘
                    observations  │            │  tool_result
                    probes/tasks  ▼            ▲  tool_call
                              ┌───────────────────┐
                              │  Agent (Adapter)  │  black box: reset / observe / respond / act
                              └───────────────────┘
                                        │ outputs, action trace, world outcome
                              ┌─────────▼──────────┐
                              │     Evaluators     │  deterministic, world-state, trajectory
                              └─────────┬──────────┘
                              ┌─────────▼──────────┐
                              │   Scoring Engine   │  probe → instance → template → dimension → MIB
                              └────────────────────┘
```

- The **Runner** loads a Scenario, materializes parameters, seeds the World, delivers visible Timeline events, strips hidden fields, delivers Probes, executes tool calls through the World Simulator, runs Evaluators, performs ablation replay, and produces the Run Artifact.
- The **World Simulator** owns world state, hidden ground truth, tool state, and the virtual clock. The Agent never mutates world state directly; it observes consequences of tool calls.
- The **Agent Adapter** is the only channel to the participant system. In-process Agents implement the Python protocol in `types.py`; external Agents speak the stdio JSONL or local HTTP protocol of `MIB-Agent-Adapter.md`.
- The **Runner MUST NOT help the Agent**: no summarizing, no highlighting relevant memories, no labeling distractors, no revealing authority, no injecting Oracle state.

---

# 4. Scenario Model (executable subset)

The machine contract is `schemas/mib-scenario.schema.json` (JSON Schema 2020-12). Every enumeration in the schema is something the reference Runner executes; the reference Scenario Validator additionally rejects anything the Runner cannot execute (§4.10).

## 4.1 Top-level object

Required: `mib` (`"0.1"`), `kind` (`MemoryEpisodeProgram`), `id`, `version`, `title`, `suite`, `dimensions`, `world`, `timeline`, `probes`, `evaluators`, `scoring`. Optional: `status`, `description`, `tags`, `difficulty`, `template`, `instantiation`, `requirements`, `execution`, `leakage`, `actors`, `ablations`, `metadata`, `extensions`.

Scenario ids follow `MIB-<FAMILY>-<NNN>` (`RET`, `TIME`, `EPI`, `EXP`, `SKILL`, `CAUSAL`, `X` for cross-dimension, `ADV` for adversarial). `version` is semantic-version-like; a change to timeline, ground truth, ablation semantics, or scoring **MUST** bump at least the minor version.

`dimensions` lists the dimensions the Scenario evidences; `scoring.dimension_weights` (§4.9) partitions its evidence among them.

## 4.2 Template vs Instance

A **Template** carries `template.parameters`; an **Instance** is fully materialized. The reference materializer supports parameter `source` values `fixed`, `choice`, `integer_range`, `number_range`, seeded by `random.Random(str(seed))`, and substitutes `${name}` placeholders everywhere in the document (oracle included), preserving JSON type when a field is exactly one placeholder.

A materialized Instance records `instantiation`: `template_id`, `template_version`, `seed`, `parameter_digest`, `generator_version`. Hidden evaluation replaces the seed with an opaque HMAC alias before anything reaches the participant (§11).

## 4.3 Requirements, execution policy, leakage policy

`requirements.capabilities` lists what the Agent must support: `observe`, `respond`, `act`, `tools`, `virtual_time` (the schema also reserves `maintenance`, `snapshot`, `memory_inspect`, `memory_delete`, `memory_restore`). A Template is **unsupported** for an Agent only when the Agent's descriptor declares a required capability `false` (§6.6).

`execution` sets `max_agent_turns` (default 20) and `max_tool_calls` (default 20) per act Probe. The only execution policy is `fail_probe` (§5.4).

`leakage` **MUST** declare `future_probe_visible_during_formation`, `oracle_visible_to_agent`, `ablation_labels_visible_to_agent`, and `hidden_world_state_visible_to_agent` as `false`; the validator rejects anything else. `probe_sampling` is `fixed`, `late`, or `hidden_late` (§4.6).

## 4.4 Actors and World

`actors` give benchmark identities (`id`, `kind`, `display_name`); the Runner projects only those three fields into observations. Actor identity is not authentication.

`world` contains:

- `clock` — `{mode: "virtual", start: <ISO 8601 UTC>, timezone}`; the Runner owns clock progression (§4.5).
- `state` — mutable simulator state, addressed by JSON Pointer.
- `hidden_ground_truth` — oracle-only facts; never delivered to the Agent.
- `tools` — tool definitions exposed to act Probes. Each tool declares `id`, `version`, `operations[]` (`name`, `description`, `input_schema`) and a `simulator_binding`. The reference World Simulator implements three bindings: `mib.deployment.v1` (inspect / select target, run migration, restart service), `mib.workspace.v1` (select workspace, edit, save), `mib.contextual_save.v1` (activate context, edit, commit, with an `context_required` flag that turns activation into a policy violation when false). A tool call reaches the Agent as `<tool id>.<operation>`.

## 4.5 Timeline

Each event has `id`, `stage` (`seed` | `past` | `interference` | `consolidation` | `pre_probe`), `type`, `at`, `visibility`, and optionally `actor`, `content`, `payload`, `world_updates`, `oracle_labels`, `tags`.

Executable event types and their observation projection:

| Scenario type | Delivered as | Notes |
|---|---|---|
| `interaction`, `distractor` | `user_message` | |
| `observation` | `environment_event` | |
| `tool_result` | `tool_result` | with `tool_call_id`, `tool`, `payload` |
| `document`, `feedback`, `custom` | same name | |
| `time_advance` | `time_event` | moves the clock (below) |
| `maintenance_window` | `system_event` | no maintenance hook is invoked in v0.1 |
| `checkpoint`, `world_update` | not delivered | harness-only |

`visibility` is `agent`, `harness`, or `both`; only `agent`/`both` events are delivered. `oracle_labels`, `tags`, relevance annotations, and hidden ground truth are never delivered.

`world_updates` (`set`, `unset`, `increment`, `append`, `remove` on a JSON Pointer path) are harness operations, not memory writes. They are applied in **every** condition, including conditions that ablate the event (§5.2).

**Virtual time.** The Runner keeps a current virtual time, initialized from `clock.start`. An event's `at.time` sets it; a `time_advance` event may instead carry `payload.duration` as an ISO 8601 duration (`P3D`, `PT2H30M`) that advances it. Every observation and Probe carries the current virtual time. `at.sequence` orders events and **MUST** be monotonic when present.

## 4.6 Probes

A Probe is a future test. Required: `id`, `kind`, `trigger`, `delivery`, `input`, `oracle`, `evaluators`. Optional: `dimensions`, `weight` (default 1.0), `tags`, `extensions`.

- `trigger` is `{after_event: <event id>}`. Probes fire immediately after that event is processed, in Scenario order.
- `delivery` is `respond` (a cognitive answer; `input.content`) or `act` (a task; `input.goal`, `input.available_tools`, `input.constraints`).
- `kind` is descriptive (`factual`, `implicit`, `multi_hop`, `temporal`, `epistemic`, `experience`, `skill`, `action`, `historical`, `abstention`, …). It selects failure-code vocabulary (§5.4) but not scoring.
- `dimensions` tags the Probe for dimension attribution (§6.3).

**Late sampling.** When `leakage.probe_sampling` is `late` or `hidden_late`, the Runner may choose among `extensions["mib.probe_sampling"].input_variants` only when the Probe fires. The choice is a deterministic function of (scenario id, instance seed, repetition, probe id) and is therefore identical across a full run and all its ablation runs; a digest of the delivered input is recorded for pair validation (§7.7). Oracle and evaluator fields are never sampled.

Future Probes **MUST NOT** be visible during memory formation. The Runner enforces this: nothing from `probes` is projected into an observation.

## 4.7 Oracle and Evaluators

`oracle` may carry `accepted[]`, `forbidden[]`, `expected_status` (`known` | `unknown` | `contested` | `historical` | `not_applicable`), `world_assertions[]`, `trajectory_requirements[]`, and free-text `expected`, `reference`, `notes`. Oracle data is harness-only.

Evaluators are referenced by id from `evaluators[]`. Each produces `score ∈ [0,1]`, `passed`, `failure_codes[]`, `details`.

**`set_match`** — short answers. `config.normalization` ∈ `none` | `trim` | `casefold_trim` | `casefold_trim_collapse_ws` | `answer_normalized` (default; collapses whitespace, casefolds, strips edge punctuation so that "AX-91." equals "AX-91"). `config.match` ∈ `contains` (default; whole-token containment, so "AX-9" does not match inside "AX-91") | `exact`. A structured output whose value is a scalar is compared as that scalar's text.

```text
accepted value present, no forbidden value       → 1
forbidden value present anywhere                 → 0   stale_memory_adoption
neither                                          → 0   retrieval_miss
expected_status = unknown:
  output.type = abstention, or an accepted value → 1
  any other definite answer                      → 0   false_certainty
expected_status ≠ unknown and output.type = abstention → 0   retrieval_miss
```

Policy: an answer that hedges between the current and the superseded value ("UTC+1, previously UTC+8") fails a Probe that lists the old value as forbidden. Such Probes ask for the value only; a Scenario that wants historical context asks for it in a separate historical Probe.

**`world_state`** — `oracle.world_assertions[]` of `{path, operator, value}` against the final simulator state, operators `eq`, `neq`, `exists`, `not_exists`, `contains`, `gte`, `lte`. Score is the fraction of satisfied assertions; any unsatisfied assertion adds `trajectory_collapse`. World truth outranks anything the Agent says.

**`trajectory`** — `oracle.trajectory_requirements[]` against the tool-call sequence of the act Probe: `required_action`, `forbidden_action`, `before` / `after` (first occurrences), `max_occurrences`, `min_occurrences`. Score is the fraction satisfied. `forbidden_action` is satisfied only by a **non-empty** trajectory that omits the action; an Agent that does nothing earns no credit for avoiding it. A forbidden action that was taken is coded `error_recurrence` for `experience` Probes and `negative_transfer` otherwise.

**`composite`** — `components[]` of `{evaluator, weight}`; weighted mean of the component scores, weights normalized, failure codes unioned.

A Probe that references several evaluators receives their unweighted mean; canonical packs **SHOULD** reference one evaluator (a composite when several signals matter).

## 4.8 Ablations

An Ablation turns a memory test into a causal test. Required: `id`, `kind`, `probes[]` (the scored subset), `method`, `expected_effect`. Optional: `targets.event_ids[]`, `injections[]`, `tolerance`, `oracle_value_survives_by_design`, `description`.

Kinds: `relevant_memory` (expected `degrade`), `irrelevant_memory` (`neutral`), `no_memory` (`degrade`), `harmful_memory` and `stale_memory` (`resist`), `counterexample` (`degrade`; §7.8), `custom`.

Methods:

- `replay_excluding_events` — the full timeline is replayed with `targets.event_ids` withheld from the Agent. Their `world_updates` still apply.
- `replay_with_injections` — the full timeline is replayed plus `injections[]`, evaluator-controlled events delivered through the ordinary observation channel. An injection anchored with `at.after_event` is delivered after that event and before any Probe that event triggers; otherwise it is inserted by `at.sequence` / `at.time` order. Injections **MUST NOT** carry `world_updates`: memory is the treatment variable, world truth is not.

`tolerance` (default 0) is the stochastic-wobble allowance used by the tolerant IMS and HRS forms (§7.3, §7.4) and is copied onto every run of that ablation as `ablation_tolerance`.

A `relevant_memory` ablation is only meaningful when removing its targets removes the answer. The validator warns when an accepted Oracle value still appears verbatim in a surviving event; `oracle_value_survives_by_design: true` silences the warning when that is intended.

## 4.9 Scoring block

`scoring.probe_aggregation` is `weighted_mean`. `scoring.score_range` is `{min: 0, max: 100}`. `scoring.dimension_weights` maps each declared dimension to its evidence weight and **MUST** sum to 1; `scoring.causal_metrics[]` names the causal metrics the Scenario intends to produce (descriptive; computation follows the ablation kinds actually declared).

## 4.10 Validation

A Scenario enters a pack only if all of the following pass:

1. JSON Schema validation.
2. Reference resolution: unique ids for events, probes, evaluators, ablations, actors; every actor, trigger event, evaluator, composite component, ablation probe, ablation target, injection anchor, and `available_tools` entry resolves.
3. Timeline sequence monotonic when numeric.
4. Leakage policy flags all `false`; `dimension_weights` sum to 1; composite weights sum to 1 (warning otherwise, the Runner normalizes).
5. Injections carry no `world_updates` and no ids that collide with timeline events.
6. Runner executability: evaluator types, trigger kinds, delivery modes, ablation methods, simulator bindings, event types, `set_match` configuration, world-assertion operators, and trajectory requirement types are all ones the reference Runner implements. A schema-valid Scenario that would crash the Runner or score every Agent zero is an error, not a warning.
7. Relevant-ablation leak check (§4.8) — warning.

## 4.11 Example

```json
{
  "mib": "0.1", "kind": "MemoryEpisodeProgram", "id": "MIB-TIME-001", "version": "0.2.0",
  "title": "Timezone update and historical recall", "suite": "time",
  "dimensions": ["temporal_memory", "causal_memory_impact"],
  "template": {"parameters": [
    {"name": "old_zone", "type": "string", "source": "choice", "choices": ["UTC+8", "UTC+9"]},
    {"name": "new_zone", "type": "string", "source": "choice", "choices": ["UTC+1", "UTC+2"]}]},
  "requirements": {"capabilities": ["respond", "virtual_time"]},
  "leakage": {"probe_sampling": "late", "future_probe_visible_during_formation": false,
              "oracle_visible_to_agent": false, "ablation_labels_visible_to_agent": false,
              "hidden_world_state_visible_to_agent": false},
  "actors": [{"id": "alice", "kind": "person", "display_name": "Alice"}],
  "world": {"clock": {"mode": "virtual", "start": "2026-01-01T09:00:00Z", "timezone": "UTC"}, "state": {}},
  "timeline": [
    {"id": "e-old", "stage": "past", "type": "interaction", "at": {"sequence": 1, "time": "2026-01-01T09:00:00Z"},
     "visibility": "agent", "actor": "alice", "content": "My timezone is ${old_zone}."},
    {"id": "e-update", "stage": "past", "type": "interaction", "at": {"sequence": 2, "time": "2026-02-01T09:00:00Z"},
     "visibility": "agent", "actor": "alice", "content": "I have moved. My timezone is now ${new_zone}."},
    {"id": "d-1", "stage": "interference", "type": "distractor", "at": {"sequence": 3, "time": "2026-02-02T09:00:00Z"},
     "visibility": "agent", "actor": "alice", "content": "I bought a new notebook today."},
    {"id": "cp", "stage": "pre_probe", "type": "checkpoint", "at": {"sequence": 4}, "visibility": "harness"}
  ],
  "probes": [
    {"id": "p-current", "kind": "temporal", "trigger": {"after_event": "cp"}, "delivery": "respond",
     "input": {"content": "What is my current timezone? Answer with the UTC offset only."},
     "oracle": {"expected_status": "known", "accepted": ["${new_zone}"], "forbidden": ["${old_zone}"]},
     "evaluators": ["eval-zone"], "dimensions": ["temporal_memory"], "weight": 1.0},
    {"id": "p-history", "kind": "historical", "trigger": {"after_event": "cp"}, "delivery": "respond",
     "input": {"content": "What timezone did I use before I moved? Answer with the UTC offset only."},
     "oracle": {"expected_status": "historical", "accepted": ["${old_zone}"]},
     "evaluators": ["eval-zone"], "dimensions": ["temporal_memory"], "weight": 1.0}
  ],
  "ablations": [
    {"id": "a-relevant", "kind": "relevant_memory", "probes": ["p-current"], "method": "replay_excluding_events",
     "targets": {"event_ids": ["e-update"]}, "expected_effect": "degrade"},
    {"id": "a-irrelevant", "kind": "irrelevant_memory", "probes": ["p-current", "p-history"],
     "method": "replay_excluding_events", "targets": {"event_ids": ["d-1"]}, "expected_effect": "neutral", "tolerance": 0.05}
  ],
  "evaluators": [{"id": "eval-zone", "type": "set_match", "config": {"normalization": "answer_normalized"}}],
  "scoring": {"probe_aggregation": "weighted_mean", "score_range": {"min": 0, "max": 100},
              "dimension_weights": {"temporal_memory": 0.8, "causal_memory_impact": 0.2},
              "causal_metrics": ["causal_memory_impact", "memory_benefit", "irrelevant_memory_stability"]}
}
```

---

# 5. Execution Semantics

## 5.1 Pack execution

`run_benchmark_pack` (public Templates) and `run_materialized_pack` (evaluator-materialized hidden Instances):

1. The executed Template set is exactly `profile.required_templates`; a missing or an extra Template on disk is an error, never a silent change of the score.
2. Every Template and every Instance is validated (§4.10) before execution.
3. For each Instance and each repetition `r`, the Agent seed is `"<instance seed>:<r>"` (an opaque alias for hidden Instances), and the full condition plus every declared ablation are executed as separate conditions.
4. Templates the Agent does not support (§6.6) are not executed and are listed in the report.

## 5.2 Conditions and isolation

Each condition of a repetition — `full`, then each ablation in declaration order — runs against a **fresh Agent instance** (`agent_factory()`), with the same Instance, the same seed, the same virtual clock, and the same late-sampled Probe inputs. Only the memory intervention differs. No state may carry from one condition into another; a transport-backed Agent gets a fresh `reset` with a new opaque `run_id` and is closed on every exit path.

Ablation conditions execute the **complete** Probe program of the Instance, so that earlier Probe questions or actions cannot become a hidden second intervention; only the ablation's declared `probes[]` carry weight in the causal comparison (the rest are recorded with weight 0).

World updates apply identically in every condition (§4.5). Condition labels, ablation ids, and expected effects are never visible to the Agent.

## 5.3 The act loop

For an act Probe the Runner sends the goal, constraints, and the tool definitions on the first turn, then alternates: the Agent returns either a `tool_call` (with a unique `tool_call_id`, a tool name among the offered ones, and arguments the tool's `input_schema` accepts) or a terminal `final` / `abstention`. Each tool call is executed by the World Simulator and its result is delivered back as a `tool_result` observation. The loop ends at a terminal step, at `max_agent_turns`, or at `max_tool_calls`. The action trace (sequence, tool, arguments, result) is recorded on the Probe result and drives the trajectory evaluator.

## 5.4 Failure classification

Every executed Probe has exactly one `outcome`:

| Outcome | Meaning | Score | Run status |
|---|---|---|---|
| `scored` | The Probe was executed and evaluated. A **cognitive failure** is still `scored`: wrong answer, abstention where an answer was knowable, a forbidden action, and Agent misbehaviour — exhausting `max_agent_turns` or `max_tool_calls` (`trajectory_collapse`), calling a tool that was not offered, arguments the schema rejects, a reused `tool_call_id`, an unknown step type (`agent_protocol_violation`). | evaluator score, or 0 with the failure code | `succeeded` |
| `execution_failure` | Runner, World Simulator, evaluator, or transport fault (an exception outside the Agent's contract, a timeout on the transport). | 0, weight kept | `failed` |
| `unsupported` | Reserved for Probes of unsupported Templates; v0.1 skips such Templates whole (§6.6). | — | — |

Failure codes are drawn from the report schema's closed vocabulary: `formation_miss`, `retrieval_miss`, `identity_mismatch`, `stale_memory_adoption`, `source_confusion`, `correction_loss`, `false_certainty`, `trajectory_collapse`, `skill_non_transfer`, `negative_transfer`, `error_recurrence`, `counterexample_neglect`, `commitment_miss`, `self_model_drift`, `memory_hallucination`, `irrelevant_memory_interference`, `authority_confusion`, `agent_protocol_violation`, `execution_failure`, `timeout`, `rate_limited`, `adapter_error`, `tool_error`, `evaluator_error`, `custom`.

The distinction matters because the **execution failure rate** (§6.6) gates leaderboard eligibility: a looping or protocol-breaking Agent must not raise it.

## 5.5 Run Artifact

One run (one condition of one repetition) records: `run_id` (opaque), `scenario_instance_id`, `template_id`, `template_version`, `instance_seed`, `condition`, `ablation_id`, `ablation_method`, `ablation_tolerance`, `repetition`, `agent_seed`, `status`, timestamps, `scenario_score`, `probe_results[]` (probe id and kind, outcome, score, weight, dimensions, evaluator results, failure codes, latency, output digest), and `validity` (§7.7). Runner-private extensions (final world state and its digest, the action trace, late-sampling digests) are stripped from published reports.

---

# 6. Scoring

All arithmetic uses full precision (`math.fsum`); rounding is for display only. Internal scores are `p ∈ [0,1]`; displayed capability scores are `100p`; causal deltas are displayed in percentage points and may be negative.

## 6.1 Evaluator result → Probe score

A Probe's score is its evaluator's score, or the unweighted mean when it references several evaluators (§4.7).

## 6.2 Scenario score

For one run,

\[
S = \frac{\sum_q w_q P_q}{\sum_q w_q}
\]

over Probes with outcome `scored` or `execution_failure`. An execution failure stays in the denominator at score 0 (`fail_probe`); dropping it would let a partially failing Agent average only its successes.

## 6.3 Instance scores

Across the `R` full-condition repetitions of an Instance, `full_score = mean_r S_r`.

For each non-causal dimension `d` the Instance declares, the dimension score is the weighted mean over full runs of the Probes tagged with `d`; Probes without tags count for every dimension; if no Probe carries the tag the run's scenario score is used. The causal dimension is never derived from full performance; it comes only from paired metrics (§7.6).

## 6.4 Template and Dimension aggregation

Aggregation is Template-first so that instance count never becomes semantic weight:

\[
T_{t,d} = \frac{1}{N_t}\sum_{s \in t} S_{s,d}
\qquad
D_d = 100 \cdot \frac{\sum_t v_{t,d}\,T_{t,d}}{\sum_t v_{t,d}}
\]

where `v_{t,d}` is the Template's `scoring.dimension_weights[d]` (its evidence weight for `d`).

## 6.5 MIB Score, coverage, eligibility

\[
MIB_{base} = \sum_d W_d D_d, \qquad \sum_d W_d = 1
\]

with `W_d` from the Profile. v0.1 defines no global guardrail penalty, so `MIB = MIB_base`.

Coverage per dimension is the evaluated evidence weight over the required evidence weight, where the required weight counts every Template of the pack — including Templates that were not executed because the Agent does not support them. Profile coverage is `Σ_d W_d · coverage_d`. A report whose profile coverage is below `required_coverage` is **partial** and is never `official`; `official` additionally requires the Profile's `official` flag.

## 6.6 Unsupported and execution-failure rates

A Template is **unsupported** when the Agent's descriptor declares a required capability `false`. It is skipped, listed under `coverage.unsupported_required_templates`, and its weight stays in the coverage denominator; `execution.unsupported_rate` is the unsupported share of the pack.

\[
EFR = \frac{\#\ execution\_failure\ Probe\ attempts}{\#\ scheduled\ Probe\ attempts}
\]

is reported separately and may make a submission ineligible regardless of score.

---

# 7. Causal Metrics

## 7.1 Conditions and paired units

For one Instance and repetition, let the normalized performance on an ablation's declared Probe subset be

```text
F   full
R   relevant-memory ablated
I   irrelevant-memory ablated
N   no-memory
H   harmful / stale memory present
```

Every metric is computed on **paired** runs: same Instance, same seed, same late-sampled Probe input, differing only in the memory intervention. The relevant-memory ablation is the primary causal reference; the no-memory condition is used only for Probes that have no relevant ablation in the same repetition, so that one causal unit is never counted twice.

## 7.2 Memory Benefit and Headroom-Normalized Memory Benefit

\[
MB = F - R \qquad (\text{signed, never clamped})
\]

\[
HMB = \frac{\max(0, F-R)}{1-R} \quad \text{for } R < 1 - \epsilon,\ \epsilon = 0.02
\]

A pair whose ablated condition is already within `ε` of the ceiling has no measurable headroom and is excluded from HMB; its raw MB remains reported.

## 7.3 Irrelevant Memory Stability

\[
IMS_\tau = 1 - \frac{\max(0, |F-I| - \tau)}{1-\tau}, \quad \text{clamped to } [0,1]
\]

with `τ` the ablation's `tolerance`. Both unexpected help and unexpected harm from supposedly irrelevant memory reduce stability.

## 7.4 Memory Harm and Harm Resistance

With the clean control `C = F`,

\[
MH = \max(0, C-H), \qquad HRS_\tau = 1 - \frac{\max(0, C-H-\tau)}{1-\tau} \quad \text{clamped}
\]

The interrogation lane (`MIB-ADV-*`) is the purest harmful condition: the injected events are questions only, so the oracle is identical with and without them and the whole of `C − H` is false installation.

## 7.5 Net Memory Gain

`NMG = MB − MH` in performance points. It is diagnostic; it is **not** the MIB Score.

## 7.6 Causal Memory Impact dimension

\[
CausalScore = HMB \cdot \frac{0.50 + 0.20\,IMS + 0.30\,HRS}{0.50 + 0.20\,[IMS\ present] + 0.30\,[HRS\ present]}
\]

Stability and harm-resistance credit is scaled by the demonstrated benefit. Without the gate a memory-blind Agent scores `IMS = HRS = 1` trivially — ablating what it never reads changes nothing — and would earn 50–100 on a dimension that asks whether memory made a difference. When no relevant / no-memory pair with measurable headroom exists, the causal dimension is **not evaluated** for that unit, which lowers coverage; IMS and HRS are still reported as raw diagnostics.

Worked check: a memory-blind Agent scores 0. An Agent with `HMB = 0.8`, `IMS = 0.5`, no harm condition, scores `0.8 · (0.5 + 0.1) / 0.7 = 0.686`.

Causal metrics aggregate within Template first, then across Templates weighted by each Template's causal evidence weight.

## 7.7 Pair validity

A causal pair is valid only if the variant run shares the full run's Instance id, Template id, instance seed, agent seed, and late-sampled Probe digests, and its Probes are a subset of the full run's. Each run records `validity.causal_pair_valid`; an invalid pair contributes nothing and is surfaced as a report warning `causal.pair_invalid`. It is never represented as a metric value.

## 7.8 Counterexample ablations

A `counterexample` ablation removes the episode that marks a learned procedure as inapplicable. It demonstrates applicability sensitivity but is **not** the standardized Negative Transfer control (Appendix A) and produces no causal metric by itself. A Scenario that wants the counterexample's removal to count as memory benefit for the non-matching task declares it as a `relevant_memory` ablation of that task's Probe.

---

# 8. Statistics

## 8.1 Statistical unit

Repetition, hidden Instance, Template, and Dimension are not interchangeable samples. The semantic design unit is the Template; hidden Instances estimate generalization within a design.

## 8.2 Hierarchical bootstrap

Per-repetition sufficient statistics (full-run dimension scores and paired causal metrics) are precomputed so that causal pairs can never be split. One draw:

```text
resample Instances within each Template, and Repetitions within each Instance
        ↓
resample the Template set once
        ↓
recompute every Dimension score, every causal metric, and the MIB Score from that one resample
```

The Template resample is shared by all Dimensions: Cross-Dimension Templates make Dimension scores positively correlated, and resampling Templates independently per Dimension would drop that covariance and understate the MIB Score interval.

Intervals are percentile intervals (2.5 / 97.5 for a 95% level). A Dimension carried by fewer Templates than `statistics.min_templates_per_dimension` (default 5) receives no interval, and the MIB Score interval is omitted whenever any weighted Dimension lacks one; the report records the threshold and the affected Dimensions and adds the warning `statistics.insufficient_templates`. A percentile interval over three Templates is decoration, not evidence.

The statistics block carries the point estimate as `mib_score.value`, never the bootstrap mean, so a report has one MIB Score.

## 8.3 Paired comparison between systems

Two systems evaluated on identical hidden Instances are compared with a paired bootstrap of per-Template deltas, not by independently bootstrapping each. A leaderboard **SHOULD** mark two systems statistically indistinguishable when the paired interval contains zero.

---

# 9. Reports and Verification

## 9.1 Report

`schemas/mib-report.schema.json` fixes the report: benchmark identity (Profile, track, scale, pack), system and adapter identity, environment versions, execution summary (runs, Probe attempts, execution failure rate, unsupported rate), `results.runs[]`, aggregates (Instances, Templates, Dimensions, MIB Score with `base_score` / `global_guardrail_penalty` / `final_score` / `official` / `partial`), `causal_metrics[]`, coverage, statistics, warnings, and provenance.

## 9.2 Score verification

`mib verify-score` recomputes every layer the report carries and reports its `verification_level`:

- **`full`** (internal reports, which carry `results.runs`): every run's scenario score from its Probe results; every Instance's full score, dimension scores, and causal metrics from the paired runs (ablation tolerances travel on the runs); then Template, Dimension, and MIB Score.
- **`aggregates_only`** (redacted public reports, which carry no runs): Template, Dimension, and MIB Score.

The evaluation service verifies the internal report at the full level before redaction; a public report that fails aggregate verification is rejected.

## 9.3 Capability Card

Every score is published as a multidimensional card, not a scalar: Profile, track, scale, agent; MIB Score and its interval when available; each Dimension with its coverage; Memory Benefit, Memory Harm, Net Memory Gain, Irrelevant Stability, Harm Resistance; coverage; execution failure rate; and whether the score is official, partial, or development.

## 9.4 Required score identity

A published score names its MIB version, Profile, track, scale, Scenario Pack version, and Agent / model / memory versions. `MIB 77.2` alone is not a result.

---

# 10. Calibration

Before a pack is frozen, each Template **SHOULD** be run under fixed-model baselines — B0 no memory, B1 full visible history, B2 simple retrieval, B3 structured memory — with the same model, prompt, reasoning policy, tools, decoding parameters, and paired seeds. The Memory Discriminativeness Index `MDI = FC − NM` (full-context minus no-memory performance) identifies Templates that memory cannot help (`FC` low) or does not need (`NM` near ceiling); both are revised or excluded. Procedures and gates are in `docs/harness/`.

The fixture calibration shipped with v0.1 exercises the plumbing only: its Agents are hand-written to pass or fail each Template and establish nothing about difficulty.

---

# 11. Leakage, Anti-Gaming, Governance

- Future Probes, Oracle data, ablation labels, hidden ground truth, relevance labels, and evaluator results are never delivered to the Agent, and evaluator results are never shown before a condition completes.
- Hidden evaluation materializes Instances with evaluator-secret seeds, replaces Scenario identifiers and seeds with keyed aliases in public artifacts, runs external submissions in a sandbox that masks the evaluator store, and signs job manifests and results (`MIB-Leaderboard-Evaluation-Service.md`).
- Dimension weights, Template weights, causal component weights, and the bootstrap threshold are benchmark policy: versioned and public. A Scenario is removed from a canonical pack only for a documented defect, with a versioned pack update and recomputation for every affected submission.
- Scores from different Profiles or major benchmark versions are never ranked together.

---

# 12. Invariants

1. Retrieval is not memory intelligence; storage is not functional memory.
2. Future Probes do not leak into formation.
3. The Agent never mutates world state; it observes consequences.
4. World updates apply in every condition; ablation changes only what the Agent is told.
5. Every causal condition is paired, isolated, and executed on a fresh Agent.
6. Capability scores use full-memory performance; causal contribution is reported separately and the causal dimension is derived only from paired interventions.
7. Raw causal deltas stay signed; normalized components clamp to `[0,1]`.
8. Selectivity credit (IMS, HRS) is scaled by demonstrated benefit.
9. Instances aggregate within Templates before Templates enter a Dimension.
10. Missing or unsupported coverage cannot inflate a score.
11. Cognitive failure, execution failure, and unsupported are distinct outcomes.
12. Every published score is recomputable from its report at the stated verification level.
13. Deterministic and world-state evaluation outrank language similarity.
14. Track A and Track B, and different Profiles, are never ranked together.
15. KIP conformance, memory size, and vendor identity earn nothing.

---

# Appendix A — Roadmap: specified, not implemented

The archived drafts specify the following. None of it is executed or scored by the reference implementation, none of it is accepted by the v0.1 Scenario schema, and none of it should be expected in a v0.1 report.

**Dimensions.** Selective Forgetting; Prospective & Self Memory (reserved ids `selective_forgetting`, `prospective_self_memory`).

**Scales.** MIB-M (~1,000 meaningful events) and MIB-L (10,000+); MIB-S is the only shipped scale.

**Tracks.** Track C memory-component diagnostics (record ablation, snapshot comparison, retrieval traces, influence tracing).

**Scenario constructs.** Evaluator types `exact`, `structured`, `semantic_constraints`, `llm_judge`; Probe triggers `at_sequence`, `at_time`, `world_condition`, `manual`; delivery `observe_only`; ablation methods `memory_mask`, `memory_delete`, `snapshot_branch`, `filtered_memory_clone`, `context_filter`, `black_box_reconstruction`; generated `distractor_batch` events; parameter sources `datetime_range`, `generator`, `derived`; execution policies `skip_probe`, `abort_scenario`; Scenario penalties and penalty caps; global guardrail penalties; content-integrity digests and signatures; maintenance hooks and the `maintain` adapter operation.

**Metrics.** Negative Transfer / Negative Transfer Resistance / Negative Transfer Rate; Error Recurrence Rate and Error Avoidance Score; Memory-Induced Error Rate; Learning Gain and Area Under Learning Curve; Influence Precision; Memory Gap Closure; Stale Adoption Rate; Historical Fidelity; Source Attribution Accuracy; Authority Confusion Rate; Self-Limitation Continuity; Positive Transfer Gain as a named metric; efficiency metrics (writes per event, storage, latency, tokens, cost); capacity and forgetting-curve diagnostics; scale retention.

**Evaluation policy.** LLM-judge policy (versioned rubric, deterministic decoding, judge identity in the artifact); confidence-aware tiering of leaderboards; BCa intervals.

**Scenario families.** Cross-agent memory, multimodal memory, privacy boundaries, domain profiles.

---

# Appendix B — Formula summary

```text
Scenario         S = Σ w_q P_q / Σ w_q                       (scored + execution_failure Probes)
Instance         full = mean_r S_r ; dimension d = weighted mean of Probes tagged d
Template         T_{t,d} = mean over Instances
Dimension        D_d = 100 · Σ_t v_{t,d} T_{t,d} / Σ_t v_{t,d}
MIB              MIB = Σ_d W_d D_d
Coverage_d       evaluated evidence weight / required evidence weight (unsupported Templates count as required)

MB               F − R                     (signed)
HMB              max(0, F − R) / (1 − R)   for R < 0.98
IMS_τ            1 − max(0, |F − I| − τ) / (1 − τ)
MH               max(0, C − H)
HRS_τ            1 − max(0, C − H − τ) / (1 − τ)
NMG              MB − MH
CausalScore      HMB · (0.5 + 0.2·IMS + 0.3·HRS) / (0.5 + present weights)   undefined without HMB
EFR              execution-failure Probe attempts / scheduled Probe attempts
```

---

# Appendix C — Document map

| Topic | Where |
|---|---|
| This specification | `docs/MIB-Specification.md` |
| Agent Adapter protocol (stdio JSONL, local HTTP, descriptors, errors) | `docs/MIB-Agent-Adapter.md` |
| Hosted evaluation, sandbox, signing, leaderboard | `docs/MIB-Leaderboard-Evaluation-Service.md`, `docs/harness/` |
| v0.1 milestone plan and Template inventory | `docs/MIB-v0.1-Test-Plan.md` |
| Transfer Intelligence diagnostics, Memory Adapter, MIB-R | `docs/experimental/`, `src/mib_runner/experimental/` |
| Superseded design drafts (rationale) | `docs/archive/` |
| Schemas | `schemas/` |
