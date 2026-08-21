# MIB Scoring

## Score Semantics for the Memory Intelligence Benchmark

**Version:** 0.1-draft  
**Status:** Scoring Model Proposal / Companion to `MIB-Architecture.md`, `MIB-Scenario-Model.md`, and `MIB-Agent-Adapter.md`

---

# 0. Purpose

This document defines how MIB converts benchmark observations into:

```text
Probe scores
Scenario scores
Template scores
Dimension scores
Causal memory metrics
MIB Score
Capability Cards
Leaderboard statistics
```

The scoring system is designed around one central idea:

> **MIB Score measures the memory-enabled capability of the evaluated Agent. Causal metrics separately measure how much that capability was actually caused by memory.**

These are related but not identical questions.

A strong Agent may perform well even when some memory is ablated.

A weak base Agent may gain greatly from memory but still perform poorly in absolute terms.

MIB therefore reports both:

```text
Absolute memory-enabled capability
+
Causal contribution of memory
```

Neither should be hidden inside the other.

---

# 1. Scoring Philosophy

MIB MUST avoid reducing memory evaluation to:

```text
retrieval accuracy
```

or:

```text
with-memory score - no-memory score
```

alone.

The benchmark must answer several distinct questions:

```text
Can the Agent perform the future task?

Did relevant memory help?

Did irrelevant memory stay irrelevant?

Did stale or harmful memory cause avoidable errors?

Did past Experience reduce repeated failure?

Did a learned Skill transfer only where applicable?

How stable are these results across runs and hidden instances?
```

The MIB scoring model preserves these distinctions.

---

# 2. Absolute Capability vs Causal Contribution

MIB has two primary score surfaces.

## 2.1 Capability Surface

The **MIB Score** and its capability dimensions measure:

> How well does the memory-enabled Agent perform on tasks that require memory intelligence?

The ordinary full-memory condition is the primary source of capability performance.

## 2.2 Causal Surface

Metrics such as:

```text
Causal Memory Impact
Memory Benefit
Memory Harm
Net Memory Gain
Irrelevant Memory Stability
Negative Transfer
Error Recurrence
```

measure:

> What changes when memory conditions are experimentally manipulated?

The Causal Memory Impact dimension converts some of these interventions into one capability dimension, but raw causal metrics remain separately visible.

---

# 3. Why MIB Score Is Not Pure Delta

Suppose:

```text
Agent A:
  Full Memory      = 95
  Relevant Ablated = 85

Agent B:
  Full Memory      = 65
  Relevant Ablated = 20
```

A pure delta metric would prefer Agent B:

```text
A gain = +10
B gain = +45
```

But Agent A is still much more capable on the future task.

Conversely, full performance alone would hide that Agent A relies less on its memory.

MIB therefore reports:

```text
Capability:
  Agent A > Agent B

Causal Memory Benefit:
  Agent B > Agent A
```

This is informative rather than contradictory.

---

# 4. Track Interpretation

Scoring semantics depend on benchmark track.

## 4.1 Track A — Memory System Track

The benchmark fixes:

```text
base model
Agent policy
tools
Scenario
evaluation
```

and varies the memory system.

Therefore differences in MIB Score can be interpreted primarily as differences in memory-system quality.

Track A is the preferred public comparison for memory architectures.

## 4.2 Track B — Integrated Agent Track

The submitted system may vary:

```text
model
Agent policy
memory
orchestration
tool strategy
```

MIB Score measures the complete Agent's memory-enabled capability.

It is intentionally **not model-normalized**.

Causal metrics reveal how much relevant past memory contributes inside that complete system.

## 4.3 No Cross-Track Ranking

Track A and Track B MUST NOT be combined into one leaderboard.

---

# 5. Scoring Hierarchy

MIB uses the following hierarchy:

```text
Evaluator Result
      ↓
Probe Score
      ↓
Scenario Instance Score
      ↓
Scenario Template Score
      ↓
Dimension Score
      ↓
MIB Score
```

Causal variants form a paired branch:

```text
Full Condition
      │
      ├── Relevant Ablation
      ├── Irrelevant Ablation
      ├── No-Memory Control
      └── Harmful/Stale Condition
              ↓
       Causal Metrics
              ↓
 Causal Memory Impact Dimension
```

---

# 6. Fundamental Numeric Range

Internal normalized performance uses:

\[
p \in [0,1]
\]

Displayed capability scores use:

\[
score = 100p
\]

Examples:

```text
0.00  →   0.0
0.73  →  73.0
1.00  → 100.0
```

Causal deltas MAY be negative and are usually displayed in percentage points.

Example:

```text
+0.284 → +28.4 pp
-0.071 →  -7.1 pp
```

---

# 7. Do Not Round Early

All aggregation MUST use full numeric precision.

Rounding occurs only for presentation.

Recommended display:

```text
MIB Score              82.7
Dimension Score        84.3
Memory Benefit        +21.8 pp
Memory Harm            4.2 pp
Error Recurrence       7.5%
```

Leaderboard implementation MUST NOT aggregate already-rounded values.

---

# 8. Evaluator Result

Each Evaluator produces a normalized result.

Reference conceptual object:

```json
{
  "score": 0.85,
  "passed": true,
  "failure_codes": [],
  "details": {}
}
```

Required semantic field:

```text
score ∈ [0,1]
```

`passed` is optional unless the evaluator is intrinsically binary.

---

# 9. Exact Evaluator

For an exact binary condition:

\[
e =
\begin{cases}
1 & \text{correct}\\
0 & \text{incorrect}
\end{cases}
\]

Examples:

```text
timezone exact match
correct entity identity
required structured status
```

---

# 10. Set-Match Evaluator

If an Oracle provides accepted values:

```json
{
  "accepted": [
    "+01:00",
    "UTC+1"
  ]
}
```

the evaluator normalizes the Agent output according to declared rules and returns:

```text
1 if any accepted value matches
0 otherwise
```

Forbidden output MAY be handled by:

```text
evaluator failure
or
Scenario penalty
```

depending on the Scenario.

---

# 11. Structured Evaluator

A structured evaluator can score multiple fields.

Example:

```json
{
  "answer": "+01:00",
  "status": "known"
}
```

A Scenario may define:

```text
answer weight = 0.7
status weight = 0.3
```

Then:

\[
e =
0.7e_{answer}
+
0.3e_{status}
\]

Field weights MUST be explicit and sum to 1.

---

# 12. World-State Evaluator

A world-state evaluator scores observable simulator truth.

Example assertions:

```text
/auth_mode == "session"
/deployment_status == "running"
/production_data_modified == false
```

If all assertions have equal weight:

\[
e =
\frac{
\# satisfied\ assertions
}{
\# assertions
}
\]

A Scenario MAY assign explicit assertion weights.

World truth has priority over natural-language claims.

---

# 13. Trajectory Evaluator

Trajectory evaluation uses only observable Agent behavior:

```text
tool calls
actions
emissions
ordering
repeated failures
```

Example components:

```text
inspect target before migration retry     0.4
do not call deprecated API                0.4
complete task successfully                0.2
```

The evaluator MUST NOT require private chain-of-thought.

---

# 14. Semantic-Constraint Evaluator

A semantic-constraint evaluator may score:

```text
required concepts
forbidden claims
required uncertainty
historical/current distinction
source attribution
```

Whenever possible it SHOULD use deterministic structured matching.

If an LLM judge is needed internally, the result still MUST be normalized to `[0,1]`, and the Run Artifact must identify the judge.

---

# 15. LLM Judge Evaluator

A canonical LLM judge should return a structured score.

Recommended rubric output:

```json
{
  "score": 0.8,
  "failure_codes": [
    "source_attribution_partial"
  ]
}
```

The judge rubric MUST define the meaning of:

```text
0
0.25
0.5
0.75
1
```

or another explicit scale.

A free-form preference such as:

```text
"looks mostly correct"
```

is insufficient for official leaderboard scoring.

---

# 16. Multiple Evaluators per Probe

Canonical MIB Scenario Packs SHOULD normally reference **one final evaluator** per Probe.

If several signals must be combined, authors SHOULD define a:

```text
composite evaluator
```

with explicit component weights.

If a Probe references multiple non-composite evaluators and no profile-specific aggregation rule exists, v0.1 default is:

\[
E_q =
\frac{1}{m}
\sum_{j=1}^{m} e_{q,j}
\]

This fallback SHOULD be avoided in canonical packs because equal weighting may be semantically accidental.

---

# 17. Composite Evaluator

For component evaluators:

\[
E_q =
\sum_j \alpha_j e_j
\]

where:

\[
\alpha_j \ge 0,\quad
\sum_j \alpha_j = 1
\]

Example:

```text
world success              0.60
required workflow step     0.20
forbidden action absent    0.20
```

---

# 18. Probe Score

For Probe \(q\), condition \(c\), repetition \(r\):

\[
P_{q,c,r} \in [0,1]
\]

This is the normalized final evaluator result for that Probe.

The full-memory condition is denoted:

```text
c = full
```

