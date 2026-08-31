# MIB Architecture

## Memory Intelligence Benchmark

**Version:** 0.1-draft  
**Status:** Architecture Proposal / Pre-Specification Draft

---

# 0. Executive Summary

MIB — **Memory Intelligence Benchmark** — is a benchmark architecture for measuring the memory capability of intelligent agents.

MIB does **not** primarily ask:

> How much of the past can the system retrieve?

It asks:

> **Can the right parts of the past change future cognition and behavior in the right way?**

This distinction is foundational.

A system may store every interaction and retrieve relevant passages with high recall while still demonstrating weak memory intelligence if stale memories override current reality, contradictory sources collapse into one fact, successful procedures transfer into the wrong situations, or remembered information never changes future decisions.

MIB therefore treats memory as a **causal cognitive capability**, not merely a storage or retrieval subsystem.

```text
Past Interaction / Experience
            ↓
        Formation
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

MIB evaluates this entire cross-time loop.

The benchmark is architecture-neutral. A participant may use vector memory, summary memory, graph memory, episodic memory, relational memory, procedural memory, full-context replay, KIP-based memory, learned memory modules, or hybrid systems.

MIB does not require KIP. KIP v2 provides part of the conceptual inspiration — especially the separation between Knowledge, Evidence, Assertion, Experience, Skill, mnemonic state, time, provenance, and Governance — but MIB is an independent benchmark for any long-term memory system.

The primary result is:

```text
MIB Score
0 ─────────────────────────── 100
```

accompanied by a multidimensional capability profile rather than a single opaque number.

---

# 1. Core Thesis

A memory system should not be judged by how much of the past it can retrieve, but by whether the right parts of the past change the future in the right way.

Conceptually:

\[
Memory = Past\ State\ Capable\ of\ Conditioning\ Future\ Computation
\]

and:

\[
Learning = Durable,\ Context\text{-}Appropriate\ Behavioral\ Change\ Caused\ by\ Prior\ Experience
\]

This leads to three requirements.

## 1.1 Memory must have causal consequences

If removing a supposedly relevant memory does not affect a relevant future decision or behavior, the item may be stored history but is not functioning as memory for that task.

## 1.2 Memory must be context-sensitive

A memory that improves behavior in one context but harms unrelated contexts is not strong memory intelligence.

## 1.3 Memory must preserve distinctions

When relevant, a capable system should distinguish:

```text
current truth vs historical truth
statement vs accepted belief
source vs provenance
Event vs Experience
Knowledge vs Skill
confidence vs trust
memory accessibility vs importance
utility vs authority
```

Flattening these distinctions can produce retrieval success while causing cognitive failure.

---

# 2. What MIB Measures

The evaluation unit is:

```text
Agent + Long-Term Memory System
```

MIB evaluates whether the system can:

1. retain relevant information;
2. retrieve it when needed;
3. reason over changes through time;
4. preserve source and epistemic distinctions;
5. reconstruct meaningful experience;
6. learn reusable procedures;
7. forget selectively without destroying history;
8. remember commitments and self-relevant state;
9. resist stale, harmful, or irrelevant memory;
10. demonstrate causal benefit from memory.

MIB is not primarily a benchmark for raw LLM intelligence, coding ability, embedding quality, database throughput, vector search quality in isolation, or KIP protocol conformance.

---

# 3. Benchmark Tracks

## 3.1 Track A — Memory System Track

Purpose:

> Isolate the contribution of the memory system itself.

The benchmark fixes as much as practical:

```text
base model
agent prompt
reasoning policy
tools
environment
task interface
evaluation policy
```

Participants replace only the memory system.

```text
Fixed Agent
   ├── Memory A
   ├── Memory B
   ├── Memory C
   └── Memory D
