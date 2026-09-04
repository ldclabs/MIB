# MIB Specification

## Memory Intelligence Benchmark — v0.2 normative specification

**Version:** 0.2 (implementation 0.9.0)
**Status:** Normative. This document describes what the reference implementation in `src/mib_runner/` executes and scores. Everything that was designed but is not executed lives in Appendix A (Roadmap), not in the body.

v0.2 replaces hand-written Scenarios with **generated Scenario Instances**: every Instance is derived from a Program over an internal, bitemporal, per-source world model, so that answers, relevant-memory ablation sets, counterfactual twins, and leak proofs are computed rather than authored. It makes the **distance between the past and the Probe** the primary independent variable (§8.1), turns the causal test from "remove the event" into "change the event and see whether the answer follows" (§7.2), lets the Agent **live** its past instead of reading about it (§5.3), scores **prospective memory from spontaneous emissions** (§4.6), and asks for **structured answers** with an epistemic status and a confidence (§4.7). The causal dimension of v0.1 is retired into a set of causal diagnostics and one eligibility gate, **memory dependence** (§7.10).

The design rationale is in `docs/proposals/MIB-v0.2-Evolution.md`; the superseded v0.1 drafts are archived under `docs/archive/`. Where a rationale document and this document differ, this document and the code win. The Agent Adapter wire protocol is specified separately in `MIB-Agent-Adapter.md`; the hosted evaluation service in `MIB-Leaderboard-Evaluation-Service.md`; the supplemental Transfer Intelligence and MIB-R layers in `docs/experimental/`.

Normative words **MUST**, **MUST NOT**, **SHOULD**, and **MAY** carry their usual meaning. Section numbers are stable and are cited from code comments.

---

# 0. Scope

MIB measures how effectively an Agent plus its long-term memory system uses the past to improve future cognition and behavior. It does not primarily measure how much of the past the system can retrieve.

The evaluated object is:

```text
Agent + Long-Term Memory System, observed across time
```

MIB is architecture-neutral: a participant needs only a black-box Agent that implements `reset`, `observe`, `respond`, and `act`, and **MAY** implement `maintain`. No memory representation, memory API, or KIP conformance is required, and none earns points.

---

# 1. Thesis and Principles

## 1.1 Thesis

> A memory system should not be judged by how much of the past it can retrieve, but by whether the right parts of the past change the future in the right way.

Three requirements follow:

1. **Memory must have causal consequences.** If changing a supposedly relevant memory does not change a relevant future decision, that item was stored history, not functioning memory.
2. **Memory must be context-sensitive.** A memory that helps in one context and harms unrelated contexts is weak memory intelligence.
3. **Memory must preserve distinctions.** Current vs historical truth, statement vs accepted belief, source vs provenance, event vs experience, knowledge vs skill, unknown vs false, a commitment vs its trigger.

## 1.2 What a Scenario tests

Every Scenario exists to test one proposition:

> The past should change the future when relevant, should not control the future when irrelevant, and should be resisted when stale or harmful.

## 1.3 Identification: what v0.2 can claim

Replay ablation intervenes on the Agent's *input*; memory is the Agent's *internal state*. As long as the past still sits inside the working context, "the past changed the future" does not have to pass through memory at all. v0.2 therefore does not report a memory score at one point; it reports two things that together identify memory:

- a **retention curve** (§8.1): the same Program is executed at increasing interference distance, so performance that survives distance is performance that survived the working context; and
- **content tracking** (§7.2): under a counterfactual twin of the same Instance the correct answer changes, so an Agent whose answers do not follow the changed content was answering from priors, and its capability score is not a memory score (§7.10).

Every shipped Program is still **MIB-S** scale (up to a few hundred events). The ladder is the identification condition, not a difficulty knob; larger scales (Appendix A) extend it, they do not replace it.

---

# 2. Benchmark Structure

## 2.1 Tracks

**Track A — Memory System.** Base model, agent prompt, reasoning policy, tools, environment, and Runner are fixed; only the memory system varies. Preferred for comparing memory architectures.

**Track B — Integrated Agent.** Model, agent policy, memory, orchestration, and tool strategy may all vary. Measures the complete Agent's memory-enabled capability and is intentionally not model-normalized.

Track A and Track B **MUST NOT** share one ranking.

## 2.2 Dimensions

MIB-Core-0.2 scores seven capability dimensions:

| id | Dimension | What it asks |
|---|---|---|
| `retention_retrieval` | Retention & Retrieval | Can relevant past information be recovered under indirect cues and generated interference, directly and across a hop? |
| `temporal_memory` | Temporal Memory | Can current, previous, and original values of a changing state be distinguished? |
| `epistemic_memory` | Epistemic Memory | Who said what; correction vs contradiction; authority; unknown vs false; contested vs confirmed? |
| `experience_memory` | Experience Memory | Does a failure the Agent itself lived through change what it does next time? |
| `skill_learning_transfer` | Skill Learning & Transfer | Does a learned precondition transfer where it applies and stay withheld where it does not? |
| `prospective_self_memory` | Prospective & Self Memory | Does a deferred commitment fire on its trigger, and not before? Does a standing rule about the Agent itself hold against a task that asks for the forbidden step? |
| `selective_forgetting` | Selective Forgetting | Does a withdrawn fact stop being used, while the facts around it stay available? |

`causal_memory_impact` remains a schema identifier for v0.1 Profiles; a v0.2 Profile gives it no weight. Causal quantities are reported as **diagnostics** (§7) and one of them gates eligibility (§7.10).

## 2.3 Profiles

A **Profile** is a versioned JSON policy object that fixes: `id`, `version`, `track`, `scale`, `official`, `scenario_pack`, `repetitions`, `instance_seeds`, per-dimension `weight`, `required_coverage`, and `statistics` (confidence level, bootstrap resamples, `min_templates_per_dimension`). A v0.2 Profile additionally fixes:

- `programs[]` — `{id}` (optionally `ladder`), the Programs of the pack (§4.2);
- `ladder` — interference counts per rung, default `[0, 20, 100]` (§8.1);
- `canonical_rung` — the rung whose Instances carry the capability score (§8.3);
- `memory_dependence` — `{metric, floor}`, the eligibility gate (§7.10);
- `statistics.interval_method` — `percentile` (default) or `bca` (§8.2).

A v0.1 Profile fixes `required_templates` instead of `programs`; the executed pack is then exactly those static Templates (§5.1). Every published score is identified by its Profile; weights from different Profiles **MUST NOT** be mixed. Profiles with `official: false` produce development scores that are never leaderboard scores.

## 2.4 Packs and visibility

A **generated pack** is `programs × instance_seeds × ladder rungs`. Programs, surface pools, and the generator are public; official evaluation uses evaluator-secret seeds, so participants can inspect every construction and still never see an official Instance (§11). Two development Profiles ship: `MIB-Core-0.2-Dev` (scale MIB-S, ladder `[0, 20, 100]`, capability at rung 1) and `MIB-Core-0.2-Dev-M` (scale MIB-M, ladder `[0, 100, 1000]`, capability at rung 2, BCa intervals). The static v0.1 packs (24 Public Dev, 30 Hidden Eval, 6 Private Holdout Templates) remain executable as a superset and are development material.

---

# 3. Roles

```text
Program + seed + rung ──generate──▶ Scenario Instance  (world model → oracle, support sets, twins)
                                        │
                              ┌─────────▼──────────┐
                              │       Runner       │  owns the timeline, the virtual
                              │  + World Simulator │  clock, hidden ground truth, tools
                              └───┬────────────┬───┘
                    observations  │            │  tool_result
                    probes/tasks  ▼            ▲  tool_call / emissions
                              ┌───────────────────┐
                              │  Agent (Adapter)  │  black box: reset / observe / respond / act [/ maintain]
                              └───────────────────┘
                                        │ outputs, emissions, action trace, world outcome
                              ┌─────────▼──────────┐
                              │     Evaluators     │  deterministic, structured, emission, world-state, trajectory
                              └─────────┬──────────┘
                              ┌─────────▼──────────┐
                              │   Scoring Engine   │  probe → instance → template → dimension → MIB; retention; dependence
                              └────────────────────┘
```