Common counterfactual conditions:

```text
rel     relevant-memory ablated
irr     irrelevant-memory ablated
none    no-memory control
harm    harmful-memory condition
stale   stale-memory condition
counter counterexample condition
```

---

# 19. Probe Weight

Scenario Probe weight:

\[
w_q \ge 0
\]

Default:

```text
1.0
```

Probe weights represent relative importance **inside one Scenario**.

They do not determine how many hidden instances a Template receives.

---

# 20. Repetitions

If an Agent is stochastic, the same Scenario Instance may be repeated.

For condition \(c\):

\[
\bar P_{q,c}
=
\frac{1}{R}
\sum_{r=1}^{R}
P_{q,c,r}
\]

Repetition count is defined by:

```text
Scenario execution policy
or
Leaderboard Profile
```

MIB does not require one universal repetition count for every research setting.

---

# 21. Paired Repetitions

Causal conditions MUST be paired where possible.

Example:

```text
full repetition 1
relevant-ablation repetition 1
irrelevant-ablation repetition 1
harmful repetition 1
```

should share:

```text
same Scenario Instance
same world seed
same future Probe
same tool simulator seed
same Agent seed if supported
```

The memory intervention should be the intended difference.

---

# 22. Why Pairing Matters

Incorrect:

```text
100 random Full runs
vs
100 unrelated random Ablation runs
```

Correct:

```text
Instance A, seed 1:
  Full ↔ Ablated

Instance A, seed 2:
  Full ↔ Ablated

Instance B, seed 1:
  Full ↔ Ablated
```

Paired differences reduce variance and support causal interpretation.

---

# 23. Scenario Full-Condition Score

For Scenario Instance \(s\), repetition \(r\), full-memory condition:

\[
S_{s,r}^{full}
=
\frac{
\sum_q w_q P_{q,full,r}
}{
\sum_q w_q
}
\]

provided the Scenario uses:

```text
probe_aggregation = weighted_mean
```

The Scenario schema may define another explicit aggregator.

---

# 24. Mean Scenario Performance

Across repetitions:

\[
F_s =
\frac{1}{R}
\sum_r
S_{s,r}^{full}
\]

\(F_s\) is the Scenario Instance's primary full-memory capability performance.

---

# 25. Non-Weighted Aggregators

If the Scenario explicitly defines:

```text
mean
min
max
custom
```

the Runner applies that aggregator.

`min` is useful where all subrequirements are safety-critical.

Example:

```text
must preserve historical truth
AND
must use current truth
```

A Scenario author should choose aggregators intentionally.

---

# 26. Scenario Penalties

Scenario-defined penalties are applied **after Probe aggregation** unless explicitly bound to an evaluator.

Let:

\[
G_s = \sum_k g_k
\]

where \(g_k\) is expressed as normalized score deduction.

Then:

\[
F'_s =
\max(0, F_s - G_s)
\]

If Scenario penalty points are authored on a `0..100` range:

\[
g_k = points_k / 100
\]

Canonical packs SHOULD specify penalty semantics unambiguously.

---

# 27. Penalty Caps

A Scenario MAY define a penalty cap.

Example:

```text
unsupported certainty      -20 points
stale forbidden action     -30 points
scenario penalty cap        40 points
```

The cap prevents duplicated failure detectors from accidentally applying unlimited punishment.

---

# 28. Scenario Penalties vs Global Guardrails

Two different mechanisms:

```text
Scenario penalty:
  affects one experiment's score

Global guardrail policy:
  affects the final benchmark report/profile
```

MIB v0.1 defines no hidden global penalty.

A Benchmark Profile MAY define global penalties, but they MUST be explicit, versioned, and separately displayed.

---

# 29. Scenario Dimension Assignment

A Scenario may contribute to several dimensions.

Example:

```json
{
  "dimension_weights": {
    "temporal_memory": 0.70,
    "retention_retrieval": 0.15,
    "causal_memory_impact": 0.15
  }
}
```

For ordinary capability dimensions, the full-memory Scenario score contributes according to these weights.

The causal dimension is derived from causal interventions rather than simply reusing \(F_s\).

---

# 30. Dimension Weights Inside a Scenario

Scenario-local dimension weights represent:

> How much evidence does this Scenario provide for each capability dimension?

They SHOULD sum to 1 when present.

If omitted, the default is equal attribution among declared Scenario dimensions.

Example with three dimensions:

```text
1 / 3
1 / 3
1 / 3
```

---

# 31. Probe-Level Dimension Tags

A Probe may also declare dimensions.

When present, the Runner SHOULD compute a Scenario-dimension score using only Probes that contribute to that dimension.

For dimension \(d\):

\[
S_{s,d}
=
\frac{
\sum_{q \in Q_d} w_q \bar P_{q,full}
}{
\sum_{q \in Q_d} w_q
}
\]

where \(Q_d\) is the set of Probes tagged with \(d\).

If no Probe-level dimension tags exist, use the overall Scenario full score.

---

# 32. Causal Dimension Is Special

For:

```text
causal_memory_impact
```

the Scenario-dimension score MUST be derived from paired intervention metrics.

It MUST NOT be assigned merely because the full-memory task succeeded.

This preserves the meaning of the dimension:

> Did memory make the difference?

---

# 33. Scenario Instance vs Scenario Template

A Scenario Template may generate many hidden instances.

Example:

```text
Template T:
  100 different names
  100 different dates
  100 different values
```

MIB MUST NOT treat those 100 instances as 100 independent scenario-design votes against another Template with only 10 instances.

Therefore aggregation occurs in two stages:

```text
Instances within Template
        ↓
Template Score
        ↓
Templates within Dimension
```

---

# 34. Template Score

For Template \(t\), dimension \(d\), with \(N_t\) materialized instances:

\[
T_{t,d}
=
\frac{1}{N_t}
\sum_{s \in t}
S_{s,d}
\]

unless the Pack defines explicit instance weights.

Canonical hidden instantiation SHOULD normally use equal instance weights.

---

# 35. Why Template-First Aggregation Matters

Suppose:

```text
Template A:
  1000 generated direct-recall instances

Template B:
  20 difficult identity-collision instances
```

If every instance entered the Dimension Score directly, Template A would dominate simply because it was cheap to generate.

Template-first aggregation ensures benchmark semantics are controlled by:

```text
scenario design
```

not:

```text
instance count
```

---

# 36. Template Weight

A Benchmark Pack may define:

\[
v_{t,d} \ge 0
\]

representing Template \(t\)'s contribution to dimension \(d\).

Default:

```text
equal weight among eligible Templates
```

Pack authors SHOULD prefer a small number of interpretable weight classes rather than arbitrary fine-grained numbers.

---

# 37. Dimension Score

For capability dimension \(d\):

\[
D_d
=
100
\cdot
\frac{
\sum_t v_{t,d} T_{t,d}
}{
\sum_t v_{t,d}
}
\]

with:

\[
D_d \in [0,100]
\]

This is the reported Dimension Score.

---

# 38. Eight Primary Dimensions

MIB v1 defines:

```text
Retention & Retrieval
Temporal Memory
Epistemic Memory
Experience Memory
Skill Learning & Transfer
Selective Forgetting
Prospective & Self Memory
Causal Memory Impact
```

Recommended full-profile weights from `MIB-Architecture.md`:

| Dimension | Weight |
|---|---:|
| Retention & Retrieval | 0.12 |
| Temporal Memory | 0.13 |
| Epistemic Memory | 0.15 |
| Experience Memory | 0.15 |
| Skill Learning & Transfer | 0.15 |
| Selective Forgetting | 0.10 |
| Prospective & Self Memory | 0.08 |
| Causal Memory Impact | 0.12 |
| **Total** | **1.00** |

---

# 39. MIB Base Score

For a complete profile:

\[
MIB_{base}
=
\sum_d W_d D_d
\]

where:

\[
W_d \ge 0,\quad
\sum_d W_d = 1
\]

The result is on:

```text
0..100
```

---

# 40. Default MIB Score

If the Profile defines no global guardrail penalty:

\[
MIB = MIB_{base}
\]

This is the recommended default.

---

# 41. Optional Global Guardrail Penalty

A Profile MAY define:

\[
G_{global} \ge 0
\]

Then:

\[
MIB =
\max(0, MIB_{base} - G_{global})
\]

If used, the Capability Card MUST show:

```text
Base MIB Score
Global Guardrail Penalty
Final MIB Score
```

A leaderboard MUST NOT apply undocumented global deductions.

---

# 42. Coverage

A score is meaningful only when enough required benchmark evidence exists.

For each dimension:

\[
Coverage_d =
\frac{
\text{evaluated required template weight}
}{
\text{total required template weight}
}
\]

Coverage is reported as:

```text
0..100%
```

---

# 43. Unsupported Scenarios

An unsupported Scenario is not automatically a zero-memory failure.

However official profiles distinguish:

```text
required Scenario
optional Scenario
```

If a required Scenario is unsupported because the Agent lacks a mandatory profile capability, the submission may be:

```text
ineligible for that official Profile
```

rather than silently excluding the Scenario and inflating the score.

---

# 44. Partial Scores

If a submission does not satisfy full-profile coverage, MIB SHOULD report:

```text
Partial MIB Score
```

with explicit coverage.

It MUST NOT be labeled as the same official MIB Score used by fully covered submissions.

Example:

```text
Partial MIB Score     81.2
Coverage              72%
Missing:
  Prospective & Self Memory
  Selective Forgetting
```

---

# 45. MIB v0.1 Profiles

The first implementation may cover only a subset of the eventual eight dimensions.

A v0.1 Test Plan SHOULD define a named profile such as:

```text
MIB-Core-0.1
```

with its own required dimensions and weights.

Scores are always identified by Profile:

```text
MIB-Core-0.1 Score
MIB-Full-1.0 Score
```

Weights from different Profiles MUST NOT be silently mixed.

---

# 46. Execution Failure

After allowed idempotent retries, unresolved infrastructure failure follows the Scenario/Profile execution policy.

For official leaderboard profiles, `fail_probe` SHOULD normally produce:

```text
Probe score = 0
```

while also recording:

```text
execution_failure = true
```

This prevents systems from avoiding difficult Probes by failing.

`skip_probe` should normally be limited to optional/non-leaderboard analysis.

---

# 47. Wrong Answer vs Execution Failure

Both may numerically score zero.

But the Run Artifact MUST distinguish:

```text
cognitive failure
execution failure
unsupported
not run
```

Engineering interpretation depends on this distinction.

---

# 48. Causal Conditions

Let the normalized paired Scenario performance be:

```text
F = Full-memory condition
R = Relevant-memory ablated condition
I = Irrelevant-memory ablated condition
N = No-memory condition
H = Harmful/stale-memory condition
```

Each belongs to:

\[
[0,1]
\]

unless a metric explicitly uses a signed delta.

---

# 49. Primary Causal Reference

For measuring relevant memory contribution, preference order is:

```text
1. relevant-memory ablation
2. no-memory control
```

Relevant-memory ablation is more specific because it preserves unrelated past memory.

If no relevant-memory ablation exists, a no-memory condition MAY serve as the causal reference.

---

# 50. Raw Causal Memory Impact

For one paired unit:

\[
CMI_{raw}
=
F - R
\]

Range:

\[
[-1,1]
\]

Interpretation:

```text
positive:
  relevant memory helped

zero:
  no observed causal benefit

negative:
  relevant memory condition harmed performance
```

MIB MUST report negative values rather than clamping them away in diagnostics.

---

# 51. Memory Benefit

The primary raw **Memory Benefit** is:

\[
MB =
E[F - R]
\]

aggregated over eligible paired relevant-memory scenarios.

Displayed in percentage points:

```text
MB = 0.284
→ Memory Benefit = +28.4 pp
```

Memory Benefit is signed.

---

# 52. Why Raw Memory Benefit Is Not the Causal Dimension Score

A raw +20 pp gain can mean different things.

Example A:

```text
R = 0.00
F = 0.20
```

Example B:

```text
R = 0.70
F = 0.90
```

Both produce:

```text
+0.20
```

but in B memory closes most of the remaining performance gap.

MIB therefore keeps raw MB for interpretation and uses a normalized measure for part of the Causal Memory Impact Dimension.

---

# 53. Headroom-Normalized Memory Benefit

For an eligible pair with:

\[
R < 1 - \epsilon
\]

define:

\[
HMB =
\frac{
\max(0, F-R)
}{
1-R
}
\]

then clamp to:

\[
[0,1]
\]

Interpretation:

> What fraction of the performance headroom above the ablated condition did memory recover?

Example:

```text
R = 0.60
F = 0.90

Raw MB = +0.30
Headroom = 0.40
HMB = 0.75
```

---

# 54. Near-Ceiling Ablated Conditions

If:

\[
R \ge 1-\epsilon
\]

there is effectively no measurable headroom.

Such a pair is:

```text
causally non-discriminative for positive benefit
```

and SHOULD be excluded from HMB aggregation.

The raw CMI remains reportable.

Recommended default:

\[
\epsilon = 0.02
\]

A Profile may override it.

---

# 55. Negative Causal Impact

If:

\[
F < R
\]

then:

```text
HMB = 0
```

for the positive-benefit component.

But the negative raw CMI remains visible and may contribute to Memory Harm diagnostics.

MIB MUST NOT transform a harmful relevant-memory effect into apparent positive benefit.

---

# 56. No-Memory Benefit

When no relevant ablation exists:

\[
MB_{none}
=
F-N
\]

and:

\[
HMB_{none}
=
\frac{
\max(0,F-N)
}{
1-N
}
\]

subject to the same headroom rule.

Reports SHOULD identify whether causal benefit was computed from:

```text
relevant ablation
or
no-memory control
```

because they answer slightly different questions.

---

# 57. Irrelevant Memory Stability

For paired full and irrelevant-ablation performance:

\[
\Delta_I =
|F-I|
\]

Without tolerance:

\[
IMS =
1-\Delta_I
\]

Higher is better.

---

# 58. Irrelevant Stability Tolerance

Small stochastic differences should not be treated as meaningful interference.

If the Ablation defines tolerance \(\tau\):

\[
IMS_\tau
=
1 -
\frac{
\max(0, |F-I|-\tau)
}{
1-\tau
}
\]

clamped to:

\[
[0,1]
\]

Example:

```text
F = 0.91
I = 0.89
tau = 0.03

|F-I| = 0.02 <= tau

IMS_tau = 1.00
```

---

# 59. Interpretation of Irrelevant Ablation

If:

```text
I > F
```

removing irrelevant memory improved performance.

Possible explanation:

```text
irrelevant-memory interference
```

If:

```text
I < F
```

removing supposedly irrelevant memory harmed performance.

Possible explanation:

```text
unexpected dependency
or
scenario relevance labeling problem
```

Both reduce stability because both indicate the "irrelevant" past was not behaviorally neutral.

---

# 60. Harmful-Memory Condition

Let:

```text
C = clean control performance
H = harmful/stale memory performance
```

Often:

```text
C = F
```

but a Scenario may define a dedicated clean paired control.

---

# 61. Memory Harm Magnitude

Define:

\[
MH =
E[
\max(0,C-H)
]
\]

This measures average performance loss caused by harmful/stale memory conditions.

Displayed in percentage points:

```text
Memory Harm = 0.052
→ 5.2 pp
```

This is the preferred quantity for arithmetic with Memory Benefit.

---

# 62. Harm Resistance Score

For one pair:

\[
HRS =
1-\max(0,C-H)
\]

With tolerance \(\tau_h\):

\[
HRS_{\tau_h}
=
1 -
\frac{
\max(0,C-H-\tau_h)
}{
1-\tau_h
}
\]

clamped to `[0,1]`.

High is good.

---

# 63. Memory-Induced Error Rate

Some harmful scenarios are naturally binary.

Define an eligible pair when:

```text
clean condition succeeds
```

and the harmful condition introduces a memory-specific failure.

Then:

\[
MIER =
\frac{
\# memory\text{-}induced\ avoidable\ errors
}{
\# eligible\ harmful\ trials
}
\]

This is reported separately from Memory Harm Magnitude.

Example:

```text
Memory Harm             5.2 pp
Memory-Induced Errors   8.1%
```

---

# 64. Why Harm Uses an Eligible Denominator

If the Agent already fails the clean task, we cannot confidently claim harmful memory caused that failure.

Therefore a binary memory-induced error requires a successful or otherwise eligible clean paired condition.

This prevents over-attribution.

---

# 65. Net Memory Gain

For comparable paired scenario groups:

\[
NMG =
MB - MH
\]

where both terms are performance-point quantities.

Example:

```text
Memory Benefit  = +0.284
Memory Harm     =  0.052

Net Memory Gain = +0.232
```

Displayed:

```text
+23.2 pp
```

NMG is diagnostic.

It is NOT the MIB Score.

---

# 66. Why Net Memory Gain Is Not MIB Score

A system could have:

```text
low absolute performance
high memory gain
```

or:

```text
high absolute performance
low memory gain
```

Both facts matter.

Replacing MIB Score with NMG would collapse capability and causality into one number.

MIB intentionally keeps them separate.

---

# 67. Causal Memory Impact Dimension

The Causal Memory Impact Dimension converts causal behavior into a `0..100` capability dimension.

Recommended v1 component structure:

```text
Headroom-Normalized Relevant Benefit   50%
Irrelevant Memory Stability            20%
Harm / Stale Memory Resistance         30%
```

For available components:

\[
CausalScore
=
100
\cdot
\frac{
0.50HMB
+
0.20IMS
+
0.30HRS
}{
\text{sum of available component weights}
}
\]

If a component is absent for a Scenario/Template, its weight is removed and the remaining weights are renormalized.

---

# 68. Causal Coverage

A causal score must disclose which components were actually tested.

Example:

```text
Relevant Benefit Coverage   100%
Irrelevant Stability         80%
Harm Resistance              60%
```

An official Profile may require minimum causal-component coverage.

A system should not receive a full Causal Memory Impact label from only one easy ablation type.

---

# 69. Causal Template Aggregation

Causal metrics are aggregated **within Scenario Template first**, preserving paired runs.

For Template \(t\):

\[
HMB_t =
mean(HMB_s)
\]

over eligible hidden instances \(s\).

Likewise:

```text
IMS_t
HRS_t
MB_t
MH_t
```

Template-level causal components then enter the causal dimension using Pack weights.

---

# 70. Do Not Pool Pair Components Incorrectly

Incorrect:

```text
mean(all Full scores)
-
mean(all Ablated scores)
```

when pair membership differs.

Preferred:

\[
MB =
mean(F_s-R_s)
\]

over matched pairs.

Paired deltas preserve causal correspondence.

---

# 71. Positive Skill Transfer

For a matching future Skill context:

```text
F_match = full learned-memory performance
R_match = relevant-Skill/Experience ablated performance
```

Positive transfer gain:

\[
PTG =
F_{match} - R_{match}
\]

A headroom-normalized version MAY use the HMB formula.

---

# 72. Negative Transfer

For a non-matching context:

```text
B_nonmatch = baseline performance without the inapplicable Skill influence
F_nonmatch = performance with full learned memory
```

Negative Transfer Magnitude:

\[
NT =
\max(
0,
B_{nonmatch} - F_{nonmatch}
)
\]

Higher NT is worse.

---

# 73. Negative Transfer Resistance

Define:

\[
NTR =
1-NT
\]

or tolerance-normalized:

\[
NTR_\tau =
1 -
\frac{
\max(0,NT-\tau)
}{
1-\tau
}
\]

This can contribute to:

```text
Skill Learning & Transfer
```

and optionally causal diagnostics.

---

# 74. Negative Transfer Rate

If the Scenario can detect explicit inappropriate Skill use:

\[
NTRate =
\frac{
\# inappropriate\ transfers
}{
\# nonmatching\ opportunities
}
\]

Report this as:

```text
Negative Transfer Rate
```

Lower is better.

Do not confuse:

```text
Negative Transfer Rate
```

with:

```text
Negative Transfer Resistance Score
```

---

# 75. Failure Avoidance

Experience scenarios may define a known failure signature.

Example:

```text
call deprecated endpoint
deploy against wrong database
skip required workspace selection
```

A later matching opportunity tests whether the Agent avoids repeating it.

---

# 76. Error Recurrence Rate

Define:

\[
ERR =
\frac{
\# repeated\ known\ failures
}{
\# eligible\ recurrence\ opportunities
}
\]

Range:

```text
0..1
```

Lower is better.

---

# 77. Error Avoidance Score

For use inside a positive capability score:

\[
EAS = 1-ERR
\]

A Skill/Experience dimension may include this through Scenario evaluator design.

Raw ERR remains separately reported.

---

# 78. Eligible Recurrence Opportunity

An opportunity is eligible only when:

```text
the Agent previously experienced the failure
the current context matches the learned failure conditions
the relevant action is actually available
the Scenario expects avoidance
```

Do not count unrelated situations in the denominator.

---

# 79. Learning Gain

For longitudinal task families:

```text
early performance  = E
late performance   = L
```

define:

\[
LG = L-E
\]

Learning Gain may be negative.

It is useful for research reports and Skill/Experience diagnostics.

---

# 80. Area Under Learning Curve

A longitudinal profile MAY also report:

\[
AULC =
\frac{1}{N}
\sum_{t=1}^{N}
Performance(t)
\]

AULC rewards both:

```text
learning speed
+
final capability
```

It is optional in v0.1.

---

# 81. Influence Precision

Exact causal influence tracing is optional.

If a diagnostic system can identify detected memory influences:

\[
IP =
\frac{
Helpful\ Memory\ Influences
}{
All\ Detected\ Memory\ Influences
}
\]

However:

```text
self-reported attribution
```

MUST NOT be treated as definitive causal influence.

Official core MIB causality comes from intervention.

Influence Precision is therefore diagnostic unless a future profile standardizes influence tracing.

---

# 82. Temporal Memory Scoring

Temporal scenarios SHOULD separately test:

```text
current truth
historical truth
transition
staleness
valid time
```

A system should not receive full temporal credit merely because it returns the latest value.

Example scenario score may combine:

```text
current state          0.35
historical state       0.25
transition reasoning   0.20
stale avoidance        0.20
```

Canonical weights belong in the Scenario.

---

# 83. Epistemic Memory Scoring

Epistemic scenarios SHOULD make it possible to penalize:

```text
source confusion
correction loss
contradiction collapse
false certainty
evidence multiplication
```

while rewarding:

```text
source attribution
correct current belief
historical attribution
abstention when unknown
```

A benchmark should not accept the correct final answer while ignoring that the Agent falsely attributes the source if source identity is part of the capability under test.

---

# 84. Experience Memory Scoring

Experience-memory scenarios SHOULD evaluate:

```text
goal
trajectory
action/observation order
failure
recovery
outcome
prediction error
```

where relevant.

Keyword overlap with the old episode is insufficient.

Action scenarios SHOULD prefer world/trajectory evaluators over prose reconstruction.

---

# 85. Skill Learning Scoring

Skill scenarios SHOULD contain both:

```text
positive transfer opportunity
negative transfer / non-applicability opportunity
```

whenever feasible.

A system that applies the learned procedure everywhere should not score as highly as one that learns:

```text
what to do
+
when to do it
```

---

# 86. Selective Forgetting Scoring

Selective-forgetting scenarios SHOULD reward both:

```text
current stale-memory suppression
historical preservation
```

Example:

```text
current behavior uses sessions
historical query still recalls JWT
```

A system that deletes history to avoid stale use should not automatically receive full score.

---

# 87. Prospective Memory Scoring

Prospective memory should score:

```text
trigger detection
correct spontaneous emission/action
timeliness
persistence across interference
no premature triggering
```

A direct recall answer after the benchmark asks:

```text
"What should I remind you?"
```

is not equivalent to spontaneous prospective success.

---

# 88. Self-Memory Scoring

Self-memory scenarios MAY score:

```text
capability continuity
remembered limitation
self-correction
avoid repeated self-error
authority boundary
```

Remembering:

```text
"I am admin"
```

must never grant actual Runner authority.

Authority violations may receive Scenario penalties.

---

# 89. Memory Hallucination

A memory hallucination occurs when an Agent claims a specific past memory that was not present in the lived Scenario and is not justified by current context.

Examples:

```text
invented user preference
invented prior conversation
invented previous tool result
invented Experience
```

Scenario evaluators MAY classify:

```text
memory_hallucination
```

and apply a penalty where appropriate.

---

# 90. False Certainty

If the Oracle status is:

```text
unknown
```

an unsupported definite claim may receive:

```text
score = 0
```

or a Scenario-defined penalty.

A correct abstention may receive:

```text
score = 1
```

This makes epistemic discipline measurable.

---

# 91. Full-Context Baseline

The full-context baseline is a calibration and diagnostic condition.

Let:

```text
FC = full relevant history directly supplied in current context
```

It estimates whether the base Agent/model can solve the task if memory formation/retrieval is removed from the problem.

FC does not directly enter ordinary MIB Score.

---

# 92. No-Memory Baseline

Let:

```text
NM = future task with meaningful past removed
```

This estimates how much the task can be solved from:

```text
base model
current context
tools
```

alone.

NM may serve as a causal reference if a precise relevant ablation is unavailable.

---

# 93. Scenario Memory Discriminativeness

During benchmark calibration, define:

\[
MDI =
FC - NM
\]

This is the **Memory Discriminativeness Index**.

Interpretation:

```text
high FC:
  task is solvable when relevant past is available

low NM:
  task genuinely requires memory

high MDI:
  scenario can distinguish memory capability
```

---

# 94. Non-Discriminative Scenarios

A Scenario may be unsuitable for memory evaluation if:

```text
NM is near ceiling
```

because memory is unnecessary.

It may also be unsuitable if:

```text
FC is very low
```

because the base task is too difficult even with perfect context.

Calibration profiles SHOULD define thresholds.

Such scenarios should be revised, downweighted, or excluded before entering a canonical pack.

---

# 95. Memory Gap Closure

For Track A diagnostics, where the same fixed base Agent supports all conditions:

\[
MGC =
\frac{
F-NM
}{
FC-NM
}
\]

when:

\[
FC > NM + \epsilon
\]

Clamp diagnostic display to a reasonable range, but preserve raw values for analysis.

Interpretation:

> What fraction of the memory-dependent gap between no-memory and full-context performance did the memory system close?

MGC is optional and especially useful in Track A.

---

# 96. MGC Is Not Universal

Track B systems may use different models and orchestration, making one shared FC/NM reference less meaningful.

Therefore Memory Gap Closure is not a universal MIB Score component.

It is a calibrated Track A diagnostic.