```

Required reporting includes base model, agent version, prompt hash, tool set, environment version, memory system version, and MIB suite version.

## 3.2 Track B — Integrated Agent Track

Purpose:

> Measure the final memory intelligence of a complete agent.

Participants may supply model, agent policy, memory, retrieval policy, consolidation policy, and tool strategy.

Track B MUST NOT be directly ranked against Track A as if the two measured the same thing.

## 3.3 Optional Track C — Memory Component Diagnostics

Systems that expose a memory API may participate in deeper diagnostics such as precise record ablation, snapshot comparison, retrieval trace analysis, storage measurement, write amplification, and influence tracing.

Track C is optional and MUST NOT be required for primary participation.

---

# 4. Capability Model

MIB v1 is organized around eight primary dimensions:

```text
1. Retention & Retrieval
2. Temporal Memory
3. Epistemic Memory
4. Experience Memory
5. Skill Learning & Transfer
6. Selective Forgetting
7. Prospective & Self Memory
8. Causal Memory Impact
```

Default proposed weights:

| Dimension | Weight |
|---|---:|
| Retention & Retrieval | 12 |
| Temporal Memory | 13 |
| Epistemic Memory | 15 |
| Experience Memory | 15 |
| Skill Learning & Transfer | 15 |
| Selective Forgetting | 10 |
| Prospective & Self Memory | 8 |
| Causal Memory Impact | 12 |
| **Total** | **100** |

Weights are benchmark policy and may change between major versions.

---

# 5. Dimension 1 — Retention & Retrieval

Question:

> Can the system recover relevant past cognition after time, interference, and context shift?

MIB distinguishes Direct Recall, Implicit Recall, Multi-Hop Recall, Distractor Resistance, and Identity Precision.

Example direct recall:

```text
Past:   My dog's name is Pixel.
Future: What is my dog's name?
```

Example implicit recall:

```text
Past:
  Dog = Pixel
  Breed = Chihuahua
  Weight = 2.3 kg

Future:
  Should I buy the small or large harness?
```

Example multi-hop recall:

```text
Alice works at Orbit.
Orbit's office is in Tokyo.
Tokyo uses UTC+9.

Question:
What timezone should I use when scheduling with Alice?
```

MIB scores the final cognitive result, not only internal Recall@K.

---

# 6. Dimension 2 — Temporal Memory

Question:

> Can the system represent change rather than merely remember isolated facts?

Example:

```text
T1: My timezone is UTC+8.
T2: I am moving to London next month.
T3: I have arrived in London. My timezone is now UTC+1.
```

Current query:

```text
What is my timezone?
→ UTC+1
```

Historical query:

```text
What timezone did I use before moving?
→ UTC+8
```

A last-write-wins memory can answer only part of this correctly.

Subscores:

```text
Current State Accuracy
Historical State Accuracy
Transition Understanding
Temporal Ordering
Valid-Time Reasoning
Staleness Avoidance
```

---

# 7. Dimension 3 — Epistemic Memory

Question:

> Does the system remember not only content, but what kind of cognitive commitment the content represents?

This is one of MIB's central differentiators.

## 7.1 Statement vs Truth

```text
Alice: The meeting is at 3 PM.
Bob:   I think it is at 4 PM.
Calendar: 15:00
```

The system should preserve that Alice said 3, Bob said 4, and authoritative calendar evidence supports 3.

## 7.2 Correction

```text
Past:  My birthday is May 12.
Later: Sorry — I meant May 21.
```

Current answer should be May 21, while historical reasoning should preserve the earlier statement and correction.

## 7.3 Contradiction

```text
Alice: I prefer tea.
Bob:   Alice hates tea.
Alice later: I still prefer tea.
```

The system should preserve speaker, source, disagreement, corroboration, and correction vs third-party contradiction.

## 7.4 Unknown vs False

If no evidence exists about whether Alice is vegetarian, the correct behavior is `unknown` or `insufficient information`, not `no`.

## 7.5 Evidence Independence

```text
one message
→ summary A
→ summary B
→ graph fact
```

must not automatically become three independent sources.

Subscores:

```text
Source Attribution
Correction Handling
Contradiction Handling
Abstention / Unknown
Evidence Preference
Historical Attribution
Evidence Independence
```

MIB may expose an **Epistemic Integrity Score** as a named subscore.

---

# 8. Dimension 4 — Experience Memory

Question:

> Can the system preserve useful state-action-observation-outcome trajectories rather than only isolated facts?

Example experience:

```text
Goal: deploy v2
Action: run migration
Observation: migration succeeded
Action: restart service
Observation: missing-column error
Action: inspect migration
Observation: migration applied to wrong database
Action: switch target database
Outcome: success
```

Future task:

```text
Another deployment fails with a missing-column error.
What should you check first?
```

A strong experience memory should recover the reusable trajectory rather than only matching keywords.

Subscores:

```text
Goal Recall
Trajectory Recall
Action/Observation Ordering
Outcome Recall
Failure/Recovery Recall
Prediction Error Recall
Experience Compression Quality
```

---

# 9. Dimension 5 — Skill Learning & Transfer

Question:

> Can the system compile experience into reusable behavior?

Suppose repeated tasks reveal:

```text
Before Save:
  select workspace.
