# MIB Transfer Intelligence

## Formation, Routing, Uptake, and Transfer Distance

**Version:** 0.1-draft
**Status:** Diagnostic extension / Companion to `MIB-Scoring.md` and `MIB-Scenario-Model.md`

---

# 0. Purpose

MIB-Core answers one question:

> Which part of the past participated correctly in this future computation?

It answers it behaviorally, and it answers it well. What it does not do on its own is say *why* a transfer failed. A Skill Scenario that degrades under relevant-memory ablation tells you memory mattered. It does not tell you whether the system failed to compile a usable procedure, compiled one and never retrieved it, or retrieved the right one and could not execute it.

This document defines the diagnostic layer that separates those cases:

```text
Experience
    ↓
Formation
    ↓
Persistent Memory / Skill
    ↓
Routing
    ↓
Applicability
    ↓
Uptake
    ↓
Future Behavior
```

Everything here is **supplemental diagnostics**. No metric defined in this document enters the MIB Score, the Causal Score, Coverage, or a Template or Dimension aggregate. A pack whose Templates carry no Transfer Support Annotation produces a report that is byte-identical to one produced before this extension existed.

---

# 1. Non-Negotiable Invariants

## 1.1 Memory remains the treatment variable

The extension increases diagnostic resolution. It MUST NOT turn MIB into a generic self-evolution or agent-performance benchmark. Every diagnostic cell defined here varies memory state and holds everything else fixed.

## 1.2 Score compatibility

Installing this extension MUST NOT change an existing `MIB-Core-0.1` score. Template aggregation, Dimension aggregation, MIB Score, Causal Score, Coverage, Bootstrap CI, and `verify-score` all remain identical for an unchanged report.

No transfer metric enters an official score unless a future Profile explicitly opts in.

## 1.3 Architecture neutrality

Nothing here assumes memory is a vector database, a graph, a transcript store, a skill file, or a retrieval system. A compiled policy, an evolved instruction, a workflow patch, or an internal persistent state all qualify. The functional criterion is unchanged:

> If a persistent state created by past experience participates in future computation, it may be memory.

## 1.4 Missing evidence is not negative evidence

When an instrumented cell is unavailable or an oracle ceiling gives too little headroom, the affected ratio is reported as `eligible: false` with a reason. It is never reported as `0`.

## 1.5 Black-box evaluation remains first-class

Three of the four diagnostic cells run against an ordinary black-box Agent. Only one requires a Memory Adapter, and the official Track B path never requires one.

## 1.6 Hidden evaluator knowledge never reaches the Agent

Ability identity, supporting event IDs, oracle applicability, transfer relation, counterexample relation, oracle routing, and distance class are evaluator-only. They MUST NOT appear in a `ResetRequest`, `ObserveRequest`, `RespondRequest`, `ActRequest`, a tool result, participant-visible submission metadata, a public report, or a leaderboard response.

---

# 2. Terminology

## Experience

A situated causal trajectory:

```text
goal → action → observation → feedback → outcome
```

## Ability

An evaluator-defined reusable competence latent across one or more Experiences. An Ability is **benchmark annotation**. It is not a claim about the Agent's internal representation.

## Skill

A persistent reusable policy or procedure formed from Experience. The Agent may represent it however it chooses.

Do not identify `Ability == Skill`. An Ability is evaluator ontology; a Skill is Agent memory state. MIB cares whether future behavior reflects the Ability, not whether the internal representation matches the evaluator's wording.

## Formation

The transformation from past Experience into persistent reusable memory state.

## Routing

The selection and delivery of memory state relevant to the current future task.

## Uptake

The Agent's successful behavioral use of delivered relevant memory.

## Transfer

Improved future behavior caused by a reusable past-derived capability.

## Applicability Boundary

The conditions under which a Skill should, and should not, control behavior.

## Transfer Support

An evaluator claim that specific past Experience contains information sufficient to support a specific future Probe through one or more Abilities.

---

# 3. Transfer Support Annotation

## 3.1 Carrier

The annotation lives under the Scenario `extensions` key:

```text
mib.transfer_support.v1
```

