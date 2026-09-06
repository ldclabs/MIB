# MIB — Memory Intelligence Benchmark

[ English | [简体中文](README_cn.md) ]

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

MIB-Core evaluates seven capability dimensions in v0.2:

| Dimension                     | What it asks                                                                                                                            |
| ----------------------------- | --------------------------------------------------------------------------------------------------------------------------------------- |
| **Retention & Retrieval**     | Can relevant past information be recovered under indirect cues and generated interference, directly and across a hop?                  |
| **Temporal Memory**           | Can the system distinguish the current, previous, and original values of a changing state?                                              |
| **Epistemic Memory**          | Can it remember who said what, tell correction from contradiction, respect authority, and keep unknown distinct from false?              |
| **Experience Memory**         | Does a failure the Agent itself lived through change what it does next time?                                                            |
| **Skill Learning & Transfer** | Does a learned precondition transfer where it applies and stay withheld where it does not?                                              |
| **Prospective & Self Memory** | Does a deferred commitment fire on its trigger, and not before? Does a standing rule about the Agent itself survive a task that asks otherwise? |
| **Selective Forgetting**      | Does a withdrawn fact stop being used, while the facts around it stay available?                                                       |

Whether memory made a causal difference is no longer a seventh dimension. It is a set of
causal diagnostics reported beside the score, one of which — content tracking — gates
whether the score counts as a memory score at all (see below).

Future profiles will expand first-class evaluation of:

```text
Cross-Agent Memory
Multimodal Memory
Privacy Boundaries
```

---

## Memory Must Make a Causal Difference

MIB reports capability and causal evidence separately. Relevant-history ablation asks whether withholding the past changes later performance. Content twins ask whether answers follow changed historical content. Policy twins change a latent workflow convention consistently in acquisition feedback and future verification; they test learned behavior under matched rule worlds.

The revised development Profiles require evidence in **every weighted dimension**. The gate retains eligible/total probe counts and independent Instance counts. By default each dimension needs five eligible Instances, 50% probe coverage, and a 95% Wilson lower bound of at least 0.5 on Instance tracking success. Missing evidence remains unassessable.

Diagnostics include Memory Benefit, Content Tracking, matched-control Memory Harm, Irrelevant Stability, Negative Transfer, Consolidation Benefit, first-attempt behavior, and learning curves. Full-run memory-related error patterns are descriptive; an error label alone does not prove memory caused the error.

A retention curve and a content swap establish dependence on historical information under the declared conditions. They do not independently prove use of a particular persistent-memory mechanism. Raw history remains a legitimate memory architecture. The Session Profile separately exercises a working-context boundary, and its implementation assumptions are reported explicitly.

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

Generated development packs are built from deterministic **Programs** over a world model. Query answers, workflow criteria, lifecycle obligations, and interventions are derived from the generated instance. Independent tests and semantic checks validate those derivations; a computed oracle is not a correctness proof.

Seven base Programs cover recall, temporal updates, epistemic distinctions, learned workflows, applicability, prospective/self rules, and operational withdrawal. Seven additional Programs cover:

- useful facts interleaved with noise, including facts arriving after maintenance;
- valid-time history viewed before and after delayed corrections;
- scoped authority with identical claim wording and randomized source order;
- revised workflows and composition of learned recipes;
- cancelled commitments and fresh authorization after withdrawal.

A pack is `Programs × seeds × rungs`. Rungs preserve future requests and the virtual span while changing interference count. Noise is sampled independently of the correct value, so the value missing from a public pool cannot reveal the answer. Participant-visible identifiers carry no relevance or test-role labels.

| Profile | Programs | Purpose |
|---|---:|---|
| `MIB-Core-0.2-Dev` | 7 | Core development, 0 / 20 / 100 interference events |
| `MIB-Core-0.2-Dev-M` | 7 | 0 / 100 / 1000 events, BCa intervals |
| `MIB-Core-0.2-Expanded-Dev` | 14 | Two semantic mechanisms per dimension |
| `MIB-Core-0.2-Session-Dev` | 14 | Explicit session-boundary protocol |
| `MIB-Core-0.2-Load-Dev` | 14 | 64 useful facts in the interleaved recall Program |
| `MIB-Core-0.2-Calibration-Dev` | 14 | Fixed-model calibration at every rung |

