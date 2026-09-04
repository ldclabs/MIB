# MIB v0.1 Test Plan

## First Executable Benchmark Profile for the Memory Intelligence Benchmark

**Version:** 0.1-draft  
**Status:** Test Plan Proposal / Pre-Implementation Candidate  
**Profile:** `MIB-Core-0.1`

Companion documents:

```text
MIB-Specification.md
MIB-Agent-Adapter.md
schemas/mib-scenario.schema.json
schemas/mib-report.schema.json
```

This plan predates the consolidated specification. Where a milestone below
describes a construct that `MIB-Specification.md` lists under Appendix A
(Roadmap), the construct is not implemented in v0.1.

---

# 0. Purpose

This document defines the first executable test plan for MIB.

The goal of v0.1 is not to test every possible form of memory intelligence.

The goal is to build the smallest benchmark that can already separate:

```text
simple retrieval memory
summary memory
temporal memory
epistemic memory
episodic / experience memory
procedural / skill memory
causally useful memory
```

while remaining:

```text
implementable
architecture-neutral
black-box compatible
reproducible
statistically interpretable
hard to game
cheap enough to iterate
```

The v0.1 benchmark profile is named:

> **MIB-Core-0.1**

It measures six primary dimensions:

```text
1. Retention & Retrieval
2. Temporal Memory
3. Epistemic Memory
4. Experience Memory
5. Skill Learning & Transfer
6. Causal Memory Impact
```

The following full-MIB dimensions are intentionally deferred as first-class v0.1 dimensions:

```text
Selective Forgetting
Prospective & Self Memory
```

Some v0.1 scenarios may exercise stale-memory suppression or self-relevant behavior incidentally, but those capabilities do not yet receive standalone dimension scores.

---

# 1. v0.1 Success Criteria

MIB v0.1 is successful if it can demonstrate all of the following:

1. different long-term memory systems produce meaningfully different capability profiles;
2. simple retrieval systems perform well on some tests but fail on deeper temporal, epistemic, experience, or skill tests;
3. relevant-memory ablation causes measurable performance loss on memory-dependent scenarios;
4. irrelevant-memory ablation usually leaves performance stable;
5. stale or harmful memory can be shown to cause or fail to cause avoidable errors;
6. hidden parameterization prevents trivial hardcoded-answer strategies;
7. black-box Agents can participate without exposing internal memory records;
8. score recomputation from `mib-report.schema.json` is deterministic;
9. official results include uncertainty, coverage, and execution-failure information;
10. the benchmark is small enough to run repeatedly during development.

---

# 2. Non-Goals for v0.1

MIB v0.1 does NOT attempt to fully standardize:

```text
prospective autonomous reminders
self-model continuity
privacy isolation
cross-agent memory
multimodal memory
robotics / embodied memory
very-long real-time aging
memory governance
memory deletion compliance
cross-device memory portability
continuous autonomous agents
```

These belong to future profiles.

MIB v0.1 also does not attempt to decide:

```text
the best internal memory architecture
the best embedding model
the best database
the best prompting strategy
```

It measures externally observable memory intelligence.

---

# 3. Profile Identity

Canonical profile identity:

```text
MIB-Core-0.1
```

Recommended machine identity:

```json
{
  "id": "MIB-Core-0.1",
  "version": "0.1.0"
}
```

A published score MUST include:

```text
Profile
Track
Scale
Scenario Pack version
Agent version
Model version
Memory version
```

Example:

```text
MIB-Core-0.1 / Track A / MIB-M
Score: 78.4
```

---

# 4. Primary Benchmark Tracks

v0.1 supports:

## Track A — Memory System

Preferred research leaderboard.

Fixed:

```text
base model
reference Agent
system prompt
tools
Scenario Pack
Runner
Evaluator bundle
```

Variable:

```text
memory system
memory-specific formation/retrieval/consolidation logic
```

Track A answers:

> Which memory system makes the same Agent more memory-intelligent?

## Track B — Integrated Agent

The participant may vary:

```text
model
Agent
memory
orchestration
tool strategy
```

Track B answers:

> How memory-capable is this complete Agent?

Track A and Track B MUST have separate rankings.

---

# 5. v0.1 Dimensions

`MIB-Core-0.1` includes:

```text
retention_retrieval
temporal_memory
epistemic_memory
experience_memory
skill_learning_transfer
causal_memory_impact
```

The profile intentionally preserves the relative priorities proposed by the full v1 architecture.

The full-v1 candidate weights for these six dimensions are:

```text
0.12
0.13
0.15
0.15
0.15
0.12
```

Their sum is:

```text
0.82
```

For `MIB-Core-0.1`, they are renormalized.

---

# 6. v0.1 Dimension Weights

Recommended:

| Dimension | Weight |
|---|---:|
| Retention & Retrieval | 0.146341 |
| Temporal Memory | 0.158537 |
| Epistemic Memory | 0.182927 |
| Experience Memory | 0.182927 |
| Skill Learning & Transfer | 0.182927 |
| Causal Memory Impact | 0.146341 |
| **Total** | **1.000000** |

Conceptually:

```text
Retention                14.6%
Temporal                 15.9%
Epistemic                18.3%
Experience               18.3%
Skill                    18.3%
Causal                   14.6%
```

This avoids inventing a temporary v0.1 philosophy that would later conflict with the full benchmark.

---

# 7. Suite Structure

v0.1 defines six primary Suites plus one integration Suite:

```text
MIB-Recall
MIB-Time
MIB-Belief
MIB-Experience
MIB-Skill
MIB-Causal
MIB-Cross
```

`MIB-Cross` contains multi-dimensional scenarios.

It does not create a seventh MIB capability dimension.

---

# 8. Canonical Template Count

The v0.1 plan defines:

| Suite | Templates |
|---|---:|
| Recall | 10 |
| Time | 10 |
| Belief | 10 |
| Experience | 8 |
| Skill | 8 |
| Causal | 8 |
| Cross | 6 |
| **Total** | **60** |

These are **Scenario Templates**, not fixed QA items.

Each Template may generate many hidden Scenario Instances.

---

# 9. Public / Hidden Split

The 60 Templates are divided into three visibility classes.

| Class | Count | Exact Template Public? | Used in Official Score? |
|---|---:|---|---|
| Public Dev | 24 | Yes | No |
| Hidden Eval | 30 | Family public; exact hidden generation/oracle partly private | Yes |
| Private Holdout | 6 | No exact composition | Yes |
| **Total** | **60** |  |  |

This produces:

```text
24 development templates
+
36 official evaluation templates
```

The exact private Scenario bodies for Hidden Eval and Private Holdout MUST NOT be committed to the public benchmark repository used by participants.

---

# 10. Why Public Dev Is Excluded from Official Score

Participants are expected to optimize against Public Dev.

Therefore it is useful for:

```text
adapter development
debugging
research
regression testing
local score estimation
```

but should not determine leaderboard rank.

Official score uses:

```text
Hidden Eval
+
Private Holdout
```

This reduces benchmark-specific memorization.

---

# 11. Visibility Allocation by Suite

| Suite | Dev | Hidden Eval | Private Holdout | Total |
|---|---:|---:|---:|---:|
| Recall | 4 | 5 | 1 | 10 |
| Time | 4 | 5 | 1 | 10 |
| Belief | 4 | 5 | 1 | 10 |
| Experience | 3 | 4 | 1 | 8 |
| Skill | 3 | 4 | 1 | 8 |
| Causal | 3 | 4 | 1 | 8 |
| Cross | 3 | 3 | 0 | 6 |
| **Total** | **24** | **30** | **6** | **60** |

---

# 12. Benchmark Scale

v0.1 supports two practical scales:

```text
MIB-S
MIB-M
```

`MIB-L` is reserved for later stress testing.

## MIB-S

Development scale.

Target:

```text
50–100 meaningful visible events
0–100 distractor events
short tool trajectories
1 hidden or fixed instance per Template
```

Use:

```text
local development
CI
Adapter verification
fast comparison
```

## MIB-M

Official v0.1 leaderboard scale.

Target per Scenario Instance:

```text
100–1,000 visible events
meaningful long-range delay
50–500 distractor events where relevant
multiple revisions or Experience steps
longer Agent memory horizon
```

Official MIB-Core-0.1 score SHOULD use MIB-M.

---

# 13. Meaningful Event, Distractor Event, and Token Count

MIB reports all three separately.

A **meaningful event** is an event that contributes to:

```text
world state
relevant memory
source state
Experience trajectory
Skill learning
future action conditions
```

A **distractor event** is benchmark-generated interference not intended to be causally necessary for the Probe.

Token count is still recorded, but v0.1 MUST NOT define difficulty only by token count.

---

# 14. Official Hidden Instance Count

Recommended v0.1 leaderboard default:

```text
4 hidden instances
per official Scenario Template
```

With:

```text
36 official Templates
```

this gives:

```text
144 hidden Scenario Instances
```

before repetitions and causal variants.

The Runner MAY rotate hidden instance seeds between leaderboard evaluation cycles.

---

# 15. Repetitions

Recommended official default:

```text
2 repetitions per condition
```

for general Track A / Track B leaderboard evaluation.

Research runs MAY use more.

A system that is demonstrably deterministic still participates in the same nominal evaluation schedule unless leaderboard policy defines a deterministic optimization.

