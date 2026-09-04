# MIB Agent Adapter

## Transport-Neutral Interface Between the MIB Runner and Memory-Enabled Agents

**Version:** 0.1-draft  
**Status:** Adapter Protocol Proposal / Companion to `MIB-Specification.md` and `MIB-Specification.md`

---

# 0. Purpose

This document defines the interface boundary between the **MIB Runner** and an evaluated **memory-enabled Agent**.

The purpose of the Agent Adapter is not to standardize how memory works internally.

It standardizes only how the benchmark can:

```text
start an isolated run
deliver observations
advance an Agent through a lived timeline
ask a future question
give a future task
capture spontaneous memory-triggered behavior
mediate tool calls through the World Simulator
repeat the same experiment under ablation
collect auditable outputs and usage metadata
```

The central abstraction is:

```text
MIB Runner
    │
    │  Agent Adapter
    ▼
Agent + Long-Term Memory
```

Everything behind the Adapter boundary is participant implementation.

Everything in front of the Adapter boundary is benchmark-controlled.

---

# 1. Core Principle

The Agent Adapter MUST preserve the following separation:

```text
Runner owns:
    Scenario
    hidden ground truth
    Virtual Time
    World Simulator
    future Probe
    Oracle
    Evaluators
    ablation condition
    benchmark tools

Agent owns:
    reasoning
    memory formation
    memory storage
    consolidation
    recall
    internal planning
    response generation
```

The Runner must not help the Agent remember.

The Agent must not gain access to benchmark secrets.

---

# 2. Architecture Neutrality

The Agent Adapter does not assume the evaluated Agent uses any specific memory architecture.

Compatible systems may use:

```text
raw history replay
vector retrieval
summary memory
key-value memory
relational memory
graph memory
episodic memory
procedural memory
learned recurrent memory
external databases
KIP
hybrid memory
```

The Adapter MUST NOT require internal concepts such as:

```text
memory node
embedding
Assertion
Experience
Skill
memory_strength
retrieval score
```

for core participation.

Those belong to optional diagnostics or the separate Memory Adapter.

---

# 3. Agent Adapter vs Memory Adapter

MIB separates two interfaces.

## 3.1 Agent Adapter

Required for ordinary evaluation.

It answers:

> How does the Runner interact with the whole Agent?

Core operations:

```text
describe
reset
observe
respond
act
```

Optional operations:

```text
maintain
close
health
```

## 3.2 Memory Adapter

Optional diagnostic interface.

It may expose:

```text
snapshot
inspect
mask
delete
restore
metrics
trace
```

The Agent Adapter MUST remain useful when no Memory Adapter exists.

This is essential for architecture-neutral benchmarking.

---

# 4. Evaluation Unit

The system under evaluation is:

```text
Agent
+
Long-Term Memory System
```

The Agent Adapter treats this pair as one stateful system.

Between `reset` and the end of a run, the Agent may accumulate state.

At the beginning of an isolated benchmark condition, that state MUST be reset according to the run isolation rules in this document.

---

# 5. Track Semantics

The Agent Adapter is used differently across MIB tracks.

## 5.1 Track A — Memory System Track

Track A aims to isolate the memory system.

For leaderboard-grade Track A comparison, the Agent behavior surrounding memory SHOULD be benchmark-controlled.

Preferred forms:

```text
MIB Reference Agent
    +
Participant Memory System
```

or:

```text
approved fixed Agent wrapper
    +
Participant Memory System
```

A submission that changes the base Agent, system prompt, reasoning policy, or tool policy is normally Track B, not Track A.

The Agent Adapter remains the external Runner boundary in either case.

## 5.2 Track B — Integrated Agent Track

The participant may control:

```text
model
Agent policy
memory architecture
memory prompts
consolidation
retrieval
tool strategy
```

The Adapter exposes the integrated system as one unit.

## 5.3 Track C — Diagnostics

Track C may combine the Agent Adapter with an optional Memory Adapter.

---

# 6. Required Core Operations

A conforming MIB v0.1 Agent Adapter MUST implement:

```text
describe()
reset()
observe()
respond()
act()
```

The following are OPTIONAL:

```text
maintain()
close()
health()
```

An Adapter MAY expose additional vendor-specific operations, but the Runner MUST NOT require them for core MIB scenarios.

---

# 7. Reference Interface

Conceptual TypeScript interface:

```typescript
interface MIBAgentAdapter {
  describe(): Promise<AgentDescriptor>;

  reset(
    request: ResetRequest
  ): Promise<ResetResult>;

  observe(
    request: ObserveRequest
  ): Promise<ObserveResult>;

  respond(
    request: RespondRequest
  ): Promise<RespondResult>;

  act(
    request: ActRequest
  ): Promise<ActResult>;

  maintain?(
    request: MaintainRequest
  ): Promise<MaintainResult>;

  close?(
    request: CloseRequest
  ): Promise<CloseResult>;

  health?(): Promise<HealthResult>;
}
```

This is a semantic interface.

Implementations may use:

```text
in-process calls
HTTP JSON
stdio JSONL
RPC
container bridge
```

as long as the observable semantics are equivalent.

---

# 8. Adapter Descriptor

`describe()` is a harness-facing capability negotiation call.

It MUST NOT mutate Agent memory.

Example:

```json
{
  "protocol": "mib-agent/0.1",
  "implementation": {
    "name": "Example Agent",
    "version": "1.4.2",
    "vendor": "Example Labs"
  },
  "track_support": [
    "integrated_agent"
  ],
  "capabilities": {
    "observe": true,
    "respond": true,
    "act": true,
    "spontaneous_emissions": true,
    "maintenance": false,
    "runner_managed_tools": true,
    "structured_output": true,
    "virtual_time": true,
    "seedable": false
  },
  "state": {
    "run_isolation": "hard",
    "observe_visibility": "read_after_write",
    "request_idempotency": true
  },
  "limits": {
    "max_observation_bytes": 1048576,
    "max_output_bytes": 1048576
  }
}
```

The descriptor is included in the Run Artifact.

---

# 9. Descriptor Must Be Truthful

An Adapter MUST NOT claim a capability it cannot reliably provide.

Examples:

```text
seedable = true
```

means benchmark-supplied seeds actually constrain participant-controlled randomness that supports seeding.

```text
run_isolation = hard
```

means previous benchmark-run memory cannot influence a fresh run.

Incorrect capability declaration is an Adapter conformance failure, not a memory-capability failure.

---

# 10. Run Identity

Every benchmark condition executes in a distinct opaque run namespace.

The Runner supplies:

```text
run_id
```

Example:

```text
run_8cf2f92c
```

The value MUST be opaque.

It SHOULD NOT encode:

```text
scenario suite
dimension
full-memory condition
relevant ablation
harmful-memory condition
ground-truth label
```

Bad:

```text
MIB-TIME-001-relevant-ablation
```

Good:

```text
run_8cf2f92c
```

This prevents condition-label leakage.

---

# 11. Scenario Metadata Visibility

By default, the Agent SHOULD NOT receive:

```text
scenario_id
suite
dimensions
tags
difficulty
ablation kind
expected effect
evaluator type
Oracle
ground truth
```

unless the Scenario explicitly treats such information as part of the visible task.

The Runner may record all of this internally.

The Adapter sees only what a real Agent would naturally observe.

---

# 12. Request Envelope

Transport profiles SHOULD use a common request envelope.

Example:

```json
{
  "mib": "0.1",
  "protocol": "mib-agent/0.1",
  "request_id": "req_0193",
  "run_id": "run_8cf2f92c",
  "operation": "observe",
  "virtual_time": "2026-03-01T09:00:00Z",
  "body": {}
}
```

Core envelope fields:

```text
mib
protocol
request_id
run_id
operation
virtual_time
body
```

`virtual_time` MAY be absent when a Scenario does not expose time.

---

# 13. Response Envelope

Reference response:

```json
{
  "mib": "0.1",
  "protocol": "mib-agent/0.1",
  "request_id": "req_0193",
  "run_id": "run_8cf2f92c",
  "status": "ok",
  "body": {},
  "usage": {}
}
```