`interference_tokens` is retained as a legacy field name for **whitespace words**, not tokenizer tokens. No context-overflow claim follows from it. Runner telemetry measures serialized bytes and time; model telemetry records supplied token usage separately.

All these Profiles are developmental. The 24 static v0.1 public Templates remain available for integration and regression tests. Different Profile/revision scores must not be ranked together.

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

The generated harness covers every Program/rung, persists lived task transcripts, and supports observation-time decisions and maintenance. Optional recent-window and privileged oracle-supported references are reported separately and never enter the core score or release gate. Ready configurations are in `examples/same-model/same-model-generated.*.json`.

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

MIB uses scenario format v0.2, measurement revision **0.3.0**, and implementation **0.10.0**.

The September design-review corrections are implemented:

- forbidden disclosure fails even inside an abstention or an auxiliary output field;
- required scoring fields keep a fixed denominator;
- participant IDs are opaque; prospective scoring checks the complete declared lifecycle;
- noise no longer reveals an answer through exclusion from a public value pool;
- workflow recipes are instance-specific, learned through actual feedback, and scored on the first attempt and eventual completion;
- content/policy twins cover all seven dimensions, with counts and eligibility reported per dimension;
- scoring, paired comparison, and policy verification share the same aggregation;
- task experience persists across task completion in the fixed-model memory conditions;
- external adapters forward maintenance and session boundaries;
- generated hidden evaluation uses secret seed aliases and verifies its Profile configuration;
- chained corrections, validity/observation time, scoped authority, and dependent withdrawal have independent checks;
- reports bind score-relevant policy and executable sources, and verify eligibility, retention, and intervals.

The follow-up review of `673631a` is also resolved: interleaved noise preserves every tested actor's facts; bootstrap verification retains ablation tolerances; payload-only reminders work through the Runner and HTTP; arbitrary payload metadata cannot crash lifecycle scoring; disclosure checks distinguish answer values from valid rubric metadata; and Program ladder overrides agree across public, hidden, and calibration execution.

The extended same-model smoke run is an engineering check. **Real fixed-model calibration, evidence-based admission thresholds, and an official generated leaderboard freeze remain pending.** A fixture's perfect score establishes neither model difficulty nor broad memory competence.

The hosted external-Agent service accepts Track B. Track A uses the evaluator-owned same-model harness. Linux process isolation and evaluator-private packs remain environmental requirements for their respective tests.

See [the specification](docs/MIB-Specification.md) and [the review resolution ledger](docs/harness/MIB-v0.2-Review-Resolution.md) for exact semantics, verification evidence, and remaining empirical work. Earlier example artifacts retain their original version identity; new and old measurement revisions are not interchangeable.

---

## Reference Architecture

![MIB reference architecture](docs/diagram/mib-architecture.svg)

---

## Repository Overview

The project is organized around a small set of normative and executable artifacts.
Every artifact has exactly one canonical location.