---

# 97. Scenario Calibration Matrix

Canonical Scenario authors SHOULD test at least:

```text
No Memory
Full Context
Simple Memory Baseline
Stronger Memory Baseline
```

and inspect:

```text
solvability
memory dependence
variance
ablation sensitivity
distractor effect
score stability
```

A benchmark should be calibrated before it is used to rank others.

---

# 98. Statistical Unit

The benchmark must distinguish:

```text
repetition
hidden Scenario Instance
Scenario Template
dimension
```

These are not interchangeable independent samples.

The primary semantic design unit is the:

```text
Scenario Template
```

Hidden instances estimate generalization within that design.

---

# 99. Multi-Run Aggregation

Recommended order:

```text
1. aggregate evaluator outputs into Probe score
2. pair causal conditions by repetition/seed
3. aggregate repetitions within Scenario Instance
4. aggregate Instances within Template
5. aggregate Templates within Dimension
6. aggregate Dimensions into MIB Score
```

Changing this order can unintentionally change benchmark weighting.

---

# 100. Mean as Primary Estimator

For ordinary normalized performance, arithmetic mean is the default estimator.

Reasons:

```text
interpretable
linear
compatible with weighted scores
supports paired differences
```

MIB SHOULD additionally report medians for highly variable latency/cost metrics, but capability scoring uses means unless a Profile says otherwise.

---

# 101. Variance Reporting

For stochastic systems, reports SHOULD include:

```text
mean
standard deviation
number of repetitions
number of hidden instances
```

at least for:

```text
MIB Score
dimension scores
major causal metrics
```

---

# 102. Confidence Intervals

Official leaderboard results SHOULD report:

```text
95% confidence intervals
```

for:

```text
MIB Score
Dimension Scores
Memory Benefit
Memory Harm
Net Memory Gain
```

where sample size is sufficient.

---

# 103. Hierarchical Bootstrap

Recommended default for official MIB:

> **Hierarchical bootstrap over Scenario Templates and hidden Instances, preserving paired causal conditions.**

One bootstrap draw conceptually:

```text
sample Templates within each Dimension
        ↓
sample hidden Instances within selected Template
        ↓
keep all paired causal variants together
        ↓
sample repetitions if required
        ↓
recompute Dimension Scores
        ↓
recompute MIB Score
```

This respects the benchmark hierarchy.

---

# 104. Bootstrap Draw Count

Recommended:

```text
10,000 bootstrap resamples
```

for leaderboard publication.

Development tooling MAY use fewer for speed.

The exact count belongs in benchmark/profile metadata.

---

# 105. Percentile Confidence Interval

A simple v0.1 baseline is the percentile interval:

```text
2.5th percentile
97.5th percentile
```

of bootstrap scores.

Future MIB versions may adopt BCa or another method if justified.

The statistical method must be versioned.

---

# 106. Paired Comparison Between Systems

When two Track A systems are evaluated on identical hidden instances, system difference should use a paired estimator.

For each Template/Instance:

\[
\Delta_s =
Score_{A,s}
-
Score_{B,s}
\]

Bootstrap the paired deltas rather than independently bootstrapping A and B.

This increases statistical power and preserves shared Scenario difficulty.

---

# 107. Ranking and Statistical Ties

Leaderboard may sort by point estimate.

However MIB SHOULD avoid claiming:

```text
A is definitively better than B
```

when uncertainty is large.

Recommended publication:

```text
A    84.1 [82.7, 85.5]
B    83.8 [82.1, 85.2]
```

plus optional:

```text
statistically indistinguishable at 95% paired interval
```

when the paired difference interval contains zero.

---

# 108. Hidden Evaluation Reuse

Repeatedly evaluating the same hidden instances can eventually leak benchmark structure through leaderboard feedback.

Official MIB MAY use:

```text
rotating hidden instance seeds
private holdout templates
submission-rate limits
coarse public feedback
```

Scoring remains identical across these operational policies.

---

# 109. Score Confidence vs Epistemic Confidence

Benchmark statistical confidence is not Agent epistemic confidence.

Do not confuse:

```text
95% confidence interval of MIB Score
```

with:

```text
Agent confidence in a remembered fact
```

They belong to different layers.

---

# 110. Dimension Minimum Evidence

A Benchmark Profile SHOULD define a minimum number/weight of Scenario Templates required per Dimension.

Example policy:

```text
at least 5 canonical Templates
and
at least 80% required template-weight coverage
```

The exact thresholds belong to the Profile/Test Plan.

The scorer must expose coverage so these policies can be enforced.

---

# 111. Cross-Dimension Scenario Weighting

A Cross-Dimension Scenario may produce evidence for several Dimensions.

Its contribution should be explicitly partitioned.

Example:

```text
Temporal         0.40
Epistemic        0.30
Retention        0.15
Causal           0.15
```

This prevents one complex Scenario from unintentionally counting at full weight in every Dimension.

---

# 112. Avoid Double Counting Causality

If a Scenario's full-performance score contributes to:

```text
Temporal Memory
```

and the same Scenario has relevant-memory ablation, the causal difference may additionally contribute to:

```text
Causal Memory Impact
```

This is intentional because they answer different questions.

But the same causal delta SHOULD NOT also be silently added again as a bonus to Temporal Memory unless the Scenario explicitly defines such scoring.

---

# 113. Capability Score Does Not Reward More Memory

MIB does not directly award points for:

```text
number of stored records
database size
number of embeddings
number of graph edges
```

Memory quantity is not capability.

Storage metrics belong to efficiency/capacity reporting.

---

# 114. Efficiency Is Separate

Recommended efficiency metrics:

```text
memory writes / meaningful event
storage / 1k events
retrieval latency p50/p95
end-to-end latency
tokens injected / task
formation token cost
recall token cost
external calls
cost / 1k events
```

They MUST NOT be directly mixed into MIB Score.

---

# 115. Capability–Efficiency Frontier

Research and leaderboards MAY plot:

```text
MIB Score vs Cost
MIB Score vs Latency
Memory Benefit vs Storage
Skill Transfer vs Memory Writes
```

Pareto comparison is preferable to a hidden capability/cost exchange rate.

---

# 116. Capacity Stress

MIB-L and other stress profiles may measure performance as history grows.

Let:

\[
D(n)
\]

be Dimension performance after \(n\) meaningful events.

Reports MAY show:

```text
D(100)
D(1,000)
D(10,000)
```

Capacity degradation is useful diagnostic evidence but should not be folded into another profile's score without explicit policy.

---

# 117. Forgetting Curve Diagnostics

A Scenario family may evaluate:

\[
Recall(\Delta t)
\]

over increasing virtual-time intervals.

MIB should distinguish:

```text
time-based decay
interference-based decay
semantic supersession
selective operational forgetting
```

A simple decline with time is not automatically good or bad; correctness depends on whether the memory remains relevant.

---

# 118. Freshness Adoption Rate

For stale-memory scenarios:

\[
SAR =
\frac{
\# stale\ choices\ adopted
}{
\# stale\ trap\ opportunities
}
\]

Lower is better.

A corresponding resistance score:

\[
SRS = 1-SAR
\]

may contribute to Selective Forgetting.

---

# 119. Historical Fidelity

For scenarios where old state remains historically queryable:

\[
HF =
\frac{
\# correct\ historical\ recalls
}{
\# historical\ probes
}
\]

Historical Fidelity complements stale suppression.

A system should ideally have:

```text
low stale adoption
+
high historical fidelity
```

---

# 120. Source Attribution Accuracy

For epistemic scenarios:

\[
SAA =
\frac{
\# correctly\ attributed\ claims
}{
\# attribution\ opportunities
}
\]

A final answer may be factually correct while SAA is poor.

This is why Epistemic Memory is broader than fact recall.

---

# 121. Correction Retention

A correction scenario may score two independent properties:

```text
Current Correction Adoption
Historical Prior-State Recall
```

A system that simply destroys old state may succeed on the first and fail on the second.

---

# 122. Evidence Independence Diagnostic

Where one original source is transformed into several derived memories, the Agent should not treat them as multiple independent corroborations.

An epistemic scenario may define:

```text
single-root evidence condition
duplicate-derived condition
```

and score whether confidence/behavior changes inappropriately.

The exact evaluator remains Scenario-specific.

---

# 123. Prospective Timeliness

For a trigger at time \(t_0\), a prospective emission may have delay:

\[
\Delta t =
t_{emit}-t_0
\]

A Scenario may define:

```text
on-time window
late-but-useful window
too-late window
```

and map them into normalized score.

Virtual Time should be used when timeliness is semantic.

Wall-clock latency belongs to efficiency.

---

# 124. Premature Trigger Penalty

Prospective memory should not activate before its condition.

A Scenario MAY penalize:

```text
premature reminder
repeated reminder without trigger
wrong-actor trigger
```

This measures selectivity, not only retention.

---

# 125. Self-Limitation Continuity

A Self Memory scenario may measure:

\[
SLC =
\frac{
\# correctly\ remembered\ capability\ limitations
}{
\# relevant\ opportunities
}
\]