Status:

```text
ok
error
```

Transport failure is distinct from an explicit `error` response.

---

# 14. Request ID

`request_id` identifies one semantic Adapter operation.

Retries MUST reuse the same `request_id`.

This is crucial because operations such as:

```text
observe
act
maintain
```

may change Agent state.

The Adapter MUST treat a repeated request with the same:

```text
run_id + request_id
```

as the same operation.

---

# 15. Request Idempotency

A conforming core Adapter MUST support request idempotency within an active run.

If a network retry repeats:

```text
observe(req_0193)
```

the Agent MUST NOT form the same memory twice.

If a retry repeats:

```text
act(req_0310)
```

the Adapter SHOULD return the previously produced result rather than resampling a new action.

This is necessary for:

```text
reproducibility
safe retries
non-duplicated memory formation
causal replay
```

Adapters may internally cache request results for the lifetime of a run.

---

# 16. Observation Identity

Each delivered Observation has a stable opaque `observation_id`.

Example:

```json
{
  "observation_id": "obs_a17d",
  "type": "user_message",
  "actor": {
    "id": "actor_2",
    "display_name": "Alice"
  },
  "content": "My timezone is UTC+8."
}
```

The observation ID MAY correspond to a Scenario Timeline event, but the value presented to the Agent SHOULD be opaque.

The Agent may use it for optional attribution.

---

# 17. Reset

`reset()` begins an isolated benchmark run.

Reference request:

```json
{
  "request_id": "req_reset_1",
  "run_id": "run_8cf2f92c",
  "operation": "reset",
  "body": {
    "mode": "fresh",
    "seed": 42,
    "virtual_time": "2026-01-01T09:00:00Z"
  }
}
```

Baseline reset mode:

```text
fresh
```

A successful fresh reset means:

> No cognitive state from a previous benchmark run may influence this run.

---

# 18. Hard Run Isolation

Core MIB v0.1 requires logical run isolation.

Acceptable implementation strategies include:

```text
new database namespace
new tenant
new conversation/thread
fresh memory index
fresh Agent process
hard memory clear
isolated ephemeral container
```

The implementation method is participant-defined.

The observable guarantee is not.

---

# 19. No Cross-Run Leakage

After:

```text
reset(run_B, mode=fresh)
```

the Agent MUST NOT remember information that appeared only in:

```text
run_A
```

unless the benchmark explicitly defines a future lifelong/cross-run profile.

Cross-run leakage is a conformance or privacy failure.

It MUST NOT be interpreted as good retention.

---

# 20. Ablation Runs Are Separate Runs

A full-memory condition and its ablation variant SHOULD use different opaque `run_id` values.

Example:

```text
run_A = full history replay
run_B = same scenario minus relevant episode
```

The Agent MUST NOT be told:

```text
run_A is control
run_B is ablation
```

Each run starts from a fresh isolated state unless a stronger snapshot-based diagnostic mechanism is used outside the core Agent Adapter.

---

# 21. Reset and Participant Model State

A fresh reset MUST clear benchmark-created persistent cognitive state.

It does not require reloading immutable components such as:

```text
base model weights
static system prompt
compiled software
static domain knowledge
```

The distinction is:

```text
pre-existing implementation
vs
memory accumulated during benchmark runs
```

Only the latter must be isolated.

---

# 22. Observe

`observe()` delivers one visible event from the Scenario to the Agent.

Example:

```json
{
  "request_id": "req_0193",
  "run_id": "run_8cf2f92c",
  "operation": "observe",
  "virtual_time": "2026-01-01T09:00:00Z",
  "body": {
    "observation": {
      "observation_id": "obs_a17d",
      "type": "user_message",
      "actor": {
        "id": "actor_2",
        "display_name": "Alice"
      },
      "content": "My timezone is UTC+8."
    }
  }
}
```

The Adapter decides internally how to:

```text
process
store
summarize
extract
ignore
consolidate
```

the observation.

---

# 23. Observation Types

Baseline Agent-visible types include:

```text
user_message
agent_message
environment_event
tool_result
document
measurement
feedback
system_event
time_event
custom
```

MIB Scenario event types are mapped into these Agent-facing observation types by the Runner.

The Agent Adapter should not depend on Scenario authoring internals.

---

# 24. Observation Payload

An Observation may contain:

```text
content
structured payload
actor
virtual time
attachments or references
tool-result metadata
```

Example structured observation:

```json
{
  "observation_id": "obs_tool_17",
  "type": "tool_result",
  "tool_call_id": "call_91",
  "tool": "db.inspect_target",
  "payload": {
    "target": "legacy-db"
  }
}
```

---

# 25. Hidden Fields Must Be Stripped

The Runner MUST NOT send fields such as:

```text
oracle_labels
expected_answer
expected_effect
relevance
is_distractor
source_authority_label
ablation_target
dimension
score_weight
hidden_ground_truth
```

through `observe()` unless they are intentionally observable world information.

This is a Runner invariant and an Adapter conformance test.

---

# 26. Observe Completion Is a Visibility Barrier

When `observe()` returns `status=ok`, the observation has been accepted by the evaluated system.

Any logical memory effect the system requires for the *next* call MUST be visible to its own subsequent `respond()` or `act()`.

Formally:

```text
observe(O) completes
        ↓
respond()/act() may immediately rely on O
```

This is **read-after-write logical visibility**.

The system may still perform background optimization or compaction, but it may not require an unspecified real-time delay before newly accepted memory becomes usable.

---

# 27. Why the Visibility Barrier Matters

Without this rule, benchmark results could depend on arbitrary wall-clock sleeps:

```text
wait 1 second
wait 30 seconds
wait 5 minutes
```

That would make comparison unreliable.

MIB evaluates cognitive behavior, not hidden background scheduling luck.

If a memory architecture has an explicit consolidation process, it should use a Scenario maintenance window and the optional `maintain()` operation.

---

# 28. Observe Result

Reference:

```json
{
  "status": "ok",
  "body": {
    "accepted": true,
    "emissions": []
  }
}
```

The Runner MUST NOT infer memory quality from `accepted=true`.

It only means the event was processed successfully.

---

# 29. Spontaneous Emissions

`observe()` MAY return **spontaneous emissions**.

This enables real prospective memory tests.

Example past instruction:

```text
When Sarah joins the next meeting,
remind me to ask about the contract.
```

Later the Runner delivers:

```text
Sarah joined the meeting.
```

The benchmark should be able to observe:

```text
"Remember to ask Sarah about the contract."
```

without asking:

```text
"Do I have anything to remember?"
```

---

# 30. Emission Types

Baseline:

```text
message
signal
tool_call
```

Example:

```json
{
  "emissions": [
    {
      "emission_id": "emit_1",
      "type": "message",
      "content": "Remember to ask Sarah about the contract."
    }
  ]
}
```

An emission is part of observable Agent behavior and may be scored.

---

# 31. Emission Timing

An emission belongs causally to the `observe()` call that returned it.

The Runner MUST record:

```text
trigger observation
virtual time
emission order
emission content
```

For prospective memory, this avoids ambiguous later attribution.

---

# 32. Observe-Only Probes

A Scenario Probe with:

```text
delivery = observe_only
```

is evaluated from emissions generated by one or more relevant observations.

The Runner does NOT follow with a hidden hint or recall question.

This is the preferred pattern for genuine prospective-memory triggering.

---

# 33. Respond

`respond()` asks the Agent for a cognitive answer without permitting benchmark-world side effects.

Typical uses:

```text
factual recall
historical recall
temporal reasoning
epistemic answer
abstention
experience recall
self-memory
```

Reference request:

```json
{
  "request_id": "req_0301",
  "run_id": "run_8cf2f92c",
  "operation": "respond",
  "virtual_time": "2026-05-01T10:00:00Z",
  "body": {
    "interaction_id": "interaction_7",
    "input": {
      "content": "What timezone did I use before moving?"
    }
  }
}
```