- The **Program** is a deterministic generator `(seed, rung) → Instance`. It builds a world model, realizes it as a timeline, and derives every Oracle and Ablation from the model (§4.2).
- The **Runner** loads an Instance, delivers visible Timeline events, executes lived tasks, strips hidden fields, delivers Probes, executes tool calls through the World Simulator, collects emissions, calls `maintain` at maintenance windows, runs Evaluators, performs ablation and counterfactual replay, and produces the Run Artifact.
- The **World Simulator** owns world state, hidden ground truth, tool state, and the virtual clock. The Agent never mutates world state directly; it observes consequences of tool calls.
- The **Agent Adapter** is the only channel to the participant system. In-process Agents implement the Python protocol in `types.py`; external Agents speak the stdio JSONL or local HTTP protocol of `MIB-Agent-Adapter.md`.
- The **Runner MUST NOT help the Agent**: no summarizing, no highlighting relevant memories, no labeling distractors, no revealing authority, no injecting Oracle state, no hint that an observation is a prospective trigger.

---

# 4. Scenario Model (executable subset)

The machine contract is `schemas/mib-scenario.schema.json` (JSON Schema 2020-12). Every enumeration in the schema is something the reference Runner executes; the reference Scenario Validator additionally rejects anything the Runner cannot execute (§4.10).

## 4.1 Top-level object

Required: `mib` (`"0.2"`; `"0.1"` bodies remain accepted), `kind` (`MemoryEpisodeProgram`), `id`, `version`, `title`, `suite`, `dimensions`, `world`, `timeline`, `probes`, `evaluators`, `scoring`. Optional: `status`, `description`, `tags`, `difficulty`, `template`, `instantiation`, `requirements`, `execution`, `leakage`, `actors`, `ablations`, `metadata`, `extensions`.

Generated Instances use `id = MIB-GEN-<PROGRAM>-V<n>` and `status: "generated"`; static Templates follow `MIB-<FAMILY>-<NNN>`. A change to a Program's timeline construction, oracle derivation, ablation semantics, or scoring **MUST** bump at least its minor version.

`dimensions` lists the dimensions the Scenario evidences; `scoring.dimension_weights` (§4.9) partitions its evidence among them.

## 4.2 Programs, the world model, and Instances

A **Program** (`src/mib_runner/generate/programs.py`) is registered under an id such as `mib.temporal.v1` and exposes a Template-shaped **descriptor** (`template.program = {id, version, ladder}`) plus `generate(seed, rung)`. Generation is a pure function of `(program id, program version, seed, rung, ladder)`; the same inputs **MUST** produce byte-identical Instances.

**World model.** A Program builds a bitemporal, per-source model (`worldmodel.py`): a sequence of assertions `(event, source, subject, attribute, value, kind)` with `kind ∈ state | update | correction | contradiction | question | hypothetical`. Rules:

- a `state` or `update` by an authoritative source is truth-bearing and supersedes the previous value of that subject/attribute;
- a `correction` is **retroactive**: it replaces the corrected assertion in the truth series, so "what was the value before" is answered from the corrected history;
- a `contradiction` by a non-authoritative source is recorded as *said* but is not truth-bearing; the attribute's status becomes `contested` until an authoritative source (a person with authority or a tool observation) resolves it;
- `question` and `hypothetical` assert nothing; they are the material of the interrogation-installation and stale-adoption traps;
- a `retraction` ("forget my access code") withdraws the assertion it supersedes from **every** layer — truth, evidence, and history — and asserts nothing itself; the withdrawn value becomes forbidden, and withholding the retraction restores the assertion, which is what its relevant-memory Ablation tests;
- tool observations are authoritative.

**Queries** are evaluated against the model: `current`, `as_of` (the value before a change), `first_stated`, `said_by` (what a given source said), `known` (is anything known), `status` (`known | contested | unknown | historical`), and `hop` (a chain of attributes with a decoy). A query result is `(kind, value, status)` with `kind ∈ value | unknown | contested`.

**Oracle derivation.** Every Probe declares its `query` (harness-only); `finalize()` turns the result into `oracle.accepted` (every canonical surface form of the value), `oracle.forbidden` (every other value ever seen for that subject/attribute, historical and retracted ones included), `oracle.expected_status`, and `oracle.failure_code_by_value` — why each forbidden value would be wrong: a superseded or retracted value is `stale_memory_adoption`, the original of a correction is `correction_loss`, a non-authoritative contradiction is `authority_confusion`, a value that was only asked about or hypothesized is `memory_hallucination`. Nothing in an Oracle is authored by hand.

**Instance identity.** A generated Instance records `instantiation`: `template_id`, `program`, `program_version`, `rung`, `interference_count`, `seed`, `parameter_digest` (SHA-256 of events and probes), `generator_version`. Its Instance key is `<template_id>:<seed>:r<rung>`. Hidden evaluation replaces the seed with an opaque alias before anything reaches the participant (§11).

**Shipped Programs (all version 0.2.0):**

| Program | Dimension | Tests | Capabilities |
|---|---|---|---|
| `mib.recall.v1` | retention_retrieval | a fact and a two-hop chain with a decoy, under generated interference | observe, respond, virtual_time |
| `mib.temporal.v1` | temporal_memory | one or two updates: current, previous, original value | observe, respond, virtual_time |
| `mib.epistemic.v1` | epistemic_memory | correction; contradiction by organizer vs colleague, resolved by a calendar tool in half of the seeds; said-by; status; unknown | observe, respond, virtual_time |
| `mib.experience.v1` | experience_memory | two **lived** deployment trials against a wrong target (failure, then recovery), each with a trial oracle, then a related deployment | + act, tools |
| `mib.skill.v1` | skill_learning_transfer | a lived "activate context before commit" lesson; the non-matching task first (the Negative Transfer control, §7.8), then the matching task | + act, tools |
| `mib.prospective.v1` | prospective_self_memory | a deferred commitment; a near-trigger that must not fire; the real trigger; a standing rule about the Agent ("you never restart services") tested by a task that asks for the restart | + act, tools |
| `mib.forgetting.v1` | selective_forgetting | two facts, then a retraction of one; the withdrawn fact must be unknown (current and historical), the neighbour must still be known | observe, respond, virtual_time |

Every Program consolidates once (`maintenance_window`, §4.5) between its past and its interference block.

Static v0.1 Templates carry `template.parameters` (`fixed`, `choice`, `integer_range`, `number_range`, seeded by `random.Random(str(seed))`, `${name}` substitution) and are materialized as before.

## 4.3 Requirements, execution policy, leakage policy

`requirements.capabilities` lists what the Agent must support: `observe`, `respond`, `act`, `tools`, `virtual_time`, `maintenance` (the schema also reserves `snapshot`, `memory_inspect`, `memory_delete`, `memory_restore`). A Template is **unsupported** for an Agent only when the Agent's descriptor declares a required capability `false` (§6.6). `maintenance` is never required by a shipped Program: an Agent without `maintain` simply receives the maintenance window as a system event.

`execution` sets `max_agent_turns` (default 20) and `max_tool_calls` (default 20) per act Probe and per lived task. The only execution policy is `fail_probe` (§5.4).

`leakage` **MUST** declare `future_probe_visible_during_formation`, `oracle_visible_to_agent`, `ablation_labels_visible_to_agent`, and `hidden_world_state_visible_to_agent` as `false`; the validator rejects anything else. `probe_sampling` is `fixed`, `late`, or `hidden_late` (§4.6).

## 4.4 Actors and World