```

Future tasks vary in page, content, entity, and tool state but preserve the hidden procedural rule.

MIB measures:

```text
Skill Acquisition
Positive Transfer
Failure Avoidance
Applicability Detection
Counterexample Use
Negative Transfer Resistance
```

Negative transfer is essential. If a new environment does not require workspace selection, blindly applying the old Skill should reduce score.

A successful example is not enough; a capable memory system must understand applicability.

---

# 10. Dimension 6 — Selective Forgetting

Question:

> Can the system stop obsolete memory from controlling current behavior while preserving history when needed?

Example:

```text
T1: API uses JWT.
T2: API migrated to session authentication. JWT must no longer be used.
```

Current task:

```text
Implement authentication.
→ use sessions
```

Historical query:

```text
What did the API use before migration?
→ JWT
```

This tests:

```text
operational forgetting
+
historical preservation
```

Subscores:

```text
Stale Memory Suppression
Historical Preservation
Distractor Suppression
Signal Preservation
Retention Prioritization
```

---

# 11. Dimension 7 — Prospective & Self Memory

## 11.1 Prospective Memory

```text
Past:
When Sarah joins the next call, remind me to ask about the contract.

Much later:
Sarah joined the call.
```

The agent should react to the trigger without requiring the user to explicitly query the old instruction.

## 11.2 Self Memory

Suppose the agent repeatedly learns:

```text
I cannot access private GitHub repositories without a connected capability.
```

Later:

```text
Inspect my private repository.
```

The agent should preserve capability continuity and avoid pretending it has access.

MIB also tests the inverse failure: remembered content such as `I am admin` must not magically grant real authority.

Subscores:

```text
Prospective Triggering
Commitment Persistence
Capability Continuity
Self-Correction
Self-Limitation Recall
Authority Boundary
```

---

# 12. Dimension 8 — Causal Memory Impact

This is the architectural center of MIB.

Question:

> Did memory actually cause better future behavior?

MIB runs controlled variants of the same future task.

## 12.1 Full Memory

```text
Agent + complete relevant history
```

## 12.2 Relevant Memory Ablated

```text
Same Agent + specific relevant memory removed or masked
```

## 12.3 Irrelevant Memory Ablated

```text
Same Agent + irrelevant memory removed
```

## 12.4 Harmful / Stale Memory Present

```text
Same Agent + plausible but obsolete or misleading memory
```

Define:

\[
CMI = Performance_{full} - Performance_{relevant\_ablated}
\]

A positive CMI indicates that relevant memory materially improved behavior.

Ideally:

\[
Performance_{full} \approx Performance_{irrelevant\_ablated}
\]

The system should also resist stale facts, wrong-source memory, high-similarity irrelevant memory, out-of-context Skills, poisoned memory, and remote autobiographical memory.

---

# 13. Memory Benefit, Harm, and Net Gain

MIB SHOULD report causal metrics separately from the aggregate score.

## Memory Benefit

\[
MB = Performance_{full} - Performance_{relevant\_ablated}
\]

## Memory Harm

Approximate:

\[
MH = P(memory\ causes\ an\ otherwise\ avoidable\ error)
\]

## Net Memory Gain

\[
NMG = MB - MH
\]

Example:

```text
Memory Benefit     +28.4%
Memory Harm          5.2%
Net Memory Gain    +23.2%
```

---

# 14. Influence Precision

MIB introduces a concept beyond retrieval precision.

Question:

> Of the memories that influenced behavior, how many helped in the correct way?

Approximate:

\[
Influence\ Precision =
\frac{Helpful\ Memory\ Influences}{All\ Detected\ Memory\ Influences}
\]

A system may have excellent retrieval but poor Influence Precision because it injects too many irrelevant memories into decision-making.

Exact tracing may be available only in diagnostic tracks; black-box agents may use behavioral proxies.

---

# 15. Learning Curves

MIB SHOULD include longitudinal suites:

```text
Task 1
Task 2
Task 3
...
Task N
```

and measure `Performance(t)`.

Derived metrics:

## Learning Gain

\[
LG = Performance_{late} - Performance_{early}
\]

## Error Recurrence Rate

\[
ERR = \frac{Repeated\ Previously\ Learned\ Failure}{Relevant\ Opportunities}
\]

Strong experiential memory should reduce repeated known failure.

---

# 16. Scenario as the Fundamental Unit

MIB is not primarily a static QA dataset.

The fundamental unit is a **Memory Episode Program** describing a world unfolding through time.

```yaml
id: MIB-TIME-001

world:
  initial_state:
    user_timezone: "+08:00"