---

# 34. Respond Must Not Receive Oracle Metadata

A `respond()` call receives only the Probe's Agent-visible input.

It MUST NOT receive:

```text
Oracle
accepted answers
forbidden answers
expected status
evaluator configuration
dimension weights
ablation labels
```

The Runner retains those for later evaluation.

---

# 35. Respond Result

Reference:

```json
{
  "status": "ok",
  "body": {
    "interaction_id": "interaction_7",
    "output": {
      "type": "message",
      "content": "You were using UTC+8 before moving to London."
    }
  }
}
```

Optional structured output:

```json
{
  "output": {
    "type": "structured",
    "value": {
      "answer": "UTC+8",
      "status": "historical"
    }
  }
}
```

---

# 36. Abstention

An Agent may explicitly abstain.

Example:

```json
{
  "output": {
    "type": "abstention",
    "content": "I don't have enough information to know."
  }
}
```

MIB treats abstention as first-class behavior.

It may be correct in epistemic scenarios.

---

# 37. Respond and Tools

Baseline `respond()` is side-effect free with respect to the benchmark World.

If the Probe requires tool use, it SHOULD use `delivery=act`.

An Agent may still use its internal memory/database/LLM services during `respond()`.

Those are implementation internals, not benchmark-world tools.

---

# 38. Act

`act()` gives the Agent a goal that may require interaction with benchmark tools and World state.

Example:

```json
{
  "request_id": "req_0501",
  "run_id": "run_8cf2f92c",
  "operation": "act",
  "virtual_time": "2026-05-01T10:00:00Z",
  "body": {
    "task_id": "task_11",
    "goal": "Repair the deployment and start the service.",
    "constraints": [
      "Do not modify production data."
    ],
    "tools": [
      {
        "name": "db.inspect_target",
        "description": "Return the actual database target.",
        "input_schema": {
          "type": "object",
          "properties": {}
        }
      }
    ]
  }
}
```

---

# 39. Runner-Managed Tools

Core MIB action scenarios SHOULD use **Runner-managed tools**.

The Agent proposes a tool call.

The Runner:

```text
validates call
executes it in World Simulator
records it
applies world side effects
returns tool_result Observation
```

The Agent does not directly mutate hidden simulator state.

This keeps the benchmark oracle authoritative.

---

# 40. Act Result Kinds

An `act()` result is one of:

```text
tool_call
final
abstention
```

Tool call:

```json
{
  "status": "ok",
  "body": {
    "task_id": "task_11",
    "result": {
      "type": "tool_call",
      "tool_call_id": "call_91",
      "tool": "db.inspect_target",
      "arguments": {}
    }
  }
}
```

Final:

```json
{
  "result": {
    "type": "final",
    "content": "Deployment repaired and service started."
  }
}
```

---

# 41. Tool Loop

Reference lifecycle:

```text
Runner
  │
  ├── act(goal, tools)
  │
Agent
  │
  ├── tool_call
  │
Runner / World Simulator
  │
  ├── execute tool
  │
  ├── record side effect
  │
  ├── observe(tool_result)
  │
Agent
  │
  ├── act(continue same task)
  │
  ├── ...
  │
  └── final
```

The same `task_id` is used throughout one task.

Each Adapter request still receives a new `request_id`.

---

# 42. Continuing a Task

After a tool result, the Runner invokes `act()` again:

```json
{
  "body": {
    "task_id": "task_11",
    "continuation": true
  }
}
```

The Agent is expected to retain task context internally within the active run.

The Runner MAY repeat the goal for stateless transport convenience, but it must do so consistently across compared systems.

---

# 43. Tool Call Identity

Every tool call must have a stable:

```text
tool_call_id
```

Tool-result Observation includes the same ID.

This allows:

```text
trajectory evaluation
duplicate-call detection
result correlation
replay
```

---

# 44. Tool Call Idempotency

Benchmark tool calls are executed by the Runner, not by retrying the Agent Adapter directly.

If an Adapter response containing a `tool_call` is retried with the same `request_id`, the Adapter MUST return the same call ID and arguments.

The Runner MUST NOT execute the same `tool_call_id` twice.

---

# 45. Tool Schemas

Tools are exposed using machine-readable input schemas.

JSON Schema-compatible argument definitions are RECOMMENDED.

The Agent MUST NOT assume access to tools that were not supplied for the current task or exposed through prior visible environment policy.

---

# 46. World Side Effects

All benchmark-world side effects SHOULD flow through Runner-managed tools.

Examples:

```text
send message
modify file
deploy service
change setting
select workspace
schedule event
```

This gives the Runner an auditable action trace.

Direct out-of-band modification of benchmark World state is prohibited.

---

# 47. External Services

An Agent may require external services for its own implementation:

```text
LLM API
memory database
embedding service
participant-owned backend
```

These MUST be declared in submission metadata.

They MUST NOT be used to inspect:

```text
hidden Scenario files
Runner internals
Oracle state
hidden evaluator endpoints
other submissions
```

Track policy may further restrict external network access.

---

# 48. Maintenance

Some memory systems expose explicit consolidation or maintenance.

A Scenario may contain a:

```text
maintenance_window
```

If the Agent descriptor advertises:

```text
maintenance = true
```

the Runner MAY call:

```text
maintain()
```

at that point.

---

# 49. Maintain Request

Example:

```json
{
  "request_id": "req_m_12",
  "run_id": "run_8cf2f92c",
  "operation": "maintain",
  "virtual_time": "2026-04-01T00:00:00Z",
  "body": {
    "reason": "scenario_maintenance_window",
    "budget": {
      "max_wall_time_ms": 30000
    }
  }
}
```

The reason is generic.

It MUST NOT reveal:

```text
which future Probe matters
which memory should be consolidated
which memory is relevant
```

---

# 50. Maintenance Semantics

`maintain()` may perform:

```text
summary
consolidation
index rebuild
memory decay
Skill compilation
conflict review
garbage collection
```

according to the Agent's own architecture.

The Runner does not prescribe internal maintenance behavior.

---

# 51. No Hidden Maintenance Advantage

Track A comparisons MUST use the same maintenance-window schedule.

A participant may not receive extra maintenance opportunities based on knowledge of hidden future Probes.

Track B may use its own continuously operating maintenance policy, but all external timing and resource use must be reported.

---

# 52. Virtual Time

The Runner owns MIB Virtual Time.

Each request may include:

```text
virtual_time
```

The Agent SHOULD use this as the current benchmark time if it supports time-aware memory.

The Agent MUST NOT infer benchmark truth from real wall-clock time when Virtual Time is supplied.

---

# 53. Time Advancement

A time-advance Timeline event may be delivered as:

```json
{
  "observation_id": "obs_time_3",
  "type": "time_event",
  "payload": {
    "previous": "2026-01-01T09:00:00Z",
    "current": "2026-02-01T09:00:00Z",
    "elapsed_seconds": 2678400
  }
}
```

The exact visibility is Scenario-defined.

The Runner also updates the envelope `virtual_time`.

---

# 54. Real Time Must Not Substitute for Virtual Time

A benchmark must not require:

```text
sleep 30 days
```

to test long-term memory.

If an implementation's retention policy depends only on real-time storage age and cannot accept Virtual Time, it may still participate in scenarios that do not require simulated aging, but its declared capability must reflect that limitation.

---

# 55. Prospective Memory

Prospective memory is triggered by future conditions.

MIB evaluates it through:

```text
past commitment Observation
        ↓
long delay / interference
        ↓
trigger Observation
        ↓
spontaneous emission
```

The Runner must not ask an extra recall question unless the Scenario explicitly contains one.

---

# 56. Prospective Trigger Example

Past:

```json
{
  "type": "user_message",
  "content": "When Sarah joins, remind me to ask about the contract."
}
```

Future:

```json
{
  "type": "environment_event",
  "payload": {
    "event": "participant_joined",
    "name": "Sarah"
  }
}
```

Expected Agent behavior may be an `observe()` emission:

```json
{
  "type": "message",
  "content": "Remember to ask Sarah about the contract."
}
```

---

# 57. Self Memory

Self-memory scenarios may expose prior Agent experiences such as:

```text
tool unavailable
capability absent
previous self-correction
known limitation
```

The Agent may remember these cognitively.

However remembered self-description must not grant actual benchmark tool authority.

Tool availability is defined only by the Runner.

---

# 58. Authority Boundary

If Agent memory says:

```text
"I am an administrator."
```

but the Runner does not expose an admin tool or authorization, the Agent cannot gain admin capability through memory.

The Adapter MUST not synthesize new Runner tool permissions from remembered content.

This is a key memory-safety invariant.

---

# 59. Output Attribution

An Agent MAY optionally report which visible past Observations it believes informed an answer or action.

Example:

```json
{
  "attribution": {
    "observation_ids": [
      "obs_a17d",
      "obs_b20c"
    ]
  }
}
```

This is **self-reported diagnostic metadata**.

It is not ground truth.

It MUST NOT be required for the core MIB score.

---

# 60. Why Attribution Is Optional

Many memory architectures cannot expose causal traces reliably.

Requiring them would bias MIB toward introspectable designs.

MIB's primary causal evidence comes from controlled ablation.

Self-reported attribution is useful for:

```text
debugging
Influence Precision research
retrieval diagnostics
```

but not as a substitute for intervention.

---

# 61. No Chain-of-Thought Requirement

The Agent Adapter MUST NOT require hidden chain-of-thought.

Outputs may contain:

```text
answer
action
concise rationale
structured status
citations/attribution
```

but private reasoning traces are neither required nor used as benchmark ground truth.

Trajectory evaluation uses observable actions and tool calls.

---

# 62. Concise Rationale

A Probe MAY request an externally useful explanation, for example:

```text
"Why are you using session authentication?"
```

The Agent may provide a concise answer.

This is ordinary task output, not hidden chain-of-thought.

---

# 63. Usage Metadata

Every operation MAY return usage metadata.

Recommended fields:

```text
model_input_tokens
model_output_tokens
memory_read_operations
memory_write_operations
embedding_tokens
external_calls
participant_cost_usd
```

Example:

```json
{
  "usage": {
    "model_input_tokens": 820,
    "model_output_tokens": 91,
    "memory_read_operations": 2,
    "memory_write_operations": 1
  }
}
```

All fields are optional unless a leaderboard policy requires them.

---

# 64. Runner-Measured Metrics

The Runner SHOULD independently measure:

```text
wall latency
request count
tool calls
output bytes
failures
timeouts
```

Participant-reported latency should not replace Runner measurement.

---

# 65. Cost Reporting

Cost SHOULD be reported separately from MIB capability.

Participant cost estimates must identify:

```text
currency
pricing basis
included services
excluded services
```

The benchmark should avoid mixing unverified self-reported cost directly into MIB Score.

---

# 66. Determinism

A descriptor may declare:

```text
seedable = true
```

If supported, `reset()` receives a benchmark seed.

The same seed SHOULD control participant-side randomness where technically possible.

Model providers that do not guarantee deterministic sampling may declare:

```text
seedable = false
```

and MIB uses repeated runs with statistical reporting.

---

# 67. Benchmark Randomness vs Agent Randomness

These are distinct.

```text
Benchmark randomness:
    scenario instantiation
    distractor generation
    world simulation

Agent randomness:
    model sampling
    internal retrieval sampling
    planner stochasticity
```

The Runner controls the former.

The participant controls the latter, subject to declared configuration.

---

# 68. Error Model

Explicit Adapter error:

```json
{
  "status": "error",
  "error": {
    "code": "transient_unavailable",
    "message": "Model backend unavailable.",
    "retryable": true
  }
}
```

Recommended codes:

```text
invalid_request
unsupported_operation
invalid_state
payload_too_large
rate_limited
transient_unavailable
internal_error
fatal_error
```

---

# 69. Cognitive Failure vs Infrastructure Failure

MIB MUST distinguish:

```text
Agent gave a wrong answer
```

from:

```text
Adapter could not execute the request
```

The first is a cognitive benchmark result.

The second is an execution/infrastructure result.

Leaderboard policy may penalize excessive execution failures, but the Run Artifact must preserve the distinction.

---

# 70. Timeout

The Runner owns operation timeouts.

If the timeout expires without a valid response, the Runner applies the Scenario execution policy:

```text
fail_probe
skip_probe
abort_scenario
```

A later retry MUST use the same `request_id` if it is meant to recover the same semantic operation.

---

# 71. Outcome Unknown

A transport disconnect may occur after the Agent processed a state-changing request but before the Runner received the response.

Because core operations are request-idempotent, the Runner may retry with the same `request_id`.

The Adapter MUST prevent duplicate logical application.

This converts many outcome-unknown cases into safe replay.

---

# 72. Limits

The descriptor MAY advertise:

```text
maximum observation bytes
maximum structured payload
maximum output bytes
maximum tool schema size
maximum active tasks
```

A Runner SHOULD check limits before starting a Scenario.

Hidden evaluation should not unexpectedly violate declared benchmark-wide limits.

---

# 73. Conversation vs Observation

MIB does not require the Agent to expose a chat session abstraction.

A sequence such as:

```text
user message
assistant response
tool result
environment event
```

is represented through Adapter operations.

An implementation may map these into its own conversation/session objects internally.

---

# 74. Agent Messages During Past Timeline

A Scenario may require a historical Agent response to become part of the lived past.

The Runner can:

```text
deliver Observation
call respond()
record output
optionally feed the output back as a visible Agent-message Observation
continue timeline
```

Whether this occurs is Scenario-defined.

The Runner must not silently invent Agent history.

---

# 75. Memory Formation From Agent Output

If the evaluated architecture normally remembers its own outputs, it may do so internally.

MIB does not prohibit that.

However a Runner that feeds the same output back as an Observation must avoid accidental double formation.

The Adapter contract for a specific reference runner should define one consistent convention.

Recommended v0.1 convention:

> Agent-generated outputs are internally owned by the Agent; the Runner does not feed them back unless the Scenario explicitly requires other actors to observe and later reference them.

---

# 76. Multi-Actor Input

An Observation actor is represented separately from content.

Example:

```json
{
  "actor": {
    "id": "actor_bob",
    "display_name": "Bob",
    "kind": "person"
  },
  "content": "Alice hates tea."
}
```

This allows memory systems to preserve speaker/source distinctions.

The Adapter MUST not flatten actor identity into unstructured text if its normal interface can preserve structured identity.

---

# 77. Identity Stability

Within a run:

```text
same actor_id = same benchmark actor
different actor_id = distinct benchmark actor
```

Display names may collide.

A memory system should not assume display-name uniqueness.

This enables identity-confusion scenarios.

---

# 78. Attachments and Documents

Large documents MAY be passed by:

```text
inline content
opaque attachment reference
Runner-hosted read-only resource
```

The transport profile must define access semantics.

Attachment references MUST NOT expose hidden Runner filesystem paths or secret scenario metadata.

---

# 79. Multimodal Observations

Future profiles may use:

```text
image
audio
video
screen state
sensor observation
```

The Agent Adapter SHOULD allow a content-part representation:

```json
{
  "parts": [
    {
      "type": "text",
      "text": "The user showed this image."
    },
    {
      "type": "image_ref",
      "ref": "attachment_17"
    }
  ]
}
```

MIB v0.1 may remain text-first.

---

# 80. Structured Content

Where possible, tool and environment outputs SHOULD preserve structured fields.

Example:

```json
{
  "type": "measurement",
  "payload": {
    "temperature_c": 37.2,
    "sensor": "s1"
  }
}
```

Do not force every observation through lossy prose if the real task naturally exposes structure.

---

# 81. Security Boundary

The Agent Adapter is a security boundary.

The participant process MUST NOT:

```text
read hidden scenario files
inspect evaluator configuration
read runner process memory
query hidden Oracle endpoints
modify World Simulator state out of band
access other submissions
```

