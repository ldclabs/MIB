# MIB v0.1 Same-Model Empirical Baseline Harness

**Version:** 0.1-draft  
**Status:** Implementation Candidate / Release-Calibration Infrastructure  
**Profile target:** `MIB-Core-0.1`

## 1. Purpose

The Same-Model Empirical Harness answers a narrower and stronger question than the deterministic fixture calibration:

> If the base model, prompt, tools, reasoning policy, Scenario instances, and decoding policy are held fixed, how much does changing only the long-term memory condition change future cognition and behavior?

The four calibration conditions are:

```text
B0  No Memory
B1  Full Visible History
B2  Simple Lexical Retrieval
B3  Structured Deterministic Memory
```

The Harness is intended to provide the empirical evidence needed before freezing the MIB v0.1 leaderboard pack.

## 2. Experimental Invariant

For a valid same-model experiment:

```text
same base model
same model endpoint / model identifier
same system prompt
same reasoning policy
same benchmark tools
same decoding parameters
same Scenario Instance
same repetition / paired seed policy
same future Probe

ONLY memory policy may differ.
```

If any of the locked fields changes, the comparison is not a same-model memory experiment.

## 3. Stateless Model Boundary

Every `respond()` and `act()` turn is a fresh model request.

The model provider MUST NOT preserve hidden conversation state between requests. Long-term history reaches the model only through the Harness-controlled `LONG_TERM_MEMORY_CONTEXT` section.

Current action-loop tool results are different: they belong to the current task and are supplied in `CURRENT_TASK_TRANSIENT_STATE` equally to B0–B3.

This prevents a provider-side session from silently becoming an unmeasured fifth memory system.

## 4. Memory Conditions

### B0 — No Memory

Timeline observations are not retained for future Probes. Current task tool results remain available until that action task ends.

### B1 — Full Visible History

All Agent-visible Timeline observations are replayed to the fixed model at each future Probe.

B1 is considered a valid Full Context baseline only when the Harness reports:

```text
memory_truncations = 0
```

If the model context window forces B1 truncation, release calibration is ineligible until the Scenario scale/model context configuration is corrected.

### B2 — Simple Lexical Retrieval

Past observations are stored verbatim. At Probe time, a deterministic token-overlap ranker selects fixed `top_k` memories.

B2 intentionally has no temporal revision model, source graph, episodic structure, or learned procedural representation.

### B3 — Structured Deterministic Memory

Past observations remain verbatim, but retrieval combines:

```text
lexical relevance
correction/currentness cues
source/authority cues
failure/recovery cues
applicability/exception cues
small recency term
salience supplement
```

B3 is deterministic and uses the same base model as B0–B2. The memory policy, not a second LLM, supplies the structural advantage.

## 5. Experiment Lock

`MIBSameModelExperimentLock` cryptographically binds:

```text
model client type
model id
model endpoint or subprocess command
model parameters
seed policy
system-prompt digest
reasoning-policy digest
Scenario schema digest
Profile digest
official Scenario Pack digest
B0–B3 memory-policy definitions
```

The lock produces one SHA-256 digest. Reports from different lock digests MUST NOT be merged as one same-model experiment.

Secrets are not included in the lock; API-key environment-variable names may be recorded, but secret values never are.

## 6. Paired Decoding

Release calibration SHOULD use deterministic decoding (`temperature = 0`) where supported.

For stochastic providers, the Harness supports a paired-per-call seed policy implemented with semantic call keys. The seed is derived from the paired Agent run seed plus `respond:<probe_id>` or `act:<task_id>:<turn>` and never includes the memory-condition label. A longer tool loop in one condition therefore cannot shift the sampling seed of a later corresponding Probe.

## 6.1. Counterbalanced Condition Order

A real remote model may exhibit load, cache, throttling, or time-of-run effects even when requests are stateless. The Harness therefore does not execute all B0 runs, then all B1 runs, and so on.

Each `(Template, Scenario Instance, repetition)` is one paired experimental unit. Within that unit, B0/B1/B2/B3 are executed using a deterministic Latin rotation:

```text
unit 0: B0 B1 B2 B3
unit 1: B1 B2 B3 B0
unit 2: B2 B3 B0 B1
unit 3: B3 B0 B1 B2
...
```

For the release shape of 36 Templates × 4 instance seeds × 2 repetitions, there are 288 paired units. Each memory condition occurs exactly 72 times in each execution position.