timeline:
  - t: 1
    type: interaction
    content: "My timezone is UTC+8."

  - t: 20
    type: interaction
    content: "I'm moving to London next month."

  - t: 50
    type: interaction
    content: "I've arrived. My timezone is now UTC+1."

  - t: 60
    type: distractor_batch
    count: 200

probes:
  - id: current
    type: factual
    ask: "What's my timezone now?"
    expected: "+01:00"

  - id: historical
    type: temporal
    ask: "What timezone did I use before moving?"
    expected: "+08:00"

ablations:
  - remove: [event:t50]
  - remove: [unrelated_distractors]
```

The agent **lives through the scenario** rather than receiving a preassembled context window.

---

# 17. Scenario Lifecycle

```text
RESET
  ↓
SEED WORLD
  ↓
PAST EPISODES
  ↓
INTERFERENCE / DISTRACTORS
  ↓
OPTIONAL CONSOLIDATION WINDOW
  ↓
FUTURE PROBE / TASK
  ↓
OUTCOME
  ↓
ABLATION RE-RUNS
  ↓
EVALUATION
```

The future probe MUST NOT be leaked during memory formation unless the scenario explicitly tests planning for a known future task.

---

# 18. No Future-Question Leakage

Critical invariant:

> The memory system should not know which future probe will be asked when deciding what to remember.

Incorrect:

```text
Tell the system:
You will later be asked for Alice's timezone.
```

Correct:

```text
Past episode generated
→ agent experiences it
→ memory formation completes
→ future probe sampled later
```

This tests genuine selection, compression, salience, and retention.

---

# 19. Scenario Families

MIB SHOULD define parameterized templates rather than only fixed instances.

Examples:

```text
attribute update
identity collision
source disagreement
explicit correction
temporal transition
multi-hop relation
failure/recovery
hidden workflow rule
Skill counterexample
prospective commitment
self-limitation
stale-memory trap
irrelevant-memory overload
cross-agent imported memory
```

Templates may randomize names, values, dates, order, distractors, task wording, tools, environment state, and failure conditions.

---

# 20. Public and Hidden Evaluation

MIB SHOULD publish:

```text
Public Dev Set
Hidden Evaluation Set
```

The public set supports adapter development and research. The hidden set protects leaderboard integrity and reduces template hardcoding.

Hidden evaluation SHOULD use unseen scenario instantiations and MAY include unseen template compositions.

---

# 21. Benchmark Scales

MIB defines cognitive horizon rather than only token length.

## MIB-S

```text
50–100 meaningful events
low-to-moderate interference
short runtime
```

For debugging and CI.

## MIB-M

```text
~1,000 meaningful events
many distractors
multiple revisions
multiple Experiences and Skills
```

Primary leaderboard scale.

## MIB-L

```text
10,000+ meaningful events
many entities
multiple temporal epochs
repeated environment tasks
heavy interference
long-range transfer
```

Stress scale.

Reports SHOULD include event count, meaningful state changes, Experience count, distractor count, and token count.

---

# 22. Benchmark Runner Architecture

```text
                  ┌─────────────────────┐
                  │  Scenario Registry  │
                  └─────────┬───────────┘
                            │
                  ┌─────────▼───────────┐
                  │   World Simulator   │
                  │ state + clock + RNG │
                  └─────────┬───────────┘
                            │
                  ┌─────────▼───────────┐
                  │   Benchmark Driver  │
                  └─────────┬───────────┘
                            │
          ┌─────────────────┴──────────────────┐
          │                                    │
┌─────────▼──────────┐              ┌──────────▼──────────┐
│    Agent Adapter   │              │ Ablation Controller │
└─────────┬──────────┘              └──────────┬──────────┘
          │                                    │
┌─────────▼──────────┐                         │
│ Agent + Memory     │◄────────────────────────┘
└─────────┬──────────┘
          │
          ▼
┌────────────────────┐
│  Output / Actions  │
└─────────┬──────────┘
          │
          ▼
┌────────────────────┐
│    Evaluators      │
│ deterministic      │
│ world-state        │
│ semantic           │
│ trajectory         │
│ optional LLM judge │
└─────────┬──────────┘
          │
          ▼
┌────────────────────┐
│   Scoring Engine   │
└─────────┬──────────┘
          │
          ▼