This keeps result handling simple in v0.1.

---

# 16. Statistical Unit

The hierarchy is:

```text
Repetition
    ↓
Scenario Instance
    ↓
Scenario Template
    ↓
Dimension
    ↓
MIB-Core-0.1 Score
```

Hidden instances inside one Template do not become independent Template weight.

This follows `MIB-Specification.md`.

---

# 17. Benchmark Conditions

Every official Scenario runs:

```text
Full
```

Additional conditions are selected according to Scenario semantics:

```text
Relevant Memory Ablation
Irrelevant Memory Ablation
No-Memory Control
Harmful Memory
Stale Memory
Counterexample
Full-Context Calibration
```

Not every Scenario needs every condition.

---

# 18. Core Causal Condition Policy

Across the 36 official Templates, the Pack SHOULD guarantee substantial coverage of:

```text
Relevant Ablation
Irrelevant Ablation
Harm/Stale Condition
```

The initial target is:

```text
Relevant Benefit Coverage    ≥ 80% of causal Template weight
Irrelevant Stability Coverage ≥ 60%
Harm Resistance Coverage      ≥ 60%
```

These thresholds apply to the `causal_memory_impact` dimension evidence, not necessarily every non-causal Suite.

---

# 19. Full-Context and No-Memory Calibration

Before a Template is admitted to the official Pack, maintainers SHOULD evaluate:

```text
Full Context
No Memory
```

even if these conditions are not run for every leaderboard submission.

Purpose:

```text
Full Context:
  Can the fixed Agent solve the task when the relevant past is available?

No Memory:
  Can it solve the task without the past?
```

This supports Memory Discriminativeness Index calibration.

---

# 20. Calibration Acceptance Targets

Recommended candidate thresholds for Track A Scenario admission:

```text
Full-Context baseline:
    mean ≥ 0.80

No-Memory baseline:
    mean ≤ 0.60

Memory Discriminativeness Index:
    FC - NM ≥ 0.25
```

These are v0.1 calibration targets, not metaphysical requirements.

A Scenario may be accepted outside them only with documented justification.

---

# 21. Additional Calibration Rules

A canonical Template SHOULD also satisfy:

```text
not trivially solved by lexical shortcut
not dependent on private chain-of-thought
not dependent on unavailable real-world state
stable deterministic Oracle
replayable causal intervention
reasonable variance
no obvious answer leakage
```

For hidden Templates, maintainers SHOULD test multiple random instantiations before release.

---

# 22. Reference Baseline Systems

Before public launch, v0.1 SHOULD be calibrated against at least four baselines:

```text
B0 — No Memory
B1 — Full Relevant Context
B2 — Simple Retrieval Memory
B3 — Stronger Structured / Agentic Memory
```

Optional:

```text
B4 — Summary Memory
B5 — Graph Memory
B6 — Episodic + Skill Memory
```

The benchmark should show a non-trivial ranking spread.

---

# 23. Expected Baseline Shape

The benchmark is well shaped if results roughly exhibit patterns such as:

```text
Simple Retrieval:
    strong Recall
    weaker Time
    weaker Epistemic
    weak Experience/Skill

Summary Memory:
    moderate Recall
    some compression benefit
    possible source/history loss

Structured Temporal Memory:
    stronger Time
    stronger correction handling

Episodic Memory:
    stronger Experience

Procedural Memory:
    stronger Skill

Strong Cognitive Memory:
    balanced capability
    strong causal benefit
    low harm/interference
```

These are qualitative expectations only.

MIB MUST NOT force results to fit them.

---

# 24. Evaluator Policy

v0.1 should maximize deterministic scoring.

Target official score dependence:

```text
≥ 80% weighted score:
    deterministic / structured / world-state / trajectory

≤ 20% weighted score:
    may depend materially on LLM judge
```

Preferred target:

```text
< 10% LLM-judge-dependent
```

where practical.

---

# 25. Why Limit LLM Judges

The purpose of MIB is to benchmark memory systems, not the taste of another LLM.

LLM judges are acceptable where needed for:

```text
semantic completeness
natural-language source attribution
experience explanation
```

but must not override:

```text
world truth
exact identity
temporal state
tool outcome
structured abstention status
```

---

# 26. Public Dev Suite Goals

The Public Dev set should teach participants:

```text
how Scenario replay works
how hidden fields are projected away
how Probe scoring works
how ablation works
how tool loops work
how report generation works
```

It should NOT reveal all leaderboard challenge compositions.

---

# 27. Hidden Eval Goals

Hidden Eval should vary:

```text
entity names
dates
values
ordering
distractor type
distractor density
surface wording
tool states
source conflicts
failure preconditions
Skill applicability
```

while preserving the public semantic family.

---

# 28. Private Holdout Goals

The six Private Holdout Templates exist to test:

```text
template generalization
composition generalization
anti-hardcoding
unseen memory interactions
```

Only broad dimension placement is public.

Exact Scenario structure, generator, Oracle, and ablation plan remain private.

---

# 29. Suite A — MIB-Recall

Primary dimension:

```text
retention_retrieval
```

Secondary evidence may contribute to:

```text
causal_memory_impact
```

Primary questions:

```text
Was relevant information retained?
Can it be recovered from indirect cues?
Can the correct entity be distinguished?
Can multiple memories be composed?
Can distractors be ignored?
```

---

# 30. Recall Template Inventory

## `MIB-RET-001` — Direct Delayed Recall

**Visibility:** Public Dev

Past:

```text
random entity
random attribute
random value
```

After delay/interference:

```text
direct recall Probe
```

Purpose:

```text
baseline retention
```

No fixed famous facts; values are generated.

---

## `MIB-RET-002` — Implicit Attribute Application

**Visibility:** Public Dev

Past contains an attribute such as:

```text
pet size
user preference
device constraint
```

Future Probe requires using it without repeating the same lexical cue.

Purpose:

```text
implicit recall
cue generalization
```

---

## `MIB-RET-003` — Multi-Hop Memory Composition

**Visibility:** Public Dev

Past observations separately establish:

```text
A → B
B → C
C → value
```

Future Probe requires composition.

Purpose:

```text
multi-hop retrieval + reasoning
```

---

## `MIB-RET-004` — Identity Collision

**Visibility:** Public Dev

Two actors share:

```text
same or near-identical display names
```

but have distinct stable actor IDs and attributes.

Purpose:

```text
identity precision
avoid name-based memory collision
```

---

## `MIB-RET-005` — Distractor-Heavy Rare Fact

**Visibility:** Hidden Eval

A low-frequency but important fact appears before a large unrelated history.

Purpose:

```text
long-range retention
signal preservation
```

---

## `MIB-RET-006` — Near-Match Confusor

**Visibility:** Hidden Eval

Several values differ only slightly:

```text
project-17
project-71

May 12
May 21

UTC+1
UTC+2
```

Purpose:

```text
precision under semantic similarity
```

---

## `MIB-RET-007` — Distributed Entity Bundle

**Visibility:** Hidden Eval

Properties of one entity are distributed across multiple sessions and source forms.

Future Probe requires selecting the right subset.

Purpose:

```text
multi-session reconstruction
```

---

## `MIB-RET-008` — Sparse Cue Paraphrase

**Visibility:** Hidden Eval

Future Probe shares minimal lexical overlap with the original observation.

Purpose:

```text
semantic recall beyond exact phrase matching
```

---

## `MIB-RET-009` — Relevant Document Among Routine Chatter

**Visibility:** Hidden Eval

One document observation contains the critical constraint.

Many conversational distractors follow.

Purpose:

```text
document-to-action recall
salience under modality/type variation
```

---

## `MIB-RET-010` — Retrieval Holdout Composition

**Visibility:** Private Holdout

Exact composition withheld.

Public statement:

```text
tests retrieval under a combination of
identity ambiguity,
indirect cueing,
and interference
```

---

# 31. Recall Causal Requirements

Official Recall Templates SHOULD include:

```text
Full                 all
Relevant Ablation    all official Recall Templates
Irrelevant Ablation  at least 3
No Memory            at least 2
```

Purpose:

```text
prove that successful recall is actually past-dependent
```

---

# 32. Suite B — MIB-Time

Primary dimension:

```text
temporal_memory
```

Secondary:

```text
retention_retrieval
causal_memory_impact
```

Core distinction:

```text
current truth
≠
historical truth
```

---

# 33. Time Template Inventory

## `MIB-TIME-001` — Current Value After Update

**Visibility:** Public Dev

```text
old value
→ explicit update
→ current-value Probe
```

Tests:

```text
update adoption
stale suppression
```

---

## `MIB-TIME-002` — Historical Value Before Update

**Visibility:** Public Dev

Same state transition, but Probe asks for the previous state.

Tests:

```text
historical preservation
```

---

## `MIB-TIME-003` — Planned vs Completed Change

**Visibility:** Public Dev

```text
"I will move next month."
```

does not immediately imply:

```text
"I have moved."
```

A later event completes the transition.

Tests:

```text
future intention vs realized state
```

---

## `MIB-TIME-004` — Correction vs Reversal

**Visibility:** Public Dev

Distinguish:

```text
"I misspoke; it was May 21."
```

from:

```text
"It used to be X, but now it is Y."
```

Tests:

```text
epistemic correction
vs
world-state transition
```