`actors` give benchmark identities (`id`, `kind`, `display_name`); the Runner projects only those three fields into observations. Actor identity is not authentication, and authority is a world-model fact that is never delivered as a label.

`world` contains:

- `clock` — `{mode: "virtual", start: <ISO 8601 UTC>, timezone}`; the Runner owns clock progression (§4.5).
- `state` — mutable simulator state, addressed by JSON Pointer.
- `hidden_ground_truth` — oracle-only facts; never delivered to the Agent.
- `tools` — tool definitions exposed to act Probes and lived tasks. Each tool declares `id`, `version`, `operations[]` (`name`, `description`, `input_schema`) and a `simulator_binding`. The reference World Simulator implements `mib.deployment.v1` (inspect / select target, run migration, restart service), `mib.workspace.v1` (select workspace, edit, save), and `mib.contextual_save.v1` (activate context, edit, commit, with a `context_required` flag that turns activation into a policy violation when false). A tool call reaches the Agent as `<tool id>.<operation>`.

## 4.5 Timeline

Each event has `id`, `stage` (`seed` | `past` | `interference` | `consolidation` | `pre_probe`), `type`, `at`, `visibility`, and optionally `actor`, `content`, `payload`, `world_updates`, `task`, `oracle_labels`, `tags`.

Executable event types and their observation projection:

| Scenario type | Delivered as | Notes |
|---|---|---|
| `interaction`, `distractor` | `user_message` | |
| `observation` | `environment_event` | |
| `tool_result` | `tool_result` | with `tool_call_id`, `tool`, `payload` |
| `document`, `feedback`, `custom` | same name | |
| `task` | the act loop | a **lived task** (§5.3): `task.goal`, `task.available_tools`, `task.constraints`, `task.max_agent_turns`; optional `task.oracle` + `task.evaluators` make it a learning-curve trial (§7.9) |
| `time_advance` | `time_event` | moves the clock (below) |
| `maintenance_window` | `system_event` | and the `maintain` hook is invoked when the Agent implements it (`payload.budget` is passed through); every Program emits one before its interference block and pairs it with a `no_maintenance` Ablation (§4.8) |
| `checkpoint`, `world_update` | not delivered | harness-only |

`visibility` is `agent`, `harness`, or `both`; only `agent`/`both` events are delivered. `oracle_labels`, `tags`, relevance annotations, `query` fields, and hidden ground truth are never delivered.

`world_updates` (`set`, `unset`, `increment`, `append`, `remove` on a JSON Pointer path) are harness operations, not memory writes. They are applied in **every** condition, including conditions that ablate the event (§5.2).

**Generated interference.** A Program inserts `ladder[rung]` interference events between the past and the Probes (`generate/interference.py`), drawn by seed from three classes — `neutral` (0.60; unrelated conversation), `similar` (0.25; another actor states their own value of the same attribute, a true fact about someone else), `confusable` (0.15; the target actor asks a question or poses a hypothetical about the same attribute with another value, which asserts nothing). Similar and confusable events are registered in the world model, so the Oracle already accounts for them. Interference **MUST NOT** carry the answer to any Probe of the Instance; the parser-level check is part of the test suite, and the leak proof of §4.8 covers the relevant-memory ablation. The Instance records the distance in three units — `interference_count` (events), `interference_tokens` (whitespace tokens of the interference block), and `distance_hours` (virtual time from the last formation event to the Probe checkpoint) — so retention can be read against any of them (§8.1).

**Virtual time.** The Runner keeps a current virtual time, initialized from `clock.start`. An event's `at.time` sets it; a `time_advance` event may instead carry `payload.duration` as an ISO 8601 duration (`P3D`, `PT2H30M`) that advances it. Every observation and Probe carries the current virtual time. `at.sequence` orders events and **MUST** be monotonic when present.

## 4.6 Probes

A Probe is a future test. Required: `id`, `kind`, `trigger`, `delivery`, `input`, `oracle`, `evaluators`. Optional: `dimensions`, `weight` (default 1.0), `query` (harness-only; §4.2), `tags`, `extensions`.

- `trigger` is `{after_event: <event id>}`. Probes fire immediately after that event is processed, in Scenario order.
- `delivery` is `respond` (a cognitive answer; `input.content`), `act` (a task; `input.goal`, `input.available_tools`, `input.constraints`), or `observe_only` (below).
- `input.context` names the **asker** (`{actor, display_name}`); the Runner projects it so that a first-person prompt ("What is my timezone?") is answerable. It carries no authority information.
- `input.answer_schema` (`{value, status, confidence}` flags) asks for a structured answer (§4.7). An Agent **MAY** answer in free text; the parser is deterministic and the mapping is recorded.
- `kind` is descriptive (`factual`, `implicit`, `multi_hop`, `temporal`, `epistemic`, `experience`, `skill`, `prospective`, `self`, `action`, `historical`, `audit`, `abstention`, `custom`). It selects failure-code vocabulary (§5.4) and the eligibility of the full-run diagnostics (§7.9: `historical`, `audit`, `self`) but not scoring.
- `dimensions` tags the Probe for dimension attribution (§6.3).

**Observe-only Probes (prospective memory).** `input.observation` (`type`, `actor`, `content`, `payload`) is delivered as an ordinary observation with no question attached. Every `observe` result **MAY** carry `emissions[]`; the Runner logs them with the index of the observation that produced them. `oracle.expected_emission` is `{must_contain[], window, must_not_emit}`: the Probe passes when some emission within `[trigger index, trigger index + window]` (default window 1) contains every token of `must_contain`; with `must_not_emit: true` it passes when none does (`premature_trigger` otherwise). A near-trigger Probe uses `window: 0` so that a correct later emission is not counted against it. Observe-only Probes are scored by `emission` evaluators only (§4.7) and are resolved when the run's timeline is complete.

**Late sampling.** When `leakage.probe_sampling` is `late` or `hidden_late`, the Runner may choose among `extensions["mib.probe_sampling"].input_variants` only when the Probe fires. The choice is a deterministic function of (scenario id, instance seed, repetition, probe id) and is therefore identical across a full run and all its ablation runs; a digest of the delivered input is recorded for pair validation (§7.7). Oracle and evaluator fields are never sampled.

Future Probes **MUST NOT** be visible during memory formation. The Runner enforces this: nothing from `probes` is projected into an observation, and an observe-only Probe is indistinguishable from any other observation.

## 4.7 Oracle and Evaluators

`oracle` may carry `accepted[]`, `forbidden[]`, `failure_code_by_value` (§4.2), `expected_status` (`known` | `unknown` | `contested` | `historical` | `not_applicable`), `world_assertions[]`, `trajectory_requirements[]`, `expected_emission`, and free-text `expected`, `reference`, `notes`. Oracle data is harness-only.

Evaluators are referenced by id from `evaluators[]`. Each produces `score ∈ [0,1]`, `passed`, `failure_codes[]`, `details`.

**Shared value policy.** `config.normalization` ∈ `none` | `trim` | `casefold_trim` | `casefold_trim_collapse_ws` | `answer_normalized` (default; collapses whitespace, casefolds, strips edge punctuation so that "AX-91." equals "AX-91"). `config.match` ∈ `contains` (default; whole-token containment, so "AX-9" does not match inside "AX-91") | `exact`.

```text
accepted value present, no forbidden value       → 1
forbidden value present anywhere                 → 0   failure_code_by_value[value], default stale_memory_adoption
neither                                          → 0   retrieval_miss
expected_status = unknown:
  abstention, or an accepted value               → 1
  any other definite answer                      → 0   false_certainty
expected_status ≠ unknown and abstention         → 0   retrieval_miss
```

An answer that hedges between the current and the superseded value ("UTC+1, previously UTC+8") fails a Probe that lists the old value as forbidden. Such Probes ask for the value only; a Program that wants historical context asks for it in a separate Probe.

**`set_match`** — short free-text answers under the shared value policy. A structured output whose value is a scalar is compared as that scalar's text.

