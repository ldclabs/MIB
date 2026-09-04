# MIB Scenario Model

> **Superseded design draft.** Retained for rationale and history only. The normative text is [`docs/MIB-Specification.md`](../MIB-Specification.md); where the two differ, the Specification and the reference implementation win.

## Memory Episode Program for the Memory Intelligence Benchmark

**Version:** 0.1-draft  
**Status:** Scenario Model Proposal / Companion to `MIB-Architecture.md`

---

# 0. Purpose

This document defines the semantic model for an executable MIB scenario.

MIB is not primarily a static question-answer benchmark. Its fundamental unit is a:

> **Memory Episode Program**

A Memory Episode Program describes a world that unfolds over time, the observations an Agent receives, the information that should remain hidden, the future probes or tasks that test memory, and the counterfactual variants used to determine whether memory actually changed future behavior.

Conceptually:

```text
Scenario
  ├── World
  ├── Actors
  ├── Virtual Time
  ├── Timeline
  │    ├── Past Episodes
  │    ├── Interference
  │    └── Consolidation Windows
  ├── Future Probes
  ├── Ground Truth / Oracle
  ├── Evaluators
  ├── Ablations
  └── Scoring
```

The Scenario Model is architecture-neutral.

It MUST NOT assume that the evaluated system uses:

```text
vector retrieval
summaries
knowledge graphs
episodic memory
KIP
a database
a memory API
```

A black-box Agent that only exposes `observe`, `respond`, and `act` must still be evaluable.

---

# 1. Design Principle

A MIB scenario exists to test one proposition:

> **The past should change the future when relevant, should not control the future when irrelevant, and should be resisted when stale or harmful.**

Therefore a scenario is not complete if it contains only:

```text
past text
+
future question
```

A serious scenario should define, where applicable:

```text
what actually happened
what the Agent observed
what changed over time
what was hidden
what the future task requires
what counts as success
which past episode is causally relevant
which past episodes are distractors
how to replay the future under memory ablation
```

---

# 2. Scenario vs Dataset Item

Traditional item:

```text
context
question
answer
```

MIB Scenario:

```text
initial world
    ↓
past interaction
    ↓
world transition
    ↓
more interaction
    ↓
interference
    ↓
optional maintenance/consolidation
    ↓
future probe
    ↓
agent answer/action
    ↓
world outcome
    ↓
counterfactual replay
```

The distinction matters because memory intelligence is a **cross-time process**.

---

# 3. Normative Language

The terms **MUST**, **MUST NOT**, **SHOULD**, **SHOULD NOT**, and **MAY** are used as scenario-model requirements.

This document is pre-specification design. Future MIB specifications may refine these rules.

---

# 4. Serialization

The baseline machine-readable format is JSON.

YAML MAY be used as an authoring format if it round-trips without changing scenario semantics.

The corresponding machine schema is:

```text
mib-scenario.schema.json
```

Baseline schema:

```text
JSON Schema Draft 2020-12
```

A canonical executable Scenario Instance SHOULD be materializable as plain JSON without external code execution.

---

# 5. Top-Level Scenario Object

A Scenario contains:

```text
mib
kind
id
version
status
title
description

suite
dimensions
tags
difficulty

template
instantiation

requirements
execution
leakage

actors
world
timeline
probes
ablations
evaluators
scoring

metadata
extensions
```

Not every optional field is required for every scenario.

The minimum useful executable instance contains:

```text
id
version
dimensions
world
timeline
probes
evaluators
scoring
```

---

# 6. `mib`

Identifies the benchmark format family.

For this draft:

```json
{
  "mib": "0.1"
}
```

This is the Scenario format version family, not the Scenario content version.

---

# 7. `kind`

Baseline value:

```text
MemoryEpisodeProgram
```

This distinguishes MIB scenarios from future artifacts such as:

```text
RunArtifact
CapabilityCard
ScenarioPack
LeaderboardSubmission
```

---

# 8. Scenario Identity

Example:

```text
MIB-TIME-001
```

Recommended namespaces:

```text
MIB-RET-*      Retention & Retrieval
MIB-TIME-*     Temporal Memory
MIB-EPI-*      Epistemic Memory
MIB-EXP-*      Experience Memory
MIB-SKILL-*    Skill Learning
MIB-FORGET-*   Selective Forgetting
MIB-PROS-*     Prospective Memory
MIB-SELF-*     Self Memory
MIB-CAUSAL-*   Causal Memory Impact
MIB-ADV-*      Adversarial Memory
MIB-X-*        Cross-Dimension
```

Scenario ID is stable across equivalent revisions.

A semantic change to timeline, ground truth, or scoring SHOULD increment `version`.

---

# 9. Scenario Version

Use semantic-version-like content versions:

```text
0.1.0
0.1.1
1.0.0
```

Changing spelling or documentation may be patch-level.

Changing expected behavior, ablation semantics, or scoring SHOULD be at least minor-level.

Breaking scenario semantics SHOULD increment major version once MIB reaches stable releases.

---

# 10. Suite and Dimensions

A scenario belongs to one primary `suite` and may test multiple `dimensions`.

Example:

```json
{
  "suite": "time",
  "dimensions": [
    "temporal_memory",
    "retention_retrieval",
    "causal_memory_impact"
  ]
}
```

Allowed core dimensions:

```text
retention_retrieval
temporal_memory
epistemic_memory
experience_memory
skill_learning_transfer
selective_forgetting
prospective_self_memory
causal_memory_impact
```

Additional experimental dimensions MAY be namespaced in `extensions`.

---

# 11. Tags

Tags provide discovery, filtering, and research grouping.

Examples:

```text
correction
staleness
multi-hop
failure-recovery
negative-transfer
unknown-vs-false
source-conflict
interrogation
prospective-trigger
identity
distractor-heavy
```

Tags MUST NOT carry normative scoring semantics by themselves.

---

# 12. Difficulty

