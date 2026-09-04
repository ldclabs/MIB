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

The adversarial scenario family (`MIB-ADV-*`) pushes the harmful memory condition to its purest form: the injected events consist **solely of questions** that presuppose an unestablished habit, date, or procedure. Because questions assert nothing, oracle answers remain identical across both conditions — any paired performance drop reveals that questioning alone installed unverified facts into memory, measured directly via the standard Memory Harm and Harm Resistance metrics.

Removal shows that *something* in an event mattered. v0.2 adds the stronger test —
**counterfactual content**: the same Instance is replayed with one event saying something
else, and the correct answer changes with it.

```text
Full Memory
    vs
Same past, one event's content swapped
```

An Agent whose answers follow the swapped content was using memory. An Agent whose
answers stay the same, however high its score, was answering from priors.

This produces diagnostics such as:

```text
Memory Benefit
Headroom-Normalized Memory Benefit
Content Tracking Rate          ← gates memory dependence
Stale Adoption Rate
Irrelevant Memory Stability
Memory Harm
Harm Resistance
Net Memory Gain
Error Recurrence Rate          (lived failures, see below)
Consolidation Benefit          (Agents that implement maintain)
Negative Transfer / Rate       (the standardized control on a non-matching task)
Learning Gain / Curve Area     (lived trials)
Authority Confusion, Historical Fidelity, Source Attribution, Self-Rule Continuity
```

The main **MIB Score** measures absolute memory-enabled capability at a fixed interference
distance. Causal diagnostics are reported alongside it rather than being mixed into an
opaque score, and a Profile's **memory dependence** floor (content tracking rate ≥ 0.5 by
default) decides whether that score may be called official. Negative Transfer is now
measured by its standardized control: the non-matching task with the skill memory
withheld, compared with the same task with it (`docs/MIB-Specification.md` §7.8).

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

MIB v0.2 does not ship hand-written Scenarios. It ships **Programs**: deterministic
generators `(seed, rung) → Scenario Instance` over an internal, bitemporal, per-source
world model. Answers, relevant-memory ablation sets, counterfactual twins, and leak proofs
are computed from the model, never authored.

```text
mib.recall.v1        a fact and a two-hop chain with a decoy
mib.temporal.v1      one or two updates: current, previous, original value
mib.epistemic.v1     correction, contradiction with authority, tool resolution, unknown
mib.experience.v1    a deployment the Agent itself runs and breaks, then a related one
mib.skill.v1         a learned precondition: apply where it fits, withhold where it does not
mib.prospective.v1   a deferred commitment, a near-trigger, the real trigger, a self-rule under pressure
mib.forgetting.v1    a retracted fact must stay unused; its neighbour must stay known
```

Every Program is executed on a **distance ladder** — the same Instance with 0, 20, and
100 generated interference events between the past and the Probes (0 / 100 / 1000 in the
MIB-M development profile) — so a result is a retention curve, not a point. Distance is
recorded in events, tokens, and virtual hours. The capability score is read at the
Profile's canonical rung; every rung feeds the curve. Every Program also consolidates
once (a maintenance window with a paired no-maintenance control), and every lived task
can carry a trial oracle, so learning curves come from what the Agent actually did.

A pack is `programs × seeds × rungs`. Programs, surface pools, and the generator are
public; official evaluation uses evaluator-secret seeds, so participants can inspect every
construction and still never see an official Instance.

The 24 static Public Dev Templates of v0.1 (and the hidden v0.1 packs) remain executable
as a superset and are useful for integration and regression testing. They are no longer
the benchmark.

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

MIB v0.2 (implementation 0.9.0) currently includes:

```text
✓ Benchmark architecture
✓ World model: bitemporal, per-source, computed oracles
✓ Seven generated Programs on a three-rung distance ladder (MIB-S and MIB-M profiles)
✓ Support sets, leak proofs, counterfactual twins (all derived)
✓ Lived tasks and trials (experience the Agent creates itself; learning curves)
✓ Prospective memory scored from spontaneous emissions
✓ Structured answers: value / status / confidence, deterministic parser
✓ Scoring model: capability at the canonical rung + retention curve
✓ Causal diagnostics + memory-dependence gate
✓ Standardized Negative Transfer control
✓ Full-run behaviour diagnostics (error recurrence, authority confusion,
  historical fidelity, source attribution, self-rule continuity, memory-induced errors)
✓ Consolidation windows with a paired no-maintenance control
✓ Percentile and BCa intervals; runner-measured efficiency block
✓ Report schema, score verification, Capability Card

✓ Reference Runner (respond / act / observe_only, maintain hook)
✓ Tool-loop World Simulator
✓ Causal, counterfactual, and no-maintenance replay
✓ Pack-level aggregation
✓ Hierarchical bootstrap (Instance units for generated packs)

✓ External stdio / HTTP Agent Adapter
✓ Hidden evaluation infrastructure
✓ Submission sandbox
✓ Evaluation service
✓ Signed jobs and signed results
✓ Leaderboard + paired comparison

✓ Six fixture Agents that order as the design predicts
  StructuredMemoryAgent   flat retention, content tracking 1.0
  WindowMemoryAgent       decays along the ladder
  ConsolidatingAgent      the window fixture whose maintain() pays off
  RecencyAgent            stale adoption, authority confusion, cannot forget
  OvergeneralizingAgent   negative transfer on the non-matching task
  NoMemoryAgent           low score, dependence not assessable
  (plumbing only: they establish nothing about difficulty)

✓ 24 static v0.1 Public Dev Templates, still executable as a superset

✓ Transfer Intelligence diagnostics
  supplemental only: no MIB Score changes

○ MIB-R Reality Track
  prototype; its own result family, no official score,
  never ranked against MIB-Core

○ Real fixed-model calibration at every rung
  pending

○ MIB-L ladders whose rungs exceed any working context
  pending (MIB-M reaches 1,000 interference events, about 8k tokens)

○ MIB v0.2 leaderboard pack freeze
  pending empirical calibration
```

What v0.2 can and cannot claim today:

- Every shipped Program is inside a modern context window: the MIB-S ladder
  tops out at 100 interference events, MIB-M at 1,000 (about 8k tokens). The ladder and the counterfactual
  swap together identify *memory* rather than *reading* — an Agent must retain
  the content at a distance and must follow it when it changes — but a
  full-context model can still pass rung 2 by reading. Rungs beyond the
  working context are what turn the retention curve into a memory-system
  comparison, and they are pending.
- The fixture Agents are keyed to the generated language. Their ordering
  (Structured > Window > NoMemory; Recency shows stale adoption) exercises
  the Runner and the scoring; it is not a baseline.
- No real model has been calibrated yet.

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
│   ├── agents/v2.py                       the four v0.2 fixture Agents
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

A formal paper will be added when the v0.1 benchmark pack is frozen. Until then,
[CITATION.cff](CITATION.cff) carries the machine-readable software citation and
GitHub's "Cite this repository" entry resolves to it.

In prose, please refer to the project as:

> **MIB — Memory Intelligence Benchmark**
>
> A benchmark for measuring how effectively an intelligent system uses the past to improve future cognition and behavior.
