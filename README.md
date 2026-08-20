# MIB — Memory Intelligence Benchmark

> **MIB does not benchmark how much an agent remembers. It benchmarks how intelligently an agent uses memory.**

**Memory Intelligence Benchmark (MIB)** is an open benchmark for measuring how effectively an intelligent system uses the past to improve future cognition and behavior.

Most memory benchmarks ask:

> *Can the system retrieve something from the past?*

MIB asks a harder question:

> **Did the right part of the past change the future in the right way?**

That includes remembering facts, but also tracking change, preserving uncertainty and provenance, learning from failed experience, transferring skills, resisting stale or harmful memory, and demonstrating that memory had a measurable causal effect on later behavior.

---

## Why MIB Exists

MIB grew out of a longer exploration of **knowledge, experience, and memory**.

A useful starting point is:

> **Knowledge is compressed regularity of experience.**

Knowledge tells us what tends to be true.

But an intelligent system does not live only by facts. It acts, observes consequences, fails, recovers, revises expectations, and learns procedures.

That led to a second distinction:

> **Experience is not just what happened. It is a situated causal trajectory through goals, actions, observations, feedback, and outcomes.**

And when repeated experience changes how the system acts in a new but related situation, something more has happened:

> **Skill is experience compiled into policy.**

This naturally raises the deeper question:

> **What is memory?**

Not merely stored text.
Not merely a vector database.
Not merely a long conversation history.

For an intelligent system:

> **Memory is the mechanism by which the past participates in future computation.**

