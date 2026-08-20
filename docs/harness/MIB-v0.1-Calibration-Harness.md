# MIB v0.1 Calibration Harness

**Version:** 0.1-draft  
**Profile:** `MIB-Core-0.1`  
**Status:** Reference calibration implementation

## 1. Purpose

The Calibration Harness asks whether a proposed MIB Scenario is actually useful as a memory benchmark.

For each official Scenario Template it measures four reference conditions:

```text
B0 — No Memory
B1 — Full Visible History Fixture
B2 — Simple Lexical Retrieval
B3 — Structured / Agentic Memory
```

The core calibration quantities are:

```text
FC   = B1 Full Context performance
NM   = B0 No Memory performance
MDI  = FC - NM

MGC_B2 = (B2 - NM) / (FC - NM)
MGC_B3 = (B3 - NM) / (FC - NM)
```

MIB v0.1 uses the Test Plan candidate admission targets:

```text
FC  >= 0.80
NM  <= 0.60
MDI >= 0.25
```

The reference harness additionally reports:

```text
Baseline Span
Structured-over-Retrieval gain
Memory Benefit under replay ablation
Irrelevant Memory Stability
Memory Harm / Harm Resistance
```

## 2. Two Different Calibration Questions

Calibration deliberately separates:

### 2.1 Memory dependence

```text
Can a system solve the future task with the past?
Can it solve the same task without the past?
```

Measured primarily by:

```text
FC
NM
MDI
```

### 2.2 Intervention sensitivity

```text
If the relevant past is removed, does performance actually change?
If irrelevant past is removed, does performance remain stable?
```

Measured by:

```text
Memory Benefit
Headroom-Normalized Memory Benefit
Irrelevant Memory Stability
Harm Resistance
```

A Scenario may pass the first question but fail the second if its ablation removes the wrong causal information set.

## 3. Reference Baselines

### B0 — No Memory

Past benchmark observations are discarded. Tool results generated inside the current future action loop may be used transiently.

B0 estimates how much of the task can be solved from:

```text
Probe wording
current tool affordances
base action policy
chance/default behavior
```

A high B0 score is a warning: the Scenario may look memory-dependent while actually being solvable without memory.

### B1 — Full Visible History Fixture

All Agent-visible history is retained and exposed to a deterministic evaluator-side reasoner.

This is useful for detecting gross Scenario solvability problems, but it is **not** the release-grade Full Context baseline. It is a fixture, not a fixed external LLM.

Release calibration must later replace B1 with the same fixed base model/Agent policy used by Track A, with the relevant past directly available.

### B2 — Simple Lexical Retrieval

Memory is retrieved using lexical token overlap only:

```text
top-k = 2
no temporal model
no provenance model
no Experience compilation
no Skill applicability model
```

B2 is intended to expose Scenarios that can be solved by straightforward semantic/lexical memory lookup.

### B3 — Structured / Agentic Memory

B3 adds visible-content salience and memory-type cues:

```text
current/correction/update cues
source/authority cues
failure/recovery cues
Experience/Skill cues
context/applicability cues
```

It remains a deterministic reference baseline and is not a claim about the best memory architecture.

## 4. Calibration Card

Each Template receives:

```text
FC / NM / MDI
B2 / B3
MGC_B2 / MGC_B3
baseline span
causal diagnostics
gate results
recommendation
```

Recommendations:

```text
provisional_pass
revise_or_empirically_review
retire_or_redesign_candidate
```

`provisional_pass` means only that the deterministic fixture gate succeeds.

## 5. Release Calibration Boundary

The generated reference report has:

```text
release_calibration_eligible = false
```

This is intentional.

A release-grade calibration run must use, at minimum:

```text
B0: same fixed Agent/model with meaningful past absent or memory disabled
B1: same fixed Agent/model with full relevant past available
B2: a reproducible simple retrieval implementation
B3: at least one stronger memory implementation
```

The Harness supports overriding a baseline implementation:

```bash
mib-calibrate ... \
  --baseline-override B1=my_package:FixedModelFullContextAgent
```

An external baseline should truthfully declare its calibration role and whether it is release-calibration eligible.

## 6. CLI

```bash
mib-calibrate \
  /private/MIB-v0.1-Official-Canonical-Pack \
  --schema schemas/mib-scenario.schema.json \
  --profile profiles/MIB-Core-0.1.json \
  --seeds 101,202,303,404 \
  --bootstrap-resamples 2000 \
  --output-json calibration.json \
  --output-md calibration.md \
  --output-csv calibration.csv
```

## 7. Interpretation Rule

Calibration is not a competition among B0–B3.

The baselines are diagnostic instruments.

The benchmark question is:

> **Does this Scenario create a controlled future in which memory is necessary, useful, and causally identifiable?**


---

# Calibration Status

The four-seed reference-fixture calibration reaches **36/36** on the provisional FC/NM/MDI gate and **36/36** when causal sensitivity and irrelevant-memory stability are included. See `MIB-v0.1-Calibration-Findings.md`. Fixture baselines remain `release_calibration_eligible = false`.
