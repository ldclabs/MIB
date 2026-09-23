# September 23 design-review implementation

> Historical ledger for measurement 0.4.0. The dependence gate, pilot budget and several Program constructs below were revised in measurement 0.5.0; see [the v0.5 ledger](MIB-v0.5-Review-Resolution.md).

Implementation **0.13.0**, Core measurement **0.4.0**, pack report **0.5.0**, backend report **0.2.0**. Scenario format remains **0.2**. Longitudinal measurement/report are **0.2.0**; the vendored native workflow contract is unchanged.

This ledger resolves the executable defects from [the review](../reviews/MIB-Design-Review-2026-09-23.md). It distinguishes implementation from empirical validation. Earlier reports and example fixtures retain their original version/source identity; they must be verified with their matching executable bundle and must not be compared directly to this revision.

## Implemented

| Review item | Change | Evidence |
|---|---|---|
| P0-01 scalar grading | Structured answers default to exact normalized aliases; generated scalar rubrics reject containers/non-strings and gate credit on the value. Disclosure still scans all visible values. | Negation, alternatives, whole-pool enumeration, JSON containers, valid aliases and legacy disclosure tests. |
| P0-02 dependence gate | Freeze every declared changed-probe opportunity. Joint success requires both answers correct; missing/invalid/wrong pairs remain in the denominator. Average repetitions within Instances, stratify the cluster bootstrap by Program. | Improving full correctness cannot remove eligibility; duplicated repetitions keep the same independent n and interval; missing twins remain counted; report tampering is rejected. |
| P0-03 admission | Necessary causal metrics use pass/fail/unassessable. Independent sample coverage and valid full/causal lifecycles are required; calibration settings are included in the lock. | Empty causal evidence cannot increment the complete-gate count; smoke and pilot never grant release eligibility. |
| P0-04 / P2-15 episode identity | Shared episode materialization and complete-ladder validation. Backend runs use canonical Program IDs; schedule/lock identify every Instance and repetition. | 14 Programs × 3 rungs produce full coverage and 14 complete curves. Missing rungs and missing frozen schedule units are rejected. |
| P1-05 bounded memory | One renderer enforces final context characters, including ordinal prefixes and newlines. Oversize records are omitted whole. | Oversize and Unicode observations at 1/7/100/1000-character budgets; external backend caps remain enforced. |
| P1-06 public interaction history | Persist completed public question/answer exchanges and actual emission outputs through each memory condition; B0 discards cross-task history. | Dialogue and emissions survive a boundary in B1–B3, not B0; repeated request IDs do not duplicate records; reset removes the previous run. |
| P1-07 suffix shortcut | Core acquisition/noise are interleaved; maintenance occurs inside acquisition without changing semantic order or future time across rungs. | Prefix-only fixture loses capability; complete reference retains correctness; cross-rung invariants remain tested. |
| P1-08 procedural scope | Narrow the displayed Core skill label to procedural memory/applicability. Add a separate feature-composition challenge with unseen family combinations. | Family lookup alone misses first-attempt composition; actual feature feedback supports full/twin success. The composition convention is given, so this is not a claim of unrestricted rule discovery. |
| P1-09 longitudinal interpretation | Preserve the safe inspect-first strategy. Report actual/inspection tool calls and savings against that strategy separately from safety and native outcomes. | All three requirement states remain safely solvable without memory; cost cannot offset unsafe preparation or failed commits. |
| P1-10 signed effects | Add signed harmful-history and negative-transfer effects; retain rectified downside loss separately. Score differences use `normalized_delta` in JSON and percentage-point conversion in displays. Cluster longitudinal repetitions within independent seeds. | Symmetric zero-mean fluctuations have zero signed effect while clipped loss remains positive; duplicate repetitions do not increase independent seed count. |
| P1-11 baseline controls | Label B3 as heuristic salience retrieval. The pilot gives B1/B2/B3 and the recent-window diagnostic a common context cap; the oracle-supported reference stays explicitly privileged. | Pilot configuration, budget renderer, same-model invocation audit and source/configuration locks. |
| P1-14 commitment behavior | Add a separate cancellation/renewal/multiple-commitment/repeated-trigger challenge. Preserve withdrawal and session-boundary interpretation limits. | Full and twin trajectories succeed; withholding renewed authorization degrades behavior; repeated triggers must not re-emit. |
| P2-16 optional binding | Move Brain-specific record IDs/tokenizer checks to `learning.bindings.brain`; opt-in portable audits accept bounded opaque host IDs and versioned tokenizer identity. | Shared identity, workflow, budget and lifecycle constraints remain; Brain reference checks still reject non-native IDs. Neither binding proves native learning. |
| P2-17 / P2-18 operation | Provide smoke/pilot/full configurations; add `mib run` configuration dispatch, `mib compare`, and `mib verify` alias. Add pytest discovery boundaries and synchronize version metadata. | CLI estimate/alias tests; locked pilot plan; ordinary pytest excludes local debug snapshots. |