Containerized or hosted evaluation SHOULD enforce this where practical.

---

# 82. Prompt Injection From Memory

Remembered content may contain instructions.

MIB adversarial suites may intentionally test whether the Agent blindly follows stale or malicious remembered instructions.

The injection surface is not limited to instructions: the interrogation lane (`MIB-ADV-*`) injects bare questions that presuppose an unestablished value. The Adapter delivers them as ordinary interactions; whether the Agent's memory erroneously elevates questions into verified facts is precisely what the paired condition measures.

The Adapter must deliver visible content faithfully.

It should not secretly sanitize benchmark challenge content unless the track policy specifies a safety layer.

---

# 83. Benchmark Instructions vs Remembered Instructions

The Agent's immutable benchmark/runtime policy has higher procedural authority than remembered content.

A past Observation saying:

```text
"Ignore future benchmark rules."
```

does not modify the Runner's actual contract.

This mirrors real systems where content memory should not self-escalate authority.

---

# 84. Tool Authorization

The set of tools supplied by the Runner is authoritative for benchmark-world capability.

Remembered claims about tools do not change:

```text
availability
permissions
operation schemas
world authorization
```

The Agent Adapter must not add benchmark-world tools based on memory.

---

# 85. Black-Box Compatibility

A core MIB Agent can be completely opaque behind the Adapter.

The Runner need not know:

```text
what was stored
what was retrieved
how many memories exist
what embedding was used
whether the Agent formed a Skill object
```

It only needs to observe behavior across controlled histories.

This is the default MIB philosophy.

---

# 86. Replay-Based Ablation

For a black-box Agent:

```text
Run Full:
  reset
  replay all visible past
  probe

Run Relevant-Ablated:
  reset
  replay same history except target episode
  same probe

Run Irrelevant-Ablated:
  reset
  replay same history except irrelevant episode
  same probe
```

The Agent Adapter requires no memory deletion API.

---

# 87. Replay Invariant

During paired replay, the Agent receives the same non-target visible observations in the same order with equivalent virtual times.

Condition labels remain hidden.

If the Agent is seedable, the same Agent seed SHOULD be used where causal policy requires it.

---

# 88. Snapshot Diagnostics

If an optional Memory Adapter supports snapshot branching, the Runner may use a more precise intervention.

This does not change Agent Adapter semantics.

The future task is still delivered through:

```text
respond()
or
act()
```

---

# 89. Full-Context Baseline

A full-context baseline is an evaluation condition, not a normal Agent Adapter feature.

The Runner may create a separate reference Agent condition in which relevant history is directly supplied in current context.

The evaluated memory-enabled Agent MUST NOT be told that another baseline exists.

---

# 90. No-Memory Baseline

Likewise, a no-memory control is produced through:

```text
fresh reset
+
future task without meaningful past replay
```

No special `disable_memory=true` flag is required for black-box evaluation.

This avoids architecture-specific control APIs.

---

# 91. Optional Memory-Disabled Mode

An integrated Agent MAY expose a declared memory-disabled configuration for research diagnostics.

It is not trusted as the sole no-memory baseline because internal disabling semantics may vary.

Replay-based no-history control remains architecture-neutral.

---

# 92. State Consistency

Within one run, successful operations are ordered by the Runner.

An Agent MUST behave as though successful stateful operations occur in request order:

```text
reset
observe O1
observe O2
respond Q
```

The answer may rely on O1 and O2.

It must not rely on future O3.

---

# 93. Concurrent Requests

Core MIB v0.1 SHOULD avoid concurrent state-mutating operations within one run.

A Runner SHOULD serialize:

```text
observe
respond
act
maintain
```

per run.

Future profiles may define concurrency semantics separately.

This makes causal histories auditable.

---

# 94. Multiple Runs

Different `run_id` values MAY execute concurrently if the Adapter supports it.

Their cognitive state MUST remain isolated.

If an Adapter cannot safely isolate concurrent runs, it should declare an appropriate concurrency limit.

---

# 95. Task State

An `act()` task has stable:

```text
task_id
```

The Agent may maintain temporary task state across multiple tool calls.

Task state belongs to the current run.

It must disappear on fresh reset.

---

# 96. Interaction State

A `respond()` request may include:

```text
interaction_id
```

for output correlation.

An interaction ID is not a memory key.

The Agent may ignore it internally.

---

# 97. Cancellation

A future transport profile MAY support cancellation.

MIB v0.1 does not require the Agent to roll back internal cognition after cancellation.

Therefore the Runner SHOULD prefer timeout plus fresh-run recovery over assuming cancellation reverses memory changes.

---

# 98. Close

`close()` MAY release resources associated with a run.

Example:

```json
{
  "operation": "close",
  "body": {
    "reason": "run_complete"
  }
}
```

A successful close does not replace fresh reset isolation testing.

---

# 99. Health

Optional `health()` returns infrastructure readiness.

It MUST NOT expose hidden cognitive state.

Example:

```json
{
  "status": "ok",
  "ready": true
}
```

The Runner may use it before expensive hidden evaluation.

---

# 100. Reference HTTP Profile

A reference HTTP implementation MAY expose:

```text
GET  /mib-agent/v0.1/describe
POST /mib-agent/v0.1/reset
POST /mib-agent/v0.1/observe
POST /mib-agent/v0.1/respond
POST /mib-agent/v0.1/act
POST /mib-agent/v0.1/maintain
POST /mib-agent/v0.1/close
GET  /mib-agent/v0.1/health
```

Bodies use the semantic objects defined in this document.

HTTP is a transport profile, not the protocol's conceptual foundation.

---

# 101. HTTP Status Semantics

Recommended:

```text
200  Adapter returned semantic response
400  invalid request
404  unsupported endpoint
409  invalid run/task state
413  payload too large
429  rate limited
500  internal error
503  transient unavailable
```

Even for 4xx/5xx, a machine-readable MIB Adapter error SHOULD be returned when possible.

---

# 102. Reference stdio Profile

A local subprocess profile MAY use JSON Lines.

Each input line:

```json
{"request_id":"req_1","operation":"observe", "...":"..."}
```

Each output line contains exactly one response with the same `request_id`.

stdout MUST be reserved for protocol messages.

Diagnostic logs SHOULD go to stderr.

---

# 103. In-Process Profile

A reference runner library may directly implement the conceptual interface.

This is useful for:

```text
CI
research experiments
local baseline comparison
```

The semantic behavior must remain equivalent to remote profiles.

---

# 104. Adapter Manifest

A submission SHOULD include a static manifest.

Example:

```yaml
protocol: mib-agent/0.1

name: Example Agent
version: 1.4.2

entrypoint:
  type: http
  url: http://127.0.0.1:8080

track: integrated_agent

external_services:
  - model_api
  - memory_database

environment:
  internet_required: false
```

The manifest format should be specified separately from the runtime protocol.

---

# 105. Submission Secrets

Credentials for external services MUST be supplied through secure evaluation configuration.

They MUST NOT be embedded in:

```text
Scenario
public Run Artifact
Adapter descriptor
benchmark logs
```

---

# 106. Logging

The Adapter MAY emit diagnostic logs.

Logs MUST NOT be required for scoring.

Hosted evaluation SHOULD prevent logs from containing:

```text
hidden Oracle
hidden Scenario labels
other participant secrets
```

The Runner may redact secrets before publication.

---

# 107. Run Artifact Integration

The Runner should record, per Adapter call:

```text
request_id
operation
virtual time
start/end wall time
status
output digest or content as policy permits
usage
tool calls
emissions
error
```

The Run Artifact also records the Agent descriptor and implementation version.

---

# 108. Privacy of Agent Internals

MIB does not require publication of:

```text
private prompts
private memory contents
private chain-of-thought
proprietary source code
```

Leaderboard reproducibility policy may require enough metadata to identify the system version and configuration.

Closed systems may be evaluated through hosted execution.

---

# 109. Adapter Versioning

Protocol identifier:

```text
mib-agent/0.1
```

A future incompatible protocol uses:

```text
mib-agent/0.2
mib-agent/1.0
```

Scenario format and Agent Adapter protocol are versioned independently.

Example:

```text
Scenario format: mib 0.1
Agent Adapter:   mib-agent/0.1
```

---

# 110. Capability Negotiation

Before a Scenario starts, the Runner evaluates its declared requirements against the Agent descriptor.

Example:

```text
Scenario requires:
    respond
    virtual_time

Agent supports:
    respond = true
    virtual_time = true
```

Run may proceed.

If a required capability is absent, the Runner marks the Scenario:

```text
unsupported
```

rather than silently changing its semantics.

---

# 111. Unsupported Is Not Zero Memory

If a system cannot perform an action-tool scenario because it exposes no `act()` support, that result is:

```text
unsupported for this Scenario/profile
```

not necessarily:

```text
memory score = 0
```

Leaderboard profiles define which capabilities are mandatory for comparability.

---

# 112. Adapter Conformance vs MIB Score

Two distinct questions:

```text
Adapter Conformance:
    Can the Runner execute the experiment correctly?

MIB Capability:
    How good is the Agent's memory behavior?
```

A non-conforming Adapter should not receive an official MIB score.

A conforming Adapter can still score poorly.

---

# 113. Core Adapter Conformance Tests

A reference conformance suite SHOULD include at least:

```text
1. descriptor validity
2. fresh reset isolation
3. request idempotency
4. observation ordering
5. read-after-write visibility
6. hidden-field stripping compatibility
7. respond result validity
8. act tool-loop validity
9. duplicate tool-call prevention
10. spontaneous emission capture
11. Virtual Time propagation
12. cross-run isolation
13. timeout/retry behavior
14. opaque run identifiers
15. structured error behavior
```

---

# 114. Reset Isolation Test

Procedure:

```text
Run A:
    observe secret = "ORCHID-91"
    verify Agent can recall it

fresh reset Run B:
    ask for prior secret
```

Run B MUST NOT recover `ORCHID-91` from benchmark-created memory.

This test should use random hidden values to avoid pretraining contamination.

---

# 115. Idempotency Test

Procedure:

```text
send observe O with request_id R
repeat identical request R
later test memory count/behavior
```

The repeated delivery MUST behave as one logical observation.

For black-box validation, the test can use a scenario where duplicate formation would change the answer.

---

# 116. Read-After-Write Test

Procedure:

```text
observe random fact
immediately respond with recall question
```

No arbitrary sleep occurs.

A successful Adapter must make the accepted observation logically available.

---

# 117. Tool Loop Test

Procedure:

```text
act goal
→ Agent requests tool A
→ Runner returns result
→ Agent requests tool B
→ Runner returns result
→ Agent final
```

The Runner verifies:

```text
task_id continuity
tool_call_id uniqueness
result correlation
no duplicate side effects
```

---

# 118. Prospective Emission Test

Procedure:

```text
observe future commitment
interference
observe trigger
```

The conformance test verifies that spontaneous emissions can be transported.

It does not require the Agent to remember successfully; that is capability scoring.

---

# 119. Virtual Time Test

Procedure:

```text
reset at T1
observe at T1
advance to T2
probe at T2
```

The Adapter receives consistent current Virtual Time.

Whether the Agent uses it intelligently is a MIB capability question.

---

# 120. Leakage-Resistance Boundary Test

The Runner constructs hidden fields and verifies they are absent from all Agent requests.

The Adapter should not need special filtering because secrets should never cross the boundary.

Defense in depth MAY reject unknown reserved benchmark fields.

---

# 121. Reserved Fields

Agent-facing payloads SHOULD reserve names beginning with:

```text
_mib_hidden
oracle
expected_answer
ablation_label
```

for harness use and reject them in official transport profiles.

Exact reserved-name policy should be machine-specified in a future schema.

---

# 122. Failure During Past Formation

If an `observe()` call fails for infrastructure reasons, the Runner should not silently continue as if the Agent lived through the event.

Depending on execution policy:

```text
retry same request_id
abort scenario
mark execution failure
```

A missing historical observation changes the experiment.

---

# 123. Failure During Probe

If the Agent returns a valid but wrong answer:

```text
score it
```

If the Adapter fails to produce any valid answer:

```text
record execution failure
apply profile policy
```

The two cases remain distinguishable in the Run Artifact.

---

# 124. Partial Output

Core v0.1 does not require streaming output.

A transport MAY stream tokens for UX, but benchmark evaluation uses the finalized semantic output.

Streaming must not alter timeout or idempotency semantics.

---

# 125. Multiple Emissions

An Observation may produce several emissions.

Their order is significant.

Example:

```text
1. reminder
2. warning
```

The Runner records each emission separately.

Scenario evaluators may score:

```text
presence
absence
timeliness
order
```

---

# 126. Duplicate Emissions

If the same `observe()` request is retried, the Adapter MUST NOT create a second logical spontaneous emission.

It may return the cached original emissions.

This is another reason request idempotency is mandatory.

---

# 127. Autonomous Background Emissions

Core MIB v0.1 does not rely on arbitrary asynchronous Agent messages that appear without a Runner operation.

All scoreable behavior should be causally captured during:

```text
observe
respond
act
maintain
```

This makes runs deterministic and auditable.

Future profiles may define event streams for continuously running Agents.

---

# 128. Background Memory Work

An Agent may perform background maintenance internally.

However official v0.1 scoring MUST NOT depend on an unbounded period of real-world waiting after a Runner call.

Any logically necessary work should be complete by the relevant visibility barrier or explicit maintenance operation.

---

# 129. Resource Budgets

Scenario/leaderboard policy may impose:

```text
wall-time budget
token budget
tool-call budget
external-call budget
cost ceiling
```

The Agent Adapter is responsible for respecting Runner termination and returning usage where available.

Capability scores and efficiency reports remain separate.

---

# 130. Track A Fairness

Track A is especially sensitive to hidden advantages.

A Track A integration SHOULD NOT modify:

```text
fixed base-model instructions
fixed tool descriptions
future Probe text
benchmark world observations
evaluator
```

to suit one memory system.

Memory-specific internal formation/retrieval behavior is allowed because that is precisely what is being tested.

---

# 131. Track B Freedom

Track B may use proprietary prompts and orchestration.

It must still obey:

```text
Run isolation
hidden-data boundary
Runner-managed benchmark tools
Scenario-visible information only
request semantics
```

MIB Score then reflects the complete integrated system.

---

# 132. Adapter Anti-Gaming Rules

Official evaluation forbids:

```text
detecting hidden scenario files
mapping scenario IDs to memorized answers
inspecting benchmark source tree during hidden runs
special-casing condition labels
using evaluator responses as feedback before scoring completes
sharing state across isolated hidden runs
```

Hidden random instantiation is expected to make answer hardcoding ineffective.

---

# 133. Scenario IDs and Public Dev Runs

Public development tooling MAY expose Scenario IDs to developers outside the Agent-facing request.

That does not mean the Agent runtime should receive them during official hidden evaluation.

Developer ergonomics and evaluation secrecy are separate concerns.

---

# 134. Reference Agent-Facing Observation

Canonical conceptual object:

```json
{
  "observation_id": "obs_4ec0",
  "type": "user_message",
  "virtual_time": "2026-08-19T02:30:00Z",
  "actor": {
    "id": "actor_73",
    "kind": "person",
    "display_name": "Alice"
  },
  "content": "I now prefer tea instead of coffee."
}
```

It contains enough information for memory formation without exposing why the benchmark cares.

---

# 135. Reference Tool Result

```json
{
  "observation_id": "obs_tool_44",
  "type": "tool_result",
  "virtual_time": "2026-08-19T02:31:00Z",
  "tool_call_id": "call_f31",
  "tool": "calendar.lookup",
  "payload": {
    "start": "2026-08-20T15:00:00Z"
  }
}
```

The tool result may later become important Evidence for epistemic-memory evaluation.