Primary scoring remains temporal.

---

## `MIB-TIME-005` — Multiple Successive Revisions

**Visibility:** Hidden Eval

Three or more state changes.

Probe asks:

```text
current
one historical point
ordering
```

---

## `MIB-TIME-006` — Temporary Validity Window

**Visibility:** Hidden Eval

A policy or state is valid only within a virtual-time interval.

Tests:

```text
valid-time reasoning
```

---

## `MIB-TIME-007` — Reversion to Prior State

**Visibility:** Hidden Eval

```text
A
→ B
→ A
```

Tests whether history is represented as transitions rather than collapsed values.

---

## `MIB-TIME-008` — Late-Arriving Evidence

**Visibility:** Hidden Eval

Observation time differs from the time the fact was valid.

Tests:

```text
recorded time
vs
world-valid time
```

without requiring KIP terminology.

---

## `MIB-TIME-009` — Stale Operational Rule Trap

**Visibility:** Hidden Eval

A historical procedure becomes invalid.

Future action must use the current procedure while historical Probe still recalls the old one.

Tests:

```text
staleness resistance
historical fidelity
```

---

## `MIB-TIME-010` — Temporal Holdout Composition

**Visibility:** Private Holdout

Exact composition withheld.

Public scope:

```text
multiple revisions
historical query
current action
temporal interference
```

---

# 34. Time Causal Requirements

Official Time Templates SHOULD include:

```text
Relevant Ablation      at least 5 of 6
Irrelevant Ablation    at least 2
Stale/Harm condition   at least 4
No Memory              at least 2
```

This Suite is a major source of stale-memory resistance evidence.

---

# 35. Suite C — MIB-Belief

Primary dimension:

```text
epistemic_memory
```

Questions:

```text
Who said it?
Was it observed, stated, or tool-derived?
Was it corrected?
Are sources in conflict?
Is the answer actually unknown?
Are multiple derived copies really one evidence root?
```

The Agent does not need KIP objects.

It only needs to behave correctly.

---

# 36. Belief Template Inventory

## `MIB-EPI-001` — Unknown vs False

**Visibility:** Public Dev

No evidence exists for a proposition.

Probe asks for a binary-looking answer.

Correct:

```text
unknown / insufficient
```

Incorrect:

```text
fabricated yes/no certainty
```

---

## `MIB-EPI-002` — Explicit Self-Correction

**Visibility:** Public Dev

```text
"My birthday is May 12."
"Sorry, I meant May 21."
```

Tests:

```text
current corrected belief
+
historical attribution
```

---

## `MIB-EPI-003` — Source Disagreement

**Visibility:** Public Dev

Two actors make contradictory claims.

Probe asks for:

```text
what is known
who said what
```

---

## `MIB-EPI-004` — Tool Evidence vs Human Statement

**Visibility:** Public Dev

Human claims one value.

Benchmark tool returns another.

Scenario defines which tool evidence is authoritative for the task.

Tests:

```text
source type
evidence preference
```

---

## `MIB-EPI-005` — Derived Evidence Multiplication

**Visibility:** Hidden Eval

One source is transformed into:

```text
summary
note
derived record
```

The Agent should not treat these as independent corroboration.

---

## `MIB-EPI-006` — Tentative Statement

**Visibility:** Hidden Eval

Speaker says:

```text
"I think..."
"probably..."
"not sure..."
```

Future evidence later confirms or contradicts.

Tests:

```text
uncertainty preservation
```

---

## `MIB-EPI-007` — Trusted Source Conflict

**Visibility:** Hidden Eval

Multiple source classes conflict.

Scenario defines an operational authority ordering through visible task context or tool semantics.

Tests:

```text
source-sensitive belief formation
```

without hardcoding a universal trust system.

---

## `MIB-EPI-008` — Historical Attribution After Correction

**Visibility:** Hidden Eval

After correction, Probe asks:

```text
What was originally said?
Who corrected it?
What should we use now?
```

---

## `MIB-EPI-009` — Temporal + Epistemic Conflict

**Visibility:** Hidden Eval

One source is correct historically but stale currently.

Another is current.

Tests:

```text
source
+
time
+
belief
```

---

## `MIB-EPI-010` — Epistemic Holdout Composition

**Visibility:** Private Holdout

Exact composition withheld.

Public scope:

```text
unknown
conflicting sources
correction
derived evidence
```

---

# 37. Belief Causal Requirements

Official Belief Templates SHOULD include:

```text
Relevant Ablation      at least 4 of 6
Irrelevant Ablation    at least 2
Harm/Wrong-source      at least 4
No Memory              at least 2
```

Wrong-source and duplicate-derived cases are especially important for Memory Harm.

---

# 38. Suite D — MIB-Experience

Primary dimension:

```text
experience_memory
```

The benchmark tests whether a past task remains useful as:

```text
goal
state
action
observation
failure
recovery
outcome
```

rather than as a bag of keywords.

---

# 39. Experience Template Inventory

## `MIB-EXP-001` — Failure and Recovery

**Visibility:** Public Dev

Past Agent task contains:

```text
attempt
failure
diagnosis
recovery
success
```

Future task requires recalling the recovery pattern.

---

## `MIB-EXP-002` — Outcome Disambiguation

**Visibility:** Public Dev

Two similar attempts:

```text
Attempt A failed.
Attempt B succeeded.
```

Future Probe asks which path should be reused.

Tests:

```text
trajectory + outcome binding
```

---

## `MIB-EXP-003` — Hidden Preconditions From Prediction Error

**Visibility:** Public Dev

Agent expects an action to work.

Observed result violates expectation.

Later diagnosis reveals a hidden precondition.

Future task requires checking that precondition.

---

## `MIB-EXP-004` — Failed Attempt vs Successful Attempt Selection

**Visibility:** Hidden Eval

Several plausible historical trajectories exist.

Only one has the relevant successful causal structure.

---

## `MIB-EXP-005` — Long Multi-Step Ordering

**Visibility:** Hidden Eval

Experience is split by distractors and tool interactions.

Future task depends on:

```text
correct action/observation order
```

---

## `MIB-EXP-006` — Known Failure Recurrence

**Visibility:** Hidden Eval

The Agent encounters a future opportunity to repeat a previously observed failure.

Primary metric:

```text
Error Recurrence Rate
```

---

## `MIB-EXP-007` — Compare Two Experiences

**Visibility:** Hidden Eval

Two prior tasks differ in one causal condition.

Future task requires identifying which lesson transfers.

This bridges Experience toward Skill without becoming a full Skill Template.

---

## `MIB-EXP-008` — Experience Holdout Composition

**Visibility:** Private Holdout

Exact composition withheld.

Public scope:

```text
multiple trajectories
failure recovery
causal comparison
```

---

# 40. Experience Causal Requirements

Official Experience Templates SHOULD include:

```text
Relevant Ablation      all official Templates
Irrelevant Ablation    at least 2
No Memory              at least 2
Harmful wrong-episode  at least 2
```

The benchmark should show that future performance depends on the relevant past trajectory.

---

# 41. Suite E — MIB-Skill

Primary dimension:

```text
skill_learning_transfer
```

Core question:

> Can the Agent turn repeated Experience into a reusable action policy without overgeneralizing it?

Skill scenarios MUST test:

```text
positive transfer
+
applicability
```

where practical.

---

# 42. Skill Template Inventory

## `MIB-SKILL-001` — Learn a Hidden Precondition

**Visibility:** Public Dev

Repeated environment interaction reveals:

```text
before action B,
condition A must hold
```

Future task uses a new surface form with the same rule.

---

## `MIB-SKILL-002` — Surface-Changed Positive Transfer

**Visibility:** Public Dev

Same procedural structure.

Different:

```text
entity names
UI labels
task content
```

Tests abstraction beyond memorized wording.

---

## `MIB-SKILL-003` — Non-Matching Negative Transfer

**Visibility:** Public Dev

A prior Skill is plausible but not applicable.

Applying it harms performance.

Tests:

```text
Skill applicability
negative transfer resistance
```

---

## `MIB-SKILL-004` — Counterexample Refines Skill

**Visibility:** Hidden Eval

Initial experiences support a general rule.

Later Experience presents an exception.

Future behavior should become conditional.

---

## `MIB-SKILL-005` — Conditional Exception Handling

**Visibility:** Hidden Eval

Two contexts require different variants of the same procedure.

Tests:

```text
policy branching
```

---

## `MIB-SKILL-006` — Competing Learned Skills

**Visibility:** Hidden Eval

Two learned procedures are both superficially similar.

Future context determines which one applies.

---

## `MIB-SKILL-007` — Skill After Environment Change

**Visibility:** Hidden Eval

A previously useful Skill becomes partially obsolete.

Future task requires adapting rather than blindly replaying.

---

## `MIB-SKILL-008` — Skill Holdout Composition

**Visibility:** Private Holdout

Exact composition withheld.

Public scope:

```text
learned procedure
farther transfer
counterexample
applicability trap
```

---

# 43. Skill Causal Requirements

Official Skill Templates SHOULD include:

```text
Relevant Skill/Experience Ablation   all official Templates
Irrelevant Ablation                  at least 2
Counterexample/Harm condition        at least 4
No Memory                            at least 2
```

Required diagnostics include substantial coverage of:

```text
Positive Transfer Gain
Negative Transfer
Error Recurrence
```

---

# 44. Suite F — MIB-Causal

Primary dimension:

```text
causal_memory_impact
```

This Suite explicitly tests intervention properties rather than using causal conditions merely as diagnostics.

The ideal memory system should satisfy:

```text
Relevant past removed
    → performance drops

Irrelevant past removed
    → performance stays stable

Harmful/stale past present
    → system resists it
```

---

# 45. Causal Template Inventory

## `MIB-CAUSAL-001` — Relevant-Memory Ablation

**Visibility:** Public Dev

Minimal controlled example demonstrating:

```text
Full vs Relevant Ablated
```

---

## `MIB-CAUSAL-002` — Irrelevant-Memory Stability

**Visibility:** Public Dev

Large distractor set.

Remove distractors.

Future behavior should remain approximately stable.

---

## `MIB-CAUSAL-003` — No-Memory Gap

**Visibility:** Public Dev

Compare:

```text
No Memory
Memory Enabled
Full Context
```

Used to demonstrate:

```text
Memory Discriminativeness
Memory Gap Closure
```

---

## `MIB-CAUSAL-004` — Stale-Memory Resistance

**Visibility:** Hidden Eval

A once-valid memory remains plausible but is now obsolete.

The Agent must use current state.

---

## `MIB-CAUSAL-005` — Harmful Remembered Instruction

**Visibility:** Hidden Eval

A remembered instruction would produce avoidable error if obeyed outside its valid context.

Tests:

```text
memory ≠ authority
harm resistance
```

---

## `MIB-CAUSAL-006` — Redundant Relevant Evidence

**Visibility:** Hidden Eval

Two independent past observations encode the same operationally useful fact.

Ablation must remove the relevant **information set**, not merely one redundant event.

Tests causal-ablation validity.

---

## `MIB-CAUSAL-007` — Synergistic Memory Set

**Visibility:** Hidden Eval

Neither memory A nor B alone is sufficient.

Together they enable success.

Tests:

```text
group ablation
memory interaction
```

---

## `MIB-CAUSAL-008` — Causal Holdout Composition

**Visibility:** Private Holdout

Exact composition withheld.

Public scope:

```text
relevant benefit
irrelevant stability
harm resistance
non-trivial memory interaction
```

---

# 46. Causal Suite Condition Requirements

All official Causal Templates SHOULD support:

```text
Full
Relevant Ablation
Irrelevant Ablation
Harmful or Stale condition
```

At least three SHOULD also support:

```text
No Memory
Full Context calibration
```

This Suite anchors the Causal Memory Impact dimension.

---

# 47. Suite G — MIB-Cross

`MIB-Cross` integrates multiple capabilities in one lived Scenario.

It exists because real memory intelligence is not a collection of independent micro-tests.

Cross Scenarios SHOULD require at least three distinct memory capabilities.

---

# 48. Cross Template Inventory

## `MIB-X-001` — Preference Correction to Future Action

**Visibility:** Public Dev

```text
preference stated
→ corrected later
→ interference
→ future action must use current preference
→ historical Probe asks old preference
```

Tests:

```text
Retention
Temporal
Epistemic
Causal
```

---

## `MIB-X-002` — Source Conflict + Time + Action

**Visibility:** Public Dev

Historical source conflict is later resolved.

Future tool/action task requires current accepted state.

Tests:

```text
Epistemic
Temporal
Action influence
```

---

## `MIB-X-003` — Experience → Skill → Non-Applicability

**Visibility:** Public Dev

Past Experience compiles into a useful Skill.

One future context matches.

Another does not.

Tests:

```text
Experience
Skill
Negative Transfer
Causal
```

---

## `MIB-X-004` — Current/History Under Interference

**Visibility:** Hidden Eval

Multiple updates plus similar distractors.

Future tasks require both current behavior and historical recall.

---

## `MIB-X-005` — Wrong-Source Experience Contamination

**Visibility:** Hidden Eval

A plausible but weakly grounded remembered lesson conflicts with a better observed Experience.

Future action tests whether source/Experience quality matters.

---

## `MIB-X-006` — Uncertainty Before Action

**Visibility:** Hidden Eval

Memory contains incomplete/conflicting information.

Agent must either:

```text
verify
abstain
or use the correct uncertainty-sensitive action
```

rather than confidently applying an uncertain memory.

Tests:

```text
Epistemic
Experience
Causal
```

---

# 49. Cross Scenario Weight Partition

Cross Templates MUST explicitly partition evidence across dimensions.

Example:

```text
MIB-X-001

Retention      0.15
Temporal       0.30
Epistemic      0.30
Causal         0.25
```

No Cross Scenario receives full weight in every dimension.

This avoids double-counting.

---

# 50. Official Template Count by Dimension

The exact dimension evidence depends on Cross partitions.

At minimum, the official hidden set provides:

```text
Recall:
    6 dedicated official Templates

Time:
    6 dedicated official Templates

Belief:
    6 dedicated official Templates

Experience:
    5 dedicated official Templates

Skill:
    5 dedicated official Templates

Causal:
    5 dedicated official Templates

Cross:
    3 additional multi-dimensional Templates
```

Total:

```text
36 official Templates
```

---

# 51. Template Weights

v0.1 default:

> Equal weight among dedicated Templates inside each Suite, before Cross-dimension contributions.

Private Holdout Templates receive the same default semantic Template weight as equivalent dedicated Hidden Eval Templates.

Cross Template dimension contributions are partitioned by declared dimension weights.

Template weights MUST NOT depend on hidden instance count.

---

# 52. Public Dev Scoring

Public Dev MAY produce:

```text
MIB-Core-0.1-Dev Score
```

for local comparison.

It MUST be labeled:

```text
Development
Not Official
```

It is not comparable to official Hidden Eval leaderboard scores.

---

# 53. Official Score Coverage

For an official `MIB-Core-0.1` score:

```text
Profile required coverage = 100%
```

All required official Templates must execute.

If a required Template is unsupported:

```text
profile_eligible = false
```

The system may receive a:

```text
Partial MIB-Core-0.1 Score
```

but not an official leaderboard score.

---

# 54. Infrastructure Failure Threshold

Candidate leaderboard policy:

```text
Execution Failure Rate ≤ 2%
```

after allowed idempotent retries.

Above this threshold:

```text
official score may be withheld
```

because the system is too unreliable for a stable benchmark result.

This threshold should be finalized after reference-runner calibration.

---

# 55. Probe Outcome Policy

For official evaluation:

```text
valid wrong answer
    → cognitive score

timeout after retries
    → Probe score 0 + execution_failure flag

unsupported required Probe
    → profile ineligible

Runner infrastructure fault
    → invalid run; rerun
```

Participant failure is not silently excluded.

---

# 56. Causal Pair Validity

A causal metric is official only when the Runner verifies:

```text
same Scenario Instance
same future Probe
same world seed
same non-target history
same tool simulator behavior
same Agent seed where supported
intended memory intervention only
```

Invalid causal pairs are excluded from causal metric aggregation and trigger a benchmark warning.

If exclusion drops causal coverage below Profile minimum, the official score is withheld.

---

# 57. Hidden Instance Generation

Each hidden Template should generate values from sufficiently large spaces.

Examples:

```text
synthetic names
random identifiers
random dates
random timezones
random project IDs
random policy names
random tool states
random workflow preconditions
```

The answer should not be recoverable from pretraining.

---

# 58. Synthetic but Semantically Natural

Randomization must not produce nonsense that changes task nature.

Bad:

```text
random strings everywhere
```

Preferred:

```text
plausible synthetic entities
controlled values
semantically natural conversations
```

MIB tests memory, not robustness to garbage text.

---

# 59. Hidden Wording Variation

A Template MAY generate multiple semantically equivalent Probe phrasings.

Examples:

```text
"What timezone do I use now?"

"Which timezone should you schedule me in?"

"Use my current timezone for the meeting."
```

This reduces hardcoded lexical shortcuts.

---

# 60. Distractor Design

Distractors should be categorized.

Recommended generator families:

```text
unrelated routine chat
same-topic but different entity
near-match values
low-value status messages
tool noise
document noise
historical but no-longer-relevant state
```

The Runner records generator identity and seed.

The Agent never sees:

```text
is_distractor = true
```

---

# 61. Distractor Difficulty

MIB-M hidden instances should vary:

```text
count
position
semantic similarity
entity overlap
time distance
```

Difficulty should not be a fixed number of irrelevant tokens only.

---

# 62. Entity Identity Tests

At least several official Templates should use:

```text
same display name
similar display name
renamed entity
same organization with different actor
```

while preserving stable actor/entity IDs.

This catches memory systems that key only on text names.

---

# 63. Direct Recall Must Not Dominate

The official score should not be driven by simple fact lookup.

In `MIB-Core-0.1`:

```text
direct factual recall
```

is only a subset of:

```text
Retention & Retrieval
```

which itself is roughly:

```text
14.6%
```

of the profile.

This is intentional.

---

# 64. World-Simulator Tasks

Experience, Skill, Causal, and some Cross Templates SHOULD use Runner-managed tools.

v0.1 reference tool domains should remain small.

Recommended simulated domains:

```text
deployment / configuration
workspace / save workflow
calendar / scheduling
task workflow
document state
simple API operation
```