It is not a top-level v0.1 Scenario property. Every existing Scenario file stays valid, every existing v0.1 parser can ignore it, and Hidden packs can adopt it gradually. It may be promoted to a first-class field in a future format version.

Its shape is defined by `schemas/mib-transfer-support.schema.json`.

## 3.2 Structure

```text
Past Events
    ↓ support
Ability
    ↓ applies_to
Future Probe

Counterexamples
    ↓ refine
Applicability Boundary
```

```json
{
  "version": "1.0.0",
  "abilities": [
    {
      "id": "ability.class_a7_scoped_commit",
      "kind": "procedure",
      "support_event_ids": ["e-failure", "e-rule"],
      "counterexample_event_ids": ["e-counterexample"],
      "applicability": {
        "positive_cues": ["class=A7"],
        "negative_cues": ["class=G2"]
      },
      "oracle_artifact": {
        "artifact_type": "skill",
        "content": "When an item is marked Class A7, activate its matching context before edit and commit."
      }
    }
  ],
  "probe_relations": [
    {
      "probe_id": "p-match",
      "ability_ids": ["ability.class_a7_scoped_commit"],
      "relation": "exact_replay",
      "support_expected": true,
      "transfer_distance": {"class": "D0", "normalized": 0.0}
    }
  ]
}
```

## 3.3 Event-reference semantics

`support_event_ids` and `counterexample_event_ids` MUST refer to Scenario Timeline IDs, and every referenced event MUST exist.

An Ability MAY require several events, because a causal information set is not the same thing as a single memory record. A failure, its diagnosis, and its recovery may jointly encode one reusable Ability.

## 3.4 Redundant support

When two independent Experiences each encode the same Ability, ablating one may not degrade anything. Declare them explicitly:

```json
{
  "causal_information_sets": [["e-a1", "e-a2"], ["e-b1", "e-b2"]],
  "minimum_sets_required": 1
}
```

A baseline that leaves a surviving support set in place is not a baseline. The diagnostic harness withholds *every* declared set.

## 3.5 Transfer Support versus causal ablation

They are related and not identical.

```text
Transfer annotation   these events support this Ability
Causal ablation       remove this information set and observe behavior
```

A well-formed Skill Scenario usually aligns them — `support_event_ids` is often exactly the relevant-memory Ablation target — but redundancy and negative controls break the alignment, which is why both are declared separately.

## 3.6 Public versus private

For Public Dev content, Ability IDs and generic relations MAY be public; exact applicability predicates, support-event causal sets, and oracle routing MAY remain in fixture-only files.

For Hidden Eval and Private Holdout, the full annotation is evaluator-private. A public report may expose only aggregates: distance-class aggregate, supported-transfer aggregate, near-match resistance aggregate, and formation/routing/uptake aggregate. It MUST never expose canonical private Ability IDs, support event IDs, hidden applicability cues, or the holdout task graph.

---

# 4. Relation Taxonomy

`relation` describes the qualitative support relation. It is **not** the same field as distance.

| Relation | Meaning | What it tests |
|---|---|---|
| `exact_replay` | Same latent task, same Ability application | Procedural recall floor |
| `surface_shift` | Different entities, wording, or tool names; one Ability | Abstraction beyond lexical matching |
| `structural_transfer` | Different task structure or domain; same latent procedure | Farther positive transfer |
| `compositional_transfer` | Two or more previously learned Abilities required | Composition |
| `supported_transfer` | Generic positive transfer; distance declared separately | — |
| `near_match_non_applicable` | High surface similarity, applicability condition fails | Negative-transfer resistance |
| `unsupported_novel` | No useful learned Ability exists | Withholding, epistemic humility |
| `stale_support` | Once valid, invalidated by the current world | Temporal/Skill interaction |
| `harmful_support` | Memory contains a misleading or incorrect procedure | Memory-harm resistance |

---

# 5. Transfer Distance

For **supported positive transfer only**:

```text
D0  exact_replay            0.00
D1  surface_shift           0.33
D2  structural_transfer     0.67
D3  compositional_transfer  1.00
```