Difficulty SHOULD be described through measurable properties rather than only `easy`, `medium`, or `hard`.

Suggested fields:

```text
level
temporal_horizon
meaningful_events
distractor_events
entity_count
memory_hops
source_ambiguity
conflict_complexity
experience_steps
skill_abstraction_distance
probe_indirectness
```

Example:

```json
{
  "level": "medium",
  "meaningful_events": 7,
  "distractor_events": 200,
  "entity_count": 3,
  "memory_hops": 1,
  "probe_indirectness": 0.3
}
```

The scalar values are descriptive metadata unless the benchmark version defines a calibration.

---

# 13. Template vs Instance

MIB distinguishes:

```text
Scenario Template
Scenario Instance
```

A Template can contain parameter generators.

An Instance is fully materialized and executable.

Example template parameter:

```json
{
  "name": "current_timezone",
  "type": "string",
  "source": "choice",
  "choices": ["+01:00", "+02:00", "+09:00"]
}
```

A hidden evaluator may instantiate:

```text
person name
dates
values
distractor count
tool behavior
probe wording
```

after the participant has already implemented its memory system.

This reduces benchmark overfitting.

---

# 14. Parameter Visibility

Parameters MAY be classified:

```text
public
hidden
derived
```

`public` means the template structure may expose the parameter.

`hidden` means the evaluation service keeps its sampled value secret except where naturally revealed through Agent observations.

`derived` is computed from other scenario state.

Hidden parameter values MUST NOT be sent to the Agent except through explicitly visible scenario events.

---

# 15. Instantiation Metadata

A materialized hidden Scenario Instance SHOULD record:

```text
template_id
template_version
seed
parameter_digest
generator_version
```

It SHOULD NOT expose hidden parameter values in public leaderboard artifacts unless the evaluation policy permits it.

---

# 16. Requirements

A Scenario can declare execution requirements.

Examples:

```text
respond capability
act capability
tool-use capability
virtual-time support
replay ablation
memory adapter optional
```

Requirements determine whether the Runner can execute the scenario against a submission.

They do not describe memory quality.

---

# 17. Execution Policy

`execution` controls benchmark behavior.

Suggested fields:

```text
repetitions
random_seed
reset_between_repetitions
max_wall_time_ms
max_agent_turns
max_tool_calls
on_agent_error
on_timeout
```

Example:

```json
{
  "repetitions": 3,
  "reset_between_repetitions": true,
  "max_agent_turns": 20,
  "on_timeout": "fail_probe"
}
```

Execution limits are benchmark harness policy and MUST NOT be silently changed during leaderboard comparison.

---

# 18. Leakage Policy

Future-question leakage is one of the largest threats to valid memory evaluation.

A Scenario SHOULD declare:

```text
probe_sampling
future_probe_visible_during_formation
oracle_visible_to_agent
ablation_labels_visible_to_agent
hidden_world_state_visible_to_agent
```

Recommended defaults:

```text
future_probe_visible_during_formation = false
oracle_visible_to_agent = false
ablation_labels_visible_to_agent = false
hidden_world_state_visible_to_agent = false
```

The Runner MUST enforce the policy, not merely trust prompts.

---

# 19. Late-Sampled Probe

Strong evaluation SHOULD support:

```text
Past Episode
    ↓
Formation Complete
    ↓
Future Probe Sampled
```

rather than:

```text
Future Probe Known
    ↓
Past Memory Formation
```

Scenario Templates MAY therefore define a `probe_sampling` policy such as:

```text
fixed
late
hidden_late
```

`hidden_late` is preferred for leaderboard-critical tests where practical.

---

# 20. Actors

Actors represent entities that may communicate with or appear to the Agent.

Example:

```json
{
  "id": "alice",
  "kind": "person",
  "display_name": "Alice",
  "attributes": {
    "organization": "Orbit"
  }
}
```

Actor identity inside a Scenario is benchmark identity.

It is not authentication identity.

Actors MAY include:

```text
person
agent
organization
service
tool
environment
system
```

---

# 21. World

The World object represents benchmark-controlled reality.

It includes:

```text
clock
state
entities
tools
hidden_ground_truth
```

The Agent interacts with the World only through visible observations and tool interfaces.

The World object itself is harness state.

---

# 22. World State

`world.state` stores mutable simulator state.

Example:

```json
{
  "user_timezone": "+08:00",
  "auth_mode": "jwt",
  "deployment_target": "legacy-db"
}
```

World state may contain information the Agent does not know.

Therefore:

```text
world state ≠ Agent observation
```

The Runner controls what becomes visible.

---

# 23. Hidden Ground Truth

`hidden_ground_truth` contains oracle-only facts required for deterministic evaluation.

Examples:

```text
actual current timezone
true database target
correct workflow precondition
which source is authoritative
whether a commitment trigger has occurred
```

This state MUST NOT be automatically injected into Agent context.

---

# 24. Entities

World entities give stable identities to objects manipulated by the simulator.

Example:

```json
{
  "id": "service-api",
  "kind": "service",
  "attributes": {
    "environment": "production"
  }
}
```

Entity attributes may change through timeline state transitions.

---

# 25. Tools

A Scenario MAY define benchmark tools.

Examples:

```text
calendar
deployment API
email
filesystem
browser simulator
database inspector
task manager
```

Tool definitions declare the interface exposed to the Agent.

Implementation-specific tool code is outside the Scenario JSON, but the Scenario SHOULD identify:

```text
tool id
version
operations
visibility
simulator binding
```

---

# 26. Virtual Clock

Long-term memory MUST be testable without real waiting.

Recommended clock:

```json
{
  "mode": "virtual",
  "start": "2026-01-01T09:00:00Z",
  "timezone": "UTC"
}
```

Timeline steps may use:

```text
sequence index
absolute virtual datetime
relative time advance
```

The Runner owns clock progression. An absolute `at.time` sets the clock; a `time_advance` event may instead carry `payload.duration` as an ISO 8601 duration (`P3D`, `PT2H30M`) that moves the clock forward from the current virtual time.