The point is memory behavior, not domain breadth.

---

# 65. Reference Tool Domain 1 — Deployment

Possible operations:

```text
inspect_target
run_migration
restart_service
read_error
switch_target
```

Useful for:

```text
failure/recovery
hidden precondition
Error Recurrence
Skill transfer
```

---

# 66. Reference Tool Domain 2 — Workspace Workflow

Possible operations:

```text
select_workspace
edit_record
save
inspect_status
```

Useful for:

```text
learned precondition
positive transfer
negative transfer
counterexample
```

---

# 67. Reference Tool Domain 3 — Calendar / Scheduling

Possible operations:

```text
lookup_event
read_timezone
schedule
reschedule
```

Useful for:

```text
source conflict
temporal state
tool evidence
```

---

# 68. Tool Domain Simplicity Rule

A Scenario should not require a sophisticated domain-specific planner before memory matters.

During calibration:

```text
Full Context should solve the task reliably
```

If the base Agent cannot use the simulated tools even with perfect relevant history, the Scenario is not useful for memory evaluation.

---

# 69. Public Dev Instance Files

Public repository SHOULD include materialized examples for Dev Templates.

Recommended:

```text
scenarios/dev/
  recall/
  time/
  epistemic/
  experience/
  skill/
  causal/
  cross/
```

Each public Template should have:

```text
template JSON
at least 2 materialized example Instances
expected evaluator output
ablation example where applicable
```

---

# 70. Hidden Eval Repository Separation

Official hidden Scenario material SHOULD NOT live in the participant-visible public repository.

Recommended architecture:

```text
MIB public repo
    ├── public schemas
    ├── Runner
    ├── Dev scenarios
    └── public family descriptions

MIB evaluator private store
    ├── hidden generators
    ├── private holdouts
    ├── Oracle data
    └── hidden seeds
```

---

# 71. Template Generator Versioning

Every hidden generator must have:

```text
generator ID
generator version
seed
```

Changing generator semantics requires versioning.

A leaderboard report records generator/Pack version but need not expose secret seed values publicly.

---

# 72. Late Probe Sampling

Leaderboard-critical Templates SHOULD use:

```text
late
or
hidden_late
```

Probe sampling where practical.

This means:

```text
past is experienced
→ formation completes
→ future Probe wording/variant selected
```

The Agent cannot know exactly what will later be tested.

---

# 73. Probe Leakage Audit

Before release, the Pack validator should check:

```text
future Probe text absent from formation payload
Oracle absent
expected answer absent
relevance labels absent
ablation labels absent
Scenario tags absent
```

at the Agent Adapter boundary.

---

# 74. Memory Formation Neutrality

Past observations should resemble normal Agent interactions.

Avoid:

```text
IMPORTANT MEMORY:
THIS WILL BE TESTED LATER:
REMEMBER EXACTLY:
```

unless the Scenario explicitly tests user-signaled importance.

Most benchmark items should not reveal future benchmark relevance.

---

# 75. Explicit Importance Scenarios

A small number of scenarios MAY intentionally include:

```text
"Please remember..."
```

because real users do signal importance.

But the Pack must also contain unsignaled memory requirements.

Otherwise the benchmark measures only instruction following.

---

# 76. Experience Formation

Experience Templates should be generated from actual interaction trajectories where practical:

```text
Agent action
→ simulated consequence
→ feedback
→ recovery
```

rather than only telling the Agent:

```text
"Previously you failed because X."
```

The lived trajectory is the object of interest.

---

# 77. Skill Formation

Skill Templates should provide enough repeated or contrastive Experience that learning is plausible.

Recommended:

```text
2–5 formative task episodes
```

before the future transfer Probe.

A one-shot past example may test episodic reuse, but should not be the only definition of Skill learning.

---

# 78. Failed Experience Is First-Class

At least half of Experience/Skill official Templates SHOULD contain a meaningful failure or counterexample.

This prevents the benchmark from equating:

```text
memory of success
```

with:

```text
learning
```

---

# 79. Prediction Error

At least several Experience/Skill Templates SHOULD contain:

```text
expected outcome
≠
observed outcome
```

where the discrepancy reveals a hidden condition.

The Agent need not expose private prediction traces.

The expected action can be made observable through the Scenario trajectory.

---

# 80. Negative Transfer Requirement

At least:

```text
3 official Skill/Cross Templates
```

must contain non-matching future contexts where prior Skill application is harmful or unnecessary.

This is necessary to measure:

```text
Negative Transfer
```

rather than only positive transfer.

---

# 81. Epistemic Unknown Requirement

At least:

```text
3 official Belief/Cross Templates
```

must include cases where the correct answer is:

```text
unknown
insufficient
contested
```

rather than a positive fact.

This tests false-certainty resistance.

---

# 82. Historical + Current Dual Requirement

At least:

```text
4 official Time/Cross Templates
```

must test both:

```text
current action/state
+
historical recall
```

in the same Scenario family.

This prevents a system from scoring well by merely deleting old state.

---

# 83. Evidence Independence Requirement

At least:

```text
2 official Belief/Cross Templates
```

must contain:

```text
one source
→ multiple derived memory artifacts
```

or equivalent duplicated evidence structure.

The evaluator checks that behavior does not incorrectly treat them as independent corroboration.

---

# 84. Harmful Memory Requirement

At least:

```text
8 official Templates
```

across Time, Belief, Skill, Causal, and Cross must contain a condition where remembered content can cause an avoidable error.

This supplies enough Memory Harm evidence for v0.1.

---

# 85. Irrelevant Memory Requirement

At least:

```text
12 official Templates
```

must support meaningful Irrelevant Memory Ablation.

The irrelevant set should include both:

```text
obviously unrelated
and
semantically similar but causally irrelevant
```

history.

---

# 86. Relevant Ablation Requirement

At least:

```text
24 official Templates
```

must support valid Relevant Memory Ablation.

The Causal Suite plus selected Templates from all other Suites should satisfy this.

This is necessary because causal memory benefit is central to MIB.

---

# 87. Group Ablation Requirement

At least:

```text
2 official Templates
```

must require group ablation due to:

```text
redundant relevant memories
or
synergistic memories
```

This ensures the benchmark does not assume one memory event maps to one causal fact.

---

# 88. Full-Context Calibration Requirement

Every official Template should be tested during benchmark development with Full Context.

Full Context is not necessarily run for every leaderboard submission.

It is a benchmark-maintainer calibration control.

---

# 89. No-Memory Calibration Requirement

Every official Template should also be tested during benchmark development with No Memory.

This identifies:

```text
pretraining-solvable tasks
current-context-solvable tasks
poorly discriminative templates
```

---

# 90. MIB-Core-0.1 Causal Score

The `causal_memory_impact` dimension uses the scoring model from `MIB-Specification.md`.

Recommended component weights:

```text
Headroom-Normalized Relevant Benefit   0.50
Irrelevant Memory Stability            0.20
Harm / Stale Resistance                0.30
```

The Pack must provide enough intervention coverage for all three.

---

# 91. Memory Benefit Reporting

Official Capability Card reports:

```text
Memory Benefit
```

as the signed paired mean:

\[
MB = E[F-R]
\]

where relevant ablation is available.

If a Template uses No Memory instead, the report must identify that reference separately.

Do not silently merge heterogeneous references without metadata.

---

# 92. Memory Harm Reporting

Official Capability Card reports:

```text
Memory Harm
Memory-Induced Error Rate
```

where enough eligible harmful trials exist.

The denominator must be reported.

---

# 93. Net Memory Gain

When comparable causal groups exist:

\[
NMG = MB - MH
\]

This is reported as a diagnostic.

It does not replace MIB-Core-0.1 Score.

---

# 94. Error Recurrence Reporting

Experience and Skill suites should produce:

```text
Error Recurrence Rate
```

when known-failure opportunities exist.

Raw counts SHOULD accompany the rate in machine reports.

---

# 95. Negative Transfer Reporting

Skill and Cross Suites should produce:

```text
Negative Transfer Rate
```

and optionally:

```text
Negative Transfer Resistance
```

A system should not receive full Skill credit for blindly applying previously successful procedures.

---

# 96. Development CI

The public Dev Pack should support a fast CI mode.

Recommended:

```text
one fixed Instance per Dev Template
one repetition
Full condition only
selected lightweight ablations
```

Target:

```text
24 Dev Templates
```

This is a regression test, not a statistically serious benchmark result.

---

# 97. Local Research Mode

A deeper local mode may use:

```text
all 24 Dev Templates
multiple public seeds
2–3 repetitions
all public ablations
```

and generate a Development Capability Card.

---

# 98. Official Hidden Run Shape

Recommended default:

```text
36 official Templates
× 4 hidden Instances
× 2 repetitions
```

for the Full condition.

That is:

```text
288 Full condition runs
```

before additional ablation variants.

Ablations are run only where declared.

---

# 99. Cost Control

The full v0.1 official run should remain expensive enough to be meaningful but not so large that only major vendors can participate.

Cost controls include:

```text
small simulated tool domains
bounded output sizes
bounded action steps
4 hidden instances rather than hundreds
Template-first statistics
targeted, not universal, ablations
```

MIB-M should prioritize semantic diversity over brute-force token volume.

---

# 100. Maximum Agent Turns