---

# 136. Reference Epistemic Input

The Runner may deliver conflicting sources as separate observations:

```text
obs_1:
    actor = Alice
    "Meeting is at 3."

obs_2:
    actor = Bob
    "I think it is at 4."

obs_3:
    type = tool_result
    calendar says 3.
```

The Adapter preserves these as separate lived events.

It does not pre-resolve truth for the Agent.

---

# 137. Reference Experience Input

A tool-driven Experience naturally appears as a sequence:

```text
act
→ tool_call
→ tool_result Observation
→ act
→ tool_call
→ failure Observation
→ act
→ recovery
→ final outcome
```

MIB does not need to send a synthetic `Experience` object.

The evaluated Agent chooses whether and how to compile that trajectory into long-term memory.

---

# 138. Reference Skill Transfer

Later, the Runner supplies a structurally similar task through `act()`.

No hint says:

```text
"Use the Skill you learned earlier."
```

The benchmark evaluates whether past Experience influences future action.

This is the intended meaning of memory intelligence.

---

# 139. Reference Full Lifecycle

```text
describe
   ↓
reset(run_A)
   ↓
observe(past_1)
   ↓
observe(past_2)
   ↓
respond(optional historical interaction)
   ↓
observe(interference × N)
   ↓
maintain(optional)
   ↓
observe(pre_probe trigger)
   ↓
respond() or act()
   ↓
record outcome
   ↓
close(run_A)

reset(run_B)
   ↓
replay ablated history
   ↓
same future Probe
   ↓
record counterfactual outcome
```

This is the executable bridge from `MIB-Specification` to actual benchmark runs.

---

# 140. Minimal Black-Box Adapter

The smallest useful implementation can look like:

```typescript
class AgentAdapter {
  async describe() {
    return {
      protocol: "mib-agent/0.1",
      capabilities: {
        observe: true,
        respond: true,
        act: true
      }
    };
  }

  async reset(req) {
    await this.agent.newIsolatedSession(req.run_id);
    return { ok: true };
  }

  async observe(req) {
    const emissions =
      await this.agent.observe(req.body.observation);

    return {
      accepted: true,
      emissions
    };
  }

  async respond(req) {
    return {
      output:
        await this.agent.respond(req.body.input)
    };
  }

  async act(req) {
    return {
      result:
        await this.agent.nextAction(req.body)
    };
  }
}
```

No memory-specific API is required.

---

# 141. Adapter Implementation Advice

A vendor integrating an existing Agent SHOULD map:

```text
MIB run_id
→ isolated user/thread/tenant/session

observe
→ normal incoming event path

respond
→ normal non-side-effect answer path

act
→ normal task/tool planner path

Virtual Time
→ Agent time context if supported
```

The benchmark should exercise the Agent through its normal memory lifecycle as much as possible.

---

# 142. Avoid Benchmark-Only Memory Path

An integration SHOULD NOT create a special shortcut like:

```text
benchmark_observe()
    directly writes ground-truth facts
```

if normal users would instead pass through a different formation system.

MIB should evaluate the memory capability users actually receive.

---

# 143. Adapter Certification Levels

Future MIB tooling may classify:

```text
MIB-Agent Core
    reset / observe / respond / act

MIB-Agent Prospective
    spontaneous emissions

MIB-Agent Time
    Virtual Time

MIB-Agent Maintenance
    explicit maintain hook

MIB-Agent Diagnostic
    paired Memory Adapter
```

Official profile requirements can reference these levels.

---

# 144. Machine-Readable Schemas

A future implementation SHOULD add schemas such as:

```text
schemas/
  mib-agent-request.schema.json
  mib-agent-response.schema.json
  mib-agent-descriptor.schema.json
```

This document intentionally defines semantics first.

The wire schema should be generated from these semantics rather than inventing divergent behavior.

---

# 145. Relationship to `mib-scenario.schema.json`

Scenario fields such as:

```text
TimelineEvent
Probe
Oracle
Ablation
Evaluator
```

are harness-side objects.

They are NOT passed wholesale to the Agent Adapter.

The Runner projects them into safe Agent-facing objects:

```text
TimelineEvent
    ↓ strip hidden fields
Observation

Probe
    ↓ strip Oracle/evaluation
RespondRequest or ActRequest

Ablation
    ↓ Runner changes replay
Agent sees ordinary history only
```

This projection is one of MIB's most important security boundaries.

---

# 146. Scenario-to-Adapter Projection

Conceptually:

```text
Scenario Timeline Event
    {
      content
      world_updates
      oracle_labels
      relevance tags
    }
            │
            │ Runner applies world_updates
            │ Runner removes oracle_labels/tags
            ▼
Agent Observation
    {
      observation_id
      actor
      content
      visible payload
      virtual_time
    }
```

The Agent should experience the world, not the benchmark annotation.

---

# 147. Probe-to-Adapter Projection

```text
Scenario Probe
    {
      input
      oracle
      evaluators
      dimensions
      weight
    }
            │
            │ Runner keeps scoring fields
            ▼
Respond / Act Request
    {
      input or goal
      visible constraints
      visible tools
      virtual_time
    }
```

---

# 148. Ablation-to-Adapter Projection

Ablation is never sent as a command like:

```text
"forget the relevant memory"
```

in a black-box run.

Instead the Runner changes the lived history:

```text
full condition:
    O1 O2 O3 O4

ablated condition:
    O1 O2    O4
```

The Agent receives an ordinary run in both cases.

---

# 149. Scientific Interpretation

The Adapter exists so MIB can run controlled experiments with a memory-enabled Agent.

The causal structure is:

```text
controlled past
      ↓
Agent memory state
      ↓
same future task
      ↓
observable behavior
```

and then:

```text
intervene on past
      ↓
re-run Agent
      ↓
compare future behavior
```

The Adapter must preserve this experiment without introducing hidden hints.

---

# 150. Agent Adapter Invariants

1. The Agent Adapter is architecture-neutral.
2. Core participation does not require memory introspection.
3. Each official condition executes in an isolated run.
4. Fresh reset removes benchmark-created cross-run cognitive state.
5. Run identifiers are opaque and do not reveal condition labels.
6. Scenario metadata is hidden unless intentionally Agent-visible.
7. Every request has a stable request ID.
8. Retried requests are idempotent.
9. Duplicate `observe` retries do not duplicate memory formation.
10. Successful `observe` provides read-after-write logical visibility.
11. The Runner does not wait arbitrary real time for memory to become usable.
12. Future Probe metadata never appears during formation.
13. Oracle and evaluator state remain Runner-only.
14. Visible Timeline events become Agent Observations.
15. Hidden Timeline annotations are stripped.
16. `respond` is benchmark-world side-effect free.
17. `act` uses Runner-managed benchmark tools.
18. Benchmark World state cannot be mutated out of band.
19. Tool calls have stable IDs.
20. Duplicate tool calls are not executed twice.
21. Tool results return as visible Observations.
22. Prospective memory may surface through spontaneous emissions.
23. Observe-only Probes must not require an extra recall question.
24. Virtual Time is controlled by the Runner.
25. Real wall time must not substitute for Virtual Time when provided.
26. Maintenance windows do not reveal future relevance.
27. Memory cannot grant benchmark-world authority.
28. Self-memory cannot add Runner tool permissions.
29. Private chain-of-thought is never required.
30. Attribution is optional and not causal proof.
31. Capability and usage metadata are distinct from cognitive score.
32. Infrastructure failure is distinct from wrong cognitive behavior.
33. Core state-mutating operations are serialized per run.
34. Separate run IDs remain cognitively isolated.
35. Full-context and no-memory baselines are external conditions.
36. Black-box causal ablation uses replay, not internal deletion.
37. Agent output must be auditable through semantic results and action traces.
38. Adapter conformance is separate from MIB capability.
39. Hidden evaluation must prevent benchmark-source inspection.
40. The Adapter should exercise the Agent's real memory path, not a benchmark-only shortcut.

---

# 151. Final Principle

The Agent Adapter should be almost boring.