---

# 27. Timeline

The Timeline is the historical sequence through which the Agent lives.

Each Timeline Event SHOULD have:

```text
id
stage
type
at
visibility
actor
content / payload
world_updates
oracle_labels
tags
```

Example:

```json
{
  "id": "e1",
  "stage": "past",
  "type": "interaction",
  "at": {
    "sequence": 1
  },
  "visibility": "agent",
  "actor": "alice",
  "content": "My timezone is UTC+8."
}
```

---

# 28. Timeline Stages

Core stages:

```text
seed
past
interference
consolidation
pre_probe
```

Future probes are represented separately in `probes`.

`seed` initializes the lived environment.

`past` contains meaningful memory-forming episodes.

`interference` injects unrelated or weakly related information.

`consolidation` provides an explicit maintenance opportunity if the Agent architecture supports one.

`pre_probe` creates the immediate situation before a future test.

---

# 29. Timeline Event Types

Baseline event types:

```text
interaction
observation
tool_result
world_update
time_advance
distractor
distractor_batch
maintenance_window
checkpoint
feedback
document
custom
```

A future MIB version MAY extend this registry.

---

# 30. Event Visibility

Baseline values:

```text
agent
harness
both
```

`agent` means the event is delivered through the Agent Adapter.

`harness` means the event affects benchmark state but is hidden from the Agent.

`both` means it is both delivered and retained as harness-visible event state.

Hidden oracle annotations MUST NOT be transmitted simply because the event itself is visible.

---

# 31. World Updates

A timeline event MAY mutate World state.

Baseline operations:

```text
set
unset
increment
append
remove
```

Example:

```json
{
  "op": "set",
  "path": "/user_timezone",
  "value": "+01:00"
}
```

Paths are relative to `world.state`.

World updates are harness operations.

They are not memory writes.

---

# 32. Agent Observation

A visible Timeline Event is converted by the Runner into an Agent Observation.

The Scenario describes semantics; the Agent Adapter determines transport.

The Runner MUST NOT include hidden fields such as:

```text
oracle_labels
expected_answer
relevance classification
ablation role
hidden ground truth
```

unless the Scenario explicitly says they are observable.

---

# 33. Distractors

Distractors model memory interference.

A distractor SHOULD be plausible enough to consume memory capacity or retrieval attention.

Types include:

```text
unrelated conversation
similar entity names
near-match values
routine tool events
repeated low-value status messages
topic overlap without causal relevance
```

Distractor metadata MAY mark benchmark relevance for the harness.

That relevance label MUST remain hidden from the Agent.

---

# 34. Distractor Batch

Large-scale scenarios SHOULD support a compact generator declaration rather than embedding thousands of static records.

Example:

```json
{
  "id": "d200",
  "stage": "interference",
  "type": "distractor_batch",
  "at": {"sequence": 50},
  "visibility": "agent",
  "generator": {
    "id": "routine-chat-v1",
    "count": 200,
    "seed": 42
  }
}
```

The generator MUST be versioned and deterministic under the declared seed for reproducibility.

A fully materialized Run Artifact SHOULD record the generated event digest.

---

# 35. Maintenance / Consolidation Window

Some memory systems perform maintenance between interactions.

MIB SHOULD not force all systems into one schedule.

A Scenario MAY expose an explicit:

```text
maintenance_window
```

The Runner may:

```text
do nothing
call an optional maintenance hook
allow the Agent architecture to self-maintain
```

Track A MUST use the same maintenance policy for all compared systems unless memory-system-specific maintenance is itself the object of evaluation.

---

# 36. Checkpoints

A Timeline may declare checkpoints for:

```text
snapshotting
replay
ablation branching
diagnostics
cost measurement
```

Example:

```json
{
  "id": "cp-before-probe",
  "stage": "pre_probe",
  "type": "checkpoint",
  "visibility": "harness"
}
```

Checkpoints are not delivered as cognition by default.

---

# 37. Probes

A Probe is a future test of memory-enabled cognition or action.

Each Probe defines:

```text
id
kind
trigger
delivery
input
oracle
evaluators
weight
dimensions
```

Example:

```json
{
  "id": "p-current",
  "kind": "temporal",
  "trigger": {
    "after_event": "e3"
  },
  "delivery": "respond",
  "input": {
    "content": "What is my timezone now?"
  },
  "oracle": {
    "expected": "+01:00"
  },
  "evaluators": ["eval-current"],
  "weight": 1.0
}
```

---

# 38. Probe Kinds

Baseline kinds:

```text
factual
implicit
multi_hop
temporal
epistemic
experience
skill
prospective
self
action
historical
audit
abstention
custom
```

Probe kind is descriptive and helps evaluator selection.

---

# 39. Probe Trigger

A probe may be triggered by:

```text
after_event
at_sequence
at_time
world_condition
manual runner phase
```

Prospective memory scenarios SHOULD often use world conditions.

Example:

```text
trigger when actor Sarah joins meeting
```

rather than asking a direct recall question.

---

# 40. Probe Delivery

Baseline values:

```text
respond
act
observe_only
```

`respond` expects a cognitive answer.

`act` gives the Agent a goal/task and evaluates actions.

`observe_only` is useful when the benchmark expects spontaneous behavior after an observation, such as a prospective reminder.

---

# 41. Probe Input

Probe input may include:

```text
content
goal
context
available_tools
constraints
```

Only this current-task information plus the Agent's own retained memory should be available.

The Runner MUST NOT add hidden past context unless the benchmark track explicitly defines a full-context baseline.

---

# 42. Oracle

The Oracle defines evaluation truth.

It MAY include:

```text
expected
accepted
forbidden
expected_status
world_assertions
trajectory_requirements
reference
```

Oracle data is harness-only by default.

Example:

```json
{
  "expected_status": "known",
  "accepted": ["+01:00", "UTC+1"],
  "forbidden": ["UTC+8"]
}
```