**`structured`** — the v0.2 default for respond Probes. A deterministic parser maps any output to `{value, status, confidence}`: an abstention → `status: unknown`; a structured output or a JSON object → its `value`/`answer`, `status`, `confidence`; otherwise `value:`/`answer:`, `status:`, `confidence:` lines; otherwise the whole text is the value. The reference implementation never grades with a model; if a model is ever used to map free text to this schema, the mapping is the logged parse, not a judgment. Scoring is field by field with `config.weights` (default `value 0.8, status 0.2`): `value` follows the shared policy; `status` scores 1 when it names the expected epistemic class (`known` → `known`; `historical` → `historical` or `known`; `contested` → `contested`; `unknown` → `unknown`; `not_applicable` → `not_applicable` or `unknown`) and adds `false_certainty` when the answer claims knowledge of something unknown; `confidence ∈ [0,1]` yields a calibration term `1 − (confidence − value_score)²` that is always reported and is scored only when the evaluator gives it weight. A status of `unknown` or a value of "unknown" counts as abstention.

**`emission`** — observe-only Probes (§4.6). The score is 1 or 0; failure codes are `commitment_miss` (no matching emission) and `premature_trigger` (an emission where none was allowed).

**`world_state`** — `oracle.world_assertions[]` of `{path, operator, value}` against the final simulator state, operators `eq`, `neq`, `exists`, `not_exists`, `contains`, `gte`, `lte`. Score is the fraction of satisfied assertions; any unsatisfied assertion adds `trajectory_collapse`. World truth outranks anything the Agent says.

**`trajectory`** — `oracle.trajectory_requirements[]` against the tool-call sequence of the act Probe: `required_action`, `forbidden_action`, `before` / `after` (first occurrences), `max_occurrences`, `min_occurrences`, and `no_recurrence` `{action, without_prior}` — the action **MUST NOT** occur unless `without_prior` occurred earlier in the same trajectory; this is the operational form of "do not repeat the failure you lived through", and a violation is coded `error_recurrence`. Score is the fraction satisfied. `forbidden_action` and `no_recurrence` are satisfied only by a **non-empty** trajectory; an Agent that does nothing earns no credit for avoiding a mistake. A forbidden action that was taken is coded `error_recurrence` for `experience` Probes, `self_model_drift` for `self` Probes, and `negative_transfer` otherwise.

**`composite`** — `components[]` of `{evaluator, weight}`; weighted mean of the component scores, weights normalized, failure codes unioned.

A Probe that references several evaluators receives their unweighted mean; Programs reference one evaluator per Probe.

## 4.8 Ablations

An Ablation turns a memory test into a causal test. Required: `id`, `kind`, `probes[]` (the scored subset), `method`, `expected_effect`. Optional: `targets.event_ids[]`, `injections[]`, `counterfactual`, `tolerance`, `oracle_value_survives_by_design`, `description`.

Kinds: `relevant_memory` (expected `degrade`), `irrelevant_memory` (`neutral`), `no_memory` (`degrade`), `harmful_memory` and `stale_memory` (`resist`), `counterexample` (`degrade`; §7.8), `negative_transfer` (`resist`; the standardized control of §7.8), `counterfactual_content` (`track`; §7.2), `no_maintenance` (`informational`; §7.2; may only withhold `maintenance_window` events; generated for every Program), `custom`.

Methods:

- `replay_excluding_events` — the full timeline is replayed with `targets.event_ids` withheld from the Agent. Their `world_updates` still apply.
- `replay_with_injections` — the full timeline is replayed plus `injections[]`, evaluator-controlled events delivered through the ordinary observation channel. An injection anchored with `at.after_event` is delivered after that event and before any Probe that event triggers; otherwise it is inserted by `at.sequence` / `at.time` order. Injections **MUST NOT** carry `world_updates`: memory is the treatment variable, world truth is not.
- `swap_parameter` — the full timeline is replayed with the **content** of the pivot event replaced (`counterfactual.events[pivot] = {content}` or `{payload}` for a tool result) and the scored Probes evaluated against `counterfactual.oracle[probe]`, in which the original value is explicitly forbidden. Everything else — every other event, every interference sentence, the clock — is identical, so the pair differs in exactly one memory content.

**Support sets and the leak proof.** For every Probe whose query has a value, the generator computes the **support set** of the query in the world model: the events whose single removal changes the answer are *necessary*; when the answer survives every single removal, the redundant group that carries it is the causal information set, verified by removing it whole. The relevant-memory Ablation withholds exactly that minimal set, and generation **fails** (`GenerationError`) unless the model proves that the answer is no longer derivable from the surviving events. Redundancy groups are recorded in the Ablation's `description`. A static Template gets the weaker check of v0.1 instead: a warning when an accepted value still appears verbatim in a surviving event, silenced by `oracle_value_survives_by_design: true`.

**Counterfactual twins.** The pivot of a `swap_parameter` Ablation is the last necessary event of the support set. The generator re-derives every Probe's oracle in the twin model and lists as `probes[]` exactly those whose result changed; a Probe whose answer does not depend on the pivot is not a counterfactual test of it.

`tolerance` (default 0) is the stochastic-wobble allowance used by the tolerant IMS and HRS forms (§7.3, §7.4) and is copied onto every run of that ablation as `ablation_tolerance`.

## 4.9 Scoring block

`scoring.probe_aggregation` is `weighted_mean`. `scoring.score_range` is `{min: 0, max: 100}`. `scoring.dimension_weights` maps each declared dimension to its evidence weight and **MUST** sum to 1; `scoring.causal_metrics[]` names the causal diagnostics the Scenario intends to produce (descriptive; computation follows the ablation kinds actually declared).

## 4.10 Validation

A Scenario enters a pack only if all of the following pass:

1. JSON Schema validation.
2. Reference resolution: unique ids for events, probes, evaluators, ablations, actors; every actor, trigger event, evaluator, composite component, ablation probe, ablation target, injection anchor, `available_tools` entry, and task tool resolves.
3. Timeline sequence monotonic when numeric.
4. Leakage policy flags all `false`; `dimension_weights` sum to 1; composite weights sum to 1 (warning otherwise, the Runner normalizes).
5. Injections carry no `world_updates` and no ids that collide with timeline events.
6. Runner executability: evaluator types, trigger kinds, delivery modes, ablation methods, simulator bindings, event types, `set_match`/`structured` configuration, world-assertion operators, and trajectory requirement types are all ones the reference Runner implements. A schema-valid Scenario that would crash the Runner or score every Agent zero is an error, not a warning.
7. v0.2 semantics: an `observe_only` Probe has `input.observation`, `oracle.expected_emission`, and only `emission` evaluators; a `swap_parameter` Ablation has a replacement for every target and a counterfactual oracle for every scored Probe; a `no_maintenance` Ablation withholds only `maintenance_window` events; a `task` uses available tools, and a trial oracle comes with evaluators and executable assertions.
8. Relevant-ablation leak check (§4.8) — a generation error for Programs, a warning for static Templates.

Generated Instances are validated by exactly the same rules before execution; the generator is not trusted.

## 4.11 Example

A rung-1 Instance of `mib.temporal.v1` (abridged; `mib generate --program mib.temporal.v1 --seed 7 --rung 1`):