┌────────────────────┐
│ MIB Capability Card│
└────────────────────┘
```

---

# 23. Scenario Registry

The registry stores scenario/template definitions, version, difficulty, dimension tags, required capabilities, seed policy, ground-truth constraints, ablations, and scoring policy.

Stable IDs SHOULD follow:

```text
MIB-RET-001
MIB-TIME-001
MIB-EPI-001
MIB-EXP-001
MIB-SKILL-001
MIB-FORGET-001
MIB-PROS-001
MIB-SELF-001
MIB-CAUSAL-001
MIB-X-001
```

---

# 24. World Simulator

The World Simulator owns hidden ground truth:

```text
world state
virtual time
tool state
entity state
environment transitions
task success/failure
random seed
```

The agent cannot directly inspect hidden ground truth; it observes consequences.

Example:

```text
Agent calls deploy()
→ simulator evaluates actual state
→ returns startup_error
```

This lets MIB evaluate behavior against reality rather than only language similarity.

---

# 25. Virtual Time

MIB SHOULD support a virtual clock so days, weeks, months, or years can be simulated without real waiting.

Virtual time enables testing:

```text
staleness
commitments
validity
forgetting
long-term updates
maintenance schedules
```

The agent receives time only through its normal interface.

---

# 26. Agent Adapter

The primary adapter MUST remain minimal.

```typescript
interface MIBAgent {
  reset(run: RunContext): Promise<void>;
  observe(input: Observation): Promise<void>;
  respond(input: AgentInput): Promise<AgentOutput>;
  act(task: Task): Promise<ActionResult>;
}
```

The implementation may internally write memory, summarize, consolidate, retrieve, reason, or use tools. MIB does not prescribe how.

---

# 27. Observation and Input

Observations may include user messages, tool results, environment events, documents, measurements, feedback, system events, and time transitions.

Example:

```json
{
  "id": "obs-123",
  "type": "user_message",
  "timestamp": "2026-08-19T01:00:00Z",
  "actor": "alice",
  "content": "My timezone is UTC+8."
}
```

MIB MUST distinguish information supplied now, memory expected from the past, and hidden ground truth.

---

# 28. Optional Memory Adapter

Systems MAY expose:

```typescript
interface MIBMemoryAdapter {
  snapshot(): Promise<MemorySnapshot>;
  inspect(query?: MemoryInspectionQuery): Promise<MemoryRecord[]>;
  delete(ref: MemoryRef): Promise<void>;
  restore(snapshot: MemorySnapshot): Promise<void>;
  metrics(): Promise<MemoryMetrics>;
}
```

Optional extensions may include `mask`, `clone`, `export`, `traceInfluence`, and `retrieveTrace`.

Black-box participation remains valid without this adapter.

---

# 29. Ablation Controller

Preferred ablation methods, strongest to weakest:

```text
1. exact record deletion/masking
2. memory snapshot branching
3. cloned memory with filtered past
4. replay excluding selected events
5. black-box scenario reconstruction
```

The report MUST disclose the ablation method because different strengths may affect causal interpretation.

---

# 30. Baselines

MIB SHOULD include:

```text
Agent + Memory
Agent + Full Relevant Context
Agent + No Memory
```

The full-context baseline helps distinguish memory-system failure from base-model inability. The no-memory baseline establishes how much can be solved from present context alone.

---

# 31. Evaluator Hierarchy

Preferred order:

```text
1. Deterministic evaluator
2. World-state evaluator
3. Structured semantic constraints
4. Trajectory evaluator
5. LLM judge
```

LLM judges are fallback evaluators, not the default source of truth.

Deterministic examples:

```text
expected timezone = "+01:00"
selected auth = "session"
must not call deprecated endpoint
commitment trigger occurred
```

World-state examples include successful deployment, correct database target, reminder delivery, or avoidance of a known harmful action.

Structured natural-language constraints can specify `must_include`, `must_not_include`, and allowed uncertainty.

Trajectory evaluation may check whether the agent verified a precondition before acting or consulted a counterexample before transferring a Skill.

---

# 32. LLM Judge Policy

When a judge is required:

1. judge model/version MUST be reported;
2. temperature SHOULD be deterministic or low;
3. rubric MUST be structured;
4. multiple judge samples MAY be used;
5. confidence intervals SHOULD be reported for leaderboard-critical scores;
6. deterministic world truth always wins over judge opinion.

---

# 33. MIB Score

Default:

\[
MIB = \sum_i w_i s_i
\]

with each `s_i ∈ [0,100]` and `Σw_i = 1`.

Recommended v1 weights:

```text
Retention & Retrieval       0.12
Temporal Memory             0.13
Epistemic Memory            0.15
Experience Memory           0.15
Skill Learning & Transfer   0.15
Selective Forgetting        0.10
Prospective & Self Memory   0.08
Causal Memory Impact        0.12
```

The aggregate score MUST always be accompanied by subscores.

---

# 34. Guardrail Penalties

Severe memory pathologies may require explicit capped penalties rather than disappearing inside averages.

Examples:

```text
fabricated high-confidence memory
stale memory repeatedly causing harmful action
authority hallucination caused by memory
privacy leakage from hidden memory
catastrophic identity confusion
```

Penalty policy MUST be transparent and versioned.

---

# 35. Capability Card

Reference result:

```text
Memory Intelligence Benchmark
────────────────────────────────────────