but this should be combined with actual Runner tool authority.

Remembered limitations are cognitive state.

Actual permissions remain external truth.

---

# 126. Authority Confusion Rate

Where memory content claims authority the Agent does not have:

\[
ACR =
\frac{
\# authority\ violations
}{
\# authority\ trap\ opportunities
}
\]

Lower is better.

Severe authority violations MAY receive Scenario penalties.

---

# 127. Composite Capability Card

A complete Capability Card SHOULD show:

```text
MIB Profile
Track
Scale
Model / Agent / Memory identity

MIB Score
95% CI

8 Dimension Scores
coverage for each Dimension

Memory Benefit
Memory Harm
Net Memory Gain
Causal Memory Impact
Irrelevant Memory Stability
Memory-Induced Error Rate
Negative Transfer Rate
Error Recurrence Rate

Efficiency metrics
execution failure rate
warnings
```

---

# 128. Example Capability Card

```text
MIB — Memory Intelligence Benchmark
════════════════════════════════════════════

Profile
  MIB-Full-1.0

Track
  A — Memory System

System
  Agent:   MIB Reference Agent 1.0
  Memory:  Example Memory 2.3
  Model:   Fixed Model X

MIB Score
  77.2
  95% CI: [75.8, 78.7]

Capability
  Retention & Retrieval       91.0
  Temporal Memory             84.0
  Epistemic Memory            62.0
  Experience Memory           81.0
  Skill Learning & Transfer   74.0
  Selective Forgetting        69.0
  Prospective & Self Memory   76.0
  Causal Memory Impact        82.0

Causal Diagnostics
  Memory Benefit             +28.4 pp
  Memory Harm                  5.2 pp
  Net Memory Gain            +23.2 pp
  Irrelevant Memory Stability 96.1
  Memory-Induced Error Rate    7.4%
  Negative Transfer Rate       8.0%
  Error Recurrence Rate       11.0%

Coverage
  Full Profile               100%

Execution
  Infrastructure Failure       0.3%

Efficiency
  Storage / 1k events          ...
  Recall latency p50           ...
  Recall latency p95           ...
  Tokens injected / task       ...
  Cost / 1k events             ...
```

---

# 129. Worked Causal Example

Suppose one Scenario Template yields:

```text
Full performance               F = 0.967
Relevant-memory ablated        R = 0.300
Irrelevant-memory ablated      I = 0.950
Harmful-memory condition       H = 0.700
Clean control                  C = 0.967
```

Raw Memory Benefit:

\[
MB =
0.967-0.300
=
0.667
\]

Displayed:

```text
+66.7 pp
```

---

# 130. Worked Headroom Benefit

Remaining headroom over ablated:

\[
1-R = 0.700
\]

Therefore:

\[
HMB =
\frac{0.667}{0.700}
=
0.953
\]

or:

```text
95.3
```

as a normalized positive-benefit component.

---

# 131. Worked Irrelevant Stability

Without tolerance:

\[
IMS =
1-|0.967-0.950|
=
0.983
\]

or:

```text
98.3
```

---

# 132. Worked Harm Resistance

\[
MH =
\max(0,0.967-0.700)
=
0.267
\]

\[
HRS =
1-0.267
=
0.733
\]

or:

```text
73.3
```

---

# 133. Worked Causal Dimension Component

Using:

```text
HMB 50%
IMS 20%
HRS 30%
```

\[
CausalScore =
100(
0.50(0.953)
+
0.20(0.983)
+
0.30(0.733)
)
\]

\[
CausalScore
\approx 89.3
\]

This demonstrates why the causal dimension is richer than raw Memory Benefit alone.

---

# 134. Worked Final MIB Score

Suppose:

```text
Retention & Retrieval       91
Temporal Memory             84
Epistemic Memory            62
Experience Memory           81
Skill Learning & Transfer   74
Selective Forgetting        69
Prospective & Self Memory   76
Causal Memory Impact        82
```

Using the v1 weights:

```text
0.12
0.13
0.15
0.15
0.15
0.10
0.08
0.12
```

the Base MIB Score is:

\[
MIB_{base} = 77.21
\]

Displayed:

```text
MIB Score = 77.2
```

assuming no global guardrail penalty.

---

# 135. Score Interpretation

MIB SHOULD NOT publish universal qualitative labels such as:

```text
80 = human-level
90 = superhuman
```

without empirical calibration.

A score of:

```text
82
```

means:

> 82 under a specific MIB Profile, Track, Scale, benchmark version, and evaluation configuration.

It is not an absolute law of intelligence.

---

# 136. Required Score Identity

Every published score must identify:

```text
MIB version
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
MIB-Full-1.0 / Track A / MIB-M
77.2
```

A naked:

```text
MIB 77.2
```

is insufficient for scientific comparison.

---

# 137. Cross-Version Comparison

Scores from different major benchmark Profiles MUST NOT be directly ranked.

Example:

```text
MIB-Core-0.1 84.0
```

does not imply superiority over:

```text
MIB-Full-1.0 80.0
```

because dimensions, weights, and Scenario Packs differ.

---

# 138. Scenario Revision and Score Compatibility

If a Scenario changes:

```text
ground truth
Probe semantics
ablation meaning
evaluator logic
scoring weight
```

its semantic version must change.

Leaderboard policy determines whether the revised Scenario Pack creates a new incomparable score series.

---

# 139. Evaluator Drift

Changing an LLM judge model or semantic evaluator can change scores.

Therefore official reports MUST record:

```text
evaluator implementation version
judge model/version if used
rubric version
```

A hidden judge upgrade should not silently alter the same leaderboard score series.

---

# 140. Statistical Reproducibility

An official score is not just one number.

It is a result of:

```text
Scenario Pack
hidden instances
seeds
repetitions
Adapter
Agent configuration
Evaluator configuration
aggregation policy
```

These inputs must be versioned sufficiently for reproduction or hosted verification.

---

# 141. Leaderboard Submission Minimums

A leaderboard policy SHOULD require:

```text
Adapter conformance pass
required Profile coverage
maximum execution failure rate
declared system identity
hidden evaluation
minimum repetitions where needed
run artifact
score report
```

The exact thresholds belong to leaderboard policy.

---

# 142. Execution Failure Rate

Define:

\[
EFR =
\frac{
\# execution\ failed\ Probe\ attempts
}{
\# scheduled\ Probe\ attempts
}
\]

This is reported separately.

A high EFR may make a submission ineligible even if surviving Probe scores are high.

---

# 143. Unsupported Rate

Define:

\[
UR =
\frac{
\# unsupported\ required\ Scenario\ weight
}{
\# total\ required\ Scenario\ weight
}
\]

This is closely related to coverage.

Official profiles may require:

```text
UR = 0
```

for leaderboard eligibility.

---

# 144. Invalid Run Exclusion

A run may be excluded from cognitive scoring only for benchmark-execution reasons such as:

```text
Runner failure
corrupted Scenario instantiation
Oracle bug
tool simulator failure
verified benchmark infrastructure outage
```

Participant cognitive failure is not an invalid run.

Participant timeout is not automatically an invalid benchmark run.

---

# 145. Post-Hoc Scenario Removal

Removing a difficult Scenario after seeing participant results risks benchmark manipulation.

Canonical Scenario removal should require:

```text
documented defect
versioned Pack update
recomputation for all affected submissions
```

not participant-specific adjustment.

---

# 146. Missing Data

Missing Probe output due to participant failure follows execution policy.

Missing data due to benchmark infrastructure fault should be rerun or marked invalid.

The scorer MUST NOT silently impute a favorable value.

---

# 147. Confidence Interval for Rare Harm

Memory-induced harmful errors may be rare.

Reports should show:

```text
count
denominator
rate
confidence interval
```

Example:

```text
Authority violations:
  1 / 250
  0.4%
```

A rate alone can look more precise than the evidence supports.

---

# 148. Bootstrap for Rates

For template-structured rates such as:

```text
Negative Transfer Rate
Error Recurrence Rate
Memory-Induced Error Rate
```

the same hierarchical bootstrap SHOULD resample complete eligible opportunities within their Template context.

Simple binomial intervals MAY be shown as supplementary diagnostics.

---

# 149. Robustness Checks

Benchmark maintainers SHOULD inspect whether rankings materially change under reasonable alternatives:

```text
equal vs published Template weights
mean vs median Template aggregation
different bootstrap seeds
judge resampling
removal of one Template family
```

Large ranking instability indicates weak benchmark robustness.

These analyses need not become part of participant MIB Score.

---

# 150. Score Sensitivity

MIB SHOULD make weight sensitivity auditable.

Given Dimension vector:

\[
D
\]

and weight vector:

\[
W
\]

the final score is linear:

\[
MIB = W \cdot D
\]

This makes it easy to show whether a leaderboard result depends heavily on one policy weight.

---

# 151. No Hidden Bonus

MIB Score MUST NOT include undocumented bonuses for:

```text
novel architecture
open source
KIP usage
large memory capacity
low cost
vendor reputation
human preference
```

Only declared scoring rules count.

---

# 152. KIP Neutrality

A KIP-based Agent receives no scoring advantage simply for conforming to KIP.

MIB evaluates behavior.

KIP may make certain memory distinctions easier to implement or diagnose, but:

```text
KIP conformance != MIB score
```

---

# 153. Model Strength and Memory Strength

Track B intentionally measures a complete system, so model strength affects absolute capability.

MIB addresses this by publishing:

```text
MIB Score
+
Causal Memory Metrics
```

and by maintaining Track A for controlled memory-system comparison.

MIB SHOULD NOT apply an opaque "model intelligence correction factor."

---

# 154. Base-Model Ceiling

A memory benchmark should not punish a memory system because the fixed base model is incapable of the downstream task.

This is why Scenario calibration uses:

```text
Full-Context baseline
```

and why low-FC Scenarios should not enter a canonical Track A Pack.

---

# 155. Base-Model Floor

Likewise, if the fixed base model can solve a Scenario with no memory:

```text
NM ≈ 1
```

the Scenario contributes little evidence about memory.

It should be treated as non-discriminative during calibration.

---

# 156. Benchmark Difficulty Growth

Future MIB versions may increase difficulty by:

```text
more interference
longer time horizon
more identity collisions
more source conflicts
larger Experience spaces
farther Skill transfer
stronger stale traps
```

Scores should remain versioned rather than artificially normalized to preserve old numerical levels.

---

# 157. Score Stability Across Scale

Systems may receive:

```text
MIB-S score
MIB-M score
MIB-L score
```

These are distinct scale results.

A useful diagnostic is:

\[
ScaleRetention =
\frac{
Score_{L}
}{
Score_{S}
}
\]

when meaningful.

This is supplementary; do not replace the individual scale scores.

---

# 158. Capacity Collapse

A system that scores:

```text
MIB-S 90
MIB-M 71
MIB-L 35
```

has a different memory profile from one that remains stable.

Capability Cards SHOULD expose scale curves when available.

---

# 159. Confidence-Aware Ranking

A public UI MAY group submissions whose paired score differences are not statistically distinguishable.

Example:

```text
Tier A:
  System 1
  System 2
  System 3

Tier B:
  System 4
```

This is preferable to implying significance from differences such as:

```text
84.13 vs 84.08
```

---

# 160. Score Audit Trail

Every published MIB Score SHOULD be reconstructable from:

```text
Probe results
Scenario Instance results
Template aggregation
Dimension aggregation
Profile weights
penalties
```

A machine-readable report should eventually allow:

```text
mib verify-score report.json
```

to recompute the displayed score.

---

# 161. No Evaluator Feedback During Run

Evaluator results MUST NOT be shown to the Agent before the Scenario condition is complete.

Otherwise the Agent could learn the benchmark answer from scoring feedback.

This is especially important in longitudinal Scenarios.

---

# 162. No Cross-Condition Learning

The Agent must not carry memory from:

```text
full condition
```

into:

```text
relevant-ablation condition
```

or vice versa.

Each paired condition is an isolated run unless a controlled snapshot intervention explicitly defines otherwise.

---

# 163. Condition Ordering

To reduce order effects, the Runner MAY randomize execution order of:

```text
full
relevant ablation
irrelevant ablation
harmful condition
```

across independent run namespaces.

The Agent must not see condition labels.

Paired seeds remain aligned.

---

# 164. Causal Interference Check

A benchmark maintainer SHOULD verify that removing a relevant event does not unintentionally change unrelated generated future history.

This follows the Scenario Model's deterministic replay rule.

If ablation changes many unrelated observations, CMI no longer isolates memory.

---

# 165. Ablation Validity

A causal result is valid only if:

```text
the target episode was actually visible in full condition
the target is absent/masked in ablated condition
future task is equivalent
unrelated history is preserved
Runner world state is equivalent where intended
```

The Run Artifact should record causal-pair validity checks.

---

# 166. Relevant-Memory Coverage

For a Scenario with multiple independent relevant episodes, benchmark authors may define:

```text
single ablation
group ablation
leave-one-out ablation
```

MIB v0.1 does not prescribe one universal method.

The selected intervention must be described in the Scenario.

---

# 167. Synergistic Memories

Some tasks require two past memories jointly.

Example:

```text
A alone insufficient
B alone insufficient
A+B sufficient
```

A group relevant ablation may be more meaningful than independent leave-one-out tests.

Causal scoring should follow the Scenario's declared semantic unit of relevance.

---

# 168. Redundant Memories

If two independent past observations both contain the same relevant fact, removing one may have little effect even though memory is functioning correctly.

Therefore relevant ablation should remove the intended **causal information set**, not arbitrarily one redundant event.

Scenario authors must design ablations carefully.

---

# 169. Evidence Redundancy vs Evidence Independence

In epistemic scenarios, redundant content may still have different source semantics.

Removing one source can change:

```text
support strength
contradiction state
source attribution
```

even if the final factual answer remains unchanged.

Causal Probe design should score the intended epistemic behavior, not only one output string.

---

# 170. Scenario Weight Governance

Changing Template weights can alter leaderboard ranking.

Therefore:

```text
Dimension weights
Template weights
penalty caps
causal-component weights
```

are benchmark-governance decisions.

They MUST be versioned and public.

---

# 171. Recommended v1 Causal Component Weights

Unless a future Profile overrides them:

```text
Headroom-Normalized Relevant Benefit   0.50
Irrelevant Memory Stability            0.20
Harm/Stale Resistance                  0.30
```

Rationale:

```text
memory should help when relevant
memory should stay quiet when irrelevant
memory should be resisted when harmful
```

Positive benefit receives the largest weight but cannot dominate the whole causal score.

---

# 172. Recommended Full-Profile Dimension Weights

From MIB Architecture:

```text
Retention & Retrieval        0.12
Temporal Memory              0.13
Epistemic Memory             0.15
Experience Memory            0.15
Skill Learning & Transfer    0.15
Selective Forgetting         0.10
Prospective & Self Memory    0.08
Causal Memory Impact         0.12
```

These should be treated as v1 policy candidates until the full Test Plan is frozen.

---

# 173. Why Epistemic / Experience / Skill Receive Higher Weight

MIB intentionally goes beyond simple recall.

The proposed weight policy gives substantial emphasis to:

```text
whether memory preserves belief/source distinctions
whether past trajectories are useful
whether Experience becomes transferable Skill
```

rather than letting direct factual recall dominate the benchmark.

This is a benchmark-design value choice and should remain explicit.

---

# 174. Why Causal Is Not 50% of MIB Score

Causality is foundational, but a pure causal-delta benchmark can reward large improvement from a low baseline.

MIB therefore:

```text
makes causal intervention mandatory for strong evaluation
```

without making raw delta the majority of the final capability score.

The 12% primary dimension plus separate causal metrics keeps both views visible.

---

# 175. Score Floors and Ceilings

Capability dimensions naturally lie in:

```text
0..100
```

Signed diagnostics such as:

```text
CMI
Memory Benefit
Learning Gain
Net Memory Gain
```

may be negative.

Do not clamp signed diagnostics before reporting.

Only normalized positive score components such as:

```text
HMB
IMS
HRS
NTR
EAS
```

are bounded to `[0,1]`.

---

# 176. Anomalous Results

Examples worth flagging:

```text
MB < 0
Memory Harm very high
I >> F
I << F
FC < F by large margin
N > F
Negative Transfer Rate > 50%
ERR remains high after repeated Experience
```

The report SHOULD include warnings rather than silently hiding anomalies inside averages.

---

# 177. Above Full-Context Performance

A memory-enabled Agent may outperform a full-context baseline because its memory system:

```text
compresses useful patterns
learns Skills
reduces distractor load
maintains better state
```

This is not automatically an error.

Diagnostics such as MGC may exceed 1 before optional display clamping.

Raw values should remain available.

---

# 178. Below No-Memory Performance

If:

```text
F < N
```

memory is harming the task.

This should appear as:

```text
negative Memory Benefit
```

when no-memory is the causal reference.

The system should not receive positive causal-benefit credit.

---

# 179. Score Reporting Precision

Recommended:

```text
MIB / Dimension scores: 1 decimal
percentage-point deltas: 1 decimal
rates: 1 decimal percentage
latency: appropriate engineering units
cost: enough significant digits to avoid misleading rounding
```

Machine reports retain full precision.

---

# 180. Machine-Readable Report Requirements

The future `mib-report.schema.json` should include:

```text
benchmark identity
Profile
Track
Scale
system descriptor

per-Probe scores
per-condition scores
per-Instance scores
per-Template scores
Dimension scores
MIB Base Score
global penalties
Final MIB Score

coverage
causal pair data
MB / MH / NMG / IMS
negative transfer
error recurrence
learning gain

confidence intervals
bootstrap method
repetition counts
execution failures
efficiency
warnings
```

---

# 181. Score Recalculation

The machine report SHOULD contain enough numeric material to recompute:

```text
Scenario score
Dimension score
MIB Score
```

without rerunning the Agent.

This is important for:

```text
auditing
weight sensitivity
leaderboard verification
research reanalysis
```

---

# 182. Raw Output Retention

Whether raw Agent output can be publicly retained may depend on:

```text
privacy
license
submission policy
hidden Scenario protection
```

A report can store:

```text
output digest
evaluator result
score
```

when raw output cannot be published.

Official evaluators still require access during evaluation.

---

# 183. MIB Score as a Vector Plus Scalar

The scalar MIB Score is useful for:

```text
ranking
communication
high-level comparison
```

But serious analysis should treat the result as:

\[
MIB =
(
D_1,
D_2,
...,
D_8,
CausalMetrics,
Efficiency,
Coverage
)
\]

with one weighted scalar projection.

A single number should never replace the capability profile.

---

# 184. Memory Intelligence Profile

Two systems with the same MIB Score may be radically different.

Example:

```text
System A:
  great recall
  weak Skill learning

System B:
  moderate recall
  excellent Experience transfer
```

Therefore the Capability Card is a first-class benchmark output, not decoration.

---

# 185. Minimal Official Score Statement

A scientifically meaningful statement should look like:

```text
System X scored 77.2
on MIB-Full-1.0,
Track A,
MIB-M scale,
Scenario Pack 1.0,
95% CI [75.8, 78.7].
```

Not:

```text
System X has 77.2 memory intelligence.
```

The benchmark context matters.

---

# 186. Scoring Invariants

1. All evaluator outputs normalize to `[0,1]`.
2. Capability scores use full-memory performance.
3. Causal contribution is reported separately.
4. MIB Score is not pure with-memory minus no-memory delta.
5. Track A and Track B are not directly ranked together.
6. Probe aggregation occurs before Scenario aggregation.
7. Repetitions aggregate within Scenario Instance.
8. Hidden Instances aggregate within Scenario Template before Template enters a Dimension.
9. Instance count must not silently become semantic Template weight.
10. Template weights are benchmark policy.
11. Dimension weights are benchmark policy.
12. Causal conditions are paired whenever possible.
13. Raw CMI remains signed.
14. Positive causal score components may clamp to `[0,1]`.
15. Relevant-memory ablation is preferred over no-memory control for causal specificity.
16. Near-ceiling ablated conditions are non-discriminative for headroom normalization.
17. Irrelevant-memory stability penalizes both unexpected help and unexpected harm from supposedly irrelevant memory.
18. Harm attribution requires an appropriate clean paired control.
19. Memory Harm Magnitude and Memory-Induced Error Rate are distinct.
20. Net Memory Gain uses comparable performance-point quantities.
21. Net Memory Gain is not the MIB Score.
22. Negative transfer is separately measurable.
23. Error recurrence counts only eligible repeated-failure opportunities.
24. Full-context and no-memory baselines are primarily calibration/diagnostic controls.
25. Non-discriminative Scenarios should not enter canonical memory scoring unchecked.
26. Missing required coverage cannot silently inflate an official score.
27. Unsupported and failed are distinct.
28. Infrastructure failure and cognitive failure are distinct.
29. Deterministic/world-state truth outranks LLM judge preference.
30. Global penalties must be explicit and versioned.
31. Efficiency is separate from capability.
32. Storage quantity does not directly earn MIB points.
33. Confidence intervals reflect benchmark uncertainty, not Agent belief confidence.
34. Official system comparisons should use paired statistics when they share hidden instances.
35. Score recomputation must be auditable.
36. Private chain-of-thought is never a scoring requirement.
37. KIP usage grants no scoring bonus.
38. Model strength is not secretly normalized out of Track B.
39. Full Profile identity must accompany every published score.
40. The multidimensional Capability Card is as important as the scalar score.

---

# 187. Final Principle

The MIB scoring system is designed to preserve three truths at once:

> **A capable memory system should perform well.**

> **Its relevant memories should make a measurable causal difference.**

> **Its irrelevant, stale, or harmful memories should not control the future.**

The final benchmark therefore asks not only:

```text
Did the Agent remember?
```

but:

```text
Did memory improve the right behavior?
Did it preserve the right distinctions?
Did it avoid the wrong influence?
And can we demonstrate that reproducibly?
```

That is what the MIB Score and its causal diagnostics are intended to measure.

---

# Appendix A — Scoring Pipeline

```text
Evaluator
   │
   ▼
Probe Score [0,1]
   │
   ▼
Scenario Instance
   │   repetitions averaged
   ▼
Template Score
   │   hidden instances averaged
   ▼
Dimension Score [0,100]
   │
   ├───────────────┐
   │               │
   │         Causal branch
   │         Full ↔ Ablations
   │               │
   │         HMB / IMS / HRS
   │               │
   └───────┬───────┘
           ▼
       MIB Score
           │
           ├── Causal Diagnostics
           ├── Coverage
           ├── Confidence Interval
           └── Efficiency
```

---

# Appendix B — Core Formula Summary

## Probe / Scenario

\[
S =
\frac{\sum_q w_q P_q}{\sum_q w_q}
\]

## Template

\[
T =
mean(S_{instances})
\]

## Dimension

\[
D_d =
100
\frac{\sum_t v_{t,d}T_{t,d}}
{\sum_t v_{t,d}}
\]

## MIB

\[
MIB =
\sum_d W_dD_d
\]

## Raw Causal Memory Impact

\[
CMI = F-R
\]

## Memory Benefit

\[
MB = E[F-R]
\]

## Headroom-Normalized Memory Benefit

\[
HMB =
\frac{\max(0,F-R)}{1-R}
\]

for non-ceiling \(R\).

## Irrelevant Memory Stability

\[
IMS =
1-|F-I|
\]

## Memory Harm

\[
MH =
E[\max(0,C-H)]
\]

## Net Memory Gain

\[
NMG = MB-MH
\]

## Error Recurrence

\[
ERR =
\frac{Repeated\ Known\ Failures}
{Eligible\ Opportunities}
\]

## Negative Transfer

\[
NT =
\max(0,B_{nonmatch}-F_{nonmatch})
\]

---

# Appendix C — Recommended Report Naming

Use unambiguous labels:

```text
MIB Score
Retention & Retrieval Score
Temporal Memory Score
Epistemic Memory Score
Experience Memory Score
Skill Learning & Transfer Score
Selective Forgetting Score
Prospective & Self Memory Score
Causal Memory Impact Score

Memory Benefit (pp)
Memory Harm (pp)
Net Memory Gain (pp)

Memory-Induced Error Rate (%)
Irrelevant Memory Stability
Negative Transfer Rate (%)
Error Recurrence Rate (%)
Learning Gain (pp)
Historical Fidelity (%)
Stale Adoption Rate (%)
```

Avoid ambiguous labels such as:

```text
Memory Accuracy
Memory Quality
Memory Delta
```

without a precise definition.

---

# Appendix D — Recommended Next Artifacts

With scoring semantics defined, the next artifacts should be:

```text
1. mib-report.schema.json
2. MIB-v0.1-Test-Plan.md
3. canonical v0.1 Scenario Templates
4. Scenario Validator
5. Agent Adapter conformance suite
6. reference Runner
7. Capability Card renderer
```

The immediate next document should be:

```text
mib-report.schema.json
```

because the benchmark now has:

```text
Scenario semantics
+
Agent execution semantics
+
Score semantics
```

and needs one machine-readable artifact that records all three.

---

# Appendix E — Supplemental Transfer Diagnostics

`MIB-Transfer-Intelligence.md` defines a diagnostic layer that decomposes a transfer outcome into Formation, Routing, and Uptake, and reports how far a transfer had to reach.

Nothing in that layer is part of this specification's score semantics. Specifically, no transfer metric enters:

```text
Probe score
Scenario full-condition score
Template score
Dimension score
Causal Score
MIB Base Score
MIB Score
Coverage
```

A pack whose Templates carry no Transfer Support Annotation produces a report byte-identical to one produced before the extension existed. Diagnostics travel as the report extension `mib.transfer_diagnostics.v1` and, for MIB-R, `mib.reality.v1`.

Two naming rules matter for anyone reading both documents:

`Negative Transfer Rate`
: A transfer diagnostic. It is the share of annotated Probes whose natural score falls below their memory-removed baseline. It is **not** the standardized `negative_transfer` causal metric defined in §63 of this document, whose control semantics are stricter. Do not map one onto the other. For transfer diagnostics use the explicit terms Near-Match Harm, Wrong-Ability Harm, Unsupported Memory Delta, and Stale-Skill Harm.

`Near-Match Resistance`
: An outcome measure, not applicability precision. A correct answer is not evidence that memory was withheld. Applicability Precision and Recall may be computed only where a Scenario or a decomposable Memory Adapter provides direct observable evidence that memory was applied.

Undefined diagnostics are reported as `eligible: false` with a reason, never as `0`, following the same epistemic semantics this document applies to unsupported and non-evaluated evidence.