Candidate default per action Probe:

```text
20 Agent turns
```

Candidate tool-call limit:

```text
20 tool calls
```

Scenario-specific lower limits are encouraged.

The goal is to prevent runaway Agent loops, not to make planning the benchmark target.

---

# 101. Observation Size

v0.1 should keep each individual observation reasonably bounded.

Long history comes primarily from:

```text
number of events
```

rather than one giant document.

This better tests memory formation across time.

Dedicated document-memory profiles can expand later.

---

# 102. Scenario Time Horizon

MIB-M should simulate varied virtual horizons:

```text
hours
days
weeks
months
```

The exact elapsed virtual time matters only when the Scenario semantics use it.

The benchmark should not equate "long time" with arbitrary memory decay.

---

# 103. Random Seed Policy

Every materialized hidden Instance has:

```text
Scenario seed
```

Every stochastic Agent run may also have:

```text
Agent seed
```

where supported.

Causal pairs preserve:

```text
Scenario seed
Agent seed
World seed
Tool seed
```

as far as practical.

---

# 104. Instance Rotation

Public leaderboard infrastructure SHOULD periodically rotate hidden Instance seeds.

Recommended:

```text
same Template Pack
new hidden seeds
```

without changing Profile version.

If Template semantics or scoring change, Pack version must change.

---

# 105. Private Holdout Rotation

Private Holdout Templates SHOULD rotate less frequently than instance seeds.

They exist to detect:

```text
template-level overfitting
```

not merely fixed-answer memorization.

A major holdout composition change should create a new Scenario Pack version.

---

# 106. Anti-Hardcoding

The evaluator should assume participants may inspect all public code.

Defenses:

```text
opaque run IDs
hidden template instances
private holdout compositions
late Probe sampling
randomized entity/value spaces
surface paraphrase
tool-state variation
causal replay
```

MIB must not depend on secrecy of the public protocol.

---

# 107. Scenario Family Disclosure

Public documentation SHOULD disclose:

```text
what capability is tested
what broad causal principle applies
what evaluator class is used
```

It MAY withhold:

```text
exact hidden parameter values
exact hidden wording
private composition order
hidden Oracle
private generator details
```

This balances scientific transparency with benchmark integrity.

---

# 108. Reference Evaluator Distribution

Target v0.1 weighted evaluation mix:

```text
Exact / Set Match             ~25%
Structured                     ~20%
World State                    ~25%
Trajectory                     ~20%
Semantic / LLM Judge           ~10%
```

This is a target, not a strict quota.

The final Pack should publish the actual weighted distribution.

---

# 109. World-State Priority

When the task is behavioral:

```text
"Did the deployment work?"
```

the final World state is more important than a confident natural-language claim.

The Agent cannot earn success merely by saying:

```text
"Done."
```

if the simulator remains failed.

---

# 110. Trajectory Priority

When a Scenario tests learned failure avoidance:

```text
eventual success
```

may be insufficient.

If the Agent first repeats a known harmful action and later recovers, the trajectory evaluator may reduce score.

This is intentional.

---

# 111. Source Attribution Priority

When an Epistemic Template tests source identity, the correct fact without the correct source distinction may receive partial rather than full credit.

The Scenario evaluator defines the split explicitly.

---

# 112. Abstention Scoring

For an unknown/insufficient Oracle:

```text
correct abstention
    → full credit

unsupported confident claim
    → low/zero credit
```

The Agent does not need to use one exact word such as `unknown`.

Structured or semantic equivalence is sufficient.

---

# 113. Reference Public Dev Release Order

Recommended implementation order:

```text
Phase 1
  RET-001..004
  TIME-001..004
  EPI-001..004

Phase 2
  EXP-001..003
  SKILL-001..003
  CAUSAL-001..003

Phase 3
  X-001..003
```

This produces all 24 Public Dev Templates.

---

# 114. Why This Order

Phase 1 requires mostly:

```text
observe
respond
deterministic evaluators
```

Phase 2 adds:

```text
act
tool loop
Experience trajectories
causal replay
```

Phase 3 tests composition.

This lets the Runner become useful before every subsystem is complete.

---

# 115. Reference Runner Milestone 1

Must support:

```text
load Scenario JSON
validate mib-scenario.schema.json
reset Agent
deliver Timeline
deliver respond Probe
exact/set-match evaluator
produce basic RunResult
```

Enough for early Recall/Time/Belief Dev scenarios.

---

# 116. Reference Runner Milestone 2

Add:

```text
Runner-managed tools
act loop
World Simulator
world-state evaluator
trajectory evaluator
```

Enough for Experience/Skill.

---

# 117. Reference Runner Milestone 3

Add:

```text
replay-based ablation
condition pairing
causal metrics
Template aggregation
Dimension aggregation
mib-report.schema.json
```

Enough for meaningful end-to-end MIB-Core-0.1 Dev scoring.

---

# 118. Reference Runner Milestone 4

Add:

```text
hidden generator execution
private Scenario store
hierarchical bootstrap
Capability Card
leaderboard submission
```

Enough for official evaluation.

---

# 119. Scenario Validator Requirements

Before execution, the validator should enforce at least:

```text
JSON Schema validity
unique IDs
reference resolution
timeline consistency
hidden-field policy
Probe/evaluator resolution
ablation target resolution
dimension-weight sanity
causal-pair replay viability
```

Canonical Pack build should fail on validation errors.

---

# 120. Pack Validator Requirements

At Pack level, validate:

```text
60 Template inventory
24/30/6 visibility split
Suite counts
dimension coverage
causal coverage
LLM judge weighted fraction
required negative-transfer count
required unknown count
required stale/harm count
required group-ablation count
```

This prevents accidental benchmark drift.

---

# 121. Score Validator Requirements

`mib verify-score` should verify:

```text
Probe → Scenario aggregation
Scenario Instance → Template aggregation
Template → Dimension aggregation
dimension weight sum
MIB Score
coverage
causal metric formulas
global penalties if any
```

It should report mismatches without rerunning the Agent.

---

# 122. Development Report

A local Dev report SHOULD clearly say:

```text
Official: false
Partial: true or development
Visibility: public
```

to avoid screenshots of Dev scores being misrepresented as leaderboard results.

---

# 123. Official Report

Official report SHOULD contain:

```text
MIB-Core-0.1 Score
95% CI
six Dimension Scores
causal diagnostics
coverage = 100%
execution failure rate
efficiency
warnings
```

Hidden raw scenario content may be redacted.

---

# 124. Capability Card Example

```text
MIB — Memory Intelligence Benchmark
════════════════════════════════════════════

Profile
  MIB-Core-0.1

Track
  A — Memory System

Scale
  MIB-M

MIB Score
  78.4
  95% CI [76.9, 79.8]

Retention & Retrieval       90.1
Temporal Memory             82.0
Epistemic Memory            70.2
Experience Memory           79.8
Skill Learning & Transfer   76.4
Causal Memory Impact        73.7

Memory Benefit             +24.8 pp
Memory Harm                  4.9 pp
Net Memory Gain            +19.9 pp
Irrelevant Stability        95.2
Negative Transfer Rate       9.1%
Error Recurrence Rate        7.4%

Coverage
  100%

Execution Failure Rate
  0.3%
```

---

# 125. Benchmark Warning Examples

Possible warnings:

```text
high_stale_memory_adoption
weak_source_attribution
high_negative_transfer
high_error_recurrence
low_causal_coverage
execution_instability
non_discriminative_template
causal_pair_invalid
```

Warnings do not automatically change score unless Scenario/Profile policy says so.

---

# 126. Score Publication Policy

A public leaderboard entry should display:

```text
point estimate
95% CI
Track
Profile
Scale
system identity
date
```

and allow expansion to the full Capability Card.

A difference of:

```text
0.1
```

should not be visually presented as decisive if uncertainty overlaps.

---

# 127. Paired System Comparison

Track A comparison should evaluate systems on the same hidden Instances.

Pair by:

```text
Template
Instance seed
repetition seed
condition
```

System delta analysis uses paired bootstrap.

This improves statistical power.

---

# 128. Statistical Default

Official v0.1 recommendation:

```text
95% confidence interval

hierarchical bootstrap
10,000 resamples

resample:
  Templates
  Instances within Template
  repetitions where applicable

preserve:
  causal pairs
```

This follows `MIB-Specification.md`.

---

# 129. Small-Sample Caveat

v0.1 intentionally prioritizes:

```text
semantic breadth
```

over thousands of instances per Template.

Therefore confidence intervals may remain moderately wide.

This is preferable to pretending that 10,000 lexical variants of one easy recall task provide broad memory evidence.

---

# 130. Template Retirement

A Template should be retired or revised if:

```text
No-Memory approaches ceiling
Full-Context remains low
generator leaks answer
evaluator proves unstable
tool domain introduces unrelated difficulty
participant hardcoding invalidates discriminativeness
```

Retirement requires Pack versioning and leaderboard recomputation policy.

---

# 131. Benchmark Evolution

Expected progression:

```text
MIB-Core-0.1
    ↓
better hidden generators
more calibrated templates
    ↓
MIB-Core-0.2
    ↓
Selective Forgetting
Prospective & Self Memory
    ↓
MIB-Full-1.0
```

Scores across materially different Profiles are not directly comparable.