Agent:   Example Agent + Memory X
Model:   Model Y
Track:   A — Memory System
Scale:   MIB-M

MIB Score
  78.6 / 100

Retention & Retrieval        91
Temporal Memory              84
Epistemic Memory             62
Experience Memory            81
Skill Learning & Transfer    74
Selective Forgetting         69
Prospective & Self Memory    76
Causal Memory Impact         82

Memory Benefit              +28.4%
Memory Harm                   5.2%
Net Memory Gain             +23.2%
Known Error Recurrence       11.0%
Negative Transfer             8.0%
Stale Memory Adoption        14.0%
```

---

# 36. Efficiency Metrics

Efficiency is reported separately from Memory Intelligence.

Recommended metrics:

```text
memory writes / meaningful event
storage bytes / 1k events
retrieval latency p50 / p95
end-to-end task latency
tokens injected / task
LLM tokens spent on formation
LLM tokens spent on recall
cost / 1k events
write amplification
maintenance cost
```

Capability and cost are separate axes.

---

# 37. Reproducibility

Every run SHOULD record:

```text
scenario version
scenario seed
world simulator version
agent version
model version
prompt hash
memory version
tool version
judge version
run timestamp
```

For nondeterministic systems, MIB SHOULD run multiple repetitions and report mean, median, standard deviation, and confidence intervals.

---

# 38. Anti-Gaming

MIB must assume benchmark-specific optimization will occur.

Defenses include:

```text
hidden scenario instantiation
late-sampled future probes
randomized names/values
semantic paraphrase
template composition
distractor variation
environment variation
unseen counterexamples
causal ablation
```

Participants MUST NOT receive hidden labels through the adapter.

---

# 39. Memory Poisoning and Harm Tests

MIB SHOULD include adversarial memory cases:

```text
incorrect old fact
malicious instruction in memory
stale procedure
low-trust source
remote Skill claiming authority
false autobiographical statement
duplicate summary amplification
interrogation presupposing an unestablished habit or procedure
```

The system should preserve useful memory without blindly obeying remembered content.

The memory record must fundamentally distinguish questions from assertions: asking whether X is a standing habit must never install X as fact, regardless of repetition frequency or authoritative phrasing. The `MIB-ADV-*` Templates evaluate this property directly.

---

# 40. Privacy and Information Boundaries

Future MIB profiles MAY test whether memory leaks across users, sessions, workspaces, roles, agents, or private/public contexts.

Privacy SHOULD be reported as a dedicated safety profile or separate score rather than silently mixed into basic recall.

---

# 41. Cross-Agent Memory

Future scenarios may evaluate:

```text
Agent A Experience
→ shared/imported memory
→ Agent B
```

Questions include:

```text
Can B learn from A?
Does B preserve source identity?
Does B avoid claiming A's Experience as its own?
Does B avoid inheriting A's authority?
```

---

# 42. Multimodal Memory

MIB is modality-neutral. Observation types may eventually include text, image, audio, video, screen state, sensor state, and spatial traces.

The benchmark preserves the same conceptual questions:

```text
What was observed?
What happened?
What was learned?
What should influence future behavior?
```

---

# 43. MIB vs KIP

MIB and KIP are separate projects.

```text
KIP Conformance
  asks:
  Does this implementation obey KIP protocol semantics?

MIB
  asks:
  How capable is this agent's memory?