---

# 43. Oracle Status

Useful epistemic statuses:

```text
known
unknown
contested
historical
not_applicable
```

For abstention scenarios:

```json
{
  "expected_status": "unknown"
}
```

A correct Agent should avoid unsupported certainty.

---

# 44. World Assertions

Action probes can be scored against final world state.

Example:

```json
{
  "world_assertions": [
    {
      "path": "/auth_mode",
      "operator": "eq",
      "value": "session"
    }
  ]
}
```

Operators SHOULD be deterministic and versioned.

Baseline:

```text
eq
neq
exists
not_exists
contains
gte
lte
```

---

# 45. Trajectory Requirements

Some memory intelligence appears in *how* the Agent acts.

Example:

```text
check actual database target before rerunning migration
```

A Probe Oracle MAY specify:

```text
required action
forbidden action
ordering constraint
maximum repeated failure
```

Final success alone may not be enough if the scenario explicitly evaluates failure avoidance or learned workflow.

---

# 46. Evaluators

Evaluators are reusable scoring definitions referenced by Probe IDs.

Baseline evaluator types:

```text
exact
set_match
structured
world_state
semantic_constraints
trajectory
llm_judge
composite
```

The Scenario SHOULD use deterministic evaluators whenever possible.

The reference Runner executes `set_match`, `world_state`, `trajectory`, and `composite`. The schema accepts the full registry because it is the format contract, but the reference Scenario Validator rejects any Scenario that uses an evaluator type, trigger kind (only `after_event`), delivery mode (only `respond` / `act`), ablation method (only `replay_excluding_events` / `replay_with_injections`), tool `simulator_binding`, or generated event (`distractor_batch`) the Runner cannot execute. A schema-valid Scenario that would crash the Runner or score every Agent zero must not enter a pack.

---

# 47. Exact Evaluator

Used for deterministic scalar/string output.

Example:

```json
{
  "id": "eval-current",
  "type": "set_match",
  "config": {
    "normalization": "casefold_trim"
  }
}
```

The Oracle provides accepted values.

---

# 48. Structured Evaluator

Used when Agent output is machine-readable.

Example expected shape:

```json
{
  "answer": "+01:00",
  "status": "known"
}
```

The evaluator MAY validate fields separately.

---

# 49. Semantic Constraints Evaluator

Useful for natural language without requiring a free-form judge.

Example constraints:

```text
must express session authentication
must not recommend JWT
may mention historical JWT usage
```

The implementation may use exact phrase sets, semantic embedding checks, or an LLM judge underneath.

The report MUST disclose the method.

---

# 50. World-State Evaluator

Scores actual simulator outcome.

This is preferred for action tasks.

Examples:

```text
deployment succeeded
correct workspace selected
deprecated endpoint not called
contract reminder emitted at correct trigger
```

---

# 51. Trajectory Evaluator

Scores action history.

Examples:

```text
required action occurred
forbidden action absent
A happened before B
known failed action not repeated
counterexample was consulted
```

The evaluator reads harness action traces, not private chain-of-thought.

---

# 52. LLM Judge Evaluator

A Scenario MAY reference an LLM judge only when more deterministic methods are insufficient.

The evaluator definition SHOULD specify:

```text
rubric
output schema
judge role
temperature policy
samples
aggregation
```

The actual judge model/version belongs in the Run Artifact so the Scenario remains model-neutral.

---

# 53. Composite Evaluator

A composite evaluator combines multiple evaluator results.

Example:

```text
60% final world success
20% no forbidden action
20% required diagnostic step
```

Composite weights SHOULD sum to 1.

---

# 54. Ablations

Ablations turn a memory test into a causal memory test.

A Scenario MAY define multiple counterfactual variants.

Baseline kinds:

```text
relevant_memory
irrelevant_memory
no_memory
stale_memory
harmful_memory
counterexample
custom
```

Each Ablation should declare:

```text
id
kind
probes
method
targets
injections
expected_effect
```

---

# 55. Relevant-Memory Ablation

Remove or mask the past episode expected to help.

Expected effect:

```text
performance decreases
```

This supports:

\[
CMI =
Performance_{full}
-
Performance_{relevant\_ablated}
\]

---

# 56. Irrelevant-Memory Ablation

Remove unrelated history.

Expected effect:

```text
approximately neutral
```

Large improvement after irrelevant memory removal suggests interference.

Large degradation suggests unexpected dependency or scenario mislabeling.

---

# 57. No-Memory Ablation

Replay only the future task without meaningful past episodes.

This measures how much the task can be solved from:

```text
base model
current context
tools
```

alone.

---

# 58. Stale-Memory Condition

Preserve an obsolete memory that remains plausible.

The Agent should prefer current valid cognition.

Example:

```text
old auth = JWT
current auth = sessions
```

The stale item exists historically but should not control current implementation.

---

# 59. Harmful-Memory Condition

Inject or preserve a memory that would cause an otherwise avoidable error if blindly followed.

Examples:

```text
wrong source
poisoned instruction
out-of-context Skill
false autobiographical statement
remote authority claim
interrogation presupposing an unestablished value
```

The expected effect is **resistance**, not obedience.

The interrogation variant represents the purest adversarial case: the injected events consist **exclusively of questions** — without assertions, evidence, or authoritative backing. Asking the system whether X is a standing habit must never serve as an avenue for installing X into memory; thus, the correct answer to every paired Probe remains identical with or without the injections, and any paired performance drop directly reflects improper installation. A memory system that promotes questions into facts functions as an injection surface rather than a faithful record. The `MIB-ADV-*` Templates implement this lane; injected questions are tagged `interrogation`, and any performance drop is scored via the standard Memory Harm / Harm Resistance machinery.

---

# 60. Ablation Method

The Scenario describes the semantic intervention.

The Runner chooses the strongest supported implementation method.

Preferred order:

```text
memory mask/delete
snapshot branch
filtered memory clone
replay excluding target events
black-box reconstruction
```