This makes condition order part of the Experiment Lock and prevents a block-order effect from masquerading as a memory effect.

## 7. Admission Gates

The existing v0.1 Template gates remain unchanged:

```text
FC  >= 0.80
NM  <= 0.60
MDI >= 0.25
baseline span >= 0.20
irrelevant-memory stability >= 0.90
causal Memory Benefit >= 0.20 where defined
```

The Same-Model Harness adds fairness gates:

```text
one locked model identity
one system prompt
one reasoning policy
one tool interface
one decoding configuration
deterministic or explicitly seeded decoding
stateless model calls
only memory policy varies
B1 not truncated
zero model transport / parse errors
```

A release candidate is eligible only when every official Template passes the empirical gate and every fairness check passes.

## 8. Model Adapters

The implementation includes:

```text
http_json
openai_compatible_chat
subprocess_jsonl
deterministic_stub   # engineering only
```

`http_json` is the recommended neutral boundary for production calibration because it makes the stateless contract explicit.

The deterministic stub exists only to validate Harness plumbing. Any report produced with it is marked:

```text
same_model_engineering_stub
release_calibration_eligible = false
```

## 9. Outputs

A full run produces:

```text
Same-Model Report JSON
Same-Model Markdown summary
36-row Template CSV
Experiment Lock JSON
Model/memory telemetry
```

The report embeds the normal MIB Calibration Report, so FC/NM/MDI, dimension matrices, Template cards, causal diagnostics, and recommendations remain directly comparable with the fixture calibration.

## 10. Telemetry

For each B0–B3 condition the Harness records:

```text
model calls
model errors
input/output characters
provider usage counters when supplied
memory selections
available memory count
selected memory count
selected memory characters
memory truncations
```

Efficiency remains diagnostic and does not change the calibration score.

## 11. Reference Command

Engineering smoke:

```bash
mib-same-model-calibrate \
  examples/same-model/same-model-experiment.stub.json \
  --experiment-schema schemas/mib-same-model-experiment.schema.json \
  --report-schema schemas/mib-same-model-report.schema.json \
  --output-json examples/same-model/same-model-stub.report.json \
  --output-md examples/same-model/same-model-stub.report.md \
  --output-csv examples/same-model/same-model-stub.csv \
  --output-lock examples/same-model/same-model-stub.lock.json
```

Estimate the release run before invoking a remote model:

```bash
mib-same-model-calibrate \
  examples/same-model/same-model-experiment.external-http.json \
  --estimate-only \
  --experiment-schema schemas/mib-same-model-experiment.schema.json
```

External fixed-model run:

```bash
mib-same-model-calibrate \
  examples/same-model/same-model-experiment.external-http.json \
  --experiment-schema schemas/mib-same-model-experiment.schema.json \
  --report-schema schemas/mib-same-model-report.schema.json \
  --output-json empirical.report.json \
  --output-md empirical.report.md \
  --output-csv empirical.csv \
  --output-lock empirical.lock.json
```

## 12. Release Decision

A 36/36 deterministic fixture result means the Scenario mechanics are internally clean.

A 36/36 **same-model empirical** result means something stronger: under a real fixed model, the official Scenario Pack remains solvable with full history, meaningfully memory-dependent without history, causally sensitive to relevant-memory removal, stable to irrelevant-memory removal, and able to separate different memory organizations without changing the base intelligence.

Only the second result is evidence for freezing the v0.1 leaderboard pack.

## 13. Release-Run Estimate and Current Status

The reference release-candidate configuration uses:

```text
36 official Templates
4 hidden instance seeds per Template
2 repetitions
B0 / B1 / B2 / B3 full conditions
B3 causal replay conditions
10,000 bootstrap resamples
```

Before action-loop expansion, the current minimum estimate is:

```text
Full baseline condition runs      1,152
Additional causal ablation runs  1,080
Minimum condition runs           2,232
Minimum model turns              3,152
```

ACTION Probes may require several model turns, so actual model calls can exceed the minimum.

The package intentionally does **not** contain a claimed real-model empirical result. No externally callable fixed-model endpoint or credentials were supplied in the current execution environment, so the release candidate remains:

```text
pending_external_model_run
release_calibration_eligible = false
```

The included deterministic stub validates the experimental machinery only; it cannot satisfy the release gate.