```

A KIP implementation may score poorly on MIB. A non-KIP system may score highly. This independence is intentional.

A KIP-native adapter may enable precise diagnostics using KQL/KML/META, BELIEF, HISTORY, Evidence, Experience, Skill, or Capsule snapshots, but these capabilities are never required for primary participation.

---

# 44. Cross-Dimension Scenarios

The most valuable tests often combine dimensions.

Example:

```text
user states preference
→ later corrects preference
→ long distractor period
→ future action depends on current preference
→ historical question asks old preference
→ relevant-memory ablation run
```

This simultaneously tests retention, temporal update, epistemic correction, action influence, historical preservation, and causal impact.

MIB should not become a collection of isolated micro-tests only.

---

# 45. Difficulty Model

Scenario difficulty may be described by:

```text
temporal horizon
distractor count
entity count
memory hops
source ambiguity
conflict complexity
Experience length
Skill abstraction distance
counterexample strength
probe indirectness
```

Difficulty should derive from controlled properties rather than subjective labels alone.

---

# 46. Failure Taxonomy

MIB SHOULD classify failures such as:

```text
formation miss
retrieval miss
identity mismatch
stale-memory adoption
source confusion
correction loss
false certainty
trajectory collapse
Skill non-transfer
negative transfer
counterexample neglect
commitment miss
self-model drift
memory hallucination
irrelevant-memory interference
authority confusion
```

This makes benchmark results useful for engineering, not only ranking.

---

# 47. Memory Pipeline Diagnostics

When an optional adapter is available, MIB may distinguish:

```text
Was it observed?
Was it stored?
Was it transformed?
Was it retained?
Was it retrievable?
Was it retrieved?
Did it influence behavior?
Was that influence correct?
```

Diagnostic chain:

```text
Observe → Store → Retain → Retrieve → Influence → Outcome
```

Each failure stage implies a different engineering problem.

---

# 48. Black-Box Causality

For black-box agents, causal evaluation remains possible through replay:

```text
Run A: full history
Run B: same history minus relevant episode
Run C: same history minus irrelevant episode
Run D: same history plus stale/harmful trap
```

This preserves architecture neutrality.

---

# 49. Benchmark Profiles

Future profiles may include:

```text
MIB-Assistant
MIB-Coding
MIB-Research
MIB-Enterprise
MIB-Companion
MIB-Robotics
MIB-Multimodal
```

Domain profiles may add specialized suites, but cross-system comparison requires a common core suite.

---

# 50. Reference MIB v0.1 Scope

The first implementable release should remain small:

```text
MIB-Recall
MIB-Time
MIB-Belief
MIB-Experience
MIB-Skill
MIB-Causal
```

These six suites are already sufficient to separate simple retrieval memory from temporal, epistemic, experiential, procedural, and causally useful memory.

A useful first target is approximately 60 canonical scenario templates:

```text
Recall       10
Time         10
Belief       10
Experience    8
Skill         8
Causal        8
Cross-suite   6
───────────────
Total        60
```

Each template should support multiple hidden randomized instantiations.

---

# 51. Machine-Readable Artifacts

A future MIB repository SHOULD include:

```text
MIB-Architecture.md

schemas/
  mib-scenario.schema.json
  mib-run.schema.json
  mib-observation.schema.json
  mib-agent-output.schema.json
  mib-report.schema.json
  mib-capability-card.schema.json

adapters/
  MIB-Agent-Adapter.md
  MIB-Memory-Adapter.md

scenarios/
  recall/
  time/
  epistemic/
  experience/
  skill/
  causal/

runner/
  reference implementation

evaluators/
  deterministic/
  world-state/
  semantic/
  trajectory/

leaderboard/
  policy.md