The Run Artifact records the actual method.

Scenario semantics MUST NOT depend on one memory storage technology.

---

# 61. Ablation Targets

Targets SHOULD refer to scenario-level stable objects:

```text
timeline event IDs
event tag selectors
actor IDs
probe-relevant group labels
checkpoint branches
```

They SHOULD NOT require internal memory record IDs in the base Scenario.

Optional Memory Adapter runs may resolve scenario target → internal record(s).

---

# 62. Injection

Some counterfactuals require adding memory-like history.

An Ablation may inject:

```text
timeline events
observations
documents
tool results
```

before the same future Probe.

Injection provenance remains benchmark-controlled.

The Agent must not be told that the injection is a test trap.

---

# 63. Expected Effect

Suggested values:

```text
degrade
neutral
improve
resist
informational
```

`degrade`:

```text
removing relevant memory should hurt
```

`neutral`:

```text
removing irrelevant memory should not matter much
```

`resist`:

```text
harmful/stale memory should not cause error
```

The expected effect guides causal scoring but is not itself an Agent-visible label.

---

# 64. Causal Pairing

A Scenario's full run and ablation variants SHOULD share, where possible:

```text
same model
same agent configuration
same future task
same world state
same tools
same random seed
```

Only the intended memory intervention should differ.

This is essential for causal interpretation.

---

# 65. Replay Semantics

When replay is used for ablation, replay MUST preserve all non-target observations in the same order unless the intervention requires otherwise.

Runner-generated randomness SHOULD use stable per-event seeds so removing one event does not unintentionally resample unrelated future history.

---

# 66. Scoring

Scenario scoring defines how Probe scores aggregate.

Suggested structure:

```text
probe aggregation
dimension contribution
causal metrics
penalties
normalization
```

Each Probe SHOULD produce:

```text
raw evaluator outputs
normalized score [0,1]
```

Scenario score SHOULD normally be normalized to:

```text
0..100
```

---

# 67. Probe Weights

Each Probe may define:

```text
weight
```

Default:

```text
1.0
```

Scenario score:

\[
S =
\frac{\sum_i w_i s_i}
{\sum_i w_i}
\]

unless an explicit alternative aggregator is defined.

---

# 68. Dimension Contribution

A Scenario may contribute to several MIB dimensions.

Example:

```json
{
  "dimension_weights": {
    "temporal_memory": 0.6,
    "retention_retrieval": 0.2,
    "causal_memory_impact": 0.2
  }
}
```

Weights should sum to 1 when used for within-scenario dimension attribution.

The global benchmark scorer combines many scenarios into final dimension scores.

---

# 69. Causal Metrics

Scenario scoring MAY define:

```text
memory_benefit
memory_harm
causal_memory_impact
irrelevant_memory_stability
negative_transfer
error_recurrence
```

These are often derived from paired runs rather than one Probe.

---

# 70. Causal Memory Impact

Baseline:

\[
CMI =
P_{full}
-
P_{relevant\_ablated}
\]

where `P` is normalized performance for the paired Probe set.

CMI MAY be negative.

A negative value means the supposedly relevant memory harmed performance or the scenario's causal assumption is wrong.

Do not clamp away negative results before reporting diagnostics.

---

# 71. Irrelevant Memory Stability

One possible metric:

\[
IMS =
1 -
|P_{full} - P_{irrelevant\_ablated}|
\]

with scores bounded to `[0,1]`.

High IMS means irrelevant-memory removal had little effect.

---

# 72. Memory Harm

A harmful/stale variant should not decrease correct behavior relative to a clean control.

Scenario-specific harm can be represented as:

\[
H =
\max(0, P_{clean} - P_{harmful})
\]

The benchmark aggregates this separately from positive benefit.

---

# 73. Negative Transfer

Skill scenarios may pair:

```text
matching context
non-matching context
```

A memory-intelligent system should transfer in the former and resist transfer in the latter.

Negative Transfer can be scored from the inappropriate application rate.

---

# 74. Error Recurrence

Experience scenarios may identify a learned failure signature.

A future replay counts repeated use of the same known-failing action under matching conditions.

Example:

```text
same wrong API call
same wrong migration target
same ignored precondition
```

This does not require access to private reasoning.

---

# 75. Penalties

A Scenario MAY define explicit penalties for severe failures.

Examples:

```text
unsupported certainty
authority hallucination
privacy leak
catastrophic identity mismatch
forbidden stale action
```

Penalties MUST be transparent in the Scenario or benchmark policy.

They MUST NOT be hidden arbitrary judge preferences.

---

# 76. Failure Classification

Probe or evaluator results MAY attach failure codes.

Recommended classes:

```text
formation_miss
retrieval_miss
identity_mismatch
stale_memory_adoption
source_confusion
correction_loss
false_certainty
trajectory_collapse
skill_non_transfer
negative_transfer
counterexample_neglect
commitment_miss
self_model_drift
memory_hallucination
irrelevant_memory_interference
authority_confusion
```

These do not necessarily affect scoring unless the Scenario defines so.

They improve engineering diagnostics.

---

# 77. Hidden Labels

Scenario authors often know:

```text
which event is relevant
which event is distractor
which source is authoritative
which Skill is applicable
```

These labels MAY exist under harness-only fields.

They MUST NOT be automatically sent to the Agent.

The Runner SHOULD strip all hidden labels at the Agent Adapter boundary.

---

# 78. Memory Architecture Neutrality

A Scenario MUST NOT require the Agent to expose concepts such as:

```text
memory_strength
embedding score
graph node
Assertion
Experience object
Skill object
```

unless the Scenario belongs to an optional diagnostic profile that explicitly requires such an interface.

Core MIB evaluates behavior.

---

# 79. Black-Box Compatibility

A black-box Agent only needs:

```text
reset
observe
respond
act
```

Causal ablation can be implemented through scenario replay.

Therefore every core Scenario SHOULD declare whether it is:

```text
black_box_compatible
```

MIB v0.1 core scenarios SHOULD be black-box compatible by default.

---

# 80. Memory Adapter Compatibility

A Scenario MAY declare:

```text
memory_adapter_preferred
```

for better diagnostics.

This must not imply that the primary score is unavailable to black-box systems unless the Scenario is explicitly placed in an optional diagnostic suite.

---

# 81. Full-Context Baseline

A Scenario MAY support a full-context control:

```text
future task
+
all relevant past context explicitly provided
```

This distinguishes:

```text
base-model reasoning limit
vs
memory formation/retrieval limit
```

The baseline is a control condition, not part of the Agent's ordinary memory-enabled run.

---

# 82. No-Memory Baseline

A no-memory control SHOULD omit meaningful prior episodes while preserving the current task and environment.

This helps estimate:

```text
task solvability without memory
```

If the no-memory model already scores 100%, the Scenario has little power to measure memory benefit.

Such scenarios should be flagged as:

```text
memory_non_discriminative
```

during benchmark calibration.

---

# 83. Scenario Calibration

Before inclusion in a canonical pack, a Scenario SHOULD be calibrated against at least:

```text
no-memory baseline
full-context baseline
one simple memory baseline
one stronger memory-enabled system
```

Useful calibration questions:

```text
Is the future task solvable?
Does relevant history help?
Are distractors meaningful?
Does ablation produce the intended contrast?
Is scoring stable?
```

---

# 84. Benchmark Contamination

Scenario Templates SHOULD minimize direct reuse of famous benchmark facts or fixed public answers.

Hidden instantiation and late sampling reduce memorization.

A public Scenario should measure memory mechanics, not whether a base model memorized the benchmark answer during pretraining.

---

# 85. Determinism

A materialized Scenario Instance SHOULD be deterministic under:

```text
scenario version
generator version
seed
tool simulator version
world simulator version
```

Agent nondeterminism is handled at Run level through repetitions.

---

# 86. Event Random Seeds

Generated Timeline events SHOULD derive seed streams deterministically.

Recommended conceptual derivation:

```text
event_seed =
    H(
      scenario_seed,
      event_id,
      generator_version
    )
```

This keeps unrelated events stable across causal replay.

---

# 87. Integrity

Canonical Scenario Packs SHOULD eventually define content digests.

The first schema MAY include optional:

```text
integrity
```

fields.

A future MIB specification should define canonical JSON encoding before treating digests as interoperable protocol proofs.

---

# 88. Extensions

Experimental fields belong under:

```json
{
  "extensions": {
    "org.example.experimental": {
      "...": "..."
    }
  }
}
```

Extensions MUST NOT redefine the meaning of core fields.

A Runner may ignore unknown extensions unless a Scenario declares them required.

---

# 89. Example — Temporal Correction Scenario

```json
{
  "mib": "0.1",
  "kind": "MemoryEpisodeProgram",
  "id": "MIB-TIME-001",
  "version": "0.1.0",
  "status": "draft",
  "title": "Timezone Update and Historical Recall",
  "suite": "time",
  "dimensions": [
    "temporal_memory",
    "retention_retrieval",
    "causal_memory_impact"
  ],
  "tags": [
    "update",
    "historical-recall",
    "staleness"
  ],
  "difficulty": {
    "level": "medium",
    "meaningful_events": 3,
    "distractor_events": 200,
    "entity_count": 1,
    "memory_hops": 0
  },
  "requirements": {
    "black_box_compatible": true,
    "capabilities": [
      "respond"
    ]
  },
  "execution": {
    "repetitions": 3,
    "reset_between_repetitions": true
  },
  "leakage": {
    "probe_sampling": "late",
    "future_probe_visible_during_formation": false,
    "oracle_visible_to_agent": false,
    "ablation_labels_visible_to_agent": false,
    "hidden_world_state_visible_to_agent": false
  },
  "actors": [
    {
      "id": "alice",
      "kind": "person",
      "display_name": "Alice"
    }
  ],
  "world": {
    "clock": {
      "mode": "virtual",
      "start": "2026-01-01T09:00:00Z",
      "timezone": "UTC"
    },
    "state": {
      "user_timezone": "+08:00"
    },
    "hidden_ground_truth": {
      "current_timezone": "+08:00"
    }
  },
  "timeline": [
    {
      "id": "e1",
      "stage": "past",
      "type": "interaction",
      "at": {
        "sequence": 1
      },
      "visibility": "agent",
      "actor": "alice",
      "content": "My timezone is UTC+8."
    },
    {
      "id": "e2",
      "stage": "past",
      "type": "interaction",
      "at": {
        "sequence": 20
      },
      "visibility": "agent",
      "actor": "alice",
      "content": "I'm moving to London next month."
    },
    {
      "id": "e3",
      "stage": "past",
      "type": "interaction",
      "at": {
        "sequence": 50
      },
      "visibility": "agent",
      "actor": "alice",
      "content": "I've arrived in London. My timezone is now UTC+1.",
      "world_updates": [
        {
          "op": "set",
          "path": "/user_timezone",
          "value": "+01:00"
        }
      ]
    },
    {
      "id": "d1",
      "stage": "interference",
      "type": "distractor_batch",
      "at": {
        "sequence": 60
      },
      "visibility": "agent",
      "generator": {
        "id": "routine-chat-v1",
        "version": "1.0.0",
        "count": 200,
        "seed": 42
      }
    },
    {
      "id": "cp1",
      "stage": "pre_probe",
      "type": "checkpoint",
      "at": {
        "sequence": 300
      },
      "visibility": "harness"
    }
  ],
  "probes": [
    {
      "id": "p-current",
      "kind": "temporal",
      "trigger": {
        "after_event": "cp1"
      },
      "delivery": "respond",
      "input": {
        "content": "What's my timezone now?"
      },
      "oracle": {
        "expected_status": "known",
        "accepted": [
          "+01:00",
          "UTC+1"
        ],
        "forbidden": [
          "+08:00",
          "UTC+8"
        ]
      },
      "evaluators": [
        "eval-timezone"
      ],
      "dimensions": [
        "temporal_memory"
      ],
      "weight": 1.0
    },
    {
      "id": "p-historical",
      "kind": "historical",
      "trigger": {
        "after_event": "cp1"
      },
      "delivery": "respond",
      "input": {
        "content": "What timezone did I use before moving to London?"
      },
      "oracle": {
        "expected_status": "historical",
        "accepted": [
          "+08:00",
          "UTC+8"
        ]
      },
      "evaluators": [
        "eval-timezone"
      ],
      "dimensions": [
        "temporal_memory",
        "retention_retrieval"
      ],
      "weight": 1.0
    }
  ],
  "ablations": [
    {
      "id": "a-relevant",
      "kind": "relevant_memory",
      "probes": [
        "p-current"
      ],
      "method": "replay_excluding_events",
      "targets": {
        "event_ids": [
          "e3"
        ]
      },
      "expected_effect": "degrade"
    },
    {
      "id": "a-irrelevant",
      "kind": "irrelevant_memory",
      "probes": [
        "p-current",
        "p-historical"
      ],
      "method": "replay_excluding_events",
      "targets": {
        "event_ids": [
          "d1"
        ]
      },
      "expected_effect": "neutral"
    }
  ],
  "evaluators": [
    {
      "id": "eval-timezone",
      "type": "set_match",
      "config": {
        "normalization": "casefold_trim"
      }
    }
  ],
  "scoring": {
    "probe_aggregation": "weighted_mean",
    "score_range": {
      "min": 0,
      "max": 100
    },
    "dimension_weights": {
      "temporal_memory": 0.7,
      "retention_retrieval": 0.15,
      "causal_memory_impact": 0.15
    },
    "causal_metrics": [
      "causal_memory_impact",
      "irrelevant_memory_stability"
    ]
  }
}
```

