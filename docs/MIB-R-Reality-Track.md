# MIB-R — Reality Track

## Memory Intelligence Benchmark, Realistic External Task Environments

**Version:** 0.1-draft
**Status:** Prototype / Companion to `MIB-Transfer-Intelligence.md`
**Profile:** `MIB-R-0.1-Dev` — **not official**

---

# 0. Purpose

MIB-Core is a controlled synthetic causal laboratory. It establishes that a memory intervention changes future behavior, under conditions the evaluator fully owns. What it cannot establish on its own is whether the same memory intelligence survives contact with real tasks.

MIB-R asks:

> Can past experience causally improve performance on real, held-out tasks that share verified procedural support?

MIB-R is **not** a replacement for MIB-Core, and it is not a general agent-performance benchmark. Its contribution is not the tasks. Plenty of benchmarks have realistic tasks. Its contribution is that every condition is paired, and only memory state varies.

---

# 1. Non-Negotiable Invariants

## 1.1 Separation from MIB-Core

MIB-R has its own Profile ID, its own result family (`reality`), and its own leaderboard surface. A leaderboard query MUST NOT produce one rank that mixes families, and a paired comparison across families is refused, not approximated.

## 1.2 No official score

There is deliberately no single official MIB-R Score in v0.1-Dev. Upstream benchmarks have incompatible score scales, and hiding domain behavior inside one mean this early would destroy exactly the information the track exists to produce. If a future spec introduces one, it must document its normalization rules explicitly.

## 1.3 Prototype status

`MIB-R-0.1-Dev` is a prototype. Passing the acceptance criteria in §9 does not make it official, and it MUST NOT be advertised as such.

## 1.4 The transfer graph is evaluator-only

The Reality Transfer Graph MUST NOT be participant-visible during official evaluation. Transfer graphs are especially vulnerable to adaptive reverse engineering across repeated submissions.

## 1.5 No unlicensed redistribution

MIB stores upstream task identity, immutable revision, and content digest. Where licensing does not permit redistribution, MIB keeps only the ID, the digest, and setup instructions.

---

# 2. Experiment Structure

```text
Phase A — Experience acquisition
    Train Task
        ↓
    Agent acts in a realistic environment
        ↓
    Trajectory
        ↓
    Verifier result
        ↓
    Experience / Skill formation

Phase B — Held-out transfer
    Related Test Task
        ↓
    same base Agent / model / tools
        ↓
    memory condition varies
        ↓
    verifier score
```

Acquisition is real: the Agent attempts the training task, the verifier judges it, and the verdict — plus, on failure, the reviewer correction — is delivered back as an observation. That is what makes the memory an Experience rather than a document dump.

---

# 3. Paired Conditions

```text
no_memory                    no acquisition at all
natural_memory               full acquisition; the deployed behavior
relevant_ability_ablated     acquisition minus the support for the Ability under test
irrelevant_ability_ablated   acquisition minus an equal amount of past the target
                             does not depend on
wrong_ability_injected       full acquisition plus a plausible over-generalization

optional:
oracle_skill                 support withheld, canonical artifact placed in the pool
oracle_routing               support withheld, canonical artifact surfaced at task time
```

All conditions MUST be paired on:

```text
same source task set
same target task
same environment revision
same Agent
same model
same tools
same timeout
same task seed where supported
same verifier
```

Only memory or evolution state may vary. This is the MIB-specific contribution.

## 3.1 The irrelevant control must stay irrelevant

An edge declares two task sets:

```text
source_task_ids   support for the Ability the relation names
causal_task_ids   every acquisition task the target's answer actually depends on
```

On a positive edge these usually coincide. On a **near-match** edge they do not: the named Ability is the one that must be *withheld*, while the target still depends on whatever governs it correctly. The irrelevant control draws only from tasks outside `causal_task_ids`, so "irrelevant" never quietly means "load-bearing".

When fewer non-load-bearing tasks exist than the relevant ablation withholds, the two conditions differ in magnitude as well as content. The report emits `reality.ablation_magnitude_mismatch` rather than presenting a weaker control as a clean one.

---

# 4. Reality Transfer Graph