There is deliberately no `D4` for near-match and no `D5` for unsupported. Those are not farther positive transfer; they are different causal control classes, and collapsing them onto the same axis would make "worse at transfer" and "correctly refused to transfer" look like the same number.

A negative control MUST NOT declare a `transfer_distance`. The validator rejects it.

The resulting curve is the **Transfer Profile**:

```text
D0  ███████████
D1  █████████
D2  ███████
D3  ████
```

It is reported alongside the MIB Score, never inside it.

---

# 6. The 2×2 Diagnostic Matrix

Two axes, Content Formation and Routing, each Automatic or Oracle:

```text
                    ROUTING
                Automatic    Oracle

CONTENT  Auto       AA          AO

         Oracle     OA          OO
```

`AA`
: The ordinary `full` condition. Real deployed behavior.

`AO`
: Automatic content, oracle routing. Does the system form useful content when routing is perfect?

`OA`
: Oracle content, automatic routing. Is routing the bottleneck when content quality is perfect?

`OO`
: Oracle content, oracle routing. An **uptake ceiling**, not a deployable method.

## 6.1 Cell construction

```text
B   supporting Experience removed, nothing supplied
AA  supporting Experience present, nothing supplied
AO  supporting Experience present, the system's own best-matching formed
    artifact surfaced at task time            (Memory Adapter required)
OA  supporting Experience removed, the canonical oracle artifact placed in
    the past stream where the Experience was  (black-box compatible)
OO  supporting Experience removed, the canonical oracle artifact surfaced
    at task time                              (black-box compatible)
```

`OA` and `OO` both carry oracle content and differ only in *when* it is available, which is what isolates Routing. `AA` and `AO` both carry automatic content and differ only in routing, which is what isolates Formation.

Oracle content **replaces** the Experience it stands in for. If the natural support stayed in place, `OA` would measure "natural memory plus a hint" rather than routing.

## 6.2 Routing means surfacing, not answering

A routed artifact is delivered through the ordinary observation channel, prefixed the way a memory system surfaces a recalled Skill:

```text
Reusable procedure recalled from earlier work: <artifact content>
```

Using one channel for every system keeps the cells paired between black-box and decomposable Agents.

## 6.3 Pairing

Every cell MUST preserve:

```text
same Scenario Instance
same repetition
same future Probe
same future world
same Agent seed where supported
```

Diagnostic runs are kept in their own list and are never merged into `results.runs`. Merging them would move condition scores, causal pair sets, and execution counts, and a supplemental diagnostic must never do that.

---

# 7. Oracle Skill Artifacts

An oracle artifact MUST:

```text
state a reusable procedure
state its trigger at an appropriate abstraction level
avoid task-specific hidden answers
avoid hidden test entity values
avoid verifier internals
avoid future Probe wording
```

Good:

```text
"When an item is marked Class A7, activate its matching context before edit and commit."
```

Bad:

```text
"For tomorrow's item Q-391, call workspace.select('west') and answer 42."
```

The validator enforces this: an oracle artifact that restates a Probe's accepted value, a world-assertion value, or a hidden-ground-truth string is a hard error.

Oracle routing means the evaluator selects the Ability the annotation declares for this Probe. It does not mean giving the Agent the answer, hidden world state, or the evaluator's oracle outcome.

---

# 8. Memory Adapter

Only the `AO` cell requires reaching into the memory system. The optional Memory Adapter (`src/mib_runner/memory_adapter.py`) exposes:

```text
describe_memory
reset_memory
observe_memory_event
consolidate_memory
export_artifacts
retrieve_artifacts
inject_artifacts
```

No method may require chain of thought, and none is required for a black-box submission.

`metadata.source_event_ids` on an exported artifact is a diagnostic only. It is self-reported and MUST NOT be trusted as ground truth for scoring or for oracle routing. The evaluator selects an artifact by matching it against its own canonical description of the Ability; claimed provenance only breaks ties. A system therefore cannot win the `AO` cell by labelling an unusable artifact with the right event IDs.

---

# 9. Metrics

Let:

```text
B  = memory-removed baseline
AA = natural automatic score
AO = automatic content + oracle routing
OA = oracle content + automatic routing
OO = oracle content + oracle routing
```