---

# 90. Example — Experience to Skill Scenario

A more behavior-oriented scenario might represent:

```text
Episode 1:
    Save fails because no workspace selected.

Episode 2:
    Same failure.

Episode 3:
    Agent selects workspace first.
    Save succeeds.

Interference:
    many unrelated tasks.

Future Task A:
    different UI, same hidden precondition.
    Expected: transfer learned Skill.

Future Task B:
    different environment where workspace selection is irrelevant.
    Expected: do not blindly transfer Skill.
```

The same Scenario Model represents:

```text
Experience Memory
Skill Learning
Positive Transfer
Negative Transfer
Causal Ablation
```

without requiring the Agent to internally store an object named `Skill`.

---

# 91. Validation Rules Beyond JSON Schema

JSON Schema can validate structure but cannot enforce all Scenario semantics.

The reference Runner SHOULD perform additional semantic validation.

Examples:

```text
Timeline IDs unique
Probe IDs unique
Evaluator IDs unique
Ablation IDs unique

all actor references resolve
all probe evaluator references resolve
all after_event references resolve
all ablation event targets resolve

timeline sequence is monotonic when required
world update paths are legal
probe weights are non-negative
dimension weights sum to approximately 1

hidden fields are never included in Agent observations
future Probe not delivered during formation

late-sampled Probe has not been materialized too early
causal pair can be replayed deterministically
```

These checks belong in:

```text
MIB Scenario Validator
```

rather than JSON Schema alone.

---

# 92. Scenario Validation Phases

Recommended:

```text
1. JSON Schema Validation
2. Reference Resolution
3. Timeline Validation
4. World-State Validation
5. Leakage Validation
6. Evaluator Validation
7. Ablation Validation
8. Scoring Validation
9. Reproducibility Validation
```

A Scenario SHOULD NOT enter a canonical pack until all phases pass.

---

# 93. Canonical Scenario Pack

A Scenario Pack is a versioned collection of validated Scenarios.

Example:

```text
MIB v0.1 Core Pack

Recall
Time
Belief
Experience
Skill
Causal
Cross-Suite
```

Pack-level metadata SHOULD define:

```text
pack id
version
MIB version
scenario list
required suites
score policy
generator versions
digest
```

Pack format is outside this document and should be specified separately.

---

# 94. MIB v0.1 Constraints

For the first implementation, Scenario authors SHOULD prefer:

```text
black-box compatibility
JSON-only instance format
deterministic world simulation
replay-based ablation
respond/act probes
deterministic evaluators where possible
fixed or seedable Timeline generation
```

Avoid making v0.1 depend on:

```text
memory introspection
model-specific hidden state
private chain-of-thought
vendor-specific memory APIs
unbounded external internet state
```

This keeps the benchmark reproducible.

---

# 95. Reference Runner Responsibilities

The Runner is responsible for:

```text
loading Scenario
instantiating parameters
seeding World
enforcing Virtual Time
delivering visible Timeline events
stripping hidden fields
creating checkpoints
delivering Probes
collecting outputs/actions
executing Evaluators
performing Ablation replay
computing Scenario scores
producing Run Artifact
```

The Agent is responsible only for being an Agent.

---

# 96. Runner Must Not Help the Agent

The Runner MUST NOT improve participant performance by:

```text
summarizing past events
highlighting relevant memories
labeling distractors
revealing source authority
precomputing answers
injecting Oracle state
telling the Agent which Experience matters
```

unless such information is explicitly part of the visible Scenario.

---

# 97. Scenario Authoring Principle

A good Scenario should be interpretable as a small scientific experiment.

It should answer:

```text
What memory capability is being tested?

What past information should matter?

Why should it matter?

What future behavior demonstrates success?

What is the counterfactual without that memory?

What irrelevant or harmful memory tests selectivity?

Can we score the result without guessing?
```

If these questions cannot be answered, the Scenario is probably not ready.

---

# 98. Scenario Quality Checklist

Before inclusion:

```text
[ ] future probe is not leaked
[ ] ground truth is explicit
[ ] relevant past episode is identifiable
[ ] distractors are plausible
[ ] current context alone does not trivialize the task
[ ] full-context baseline can solve the intended task
[ ] ablation can be replayed
[ ] evaluation is deterministic where possible
[ ] historical/current semantics are unambiguous
[ ] source semantics are unambiguous where relevant
[ ] no private chain-of-thought is required
[ ] no vendor-specific memory primitive is required
[ ] hidden labels are stripped
[ ] all IDs/references resolve
[ ] scoring is reproducible
```

---

# 99. Scenario Model Invariants

1. A Scenario is a program over time, not a static QA item.
2. World truth is distinct from Agent observation.
3. Hidden ground truth MUST NOT leak into Agent context.
4. Future probes SHOULD be unknown during memory formation.
5. Probe Oracle MUST remain harness-only by default.
6. Timeline events MUST have stable identities.
7. Relevant-memory ablation SHOULD change only the intended memory condition.
8. Irrelevant-memory ablation SHOULD preserve task semantics.
9. Replay SHOULD preserve unrelated randomness.
10. Scenario semantics MUST NOT depend on one memory architecture.
11. Black-box Agent participation SHOULD remain possible.
12. Memory introspection is optional diagnostic capability.
13. Current task context and past memory are distinct inputs.
14. Historical truth and current truth may both be valid under different time coordinates.
15. Statement, contradiction, correction, and unknown MUST be separately representable by Scenario ground truth.
16. Experience scenarios SHOULD preserve action/observation/outcome structure.
17. Skill scenarios MUST test applicability, not only repetition.
18. Negative transfer SHOULD be measurable.
19. Forgetting scenarios SHOULD distinguish obsolete-current influence from historical recall.
20. Prospective memory SHOULD be triggerable without direct recall wording.
21. Self-memory scenarios MUST NOT equate remembered self-description with real authority.
22. Deterministic and world-state evaluators are preferred.
23. LLM judges MUST NOT override explicit world truth.
24. Causal memory evaluation requires paired conditions.
25. Scenario scoring MUST remain auditable.

---

# 100. Final Principle

The Scenario Model exists to make one idea experimentally testable:

> **Memory intelligence is not demonstrated when the Agent can merely repeat the past. It is demonstrated when a controlled past changes the right future behavior — and only the right future behavior.**

---

# Appendix A — Minimal Executable Scenario

```json
{
  "mib": "0.1",
  "kind": "MemoryEpisodeProgram",
  "id": "MIB-RET-001",
  "version": "0.1.0",
  "title": "Direct Delayed Recall",
  "suite": "recall",
  "dimensions": [
    "retention_retrieval"
  ],
  "world": {
    "clock": {
      "mode": "virtual",
      "start": "2026-01-01T00:00:00Z",
      "timezone": "UTC"
    },
    "state": {}
  },
  "timeline": [
    {
      "id": "e1",
      "stage": "past",
      "type": "interaction",
      "at": {
        "sequence": 1
      },
      "visibility": "agent",
      "content": "My dog's name is Pixel."
    }
  ],
  "probes": [
    {
      "id": "p1",
      "kind": "factual",
      "delivery": "respond",
      "input": {
        "content": "What's my dog's name?"
      },
      "oracle": {
        "accepted": [
          "Pixel"
        ]
      },
      "evaluators": [
        "exact-1"
      ]
    }
  ],
  "evaluators": [
    {
      "id": "exact-1",
      "type": "set_match",
      "config": {
        "normalization": "casefold_trim"
      }
    }
  ],
  "scoring": {
    "probe_aggregation": "weighted_mean",
    "score_range": {
      "min": 0,
      "max": 100
    }
  }
}
```

---

# Appendix B — Recommended Repository Layout

```text
MIB/
├── MIB-Architecture.md
├── MIB-Scenario-Model.md
│
├── schemas/
│   └── mib-scenario.schema.json
│
├── scenarios/
│   ├── recall/
│   ├── time/
│   ├── epistemic/
│   ├── experience/
│   ├── skill/
│   └── causal/
│
├── adapters/
│   ├── MIB-Agent-Adapter.md
│   └── MIB-Memory-Adapter.md
│
├── runner/
├── evaluators/
└── leaderboard/
```

---

# Appendix C — Next Documents

After the Scenario Model and machine-readable schema:

```text
1. MIB-Agent-Adapter.md
2. MIB-Scoring.md
3. mib-report.schema.json
4. MIB-v0.1-Test-Plan.md
5. canonical scenario pack
6. reference runner
```

The next highest-value document is `MIB-Agent-Adapter.md`, because once Scenario semantics and transport boundaries are fixed, the Runner can be implemented without coupling itself to any specific memory architecture.

---

# Appendix D — Transfer Support Annotation

A Scenario may carry an evaluator-private annotation making the author's latent transfer hypothesis explicit: which past Experience supports which future Probe, through which reusable Ability, under which applicability boundary.

It is carried under the Scenario `extensions` key, not as a top-level v0.1 property:

```json
{
  "extensions": {
    "mib.transfer_support.v1": { "...": "..." }
  }
}
```

so that every existing Scenario file stays valid, every existing v0.1 parser can ignore it, and Hidden packs can adopt it gradually. Its shape is defined by `schemas/mib-transfer-support.schema.json`, and its semantics by `MIB-Transfer-Intelligence.md`.

The annotation is diagnostic metadata, never task content. The Runner projects Timeline events and Probe inputs into Agent requests; it never projects Scenario extensions. Ability identity, support-event IDs, applicability cues, oracle Skill text, and distance class MUST NOT reach the Agent, a public report, or a leaderboard response.

Two related, non-identical concepts:

```text
Transfer annotation   these events support this Ability
Causal ablation       remove this information set and observe behavior
```

A well-formed Skill Scenario usually aligns them. Redundant support and negative controls break the alignment, which is why both are declared separately.