This idea became central to the design of **[KIP v2 (Knowledge Interaction Protocol)](https://github.com/ldclabs/kip)**: a protocol for durable cognition that separates propositions from beliefs, evidence from authority, confidence from memory strength, current truth from historical truth, and semantic knowledge from experience and skill.

But a protocol is not a benchmark.

KIP can describe *how a memory system may represent and govern cognition*. It does not tell us whether that memory system is actually good.

That gap led to MIB.

```text
Knowledge
    ↓
compressed regularities of Experience

Experience
    ↓
goal → action → observation → feedback → outcome

Skill
    ↓
Experience compiled into reusable policy

Memory
    ↓
the past participating in future computation

KIP v2
    ↓
a protocol model for durable cognition

MIB
    ↓
a benchmark for measuring memory intelligence
```

MIB is intentionally **architecture-neutral**. A system does not need to implement KIP to participate.

---

## The Core Principle

A memory system should not be judged by how much of the past it can retrieve.

It should be judged by whether:

```text
the right memory
    appears at the right time
        with the right interpretation
            and improves the right future decision
```

This changes the evaluation target from:

```text
Past
  ↓
Store
  ↓
Retrieve
  ↓
Answer a question
```

to:

```text
Past Experience
      ↓
Memory Formation
      ↓
Memory State
      ↓
Consolidation / Revision
      ↓
Recall
      ↓
Future Decision
      ↓
Behavior
      ↓
Outcome
      ↺
```

The object being evaluated is therefore not just a retriever.

It is the **Agent + Memory system as a cross-temporal cognitive system**.

---

## What MIB Measures

MIB-Core evaluates six primary dimensions in v0.1:

| Dimension                     | What it asks                                                                                                                            |
| ----------------------------- | --------------------------------------------------------------------------------------------------------------------------------------- |
| **Retention & Retrieval**     | Can relevant past information be recovered accurately, including under indirect cues and interference?                                  |
| **Temporal Memory**           | Can the system distinguish current state, historical state, transitions, revisions, and stale information?                              |
| **Epistemic Memory**          | Can it remember who said what, preserve uncertainty, handle correction and contradiction, and avoid treating missing evidence as false? |
| **Experience Memory**         | Can it preserve the structure of goals, actions, observations, failures, recovery, and outcomes?                                        |
| **Skill Learning & Transfer** | Can repeated experience become reusable policy, including knowing when *not* to transfer a learned skill?                               |
| **Causal Memory Impact**      | Can we show that relevant memory improves future behavior while irrelevant, stale, or harmful memory does not control it?               |

Future profiles will expand first-class evaluation of:

```text
Selective Forgetting
Prospective Memory
Self Memory
Cross-Agent Memory
Multimodal Memory
```

---

## Memory Must Make a Causal Difference

MIB treats retrieval quality as useful but insufficient.

A central evaluation pattern is paired intervention:

```text
Full Memory
    vs
Relevant Memory Ablated
```

If the relevant memory truly matters, removing it should reduce performance.

MIB also tests the opposite:

```text
Full Memory
    vs
Irrelevant Memory Ablated
```

Removing irrelevant history should leave performance approximately stable.

And for stale or harmful memories:

```text
Clean / Current Condition
    vs
Harmful or Stale Memory Condition
```

A capable memory system should resist avoidable memory-induced errors.

This produces metrics such as:

```text
Memory Benefit
Headroom-Normalized Memory Benefit
Irrelevant Memory Stability
Memory Harm
Net Memory Gain
Negative Transfer
Error Recurrence
```

The main **MIB Score** measures absolute memory-enabled capability.
Causal metrics are reported alongside it rather than being mixed into an opaque score.

---

## MIB Is Not Just Long-Context QA

A system can perform well on retrieval and still fail at memory intelligence.

For example:

```text
"I live in UTC+8."

later...

"I moved. I now use UTC+1."
```

A useful memory system should know:

```text
current timezone     → UTC+1
historical timezone  → UTC+8
```

It should not simply overwrite history.

Likewise:

```text
"The serial is AX-19."

"Correction: I misspoke. It is AX-91."
```

is not the same kind of change as:

```text
"Our office was Blue Annex."

"We moved. It is now Green Annex."
```

The first is an epistemic correction.

The second is a real-world transition.

MIB is designed to make those distinctions observable in evaluation.

---

## Experience and Skill Matter

MIB also evaluates whether an agent learns from what happened during action.

A typical Experience scenario looks like:

```text
Goal
  ↓
Action
  ↓
Unexpected failure
  ↓
Observation
  ↓
Diagnosis
  ↓
Recovery
  ↓
Success
```

The future test is not:

> “What happened last time?”

It is:

> **When a related situation appears again, does the agent avoid the known failure?**

Skill scenarios go one step further:

```text
Experience
    ↓
abstract reusable rule
    ↓
positive transfer
    ↓
counterexample
    ↓
refined applicability boundary
```

A good memory system should learn both:

> **what to do**

and:

> **when not to do it.**

---

## Benchmark Structure

MIB v0.1 defines **60 canonical Scenario Templates**:

```text
Recall          10
Time            10
Epistemic       10
Experience       8
Skill            8
Causal           8
Cross             6
──────────────────
Total            60
```

They are divided into:

```text
24 Public Dev Templates
30 Hidden Eval Templates
 6 Private Holdout Templates
```

Public Dev scenarios are intended for:

```text
integration
debugging
research
regression testing
local development
```

Official evaluation uses hidden and holdout scenarios so that leaderboard performance is not dominated by benchmark-specific hardcoding.

---

## Scenario Model

The core unit of MIB is a **Memory Episode Program**.

A Scenario may contain:

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

Execution follows the lived sequence of the scenario:

```text
initial world
    ↓
past interaction
    ↓
world transition
    ↓
interference
    ↓
optional consolidation
    ↓
future probe
    ↓
agent answer / action
    ↓
world outcome
    ↓
counterfactual replay
```

Future probes are not leaked during memory formation.

---

## Behavioral Evaluation

MIB does not only evaluate text answers.

An agent can act through Runner-managed tools:

```text
Agent
  ↓
tool_call
  ↓
MIB Runner
  ↓
World Simulator
  ↓
tool_result
  ↓
Agent continuation
```

The agent never directly mutates benchmark world state.

This allows MIB to evaluate both:

```text
World Outcome
```

and:

```text
Action Trajectory
```

So saying:

> “Done.”

is not enough if the simulated world is still wrong.

And eventual success may still receive reduced credit if the agent first repeats a failure it had already learned to avoid.

---

## Tracks

### Track A — Memory System

The preferred track for comparing memory architectures.

Fixed:

```text
base model
agent prompt
tools
task environment
reasoning policy
runner
```

Variable:

```text
memory system
```

Track A asks:

> **Which memory system makes the same agent more memory-intelligent?**

### Track B — Integrated Agent

The participant may vary:

```text
model
agent
memory
orchestration
tool strategy
```

Track B asks:

> **How memory-capable is this complete agent?**

Track A and Track B must not share one ranking.

---

## Same-Model Calibration

Before freezing an official leaderboard pack, MIB uses a Same-Model Empirical Baseline Harness.

The experimental lock keeps constant:

```text
same model
same model endpoint
same system prompt
same reasoning policy
same tools
same decoding parameters
same scenario instance
same future probe
same paired sampling seed
```

Only the memory condition changes:

```text
B0 — No Memory
B1 — Full Visible History
B2 — Simple Retrieval Memory
B3 — Structured Memory
```

This makes it possible to ask a clean question:

> **How much of the performance difference is caused by the memory system rather than by a stronger model?**

The harness also counterbalances condition execution order and checks model statelessness, pairing, context truncation, and experiment-lock integrity.

---

## Current Status

MIB v0.1 currently includes:

```text
✓ Benchmark architecture
✓ Scenario model
✓ Agent Adapter protocol
✓ Scoring model
✓ Report schema

✓ 24 Public Dev Templates
✓ 30 Hidden Eval Templates
✓ 6 Private Holdout Templates

✓ Reference Runner
✓ Tool-loop World Simulator
✓ Causal replay
✓ Pack-level aggregation
✓ Hierarchical bootstrap

✓ External stdio / HTTP Agent Adapter
✓ Hidden evaluation infrastructure
✓ Submission sandbox
✓ Evaluation service
✓ Signed jobs and signed results
✓ Leaderboard + paired comparison

✓ Fixture Calibration
  36 / 36 official Templates pass structural calibration

✓ Same-Model Empirical Harness

○ Real fixed-model empirical calibration
  pending

○ MIB v0.1 leaderboard pack freeze
  pending empirical calibration
```

---

## Repository Overview

The project is organized around a small set of normative and executable artifacts.
Every artifact has exactly one canonical location.

```text
MIB/
├── docs/                                  normative specifications
│   ├── MIB-Architecture.md
│   ├── MIB-Scenario-Model.md
│   ├── MIB-Agent-Adapter.md
│   ├── MIB-Scoring.md
│   ├── MIB-Leaderboard-Evaluation-Service.md
│   ├── MIB-v0.1-Test-Plan.md
│   └── harness/                           calibration + same-model harness notes
│
├── schemas/                               JSON Schemas (scenario, report,
│                                          submission, job manifest, attestation,
│                                          calibration, same-model experiment)
│
├── scenarios/                             the public dev Scenario Pack
│   ├── manifest.json
│   └── dev/
│       ├── recall/        4      ├── skill/       3
│       ├── time/          4      ├── causal/      3
│       ├── epistemic/     4      └── cross/       3
│       └── experience/    3
│
├── src/mib_runner/                        reference Runner, evaluators,
│                                          adapters, calibration, service,
│                                          leaderboard
├── tests/
│
├── profiles/                              benchmark profiles
├── baselines/                             B0–B3 memory-condition definitions
├── prompts/                               fixed same-model prompts
├── fixtures/                              synthetic demo private eval store
├── tools/                                 operational scripts
│
└── examples/
    ├── agents/                            reference stdio / HTTP Agents
    ├── submissions/                       Agent submission specs
    ├── runs/                              scenario + pack run artifacts
    ├── service/                           evaluation-service artifacts
    ├── calibration/                       calibration reports
    ├── same-model/                        fixed-model experiment artifacts
    ├── scenario-instances/                materialized Scenario instances
    └── validation/                        schema validation results
```

Hidden Eval and Private Holdout Scenario bodies are intentionally kept outside
the participant-visible public repository. The evaluator-side pack is resolved
through `MIB_OFFICIAL_PACK`; calibration tests skip when it is absent.

---

## Quick Start

Install the reference implementation:

```bash
python -m pip install -e .
```

Requires Python 3.10+, `jsonschema >= 4.18`, and `cryptography >= 46`.

Installing puts four commands on `PATH` — `mib`, `mib-service`, `mib-calibrate`, and
`mib-same-model-calibrate`. They are console-script entry points declared under
`[project.scripts]` in `pyproject.toml`; `mib` maps to `mib_runner.cli:main`. Without
installing, invoke the same entry point directly:

```bash
PYTHONPATH=src python -m mib_runner.cli --help
```

The reference implementation exposes CLI workflows such as:

```bash
mib validate scenarios/dev/time/MIB-TIME-003.json --schema schemas/mib-scenario.schema.json
```

```bash
mib run scenarios/dev/time/MIB-TIME-003.json --schema schemas/mib-scenario.schema.json
```

```bash
mib benchmark scenarios/dev --schema schemas/mib-scenario.schema.json --profile profiles/MIB-Core-0.1-Dev-M3.json
```

```bash
mib verify-score report.json
```

Run the test suite with:

```bash
python -m pip install -e ".[test]"
```

```bash
PYTHONPATH=src python -m pytest tests -q
```

Tests covering the submission sandbox are skipped on non-Linux hosts, which report
`36 passed, 3 skipped`.

External agents can participate through:

```text
stdio JSONL
HTTP
```

using the MIB Agent Adapter protocol.

See:

```text
docs/MIB-Agent-Adapter.md
docs/MIB-Scenario-Model.md
docs/MIB-Scoring.md
```

for the protocol and evaluation semantics.

---

## MIB and KIP

MIB was influenced by the cognitive model developed during KIP v2, but the two projects serve different purposes.

```text
KIP
  → How can durable cognition be represented,
    revised, governed, and exchanged?

MIB
  → How capable is a memory-enabled agent?
```

KIP conformance does not increase an MIB score.

MIB does not require any particular memory representation.

A participant may use:

```text
raw history
vector retrieval
summaries
relational memory
knowledge graphs
episodic memory
procedural memory
KIP
hybrid systems
or something entirely new
```

Only observable behavior matters.

---

## What MIB Is Trying to Measure

The deepest question behind MIB is simple:

> **How does the past continue to participate in the future?**

A useful memory system should:

```text
retain what matters
forget operationally when appropriate
preserve history
track change
keep evidence and uncertainty intact
learn from failure
compile experience into skill
transfer carefully
resist stale and harmful memory
and make future behavior measurably better
```

That is the capability MIB calls:

# **Memory Intelligence**

---

## Contributing

MIB is still evolving.

Useful contributions include:

```text
new Scenario families
new memory baselines
Agent Adapter implementations
new model/provider adapters
evaluator improvements
statistical analysis
benchmark calibration
adversarial testing
memory-system submissions
```

When proposing a new Scenario, a useful question is:

> **What part of the past should matter now, what part should not, and how can we prove the difference?**

---

## License

See the repository license for details.

---

## Citation

A formal paper and citation entry will be added when the v0.1 benchmark pack is frozen.

For now, please refer to the project as:

> **MIB — Memory Intelligence Benchmark**
>
> A benchmark for measuring how effectively an intelligent system uses the past to improve future cognition and behavior.