---

# 132. Deferred v0.2 Candidate Suites

Likely next additions:

```text
MIB-Forget
MIB-Prospective
MIB-Self
```

Potential v0.3+:

```text
MIB-Cross-Agent
MIB-Privacy
MIB-Multimodal
```

This Test Plan should not pre-commit exact future weights.

---

# 133. Repository Layout After v0.1

Recommended:

```text
MIB/
├── MIB-Specification.md
├── MIB-Specification.md
├── MIB-Agent-Adapter.md
├── MIB-Specification.md
├── MIB-v0.1-Test-Plan.md
│
├── schemas/
│   ├── mib-scenario.schema.json
│   └── mib-report.schema.json
│
├── scenarios/
│   └── dev/
│       ├── recall/
│       ├── time/
│       ├── epistemic/
│       ├── experience/
│       ├── skill/
│       ├── causal/
│       └── cross/
│
├── generators/
│   └── public/
│
├── evaluators/
├── runner/
├── adapters/
├── reports/
└── leaderboard/
```

Private hidden material remains outside the public repository.

---

# 134. First Implementation Backlog

Recommended implementation order:

```text
1. Scenario Validator
2. Agent Adapter request/response types
3. Basic Runner
4. deterministic evaluators
5. Public RET/TIME/EPI scenarios
6. World Simulator
7. tool-loop evaluator
8. Public EXP/SKILL scenarios
9. replay ablation
10. Public CAUSAL scenarios
11. score aggregation
12. mib-report generation
13. Public CROSS scenarios
14. bootstrap statistics
15. hidden generator infrastructure
```

---

# 135. Launch Gate

MIB-Core-0.1 SHOULD NOT be presented as a serious public leaderboard until:

```text
[ ] Agent Adapter conformance suite exists
[ ] all 24 Public Dev Templates run end-to-end
[ ] all 36 official Templates pass Scenario validation
[ ] Full-Context / No-Memory calibration completed
[ ] causal-pair validity tested
[ ] score recomputation works
[ ] report schema validates real output
[ ] at least 4 baseline systems evaluated
[ ] score spread is non-trivial
[ ] LLM judge dependence is within target
[ ] hidden leakage audit passes
[ ] benchmark cost measured
[ ] statistical intervals produced
```

---

# 136. Baseline Publication Gate

Before claiming that MIB distinguishes memory systems, publish at least:

```text
No Memory baseline
Full Context baseline
Simple Retrieval Memory
one stronger memory architecture
```

Preferably include:

```text
Summary Memory
Graph Memory
Episodic/Procedural Memory
```

if implementable.

---

# 137. Scientific Validation Questions

Before v0.1 release, maintainers should answer:

```text
Do Recall scores correlate too strongly with every other dimension?

Does Temporal separate update-aware systems?

Does Epistemic separate source-aware systems?

Does Experience predict lower Error Recurrence?

Does Skill predict future task transfer?

Does Causal score correlate with, but remain distinct from, full performance?

Do irrelevant-memory tests detect interference?

Do harmful-memory tests expose stale/poisoned behavior?

Do private holdouts change rankings materially?
```

If all dimensions collapse into one general-model factor, the benchmark needs redesign.

---

# 138. Factor Separation Goal

MIB does not require statistically orthogonal dimensions.

Real cognitive capabilities interact.

But v0.1 should avoid:

```text
all six scores being nearly identical
```

for every system.

Useful profiles should reveal different strengths and weaknesses.

---

# 139. Model Confound Analysis

Track A should be the main tool for studying memory architecture.

Track B may be heavily influenced by base-model intelligence.

For Track B reports, MIB should emphasize:

```text
absolute MIB Score
+
causal metrics
+
model identity
```

rather than pretending to isolate memory-system quality.

---

# 140. Full-Context Ceiling Analysis

If a Track A fixed model has:

```text
Full Context = 70
```

on a difficult Template, a memory system cannot reasonably be expected to reach 100.

Such Templates should be revised or interpreted using calibration diagnostics such as Memory Gap Closure.

---

# 141. No-Memory Floor Analysis

If:

```text
No Memory = 80
```

then the task does not strongly require memory.

Even if it appears semantically memory-related, it is weak benchmark evidence.

Hidden random values and synthetic world state should reduce this failure mode.

---

# 142. Leakage Through General Knowledge

Avoid facts such as:

```text
Paris is in France
Tokyo is UTC+9
```

as the only reason an answer is correct.

Use synthetic benchmark-local facts when memory dependency matters.

General knowledge may be used as incidental task context but not as the hidden answer.

---

# 143. Leakage Through Common Workflow Knowledge

For Skill scenarios, avoid procedures that the base model already knows from training.

Example weak Skill test:

```text
"Save a file before closing."
```

Better:

```text
benchmark-local hidden precondition
revealed through lived tool interaction
```

This makes learning measurable.

---

# 144. Tool Error Semantics

Tool failures should be deterministic under Scenario seed.

A failure is part of the Experience when:

```text
Scenario intends it
```

A random infrastructure failure is not.

Runner and simulator errors are excluded as invalid benchmark execution, not learned Experience.

---

# 145. Experience Attribution

The benchmark does not require the Agent to say:

```text
"I learned this from Experience E7."
```

Successful future behavior is sufficient.

Optional attribution may improve diagnostics but does not replace causal ablation.

---

# 146. Hidden Chain-of-Thought Policy

No v0.1 Scenario may require private chain-of-thought for scoring.

Allowed:

```text
concise explanation
observable action
structured status
source attribution
```

Disallowed requirement:

```text
reveal internal reasoning trace
```

---

# 147. Safety of Benchmark Content

v0.1 simulated tasks should remain benign.

The benchmark does not need dangerous tool domains to measure memory intelligence.

Use:

```text
synthetic services
synthetic calendars
synthetic documents
synthetic workflows
```

---

# 148. Performance vs Efficiency

Official ranking is by:

```text
MIB-Core-0.1 Score
```

Efficiency is displayed separately.

Possible secondary views:

```text
lowest cost among ≥80 score
lowest latency among ≥75 score
Pareto frontier
```

Do not merge these into the primary MIB Score.

---

# 149. Public Narrative

The v0.1 benchmark can be described externally as:

> **MIB-Core-0.1 tests whether an Agent can retain information, track change, preserve belief/source distinctions, learn from Experience, transfer Skills, and demonstrate that relevant memory causally improves future behavior.**

This is a more accurate description than:

> "A long-context memory QA benchmark."

---

# 150. Core Principle

Every v0.1 Template should ultimately answer some version of:

```text
What part of the past should matter now?

What part should not matter?

What changed?

What was learned?

What would happen if the relevant past were removed?
```

If a Scenario cannot answer those questions clearly, it is probably not a good MIB Scenario.

---

# 151. v0.1 Invariants

1. `MIB-Core-0.1` is a six-dimension Profile.
2. v0.1 has six primary Suites plus Cross integration.
3. The canonical plan contains 60 Scenario Templates.
4. 24 are Public Dev.
5. 30 are Hidden Eval.
6. 6 are Private Holdout.
7. Only Hidden Eval + Private Holdout determine official score.
8. Public Dev is excluded from official leaderboard score.
9. Official evaluation uses MIB-M by default.
10. Every official Template runs Full condition.
11. Causal intervention has broad cross-Suite coverage.
12. Relevant ablation is preferred over No-Memory for causal specificity.
13. Full-Context and No-Memory are required during Template calibration.
14. Templates should be memory-discriminative.
15. Future Probe leakage is prohibited.
16. Hidden ground truth is never Agent-visible.
17. Random values should defeat pretraining lookup.
18. Direct recall must not dominate the benchmark.
19. Temporal tests distinguish current and historical state.
20. Epistemic tests include unknown/conflict/correction.
21. Experience tests preserve action/observation/outcome structure.
22. Skill tests include applicability and negative transfer.
23. Failed Experience is first-class.
24. Harmful/stale memory is explicitly tested.
25. Irrelevant-memory stability is explicitly tested.
26. Group ablation is represented.
27. Black-box Agents remain supported.
28. Private chain-of-thought is never required.
29. World-state evaluation is preferred for action outcomes.
30. LLM judge dependence is bounded and disclosed.
31. Template-first aggregation prevents instance-count domination.
32. Official score requires full Profile coverage.
33. Execution failures remain visible.
34. Confidence intervals accompany official score.
35. Track A and Track B remain separate.
36. Efficiency remains separate from capability.
37. Hidden material is separated from the public repo.
38. Score recomputation must be auditable.
39. Pack evolution is versioned.
40. MIB evaluates whether the right past changes the right future.

---

# 152. Final Principle

MIB v0.1 should be small enough to build, but deep enough that a vector database with good semantic search cannot automatically win.

A successful v0.1 should reveal a progression like:

```text
Can you retrieve the past?
        ↓
Can you understand how it changed?
        ↓
Can you remember why you believe it?
        ↓
Can you remember what happened during action?
        ↓
Can you turn Experience into reusable Skill?
        ↓
Can we prove that the memory actually changed future behavior?
```

That progression is the first executable definition of:

> **Memory Intelligence**

---

# Appendix A — 60-Template Inventory