An evaluator-private graph over tasks and Abilities:

```text
TrainTask-17 ──supports──►  Ability-A
TrainTask-29 ──supports──►  Ability-A

Ability-A ──applies──► TestTask-42

Ability-A ──near_match_but_not_applicable──► TestTask-51

Ability-A + Ability-B ──compose──► TestTask-77
```

Components:

```text
Task nodes
Ability nodes
Support edges
Non-applicability edges
Composition edges
```

Each edge carries the same relation taxonomy as `MIB-Transfer-Intelligence.md`, so the positive distance ladder `D0`–`D3` and the negative control classes mean the same thing in both tracks.

## 4.1 Resolution

A published pack carries only:

```json
{
  "transfer_graph": {
    "private_ref": "graph.evaluator.json",
    "digest": "sha256:..."
  }
}
```

The reference resolves relative to the pack, or to `MIB_REALITY_GRAPH_ROOT` when set, so a public pack can name a graph that exists only inside the evaluator environment. A digest mismatch is a hard error: a silently edited graph would change what every paired condition was measured against.

---

# 5. Reality Task Manifest

```json
{
  "task_id": "external:benchmark:task-42",
  "source_benchmark": "example-benchmark",
  "source_revision": "immutable-revision-or-digest",
  "content_digest": "sha256:...",
  "verifier": "upstream"
}
```

The adapter resolves a `task_id` to task content and checks the digest. A drifted environment revision fails loudly instead of silently changing the comparison.

---

# 6. Reality Task Adapter

```python
class RealityTaskAdapter(Protocol):
    def describe(self) -> dict: ...
    def load_task(self, task_ref: dict) -> dict: ...
    async def run_task(self, task, agent, *, seed, request_id) -> dict: ...
    def normalize_score(self, result: dict) -> float: ...
    def collect_trajectory(self, result: dict) -> list[dict]: ...
```

The reference implementation is synchronous, matching the in-process Agent Adapter in `types.py`. An HTTP or container-backed adapter may adopt async at its transport boundary without changing this contract.

An adapter also supplies `feedback(task, result, *, score)`: the verifier verdict and, on failure, the reviewer correction. That is the Experience Phase A forms memory from.

---

# 7. Metrics

Diagnostic metrics only:

```text
Condition scores          one per paired condition
Natural Transfer Gain     natural_memory - no_memory
Relevant-Ablation Delta   natural_memory - relevant_ability_ablated
Irrelevant Stability      1 - |natural_memory - irrelevant_ability_ablated|
Memory Harm               max(0, natural_memory - wrong_ability_injected)
Oracle Skill Gain         oracle_skill - no_memory
Oracle Routing Gain       oracle_routing - no_memory

Negative Transfer Rate
Supported Transfer Success Rate
Near-Match Resistance
Unsupported-Memory Neutrality

Transfer Gain by distance class
Transfer Gain by domain

Tool / turn / latency / cost deltas
```

All deltas are **signed**. For an over-generalizing system, removing memory it should not have been using *improves* it; an absolute value would hide precisely the finding MIB-R exists to produce.

Confidence intervals use a paired task-level bootstrap that preserves each target task's full condition set.

---

# 8. Negative Controls

A purely positive-transfer benchmark cannot distinguish a system that helps from a system that cannot stop helping. MIB-R therefore requires:

```text
Supported Transfer
Near-Match Non-Applicable
Unsupported Novel
Stale Ability
Harmful Ability
Compositional Ability
```

A memory system should score well not only by helping when support exists, but by remaining neutral when it does not. A system that remembers nothing scores perfectly on neutrality and zero on transfer; a system that over-generalizes scores perfectly on transfer and zero on the boundary. Neither number means anything alone.

---

# 9. Calibration

Before accepting a Reality transfer edge:

```text
Train Ability support
        ↓
Oracle Skill + Oracle Routing
        ↓
must improve the target task
```

If an oracle Skill does not improve the task, the edge is not empirically supported and must not be used as a positive-transfer benchmark case. `minimum_effect` is set per external benchmark after pilot calibration.