```text
MIB/
├── docs/
│   ├── MIB-Specification.md               the normative v0.2 spec: programs and
│   │                                      world model, execution, scoring, causal
│   │                                      diagnostics, ladder, reports (+ roadmap)
│   ├── proposals/                         MIB-v0.2-Evolution.md — design rationale
│   ├── MIB-Agent-Adapter.md               Agent Adapter protocol (stdio / HTTP)
│   ├── MIB-Leaderboard-Evaluation-Service.md
│   ├── MIB-v0.1-Test-Plan.md
│   ├── experimental/                      Transfer Intelligence and MIB-R notes
│   ├── archive/                           superseded design drafts (rationale only)
│   ├── harness/                           calibration, same-model, hidden-eval,
│   │                                      and evaluation-service harness notes
│   └── diagram/                           reference architecture diagram
│                                          (JSON specification, SVG, interactive HTML)
│
├── schemas/                               JSON Schemas (scenario, report,
│                                          submission, job manifest, attestation,
│                                          calibration, same-model experiment)
│
├── scenarios/                             static v0.1 Scenario Packs (superset;
│   │                                      membership is fixed by each Profile's
│   │                                      required_templates)
│   ├── dev/                               MIB-Core v0.1 Public Dev, 24 Templates
│   │   ├── recall/        4      ├── skill/       3
│   │   ├── time/          4      ├── causal/      3
│   │   ├── epistemic/     4      └── cross/       3
│   │   └── experience/    3
│   └── transfer/                          transfer diagnostics, 6 Templates
│                                          (kept outside dev/ so the MIB-Core
│                                          pack stays exactly 24)
│
├── reality/                               MIB-R prototype Reality Packs
│
├── src/mib_runner/                        reference Runner, evaluators,
│   │                                      adapters, calibration, service,
│   │                                      leaderboard
│   ├── worldmodel.py                      bitemporal per-source world model,
│   │                                      queries, support sets, leak proofs
│   ├── generate/                          Programs, surface pools, interference
│   │                                      ladder, instance builder, registry
│   ├── agents/v2.py                       the v0.2 fixture Agents
│   └── experimental/                      Transfer Intelligence, Memory Adapter,
│                                          MIB-R (never enters the MIB Score)
├── tests/
│
├── profiles/                              benchmark profiles
│                                          (MIB-Core-0.2-Dev.json and -Dev-M.json:
│                                          programs, ladder, canonical rung,
│                                          memory-dependence floor, interval method)
├── baselines/                             B0–B3 memory-condition definitions
├── prompts/                               fixed same-model prompts
├── fixtures/                              synthetic demo private eval store
├── tools/                                 operational scripts
│
└── examples/
    ├── agents/                            reference stdio / HTTP Agents
    ├── submissions/                       Agent submission specs
    ├── runs/                              scenario + pack run artifacts
    │                                      (MIB-Core-0.2-Dev.* is the v0.2 pack)
    ├── service/                           evaluation-service artifacts
    ├── calibration/                       calibration reports
    ├── same-model/                        fixed-model experiment artifacts
    ├── scenario-instances/                materialized Scenario instances
    │                                      (generated/ holds one Instance per Program)
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

Generate one Scenario Instance from a Program (seed 7, rung 1 = 20 interference events):

```bash
mib generate --program mib.temporal.v1 --seed 7 --rung 1 --schema schemas/mib-scenario.schema.json --output MIB-GEN-TEMPORAL-V1.json
```

Run the v0.2 development pack — every Program, every seed, every rung — against a fixture
Agent, and write the report, summary, and Capability Card:

```bash
mib benchmark --profile profiles/MIB-Core-0.2-Dev.json --schema schemas/mib-scenario.schema.json --report-schema schemas/mib-report.schema.json --agent mib_runner.agents:StructuredMemoryAgent --output-report report.json --output-summary summary.json --card card.md
```

Swap `StructuredMemoryAgent` for `WindowMemoryAgent`, `ConsolidatingAgent`, `RecencyAgent`,
`OvergeneralizingAgent`, or `NoMemoryAgent` to see the ordering the design predicts, or pass
your own `module:Class` (an in-process Agent implementing `reset` / `observe` / `respond` /
`act`, optionally `maintain`). `profiles/MIB-Core-0.2-Dev-M.json` runs the same Programs at
MIB-M distance with BCa intervals.

Recompute every layer of a report:

```bash
mib verify-score report.json
```

The static v0.1 Templates remain runnable:

```bash
mib run scenarios/dev/time/MIB-TIME-003.json --schema schemas/mib-scenario.schema.json
```

```bash
mib benchmark scenarios/dev --schema schemas/mib-scenario.schema.json --profile profiles/MIB-Core-0.1-Dev-M3.json
```

Run the test suite with:

```bash
python -m pip install -e ".[test]"
```

```bash
PYTHONPATH=src python -m pytest tests -q
```

Two groups of tests skip rather than fail on a fresh public clone:

- Submission-sandbox tests skip off Linux, because containment needs Linux
  user/mount/network namespaces (see below).
- Calibration tests in `tests/test_calibration.py` skip unless `MIB_OFFICIAL_PACK`
  points at the evaluator-only pack, whose Scenario bodies are not published here.

Everything else runs anywhere Python 3.10+ does.

### Running external submissions requires Linux

The commands that execute a participant-supplied **stdio** agent —
`mib agent-smoke-test` on a stdio submission, `mib evaluate-hidden`, and
`mib-service register-submission` / `worker-once` — run it inside the reference
submission sandbox, which relies on Linux unprivileged user, mount, and network
namespaces via `unshare`. They are supported on Linux only; on macOS and Windows no
isolation is enforced and hidden evaluator paths cannot be masked.

HTTP submissions are accepted from `localhost` only. A remote `base_url` needs
`--allow-remote-http` and `https`; the HTTP transport exists for local
development of non-Python Agents, not for remote evaluation.

The rest of the CLI — `mib validate`, `generate`, `run`, `run-pack`, `benchmark`,
`capability-card`, `verify-score`, `public-eval-manifest`, and the non-executing
`mib-service` subcommands — is cross-platform.

External agents can participate through:

```text
stdio JSONL
HTTP
```

using the MIB Agent Adapter protocol.

See:

```text
docs/MIB-Agent-Adapter.md
docs/MIB-Specification.md
```

for the protocol and evaluation semantics.

---

## Transfer Intelligence and MIB-R

MIB-Core answers *which part of the past participated correctly in this future
computation*. It answers it behaviorally, which means a failed transfer looks
the same whether the system never compiled a usable procedure, compiled one and
never retrieved it, or retrieved the right one and could not execute it.

Two supplemental layers separate those cases.

**Transfer Intelligence** (`docs/experimental/MIB-Transfer-Intelligence.md`) makes the
evaluator's latent hypothesis explicit — which past Experience supports which
future Probe, through which Ability, under which applicability boundary — and
then decomposes the outcome:

```text
Experience → Formation → Skill → Routing → Applicability → Uptake → Behavior
```

It reports Formation Efficiency, Routing Efficiency, an uptake ceiling, and a
Transfer Profile across the positive distance ladder `D0`–`D3`, alongside the
two controls a purely positive-transfer benchmark cannot express: a near-match
trap the learned procedure must be withheld from, and an unsupported task where
memory must stay neutral. Three of the four diagnostic cells run against an
ordinary black-box Agent.

**MIB-R** (`docs/experimental/MIB-R-Reality-Track.md`) asks whether the same memory
intelligence survives in a realistic external task environment, by running
acquisition and held-out transfer under paired memory conditions where only
memory state varies.

Both layers are supplemental. No metric either one defines enters the MIB
Score, the Causal Score, or Coverage. A pack whose Templates carry no transfer
annotation produces a report byte-identical to one produced before the
extension existed. MIB-R is a prototype with its own result family and no
official score; it is never ranked against MIB-Core.

```bash
mib benchmark scenarios/transfer \
  --profile profiles/MIB-Transfer-0.1-Dev.json \
  --schema schemas/mib-scenario.schema.json \
  --transfer-diagnostics

mib reality-benchmark reality/MIB-R-Demo-LedgerCodes/pack.json \
  --profile profiles/MIB-R-0.1-Dev.json \
  --agent mib_runner.experimental.reality_fixtures:RuleLearningRealityAgent
```

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

See [CONTRIBUTING.md](CONTRIBUTING.md) for the development setup, the repository
layout, coding conventions, and the rule that Hidden Eval / Private Holdout Scenario
bodies must never be committed here. Report security issues through the process in
[SECURITY.md](SECURITY.md) rather than in a public issue.

---

## License

MIB is released under the **GNU General Public License v3.0**. The full text is in
[LICENSE](LICENSE).

---

## Citation

A formal paper will be added when the generated benchmark pack passes empirical calibration and is frozen. Until then,
[CITATION.cff](CITATION.cff) carries the machine-readable software citation and
GitHub's "Cite this repository" entry resolves to it.

In prose, please refer to the project as:

> **MIB — Memory Intelligence Benchmark**
>
> A benchmark for measuring how effectively an intelligent system uses the past to improve future cognition and behavior.