```json
{
  "mib": "0.2", "kind": "MemoryEpisodeProgram", "id": "MIB-GEN-TEMPORAL-V1", "version": "0.2.0",
  "status": "generated", "dimensions": ["temporal_memory"],
  "instantiation": {"template_id": "MIB-GEN-TEMPORAL-V1", "program": "mib.temporal.v1", "program_version": "0.2.0",
                    "rung": 1, "interference_count": 20, "seed": 7, "parameter_digest": "…", "generator_version": "mib-generate/0.9.0"},
  "timeline": [
    {"id": "e-1", "stage": "past", "type": "interaction", "actor": "p1", "content": "My timezone is UTC+8.", "…": "…"},
    {"id": "e-2", "stage": "past", "type": "interaction", "actor": "p1", "content": "Update: my timezone is now UTC+1.", "…": "…"},
    {"id": "i-1", "stage": "interference", "type": "distractor", "…": "20 generated events"},
    {"id": "cp", "stage": "pre_probe", "type": "checkpoint", "visibility": "harness"}
  ],
  "probes": [
    {"id": "p-current", "kind": "temporal", "delivery": "respond", "trigger": {"after_event": "cp"},
     "query": {"op": "current", "subject": "p1", "attribute": "timezone"},
     "input": {"content": "What is my timezone? Answer with the UTC offset only.",
               "context": {"actor": "p1", "display_name": "Mara"}, "answer_schema": {"value": true, "status": true, "confidence": true}},
     "oracle": {"expected_status": "known", "accepted": ["UTC+1", "+01:00"], "forbidden": ["UTC+8", "+08:00"]},
     "evaluators": ["eval-structured"], "dimensions": ["temporal_memory"]}
  ],
  "ablations": [
    {"id": "a-relevant-p-current", "kind": "relevant_memory", "probes": ["p-current"],
     "method": "replay_excluding_events", "targets": {"event_ids": ["e-2"]}, "expected_effect": "degrade"},
    {"id": "a-swap-p-current", "kind": "counterfactual_content", "probes": ["p-current"], "method": "swap_parameter",
     "targets": {"event_ids": ["e-2"]},
     "counterfactual": {"events": {"e-2": {"content": "Update: my timezone is now UTC+2."}},
                        "oracle": {"p-current": {"expected_status": "known", "accepted": ["UTC+2", "+02:00"], "forbidden": ["UTC+8", "+08:00", "UTC+1", "+01:00"]}}},
     "expected_effect": "track"}
  ],
  "evaluators": [{"id": "eval-structured", "type": "structured", "config": {"normalization": "answer_normalized", "weights": {"value": 0.8, "status": 0.2}}}],
  "scoring": {"probe_aggregation": "weighted_mean", "score_range": {"min": 0, "max": 100}, "dimension_weights": {"temporal_memory": 1.0}}
}
```

---

# 5. Execution Semantics

## 5.1 Pack execution

`run_generated_pack` (v0.2 Profiles), `run_benchmark_pack` (static public Templates) and `run_materialized_pack` (evaluator-materialized hidden Instances):

1. A generated pack is exactly `profile.programs × profile.instance_seeds × ladder rungs`; a static pack is exactly `profile.required_templates`. A missing or an extra Program or Template is an error, never a silent change of the score.
2. Every descriptor and every Instance is validated (§4.10) before execution.
3. For each Instance and each repetition `r`, the Agent seed is `"<seed>:r<rung>:<r>"` for generated Instances and `"<instance seed>:<r>"` for static ones (an opaque alias for hidden Instances). The full condition plus every declared ablation are executed as separate conditions.
4. Templates the Agent does not support (§6.6) are not executed and are listed in the report.

## 5.2 Conditions and isolation

Each condition of a repetition — `full`, then each ablation in declaration order — runs against a **fresh Agent instance** (`agent_factory()`), with the same Instance, the same seed, the same virtual clock, and the same late-sampled Probe inputs. Only the memory intervention differs. No state may carry from one condition into another; a transport-backed Agent gets a fresh `reset` with a new opaque `run_id` and is closed on every exit path.

Ablation conditions execute the **complete** Probe program of the Instance, so that earlier Probe questions or actions cannot become a hidden second intervention; only the ablation's declared `probes[]` carry weight in the causal comparison (the rest are recorded with weight 0).

World updates apply identically in every condition (§4.5). Condition labels, ablation ids, counterfactual replacements, and expected effects are never visible to the Agent.

## 5.3 The act loop and lived tasks