Do not assume a curator-labelled Ability is useful merely because it sounds plausible. Every convention the reference domain declares is checked to be load-bearing: omitting it must change the answer.

---

# 10. Reporting and Redaction

Recommended public result policy:

```text
Immediate
  overall domain score
  aggregate transfer metrics
  aggregate distance profile
  attestation

Delayed / private
  per-task score
  per-Ability score
  specific support relation
  specific wrong-skill failure
```

The public projection strips per-task rows, per-relation blocks, and everything but counts and a digest from the graph summary. Consider reducing per-task public feedback further for a hosted MIB-R cycle.

## 10.1 Attestation

A MIB-R result attestation binds the Reality Pack digest, the evaluator-private transfer graph digest, the environment adapter identity, the condition set, and both report digests. It carries **no score**: MIB-R has no official Score, and inventing one in an attestation would be exactly the cross-ranking the track is separated to prevent. Its signature context is distinct from the core evaluation-service context, so a Reality attestation can never be replayed as an official MIB-Core result.

---

# 11. Choosing a Domain

A first MIB-R domain should have:

```text
a deterministic or high-quality verifier
manageable runtime
clear procedural reuse
low external data licensing complexity
```

Algorithmic coding or controlled web research are good first choices. Avoid starting with SWE-Bench-scale container orchestration until the Reality abstraction is stable.

The objective of `MIB-R-0.1-Dev` is to validate the transfer-intervention methodology, not to maximize task prestige.

---

# 12. Reference Domain — Ledger Codes

`reality/MIB-R-Demo-LedgerCodes/` ships a deterministic algorithmic-reasoning domain: 23 acquisition tasks and 12 held-out tasks with a local verifier, covering `D0`–`D3` plus the near-match and unsupported controls.

Four conventions govern the computation and none appears in a task prompt. They are learnable only from corrective feedback:

```text
A1  normalize the identifier before computing
A2  standard-family codes use modulo 97
A3  the legacy family keeps modulo 100          (the boundary of A2)
A4  a leading CK is a check marker, not a value
```

A system that has learned no convention cannot produce a code and must say so, which is what makes the unsupported control a neutrality measurement rather than a guess. A system that fires A2 past its boundary produces a confident wrong answer on a legacy record, which is what makes the near-match control a trap.

It is a **reference domain**, not an external benchmark, and it redistributes no third-party data. It exists so the methodology is reproducible in the open repository. Ecological validity comes from integrating real upstream benchmarks through the same adapter contract, and that work is not what this prototype claims to have done.

---

# 13. Running It

```bash
mib reality-benchmark reality/MIB-R-Demo-LedgerCodes/pack.json \
  --profile profiles/MIB-R-0.1-Dev.json \
  --pack-schema schemas/mib-reality-pack.schema.json \
  --agent mib_runner.agents.reality_fixtures:RuleLearningRealityAgent \
  --bootstrap-resamples 2000 \
  --output-report reality-internal.json \
  --output-public reality-public.json \
  --output-attestation reality-attestation.json \
  --card reality-card.md
```

`--submission` runs an external Agent submission through the same sandboxed transport the core Hidden Eval path uses.

---

# 14. Prototype Acceptance

```text
[x] one realistic domain adapter
[x] >= 20 acquisition tasks
[x] >= 10 held-out tasks
[x] evaluator-private Reality Transfer Graph
[x] supported + near-match + unsupported relations
[x] verifier integration
[x] Natural / No Memory / Relevant Ablation / Irrelevant Ablation
[x] paired execution
[x] result attestation
[x] public redaction
[x] no cross-ranking with MIB-Core
```

Meeting these does not make MIB-R official. The remaining work is ecological: a real upstream benchmark, real licensing, and empirical edge calibration against a base model rather than a deterministic fixture.

---

# 15. Final Position

```text
MIB-Core
────────────────────────────────────
What parts of the past participate
correctly in future cognition?

MIB Transfer Diagnostics
────────────────────────────────────
How did Experience become future capability?

MIB-R
────────────────────────────────────
Does the same memory intelligence
survive in realistic external tasks?
```

> The intelligence of memory lies not in remembering more, but in allowing the right past — and only the right past — to shape the future.