| ID | Suite | Visibility | Short Name |
|---|---|---|---|
| MIB-RET-001 | Recall | Dev | Direct Delayed Recall |
| MIB-RET-002 | Recall | Dev | Implicit Attribute Application |
| MIB-RET-003 | Recall | Dev | Multi-Hop Memory Composition |
| MIB-RET-004 | Recall | Dev | Identity Collision |
| MIB-RET-005 | Recall | Hidden | Distractor-Heavy Rare Fact |
| MIB-RET-006 | Recall | Hidden | Near-Match Confusor |
| MIB-RET-007 | Recall | Hidden | Distributed Entity Bundle |
| MIB-RET-008 | Recall | Hidden | Sparse Cue Paraphrase |
| MIB-RET-009 | Recall | Hidden | Relevant Document Among Chatter |
| MIB-RET-010 | Recall | Holdout | Retrieval Holdout Composition |
| MIB-TIME-001 | Time | Dev | Current Value After Update |
| MIB-TIME-002 | Time | Dev | Historical Value Before Update |
| MIB-TIME-003 | Time | Dev | Planned vs Completed Change |
| MIB-TIME-004 | Time | Dev | Correction vs Reversal |
| MIB-TIME-005 | Time | Hidden | Multiple Successive Revisions |
| MIB-TIME-006 | Time | Hidden | Temporary Validity Window |
| MIB-TIME-007 | Time | Hidden | Reversion to Prior State |
| MIB-TIME-008 | Time | Hidden | Late-Arriving Evidence |
| MIB-TIME-009 | Time | Hidden | Stale Operational Rule Trap |
| MIB-TIME-010 | Time | Holdout | Temporal Holdout Composition |
| MIB-EPI-001 | Belief | Dev | Unknown vs False |
| MIB-EPI-002 | Belief | Dev | Explicit Self-Correction |
| MIB-EPI-003 | Belief | Dev | Source Disagreement |
| MIB-EPI-004 | Belief | Dev | Tool Evidence vs Human Statement |
| MIB-EPI-005 | Belief | Hidden | Derived Evidence Multiplication |
| MIB-EPI-006 | Belief | Hidden | Tentative Statement |
| MIB-EPI-007 | Belief | Hidden | Trusted Source Conflict |
| MIB-EPI-008 | Belief | Hidden | Historical Attribution After Correction |
| MIB-EPI-009 | Belief | Hidden | Temporal + Epistemic Conflict |
| MIB-EPI-010 | Belief | Holdout | Epistemic Holdout Composition |
| MIB-EXP-001 | Experience | Dev | Failure and Recovery |
| MIB-EXP-002 | Experience | Dev | Outcome Disambiguation |
| MIB-EXP-003 | Experience | Dev | Hidden Preconditions From Prediction Error |
| MIB-EXP-004 | Experience | Hidden | Failed vs Successful Attempt Selection |
| MIB-EXP-005 | Experience | Hidden | Long Multi-Step Ordering |
| MIB-EXP-006 | Experience | Hidden | Known Failure Recurrence |
| MIB-EXP-007 | Experience | Hidden | Compare Two Experiences |
| MIB-EXP-008 | Experience | Holdout | Experience Holdout Composition |
| MIB-SKILL-001 | Skill | Dev | Learn a Hidden Precondition |
| MIB-SKILL-002 | Skill | Dev | Surface-Changed Positive Transfer |
| MIB-SKILL-003 | Skill | Dev | Non-Matching Negative Transfer |
| MIB-SKILL-004 | Skill | Hidden | Counterexample Refines Skill |
| MIB-SKILL-005 | Skill | Hidden | Conditional Exception Handling |
| MIB-SKILL-006 | Skill | Hidden | Competing Learned Skills |
| MIB-SKILL-007 | Skill | Hidden | Skill After Environment Change |
| MIB-SKILL-008 | Skill | Holdout | Skill Holdout Composition |
| MIB-CAUSAL-001 | Causal | Dev | Relevant-Memory Ablation |
| MIB-CAUSAL-002 | Causal | Dev | Irrelevant-Memory Stability |
| MIB-CAUSAL-003 | Causal | Dev | No-Memory Gap |
| MIB-CAUSAL-004 | Causal | Hidden | Stale-Memory Resistance |
| MIB-CAUSAL-005 | Causal | Hidden | Harmful Remembered Instruction |
| MIB-CAUSAL-006 | Causal | Hidden | Redundant Relevant Evidence |
| MIB-CAUSAL-007 | Causal | Hidden | Synergistic Memory Set |
| MIB-CAUSAL-008 | Causal | Holdout | Causal Holdout Composition |
| MIB-X-001 | Cross | Dev | Preference Correction to Future Action |
| MIB-X-002 | Cross | Dev | Source Conflict + Time + Action |
| MIB-X-003 | Cross | Dev | Experience → Skill → Non-Applicability |
| MIB-X-004 | Cross | Hidden | Current/History Under Interference |
| MIB-X-005 | Cross | Hidden | Wrong-Source Experience Contamination |
| MIB-X-006 | Cross | Hidden | Uncertainty Before Action |

---

# Appendix B — Visibility Summary

```text
Public Dev
  24

Hidden Eval
  30

Private Holdout
   6

Total
  60
```

Official scoring set:

```text
Hidden Eval + Private Holdout
= 36 Templates
```

---

# Appendix C — Candidate MIB-Core-0.1 Profile

```yaml
id: MIB-Core-0.1
version: 0.1.0

dimensions:
  retention_retrieval:
    weight: 0.146341

  temporal_memory:
    weight: 0.158537

  epistemic_memory:
    weight: 0.182927

  experience_memory:
    weight: 0.182927

  skill_learning_transfer:
    weight: 0.182927

  causal_memory_impact:
    weight: 0.146341

required_coverage: 1.0

official_scale:
  MIB-M

hidden_instances_per_template:
  4

repetitions_per_condition:
  2

statistics:
  confidence_level: 0.95
  bootstrap:
    method: hierarchical_bootstrap_percentile
    resamples: 10000
    preserve_causal_pairs: true
```

The rounded YAML weights above should be stored with higher precision in a future machine-readable Profile artifact.

---

# Appendix D — Candidate Calibration Gate

```text
For each official Template:

Full Context mean
    target ≥ 0.80

No Memory mean
    target ≤ 0.60

Memory Discriminativeness Index
    target ≥ 0.25

Future Probe leakage
    must pass

Scenario validation
    must pass

Causal replay validity
    must pass where causal

LLM judge dependence
    within Pack budget
```

---

# Appendix E — Next Artifacts

After this Test Plan, the highest-value implementation artifacts are:

```text
1. MIB-Agent Adapter request/response schemas
2. MIB Profile machine-readable file
3. Scenario Pack manifest schema
4. first 24 Public Dev Scenario Templates
5. Scenario Validator
6. reference Runner
```

A practical next step is to implement the **first Public Dev slice**:

```text
MIB-RET-001..004
MIB-TIME-001..004
MIB-EPI-001..004
```

These 12 Templates are enough to test:

```text
Scenario loading
Timeline delivery
future Probe isolation
respond()
deterministic evaluation
basic ablation
report generation
```

before the World Simulator and tool-driven Experience/Skill suites are added.

---

# Appendix F — Transfer and Reality Test Surfaces

Three test surfaces were added alongside the v0.1 plan. All three are supplemental: none of them may change a `MIB-Core-0.1` score, and the regression suite asserts that directly.

## F.1 Transfer Support Annotation

`tests/test_transfer_support.py`

```text
the 24-Template Public Dev pack validates unchanged and gains no new findings
a valid annotation parses and validates against both schemas
broken event, Probe, and Ability references fail semantic validation
a negative control cannot declare a positive-transfer distance
an oracle artifact restating a Probe answer fails
no annotation reaches any Agent request
public redaction leaks no Ability ID
annotation presence does not move a score or break verify-score
```

## F.2 Transfer diagnostics and the 2x2 matrix

`tests/test_transfer_diagnostics.py`, `tests/test_transfer_matrix.py`

```text
an unannotated pack produces a report with no diagnostics extension
disabling diagnostics leaves aggregates, causal metrics, and coverage identical
diagnostic cells never appear in results.runs or in execution counts
Template-first aggregation: four Probes in one Template do not outvote one
Formation and Routing efficiency separate the six fixture failure modes
insufficient oracle headroom is unknown, not zero
a black-box Agent still gets Routing Efficiency and the uptake ceiling
public redaction exposes aliases and aggregates only
```

## F.3 MIB-R Reality Track

`tests/test_reality_track.py`

```text
the prototype pack meets its acceptance counts and relation coverage
every declared convention is load-bearing
task and graph digest mismatches fail loudly
conditions are paired on everything but memory state
the irrelevant control never removes load-bearing experience
a capped irrelevant control is reported, not hidden
healthy / naive / over-generalizing systems produce distinct profiles
signed deltas are not absolute values
MIB-R is its own result family and cross-family comparison raises
the public report withholds per-task rows and graph structure
the attestation binds pack, graph, and environment and carries no score
```

## F.4 Development pack layout

The Transfer Diagnostic Dev Pack lives in `scenarios/transfer/`, deliberately outside `scenarios/dev/`. The Runner globs a pack root recursively, so placing it inside the Public Dev tree would silently enlarge the `MIB-Core-0.1-Dev-M3` pack beyond its 24 Templates and move its score.