For an act Probe the Runner sends the goal, constraints, and the tool definitions on the first turn, then alternates: the Agent returns either a `tool_call` (with a unique `tool_call_id`, a tool name among the offered ones, and arguments the tool's `input_schema` accepts) or a terminal `final` / `abstention`. Each tool call is executed by the World Simulator and its result is delivered back as a `tool_result` observation. The loop ends at a terminal step, at `max_agent_turns`, or at `max_tool_calls`. The action trace (sequence, tool, arguments, result) is recorded on the Probe result and drives the trajectory evaluator.

A **lived task** (`task` event, §4.5) runs the same loop during the past. Its goal is a real instruction, its tool results are real observations, and its failure — a deployment that breaks because no migration ran — is something the Agent did, not something it was told. The trace is recorded as the run's experience trace and is **never a capability score**: a task exists to create experience, and Agent misbehaviour during a task (§5.4) is recorded as a run warning. A task with a **trial oracle** (`task.oracle`, `task.evaluators`) is additionally evaluated like an act Probe and its outcome recorded in the run's `task_results[]`; a sequence of such trials is a learning curve (§7.9), a diagnostic that never enters the score. Whether the experience changed the Agent is measured by a later act Probe with `no_recurrence` (§4.7, §7.9).

## 5.4 Failure classification

Every executed Probe has exactly one `outcome`:

| Outcome | Meaning | Score | Run status |
|---|---|---|---|
| `scored` | The Probe was executed and evaluated. A **cognitive failure** is still `scored`: wrong answer, abstention where an answer was knowable, a forbidden or recurring action, a missed or premature emission, and Agent misbehaviour — exhausting `max_agent_turns` or `max_tool_calls` (`trajectory_collapse`), calling a tool that was not offered, arguments the schema rejects, a reused `tool_call_id`, an unknown step type (`agent_protocol_violation`). | evaluator score, or 0 with the failure code | `succeeded` |
| `execution_failure` | Runner, World Simulator, evaluator, or transport fault (an exception outside the Agent's contract, a timeout on the transport). | 0, weight kept | `failed` |
| `unsupported` | Reserved for Probes of unsupported Templates; such Templates are skipped whole (§6.6). | — | — |

Failure codes are drawn from the report schema's closed vocabulary: `formation_miss`, `retrieval_miss`, `identity_mismatch`, `stale_memory_adoption`, `source_confusion`, `correction_loss`, `false_certainty`, `trajectory_collapse`, `skill_non_transfer`, `negative_transfer`, `error_recurrence`, `counterexample_neglect`, `commitment_miss`, `premature_trigger`, `self_model_drift`, `memory_hallucination`, `irrelevant_memory_interference`, `authority_confusion`, `agent_protocol_violation`, `execution_failure`, `timeout`, `rate_limited`, `adapter_error`, `tool_error`, `evaluator_error`, `custom`.

The distinction matters because the **execution failure rate** (§6.6) gates leaderboard eligibility: a looping or protocol-breaking Agent must not raise it.

## 5.5 Run Artifact

One run (one condition of one repetition) records: `run_id` (opaque), `scenario_instance_id`, `template_id`, `template_version`, `instance_seed`, `condition`, `ablation_id`, `ablation_method`, `ablation_tolerance`, `repetition`, `agent_seed`, `status`, timestamps, `scenario_score`, `probe_results[]`, `warnings[]`, and `validity` (§7.7). A Probe result carries probe id and kind, outcome, score, weight, dimensions, evaluator results, failure codes, latency, output digest, and, when applicable, `counterfactual {tracks, stale}` (§7.2), `recurrence {eligible, recurred}` (§7.9), and `traps[]` — the failure codes the Oracle could elicit, which define eligibility for the §7.9 rates. A run with trial oracles carries `task_results[]` (`task_id`, `index`, `score`, `succeeded`, `failure_codes`). Runner-private extensions (final world state and its digest, the action trace, the experience trace, the emission log, late-sampling digests) are stripped from published reports.

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

For each dimension `d` the Instance declares, the dimension score is the weighted mean over full runs of the Probes tagged with `d`; Probes without tags count for every dimension; if no Probe carries the tag the run's scenario score is used. A generated Instance aggregate also records its `rung` and `interference_count` (§8.1). No capability dimension is ever derived from paired metrics; the v0.1 causal dimension, when a v0.1 Profile weights it, is computed as in §7.6.

## 6.4 Template and Dimension aggregation

Aggregation is Template-first so that instance count never becomes semantic weight:

\[
T_{t,d} = \frac{1}{N_t}\sum_{s \in t} S_{s,d}
\qquad
D_d = 100 \cdot \frac{\sum_t v_{t,d}\,T_{t,d}}{\sum_t v_{t,d}}
\]

where `v_{t,d}` is the Template's `scoring.dimension_weights[d]` (its evidence weight for `d`). For a generated pack the Template is the Program and the Instances that enter `T_{t,d}` are those of the **canonical rung** only (§8.3); every rung feeds the retention curve.

## 6.5 MIB Score, coverage, eligibility

\[
MIB_{base} = \sum_d W_d D_d, \qquad \sum_d W_d = 1
\]

with `W_d` from the Profile. No global guardrail penalty is defined, so `MIB = MIB_base`.

Coverage per dimension is the evaluated evidence weight over the required evidence weight, where the required weight counts every Template of the pack — including Templates that were not executed because the Agent does not support them. Profile coverage is `Σ_d W_d · coverage_d`. A report whose profile coverage is below `required_coverage` is **partial** and is never `official`.

`official` requires all of: the Profile's `official` flag, profile coverage, and — when the Profile declares `memory_dependence` — memory-dependence eligibility (§7.10). A report below the dependence floor carries the warning `memory_dependence.below_floor`; its MIB Score is still reported, as a capability score that was not shown to be earned through memory.

## 6.6 Unsupported and execution-failure rates

A Template is **unsupported** when the Agent's descriptor declares a required capability `false`. It is skipped, listed under `coverage.unsupported_required_templates`, and its weight stays in the coverage denominator; `execution.unsupported_rate` is the unsupported share of the pack.

\[
EFR = \frac{\#\ execution\_failure\ Probe\ attempts}{\#\ scheduled\ Probe\ attempts}
\]

is reported separately and may make a submission ineligible regardless of score.

---

# 7. Causal Diagnostics

## 7.1 Conditions and paired units

For one Instance and repetition, let the normalized performance on an ablation's declared Probe subset be

```text
F   full
R   relevant-memory ablated
I   irrelevant-memory ablated
N   no-memory
H   harmful / stale memory present
C   counterfactual content (the pivot event says something else)
M   no maintenance (maintenance windows withheld)
```

Every metric is computed on **paired** runs: same Instance, same seed, same late-sampled Probe input, differing only in the memory intervention. The relevant-memory ablation is the primary causal reference; the no-memory condition is used only for Probes that have no relevant ablation in the same repetition, so that one causal unit is never counted twice.

## 7.2 Memory Benefit, Headroom-Normalized Memory Benefit, Content Tracking

\[
MB = F - R \qquad (\text{signed, never clamped})
\]

\[
HMB = \frac{\max(0, F-R)}{1-R} \quad \text{for } R < 1 - \epsilon,\ \epsilon = 0.02
\]

A pair whose ablated condition is already within `ε` of the ceiling has no measurable headroom and is excluded from HMB; its raw MB remains reported.

Removal shows that *something* in the event mattered; the counterfactual shows that its **content** mattered. Over the Probes a `swap_parameter` Ablation changed, a pair is **eligible** only when the full-condition answer was correct (`score = 1`): a wrong answer under both conditions says nothing about tracking.

\[
CTR = \frac{\#\{\text{eligible pairs whose answer is correct under the counterfactual oracle}\}}{\#\text{eligible pairs}}
\qquad
SAR = \frac{\#\{\text{eligible pairs that answered the original value}\}}{\#\text{eligible pairs}}
\]

`content_tracking_rate` reports `eligible_n`, `total_n` (all changed Probes) and their ratio as `coverage`; `stale_adoption_rate` is its complement restricted to answers that stayed with the replaced content. A system answering from priors has a low CTR regardless of how high its full score is; this is the quantity that gates memory dependence (§7.10).

`consolidation_benefit = F − M` (percentage points, signed) reports what the Agent's own maintenance work was worth, for Agents that implement `maintain`.

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

The interrogation lane (`MIB-ADV-*`, and the `question` assertions of the world model) is the purest harmful condition: the injected events are questions only, so the oracle is identical with and without them and the whole of `C − H` is false installation.

## 7.5 Net Memory Gain

`NMG = MB − MH` in performance points. It is diagnostic; it is **not** the MIB Score.

## 7.6 Causal score (diagnostic)

\[
CausalScore = HMB \cdot \frac{0.50 + 0.20\,IMS + 0.30\,HRS}{0.50 + 0.20\,[IMS\ present] + 0.30\,[HRS\ present]}
\]

Stability and harm-resistance credit is scaled by the demonstrated benefit: without the gate a memory-blind Agent scores `IMS = HRS = 1` trivially. In v0.2 this quantity is a diagnostic; it enters a capability dimension only under a v0.1 Profile that weights `causal_memory_impact`, and then only from paired metrics, never from full performance. When no relevant / no-memory pair with measurable headroom exists it is undefined for that unit.

Causal diagnostics aggregate within Template first, then across Templates weighted by the Template's evidence weight (its causal evidence weight under a v0.1 Profile).

## 7.7 Pair validity

A causal pair is valid only if the variant run shares the full run's Instance id, Template id, instance seed, agent seed, and late-sampled Probe digests, and its Probes are a subset of the full run's. Each run records `validity.causal_pair_valid`; an invalid pair contributes nothing and is surfaced as a report warning `causal.pair_invalid`. It is never represented as a metric value.

## 7.8 Negative Transfer control and counterexample ablations

The **standardized Negative Transfer control** is a `negative_transfer` Ablation on a non-matching task: the skill-forming episodes are withheld (`V`, the task without the skill memory) and compared with the full condition (`F`, the task with it). Memory that hurts the task it does not apply to is negative transfer:

\[
NT = \max(0, V - F), \qquad NTR_\tau = 1 - \frac{\max(0, V - F - \tau)}{1 - \tau} \quad \text{clamped}
\]

`negative_transfer_rate` is the share of the control's Probes whose full-condition result carries the `negative_transfer` code (the learned action was applied where it was forbidden). The control is only valid when nothing earlier in the Probe program can re-teach the skill, so `mib.skill.v1` runs the non-matching task **before** the matching task.

A `counterexample` ablation removes the episode that marks a learned procedure as inapplicable. It demonstrates applicability sensitivity and produces no causal metric by itself; a Program that wants its removal to count as memory benefit declares it as a `relevant_memory` ablation of that task's Probe.

## 7.9 Full-run diagnostics

The following are computed from **full runs only** — the question is what the Agent did with its memory, not what removing the memory would do — and each is absent, never zero, when no unit is eligible. They are recomputable from a report's runs (§9.2).

- **Error recurrence.** An act Probe whose oracle carries a `no_recurrence` requirement is an eligible lived-failure opportunity; its result records `recurrence {eligible, recurred}`. `error_recurrence_rate = recurred / eligible`; `error_avoidance_score = 1 − error_recurrence_rate`.
- **Learning curve.** A run with at least two trial results (§5.3) is one learning curve: `learning_gain` = last trial score − first trial score; `area_under_learning_curve` = mean trial score. Both average over runs.
- **Memory-induced error rate.** The share of scored Probes whose failure codes attribute the error to memory (`stale_memory_adoption`, `correction_loss`, `authority_confusion`, `memory_hallucination`, `source_confusion`, `identity_mismatch`, `negative_transfer`, `error_recurrence`, `irrelevant_memory_interference`, `premature_trigger`, `self_model_drift`).
- **Authority confusion rate.** Over Probes whose `traps` include `authority_confusion` (their Oracle forbids a non-authoritative claim), the share that adopted it.
- **Historical fidelity**, **source attribution accuracy**, **self-limitation continuity.** Mean score over Probes of kind `historical`, `audit`, and `self` respectively.

## 7.10 Memory dependence

A capability score is a memory score only if the answers depended on memory content. The Profile's `memory_dependence = {metric, floor}` (default `content_tracking_rate ≥ 0.5`) is evaluated on the benchmark-level diagnostic:

```text
eligible = true    metric ≥ floor
eligible = false   metric < floor          → warning memory_dependence.below_floor, never official
eligible = null    no eligible pair exists → not assessable, never official
```

The report's `memory_dependence` block carries the gate (`metric`, `floor`, `eligible`, `eligible_n`, `total_n`) and the diagnostics beside it: `content_tracking_rate`, `stale_adoption_rate`, `memory_benefit`, `headroom_normalized_memory_benefit`, `harm_resistance`, `consolidation_benefit`, `error_recurrence_rate`. The floor is benchmark policy (§11).

---

# 8. Statistics and the distance ladder

## 8.1 Distance ladder and retention

A Program's `ladder` lists interference counts per rung (default `[0, 20, 100]`; the MIB-M development Profile uses `[0, 100, 1000]`). Rung `k` of a seed is the same Instance with `ladder[k]` generated interference events (§4.5) between the past and the Probes; the formation events, the Probe prompts, and their accepted answers are identical, and only the forbidden lists grow with the values the interference mentions. Performance as a function of distance is the **retention curve** of the Program, reported per Template in the `retention` block; each rung carries the distance in events, tokens, and virtual hours:

```text
rungs[]                 {rung, interference_count, interference_tokens, distance_hours, full_score, n}
retention_index         mean of the rung scores                     1.0 = no decay across the ladder
half_distance           interference count at which the score falls to half the rung-0 score,
                        linearly interpolated between rungs; null with half_distance_beyond_ladder = true
                        when the ladder never reaches it
canonical_rung          the rung that carries the capability score (§8.3)
```

The ladder is the identification condition of §1.3: a system whose curve is flat across distances that exceed its working context has demonstrated memory; a system whose curve collapses at rung 1 was reading.

## 8.2 Statistical unit and hierarchical bootstrap

Repetition, Instance, Template, and Dimension are not interchangeable samples. For a static pack the semantic design unit is the Template and hidden Instances estimate generalization within a design. For a generated pack the Program is the design and the **canonical-rung Instance** (one seed) is the unit: the Program set is a fixed policy of the Profile and is not resampled.

Per-repetition sufficient statistics (full-run dimension scores and paired causal metrics) are precomputed so that causal pairs can never be split. One draw:

```text
resample Instances within each Template, and Repetitions within each Instance
        ↓
static pack: resample the Template set once; generated pack: keep every Program
        ↓
recompute every Dimension score, every causal diagnostic, and the MIB Score from that one resample
```

The Template resample of a static pack is shared by all Dimensions: Cross-Dimension Templates make Dimension scores positively correlated, and resampling Templates independently per Dimension would drop that covariance and understate the MIB Score interval.

Intervals are percentile intervals (2.5 / 97.5 for a 95% level) by default. With `statistics.interval_method: bca` they are **bias-corrected and accelerated**: the bias term `z0` comes from the share of draws below the point estimate, the acceleration `a` from leave-one-unit-out jackknife estimates over the same statistic (Instances for a generated pack, Templates otherwise); a degenerate draw (all equal, or the point estimate outside the draws) falls back to the percentile interval and says so in `ci.method`. A Dimension carried by fewer units than `statistics.min_templates_per_dimension` (default 5; Templates for a static pack, canonical-rung Instances for a generated pack) receives no interval, and the MIB Score interval is omitted whenever any weighted Dimension lacks one; the report records the threshold and the affected Dimensions and adds the warning `statistics.insufficient_templates`. A percentile interval over three units is decoration, not evidence.

The statistics block carries the point estimate as `mib_score.value`, never the bootstrap mean, so a report has one MIB Score.

## 8.3 Canonical rung and the capability score

The Profile's `canonical_rung` names the rung whose Instances enter Template aggregation (§6.4), the bootstrap (§8.2), and the memory-dependence gate. It **SHOULD** be a rung whose interference exceeds a short working window (rung 1 in the shipped Profile) so that the capability score is read at a distance, not at rung 0. Score verification (§9.2) applies the same filter; the canonical rung travels on the retention block so that a redacted report remains verifiable.

## 8.4 Paired comparison between systems

Two systems evaluated on identical hidden Instances are compared with a paired bootstrap of per-unit deltas, not by independently bootstrapping each. A leaderboard **SHOULD** mark two systems statistically indistinguishable when the paired interval contains zero.

---

# 9. Reports and Verification

## 9.1 Report

`schemas/mib-report.schema.json` fixes the report: benchmark identity (Profile, track, scale, pack), system and adapter identity, environment versions, execution summary (runs, Probe attempts, execution failure rate, unsupported rate), `results.runs[]`, aggregates (Instances with rung and interference count, Templates, Dimensions, MIB Score with `base_score` / `global_guardrail_penalty` / `final_score` / `official` / `partial`), `causal_metrics[]`, `retention[]` (§8.1), `memory_dependence` (§7.10), `efficiency` (runner-measured probe latency and tool-call totals, plus any participant-reported usage summed over runs), coverage, statistics, warnings, and provenance. `benchmark.mib_version` is `"0.2"` for generated packs.

## 9.2 Score verification

`mib verify-score` recomputes every layer the report carries and reports its `verification_level`:

- **`full`** (internal reports, which carry `results.runs`): every run's scenario score from its Probe results; every Instance's full score, dimension scores, causal diagnostics, and error recurrence from the paired runs (ablation tolerances travel on the runs); then Template (canonical rung only), Dimension, and MIB Score.
- **`aggregates_only`** (redacted public reports, which carry no runs): Template, Dimension, and MIB Score.

The evaluation service verifies the internal report at the full level before redaction; a public report that fails aggregate verification is rejected.

## 9.3 Capability Card

Every score is published as a multidimensional card, not a scalar: Profile, track, scale, agent; MIB Score and its interval when available; each Dimension with its coverage; causal diagnostics (Memory Benefit, Memory Harm, Net Memory Gain, Irrelevant Stability, Harm Resistance, Content Tracking, Stale Adoption, Error Recurrence, Consolidation Benefit); behaviour diagnostics (Negative Transfer and its rate, Learning Gain and curve area, Historical Fidelity, Source Attribution, Authority Confusion, Self-Rule Continuity, Memory-Induced Errors); retention per Program (rung scores, retention index, half distance); the memory-dependence gate; coverage; execution failure rate; and whether the score is official, partial, or development.

## 9.4 Required score identity

A published score names its MIB version, Profile, track, scale, Scenario Pack version, canonical rung, and Agent / model / memory versions. `MIB 77.2` alone is not a result.

---

# 10. Calibration

Before a pack is frozen, each Program **SHOULD** be run under fixed-model baselines — B0 no memory, B1 full visible history, B2 simple retrieval, B3 structured memory — with the same model, prompt, reasoning policy, tools, decoding parameters, and paired seeds, at every rung. The Memory Discriminativeness Index `MDI = FC − NM` (full-context minus no-memory performance) identifies Programs that memory cannot help (`FC` low) or does not need (`NM` near ceiling); both are revised or excluded. Procedures and gates are in `docs/harness/`.

The fixture calibration shipped with v0.2 exercises the plumbing and the ordering the design predicts, nothing more. Six fixtures (`mib_runner.agents`) are hand-written over the generated language:

```text
StructuredMemoryAgent   a perfect world model over what it observed   flat retention, CTR = 1
WindowMemoryAgent       the same, limited to the last 12 observations  decays along the ladder
ConsolidatingAgent      the window fixture whose maintain() archives   consolidation_benefit > 0
RecencyAgent            every mention is a fact and the last one wins  stale adoption, authority confusion, cannot forget
OvergeneralizingAgent   applies a learned skill everywhere             negative transfer on the non-matching task
NoMemoryAgent           abstains on every question, acts naively       low score, dependence not assessable
```

They establish nothing about difficulty for a real model.

---

# 11. Leakage, Anti-Gaming, Governance

- Future Probes, Oracle data, queries, ablation labels, counterfactual replacements, hidden ground truth, relevance labels, and evaluator results are never delivered to the Agent, and evaluator results are never shown before a condition completes.
- Programs, pools, and the generator are public. Hidden evaluation generates Instances from evaluator-secret seeds, replaces Instance identifiers and seeds with keyed aliases in public artifacts, runs external submissions in a sandbox that masks the evaluator store, and signs job manifests and results (`MIB-Leaderboard-Evaluation-Service.md`). Because every construction is public, an Agent that keys on the generated language is measured exactly as intended: it must still have retained the content at a distance and must still follow the counterfactual.
- Dimension weights, Program weights, the ladder, the canonical rung, the dependence floor, causal component weights, and the bootstrap threshold are benchmark policy: versioned and public. A Program is changed in a canonical pack only for a documented defect, with a versioned pack update and recomputation for every affected submission.
- Scores from different Profiles or major benchmark versions are never ranked together.

---

# 12. Invariants

1. Retrieval is not memory intelligence; storage is not functional memory.
2. Future Probes do not leak into formation; an observe-only Probe is indistinguishable from an ordinary observation.
3. The Agent never mutates world state; it observes consequences.
4. World updates apply in every condition; ablation and counterfactual replay change only what the Agent is told.
5. Every causal condition is paired, isolated, and executed on a fresh Agent.
6. Capability scores use full-memory performance at the canonical rung; causal quantities are diagnostics, and memory dependence gates eligibility rather than entering the score.
7. Raw causal deltas stay signed; normalized components clamp to `[0,1]`.
8. Selectivity credit (IMS, HRS) is scaled by demonstrated benefit.
9. Instances aggregate within Templates before Templates enter a Dimension; rungs aggregate into a curve, never into a point.
10. Missing or unsupported coverage cannot inflate a score.
11. Cognitive failure, execution failure, and unsupported are distinct outcomes.
12. Every published score is recomputable from its report at the stated verification level.
13. Deterministic, structured, emission, and world-state evaluation outrank language similarity; no model grades.
14. Every Oracle, support set, counterfactual twin, and leak proof of a generated Instance is derived from the world model, never authored.
15. A lived task is experience, never a score; its trials are a learning curve, never a score.
16. A retraction removes a fact from every layer of the record; forgetting is tested by the value staying unused, not by the Agent claiming to have forgotten.
17. Track A and Track B, and different Profiles, are never ranked together.
18. KIP conformance, memory size, and vendor identity earn nothing.

---

# Appendix A — Roadmap: specified, not implemented

None of the following is executed or scored by the reference implementation, accepted by the Scenario schema, or to be expected in a v0.2 report.

**Scales.** MIB-L (10,000+ events) and any ladder whose rungs exceed a modern working context. The MIB-M development Profile reaches 1,000 interference events (about 8,000 tokens); it is a distance, not a context overflow. Distance is counted in generated interference events, tokens, and virtual time — not yet in "meaningful" events the Agent must track.

**Programs.** Cross-agent memory, multimodal memory, privacy boundaries (a fact told in confidence must not be disclosed to another asker), domain profiles; consolidation-window Programs in which `maintain` is load-bearing for a real system (the shipped windows are load-bearing only for the consolidating fixture).

**Tracks.** Track C memory-component diagnostics (record ablation, snapshot comparison, retrieval traces, influence tracing) and the Memory Adapter operations they need.

**Scenario constructs.** Evaluator types `semantic_constraints`, `llm_judge`; Probe triggers `at_sequence`, `at_time`, `world_condition`, `manual`; ablation methods `memory_mask`, `memory_delete`, `snapshot_branch`, `filtered_memory_clone`, `context_filter`, `black_box_reconstruction`; parameter sources `datetime_range`, `generator`, `derived`; execution policies `skip_probe`, `abort_scenario`; Scenario penalties and penalty caps; global guardrail penalties; content-integrity signatures on Instances (digests exist).

**Metrics.** Influence Precision; Memory Gap Closure (needs the full-context baseline of the calibration harness); memory-system efficiency (writes per event, storage, write amplification — the shipped `efficiency` block carries runner-measured latency and tool calls plus participant-reported usage only); budgeted-memory Profiles that make cost a first-class axis.

**Evaluation policy.** A model-assisted parser for free-text answers (versioned, deterministic decoding, parse logged as the record); confidence-aware tiering of leaderboards; real fixed-model calibration at every rung.

---

# Appendix B — Formula summary

```text
Scenario         S = Σ w_q P_q / Σ w_q                       (scored + execution_failure Probes)
Instance         full = mean_r S_r ; dimension d = weighted mean of Probes tagged d
Template         T_{t,d} = mean over canonical-rung Instances
Dimension        D_d = 100 · Σ_t v_{t,d} T_{t,d} / Σ_t v_{t,d}
MIB              MIB = Σ_d W_d D_d
Coverage_d       evaluated evidence weight / required evidence weight (unsupported Templates count as required)

MB               F − R                     (signed)
HMB              max(0, F − R) / (1 − R)   for R < 0.98
CTR              correct under counterfactual / eligible pairs (full answer correct)
SAR              answered the original value / eligible pairs
IMS_τ            1 − max(0, |F − I| − τ) / (1 − τ)
MH               max(0, C − H)
HRS_τ            1 − max(0, C − H − τ) / (1 − τ)
NMG              MB − MH
ConsolidationB   F − M
NT               max(0, V − F)             V = non-matching task without the skill memory
NTR_τ            1 − max(0, V − F − τ) / (1 − τ)
ERR              recurred / eligible lived-failure opportunities   (full runs);  EAS = 1 − ERR
LG / AULC        last − first trial score / mean trial score       (runs with ≥ 2 trials)
MIER             Probes with a memory-induced failure code / scored Probes
ACR              adopted a non-authoritative claim / Probes trapped for it
HF / SAA / SLC   mean score of historical / audit / self Probes
CausalScore      HMB · (0.5 + 0.2·IMS + 0.3·HRS) / (0.5 + present weights)   diagnostic; undefined without HMB
Retention        rung scores; retention_index = mean; half_distance by linear interpolation
Dependence       eligible ⇔ metric ≥ floor   (default content_tracking_rate ≥ 0.5)
Interval         percentile (default) or BCa: z0 from draws below the point, a from leave-one-unit-out jackknife
EFR              execution-failure Probe attempts / scheduled Probe attempts
```

---

# Appendix C — Document map

| Topic | Where |
|---|---|
| This specification | `docs/MIB-Specification.md` |
| v0.2 design rationale | `docs/proposals/MIB-v0.2-Evolution.md` |
| Programs, world model, generator | `src/mib_runner/generate/`, `src/mib_runner/worldmodel.py` |
| Agent Adapter protocol (stdio JSONL, local HTTP, descriptors, errors) | `docs/MIB-Agent-Adapter.md` |
| Hosted evaluation, sandbox, signing, leaderboard | `docs/MIB-Leaderboard-Evaluation-Service.md`, `docs/harness/` |
| v0.1 milestone plan and static Template inventory | `docs/MIB-v0.1-Test-Plan.md` |
| Transfer Intelligence diagnostics, Memory Adapter, MIB-R | `docs/experimental/`, `src/mib_runner/experimental/` |
| Superseded design drafts (rationale) | `docs/archive/` |
| Schemas | `schemas/` |