## Reproduction

```bash
python -m pytest -q
python tools/validate-review-20260923.py --output-dir /tmp/mib-review-0.4
python -m mib_runner run examples/same-model/same-model-generated.pilot.json --estimate-only
python -m mib_runner.same_model_cli examples/same-model/same-model-generated.stub.json \
  --output-json /tmp/mib-smoke-0.4.json \
  --report-schema schemas/mib-same-model-report.schema.json
```

Final local validation: **419 passed, 8 skipped** on Python 3.14.7/macOS. The skips require Linux sandboxing or evaluator-private packs. Core and Session complete-memory fixtures score 100; the prefix-only Core fixture scores **67.348** and fails the dependence gate. The separate mechanism challenges score 100 with the complete fixture. The 42-unit engineering stub has `fairness_valid: true` and `release_eligible: false`. These are engineering results, not real-model calibration.

The validation script writes full reports to the requested directory and a compact `validation.json`; it makes no provider calls and needs no private pack. The committed `examples/validation/measurement-0.4.0.json` is a compact engineering record, not model-performance evidence. The stub run is likewise only an execution/reporting check.

The bounded pilot currently estimates **463 condition runs** and **at least 1,826 business-model calls**, excluding all continuations, tool-result decisions, retries, preflight and extra diagnostic calls. It covers seven mechanisms at one rung and is a different experiment from full calibration. Observation routing uses the public `environment_event` type, equally for all memory arms; all ordinary observations still enter memory formation. Hidden probe/relevance labels never select model invocations.

## Remaining empirical and deployment work

- **P1-12:** real fixed-model pilot, power/sample-size planning, multiple-model replication, preregistered useful-effect thresholds and an official freeze require configured immutable model identities/endpoints and provider execution. No such run is claimed here.
- **P1-13:** the new challenges provide additional mechanisms, but independently authored/held-out wording, blinded semantic oracle review and independent real domains remain necessary. Public random seeds or new parameter values do not provide those guarantees.
- **P1-14:** the fixed wrapper and local contracts are tested; arbitrary remote process restarts, storage survival, cross-tenant isolation and physical deletion still need deployment-specific evidence. Withdrawal compliance is not a deletion attestation.
- **P1-10:** relevant-history removal estimates the total effect of withholding those events. Additional content-versus-length/decision-opportunity identification needs matched replacements appropriate to the domain. The harm placebo is not a universal substitute.
- **P2-15/17:** common identity/materialization/scoring seams are implemented. The service, legacy static harness and experimental tracks remain separately scheduled; a complete executor rewrite is neither required for these fixes nor claimed. Detailed legacy diagnostics remain available. Empirical evidence should decide further removal or consolidation.

Small-sample bootstrap policy remains developmental. A degenerate interval records the observed empirical distribution, not certainty about unseen tasks. No threshold is tuned here to manufacture a real-model pass.

Implementation and review follow-up: **OpenAI Codex**, 2026-09-23.