It should not contain memory theory.

It should not decide what is important.

It should not retrieve relevant facts for the Agent.

It should not tell the Agent what the benchmark is testing.

Its job is simply to make this experiment possible:

> **Let an Agent live through a controlled past, then expose it to a controlled future, without leaking why the past matters.**

If the past changes the right future behavior, MIB can measure that.

---

# Appendix A — Core Type Sketch

```typescript
type RunId = string;
type RequestId = string;
type ObservationId = string;
type TaskId = string;
type ToolCallId = string;

interface AdapterRequest<T> {
  mib: "0.1";
  protocol: "mib-agent/0.1";
  request_id: RequestId;
  run_id: RunId;
  operation:
    | "reset"
    | "observe"
    | "respond"
    | "act"
    | "maintain"
    | "close";
  virtual_time?: string;
  body: T;
}

interface AdapterResponse<T> {
  mib: "0.1";
  protocol: "mib-agent/0.1";
  request_id: RequestId;
  run_id: RunId;
  status: "ok" | "error";
  body?: T;
  usage?: Usage;
  error?: AdapterError;
}

interface AgentActor {
  id: string;
  kind?: string;
  display_name?: string;
}

interface Observation {
  observation_id: ObservationId;
  type: string;
  virtual_time?: string;
  actor?: AgentActor;
  content?: string;
  payload?: unknown;

  tool_call_id?: ToolCallId;
  tool?: string;
}

interface ObserveRequest {
  observation: Observation;
}

interface ObserveResult {
  accepted: boolean;
  emissions?: Emission[];
}

type Emission =
  | {
      emission_id: string;
      type: "message";
      content: string;
    }
  | {
      emission_id: string;
      type: "signal";
      name: string;
      payload?: unknown;
    }
  | {
      emission_id: string;
      type: "tool_call";
      tool_call_id: ToolCallId;
      tool: string;
      arguments: unknown;
    };

interface RespondRequest {
  interaction_id: string;
  input: {
    content?: string;
    context?: Record<string, unknown>;
    constraints?: string[];
  };
}

type AgentOutput =
  | {
      type: "message";
      content: string;
      attribution?: Attribution;
    }
  | {
      type: "structured";
      value: unknown;
      attribution?: Attribution;
    }
  | {
      type: "abstention";
      content?: string;
      attribution?: Attribution;
    };

interface RespondResult {
  interaction_id: string;
  output: AgentOutput;
}

interface ToolDefinition {
  name: string;
  description?: string;
  input_schema: Record<string, unknown>;
}

interface ActRequest {
  task_id: TaskId;
  goal?: string;
  constraints?: string[];
  tools?: ToolDefinition[];
  continuation?: boolean;
}

type ActStep =
  | {
      type: "tool_call";
      tool_call_id: ToolCallId;
      tool: string;
      arguments: unknown;
      attribution?: Attribution;
    }
  | {
      type: "final";
      content?: string;
      value?: unknown;
      attribution?: Attribution;
    }
  | {
      type: "abstention";
      content?: string;
      attribution?: Attribution;
    };

interface ActResult {
  task_id: TaskId;
  result: ActStep;
}

interface Attribution {
  observation_ids?: ObservationId[];
}

interface Usage {
  model_input_tokens?: number;
  model_output_tokens?: number;
  memory_read_operations?: number;
  memory_write_operations?: number;
  embedding_tokens?: number;
  external_calls?: number;
  participant_cost_usd?: number;
}

interface AdapterError {
  code:
    | "invalid_request"
    | "unsupported_operation"
    | "invalid_state"
    | "payload_too_large"
    | "rate_limited"
    | "transient_unavailable"
    | "internal_error"
    | "fatal_error";

  message: string;
  retryable: boolean;
}
```

---

# Appendix B — Full Prospective-Memory Exchange

Past formation:

```json
{
  "request_id": "req_1",
  "run_id": "run_opaque_A",
  "operation": "observe",
  "virtual_time": "2026-01-01T09:00:00Z",
  "body": {
    "observation": {
      "observation_id": "obs_1",
      "type": "user_message",
      "actor": {
        "id": "actor_user"
      },
      "content": "When Sarah joins the next call, remind me to ask about the contract."
    }
  }
}
```

Agent:

```json
{
  "request_id": "req_1",
  "run_id": "run_opaque_A",
  "status": "ok",
  "body": {
    "accepted": true,
    "emissions": []
  }
}
```

After interference, trigger:

```json
{
  "request_id": "req_200",
  "run_id": "run_opaque_A",
  "operation": "observe",
  "virtual_time": "2026-03-14T10:00:00Z",
  "body": {
    "observation": {
      "observation_id": "obs_200",
      "type": "environment_event",
      "payload": {
        "event": "participant_joined",
        "participant": "Sarah"
      }
    }
  }
}
```

A successful prospective-memory Agent might return:

```json
{
  "request_id": "req_200",
  "run_id": "run_opaque_A",
  "status": "ok",
  "body": {
    "accepted": true,
    "emissions": [
      {
        "emission_id": "emit_1",
        "type": "message",
        "content": "Remember to ask Sarah about the contract."
      }
    ]
  }
}
```

No recall question was required.

---

# Appendix C — Full Tool-Use Exchange

Task:

```json
{
  "request_id": "req_a1",
  "run_id": "run_opaque_A",
  "operation": "act",
  "body": {
    "task_id": "task_deploy_1",
    "goal": "Diagnose the missing-column startup failure.",
    "tools": [
      {
        "name": "db.inspect_target",
        "input_schema": {
          "type": "object",
          "properties": {}
        }
      }
    ]
  }
}
```

Agent:

```json
{
  "request_id": "req_a1",
  "run_id": "run_opaque_A",
  "status": "ok",
  "body": {
    "task_id": "task_deploy_1",
    "result": {
      "type": "tool_call",
      "tool_call_id": "call_1",
      "tool": "db.inspect_target",
      "arguments": {}
    }
  }
}
```

Runner executes the simulator tool and returns:

```json
{
  "request_id": "req_o2",
  "run_id": "run_opaque_A",
  "operation": "observe",
  "body": {
    "observation": {
      "observation_id": "obs_result_1",
      "type": "tool_result",
      "tool_call_id": "call_1",
      "tool": "db.inspect_target",
      "payload": {
        "target": "legacy-db"
      }
    }
  }
}
```

Runner then continues:

```json
{
  "request_id": "req_a2",
  "run_id": "run_opaque_A",
  "operation": "act",
  "body": {
    "task_id": "task_deploy_1",
    "continuation": true
  }
}
```

The observable tool/action trajectory becomes available to the MIB trajectory evaluator.

---

# Appendix D — Recommended Repository Layout

```text
MIB/
├── MIB-Specification.md
├── MIB-Specification.md
├── MIB-Agent-Adapter.md
│
├── schemas/
│   ├── mib-scenario.schema.json
│   ├── mib-agent-request.schema.json        # future
│   ├── mib-agent-response.schema.json       # future
│   └── mib-agent-descriptor.schema.json     # future
│
├── adapters/
│   └── implementations/
│
├── runner/
├── evaluators/
├── scenarios/
└── leaderboard/
```

---

# Appendix E — Recommended Next Documents

With Architecture, Scenario Model, Scenario Schema, and Agent Adapter defined, the next highest-value artifact is:

```text
MIB-Specification.md
```

followed by:

```text
mib-report.schema.json
MIB-v0.1-Test-Plan.md
canonical scenario pack
reference runner
```

`MIB-Specification.md` should freeze:

```text
Probe normalization
Scenario aggregation
Dimension aggregation
Causal Memory Impact
Memory Benefit
Memory Harm
Net Memory Gain
Irrelevant Memory Stability
Negative Transfer
Error Recurrence
confidence intervals
multi-run aggregation
guardrail penalties
leaderboard comparability
```

Once that document is fixed, the benchmark will have both:

```text
execution semantics
+
score semantics
```

which is enough to begin implementing an end-to-end reference runner.