```

---

# 52. Run Artifact

Every benchmark run SHOULD produce a machine-readable artifact containing:

```text
implementation identity
track
scale
suite version
environment
seeds
per-scenario results
dimension scores
causal metrics
efficiency metrics
warnings
judge metadata
```

The artifact should be independently auditable.

---

# 53. Leaderboard Integrity

Leaderboard submissions SHOULD require reproducible adapters, declared models/memory systems, declared external services, version-pinned configuration, run artifacts, and hidden evaluation.

For closed systems, a hosted evaluator may execute submitted adapters without revealing hidden scenarios.

---

# 54. Versioning and Governance

MIB should use explicit benchmark versions:

```text
MIB 0.1
MIB 0.2
MIB 1.0
```

Scores from different major versions should not be directly compared without an explicit normalization policy.

Public governance should cover scenario inclusion, weight changes, judge changes, leaderboard policy, contamination, deprecated scenarios, security disclosures, and appeals.

---

# 55. Research Questions Enabled by MIB

MIB is intended as a research instrument as well as a leaderboard.

Examples:

```text
Does structured episodic memory improve Skill transfer?
Does temporal memory reduce stale-action errors?
Do summaries improve recall but harm source attribution?
Does graph memory improve multi-hop reasoning?
How much does selective forgetting improve action quality?
When does memory cause negative transfer?
How much memory benefit survives model upgrades?
What is the optimal memory cost/capability frontier?
```

---

# 56. Capability vs Efficiency Frontier

MIB SHOULD encourage Pareto reporting such as:

```text
MIB Score vs Cost
MIB Score vs Latency
Causal Memory Benefit vs Storage
Skill Transfer vs Memory Writes
```

One combined cost-adjusted score would hide important tradeoffs.

---

# 57. Minimal Memory-Intelligent Agent

A minimally memory-intelligent agent should be able to:

```text
remember relevant facts
update changed facts
preserve important history
avoid treating unknown as false
remember who said what
learn from at least some Experience
avoid repeating known failure
use relevant past in future decisions
ignore irrelevant past when appropriate
```

A highly memory-intelligent agent should additionally:

```text
learn transferable Skills
use counterexamples
remember commitments
maintain coherent self-knowledge
resist stale/poisoned memory
preserve provenance
selectively forget operationally
demonstrate strong causal memory benefit
```

---

# 58. Architectural Invariants

1. Retrieval is not the same as memory intelligence.
2. Storage is not the same as functional memory.
3. Future probes should not leak into formation.
4. Relevant memory should improve future performance.
5. Irrelevant memory should have little effect.
6. Harmful or stale memory should be resisted.
7. Unknown should not be forced into false certainty.
8. Correction should not destroy historical understanding.
9. Current and historical state must be separately testable.
10. Source attribution matters when sources conflict.
11. Repeated summaries do not create independent evidence.
12. Event recall and Experience recall are distinct.
13. Successful Experience is not automatically a general Skill.
14. Skill transfer must include applicability tests.
15. Negative transfer must be measurable.
16. Forgetting need not mean deletion.
17. Prospective memory is part of memory intelligence.
18. Self memory must not imply authority.
19. Capability and efficiency are separate metrics.
20. Causal ablation is central to strong memory evaluation.
21. MIB must remain architecture-neutral.
22. KIP conformance and MIB capability are independent.
23. Deterministic/world-state evaluation is preferred over free-form LLM judging.
24. Hidden randomized evaluation is required for serious leaderboard use.
25. Results should diagnose failure modes, not only rank systems.

---

# 59. The MIB Principle

MIB can be summarized in one sentence:

> **MIB does not benchmark how much an agent remembers. It benchmarks how intelligently an agent uses memory.**

Or more precisely:

> **A memory system should not be judged by how much of the past it can retrieve, but by whether the right parts of the past change the future in the right way.**

This is the architectural foundation of MIB.

---

# Appendix A — Conceptual Model

```text
                PAST
                 │
                 ▼
        ┌─────────────────┐
        │   Observation   │
        └────────┬────────┘
                 │
                 ▼
        ┌─────────────────┐
        │    Formation    │
        └────────┬────────┘
                 │
                 ▼
        ┌─────────────────┐
        │  Memory State   │
        └────────┬────────┘
                 │
        ┌────────┴────────┐
        │                 │
        ▼                 ▼
 Consolidation         Revision
        │                 │
        └────────┬────────┘
                 │
                 ▼
        ┌─────────────────┐
        │     Recall      │
        └────────┬────────┘
                 │
                 ▼
        ┌─────────────────┐
        │ Future Decision │
        └────────┬────────┘
                 │
                 ▼
        ┌─────────────────┐
        │    Behavior     │
        └────────┬────────┘
                 │
                 ▼
        ┌─────────────────┐
        │     Outcome     │
        └────────┬────────┘
                 │
                 └───────────────↺
```

MIB evaluates the loop, not one box.

---

# Appendix B — Example Capability Card

```text
MIB — Memory Intelligence Benchmark
════════════════════════════════════════

System
  Agent:      Example Agent
  Memory:     Memory X
  Model:      Model Y
  Track:      A — Memory System
  Scale:      MIB-M

MIB Score
  78.6 / 100

Capability Profile
  Retention & Retrieval       91
  Temporal Memory             84
  Epistemic Memory            62
  Experience Memory           81
  Skill Learning              74
  Selective Forgetting        69
  Prospective & Self Memory   76
  Causal Memory Impact        82

Causal Metrics
  Memory Benefit             +28.4%
  Memory Harm                  5.2%
  Net Memory Gain            +23.2%
  Negative Transfer            8.0%
  Known Error Recurrence      11.0%
```

---

# Appendix C — Recommended Next Specifications

After this Architecture, recommended next artifacts are:

```text
1. MIB-Scenario-Model.md
2. mib-scenario.schema.json
3. MIB-Agent-Adapter.md
4. MIB-Scoring.md
5. mib-report.schema.json
6. MIB-v0.1-Test-Plan.md
7. first canonical scenario pack
8. reference runner
```

The first implementation milestone should prioritize:

```text
scenario execution
future-probe isolation
black-box agent adapter
world simulator
deterministic scoring
replay-based ablation
capability-card generation
```

before building a public leaderboard.