## 9.1 Natural Transfer Gain

```text
NTG = AA - B
```

Signed. Positive is useful transfer; negative is harmful evolution. Never take an absolute value: a negative gain is the finding, not a smaller positive number.

## 9.2 Formation Efficiency

```text
FE = (AO - B) / (OO - B)
```

## 9.3 Routing Efficiency

```text
RE = (OA - B) / (OO - B)
```

## 9.4 Natural Transfer Efficiency

```text
NTE = (AA - B) / (OO - B)
```

## 9.5 Eligibility

All three ratios apply only when:

```text
OO - B > ε        (default ε = 0.05)
```

Below that the denominator is noise. The metric is then reported as:

```json
{"value": null, "eligible": false, "reason": "insufficient_oracle_headroom",
 "numerator": 0.0, "denominator": 0.02, "epsilon": 0.05}
```

Raw values below 0 and above 1 are scientifically meaningful and are kept. Only the display form is clipped.

## 9.6 Uptake

There is deliberately no normalized "uptake efficiency": it has no defensible upper bound. Report:

```text
Oracle Routed Score = OO
Oracle Routed Gain  = OO - B
```

If a Scenario is calibrated so that an oracle Skill should enable near-complete success, a low `OO` means either the Agent cannot execute the ideal Skill, or the Scenario is not actually Skill-supported. Calibration must distinguish those.

## 9.7 Loss decomposition

```text
Formation Loss  = OO - AO
Routing Loss    = OO - OA
Deployment Gap  = OO - AA
```

These are display diagnostics. Formation and Routing interact, so the decomposition is **not** additive. The reported interaction residual makes that explicit:

```text
Interaction Residual = (OO - AA) - ((OO - AO) + (OO - OA))
```

## 9.8 Control metrics

```text
Supported Transfer Success Rate     mean AA over positive-transfer Probes
Near-Match Resistance               mean AA over near-match Probes
Unsupported-Memory Neutrality       1 - |AA - B| over unsupported Probes
Compositional Transfer Score        mean AA over compositional Probes
Negative Transfer Rate              share of annotated Probes with AA < B
```

Near-Match Resistance is an **outcome** measure, not applicability precision. A correct answer is not proof that memory was withheld. Applicability Precision and Recall may be computed only when a Scenario or a decomposable adapter provides direct observable evidence that memory was applied.

`Negative Transfer Rate` is deliberately its own name. It is not the standardized MIB `negative_transfer` causal metric, whose control semantics come from `MIB-Scoring.md`. For transfer diagnostics use the explicit terms: Near-Match Harm, Wrong-Ability Harm, Unsupported Memory Delta, Stale-Skill Harm.

## 9.9 Efficiency

Prior experience changes task cost. MIB reports, and does not score:

```text
tool call delta
latency delta
```

Both are paired per Probe, because an Ablation may cover only a subset of a Scenario's Probes and run-level totals would compare different workloads.

---

# 10. Aggregation

Aggregation is Template-first throughout:

```text
Repetition
    ↓
Scenario Instance
    ↓
Template
    ↓
Transfer relation / distance class
```

A Template with many generated Instances never becomes more semantically important, and a Template with four D2 Probes never outvotes a Template with one.

Confidence intervals use a Template-level bootstrap; Templates are the resampling unit, matching the hierarchical-bootstrap philosophy of MIB core aggregation. Development runs may use fewer resamples; official runs should use 10,000.

---

# 11. Report and Capability Card

Diagnostics are carried as the report extension `mib.transfer_diagnostics.v1`. For `scope=public`, the body is reduced to aliases and aggregates: per-Probe identity, per-Probe relation, and the Ability graph stay evaluator-private, because repeated leaderboard submissions would otherwise become an oracle-probing channel.

The Capability Card gains two optional blocks, rendered only when the diagnostics exist:

```text
Transfer Diagnostics
  Natural Transfer Gain  +18.4 pp
  Formation Efficiency     81.0
  Routing Efficiency       64.0
  Oracle-Routed Score      92.0
  Negative Transfer Rate    9.8%

Transfer Profile
  D0 Exact Replay          91.0
  D1 Surface Shift         82.0
  D2 Structural            69.0
  D3 Compositional         51.0
  Near-Match Resistance    76.0
  Unsupported Neutrality   94.0
```

An absent metric is omitted, never shown as zero.

---

# 12. Diagnostic Identifiability

A diagnostic is only worth reporting if a known failure mode produces the signature it claims. The reference fixture Agents in `src/mib_runner/agents/transfer_fixtures.py` exist to prove that:

| Fixture | AA | AO | OA | OO | Signature |
|---|---|---|---|---|---|
| Perfect | high | high | high | high | FE≈1, RE≈1 |
| BadFormation | low | low | high | high | FE≈0, RE≈1 |
| BadRouting | low | high | low | high | FE≈1, RE≈0 |
| NoTransfer | low | low | low | high | FE≈0, RE≈0 |
| BadUptake | low | low | low | low | OO low, ratios ineligible |
| OverTransfer | high | — | — | — | transfer good, boundary failed |

They are fixtures, not baselines. Nothing about them is a claim regarding any real memory system.

---

# 13. Calibration

Transfer calibration adds gates. It does **not** replace FC, NM, MDI, or causal sensitivity, which remain the primary structural admission gates.

```text
oracle_artifact_declared    every positive Probe has an oracle artifact
oracle_skill_solvable       OO ≥ threshold and OO - B ≥ minimum effect
unsupported_memory_neutral  |AA - B| within tolerance on unsupported Probes
near_match_trap_fires       an over-transferring fixture actually fails the trap
```

The admission gate turns on the **oracle edge**. A curator-labelled Ability is not useful merely because it sounds plausible: if an oracle Skill under oracle routing does not improve the target Probe, the edge is not empirically supported and the Template must not be used as a positive-transfer case.

A calibration baseline that shows no natural transfer is recorded as a *note about the baseline*, not as a Template defect. The reference B0–B3 fixtures are deterministic keyword agents; a D1 surface shift they cannot bridge is a finding about them, and it is exactly what the Transfer Profile is for.

---

# 14. Authoring Checklist

Before writing an annotation, the author must be able to answer:

```text
1. What reusable Ability should be learned?
2. Which past events jointly support it?
3. What is its applicability boundary?
4. Which future Probe expects transfer?
5. Is the future relation replay, surface shift, structural, compositional,
   near-match non-applicable, or unsupported?
6. Which ablation removes the complete causal information set?
7. Is an oracle Skill artifact safe to provide without leaking the answer?
```

If these cannot be answered clearly, do not create the annotation.

---

# 15. Tooling

```bash
# Validate a Scenario including its annotation
mib validate scenario.json \
  --schema schemas/mib-scenario.schema.json \
  --transfer-support-schema schemas/mib-transfer-support.schema.json \
  --require-transfer-annotations

# Summarize one annotation (evaluator-internal: it names Ability IDs)
mib inspect-transfer scenario.json \
  --transfer-support-schema schemas/mib-transfer-support.schema.json

# Behavioral diagnostics
mib benchmark scenarios/transfer \
  --profile profiles/MIB-Transfer-0.1-Dev.json \
  --schema schemas/mib-scenario.schema.json

# Add the AA/AO/OA/OO cells
mib benchmark scenarios/transfer \
  --profile profiles/MIB-Transfer-0.1-Dev.json \
  --schema schemas/mib-scenario.schema.json \
  --transfer-diagnostics
```

The Transfer Diagnostic Dev Pack lives in `scenarios/transfer/`, not under `scenarios/dev/`. The Runner globs a pack root recursively, so placing it inside the Public Dev tree would silently enlarge `MIB-Core-0.1-Dev-M3` and move its score. Score compatibility outranks directory tidiness.

---

# 16. Relationship to MIB-Core and MIB-R

```text
MIB-Core
    establishes causal validity

Transfer Diagnostics
    explains mechanism

MIB-R
    establishes ecological validity
```

Do not collapse these layers. See `MIB-R-Reality-Track.md`.
