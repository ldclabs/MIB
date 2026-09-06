# September 2026 design-review resolution

Measurement revision 0.3.0; implementation 0.10.0. The original review was against `50bba8b`, followed by a review of the pre-amend commit `673631a`. Chinese mirrors were excluded as requested. No subagents were used.

## Resolution ledger

| Review concern | Resolution | Verification / scope |
|---|---|---|
| Withdrawn content hidden in an abstention | Check all visible output fields independently of status; inconsistent unknown/value combinations fail | Regression cases cover structured values, explanations, text, and abstention envelopes |
| Optional fields shrinking the rubric | Fixed value/status/confidence denominator | Missing required fields cannot earn extra credit |
| Semantic identifiers | Opaque corresponding IDs across paired conditions | Capture and rename-invariance tests |
| Prospective false alarms and topic spraying | Full declared lifecycle, exact recipient/topic matching, duplicate/extraneous emission rejection | Early/spraying regression; active/cancelled commitment twins |
| Pool-complement answer leakage | Noise ignores answer exclusions and samples the complete pool | Identical-noise test under different excluded-answer sets |
| Universal procedural strategies | Instance-specific recipes, actual training feedback, first-attempt criteria, nonmatching/revised/composed tasks | Stateless scripted-model test separates B0 recovery from B1 reuse |
| Overbroad dependence gate and incorrect counts | Per-dimension evidence, probe and Instance counts, minimum coverage/Instances, Wilson lower bound | Missing-evidence and tampering tests |
| Paired interval using other rungs | Shared aggregation; canonical-only paired Instance bootstrap for generated packs; exact compatibility requirements | +100 synthetic paired case now has [+100, +100] interval |
| Same-model lifecycle and missing external hooks | Persist lived transcripts for B1–B3; clear B0/transient state; observe/maintenance decisions; HTTP/stdio lifecycle forwarding | Scripted stateless model and HTTP round trip |
| Generated hidden evaluation not integrated | Program manifests, keyed seed aliases, complete ladders, Profile/parameter/session checks | End-to-end generated-store redaction and score verification |
| Distance changing the task | Independent random streams; complete request invariance; fixed virtual span | All registered Programs checked across rungs |
| Oracle chains and semantic coverage | Chained corrections, bitemporal query, authority records, dependent withdrawal, renewed authorization | Independent truth-table and lineage tests; seven additional semantic Programs |
| Verification of ranking/interpretation | Policy/source binding, shared recomputation, gate/official/retention/interval checks; service track/eligibility restrictions | Tampering regressions and generated public-report verification |
| Ambiguous causal naming | `memory_related_error_rate` is descriptive; transfer early/late contrast described as artifact availability | Specification, report schema, and Capability Card updated |
| Information load and resource assumptions | Expanded/Session/Load Profiles; configurable useful-fact count; full operation bytes/time; optional recent-context reference | Separate profile identities; no unsupported context-overflow or physical-deletion claim |
| Real-model calibration and release | Runnable generated experiment, exact configured identity/source lock, all rungs, optional diagnostic references | **External input required:** immutable model identity, endpoint/configuration, and credentials. Engineering stubs cannot establish empirical validity |

## Follow-up review of `673631a`

All six findings have behavioral regression coverage in `tests/test_commit_673631a_regressions.py`:

| Finding | Correction | Regression evidence |
|---|---|---|
| Interleaved noise overwrites another tested actor | Exclude all primary actors from noise assertions | Accepted-answer invariance across seeds and useful-fact counts 8, 14, and 64; request/answer checks across all Programs |
| Bootstrap replay drops positive ablation tolerance | Use effective Run Artifact tolerances, with Scenario fallback for legacy evidence | A real partial-recall run with full=1, irrelevant=0.5, and tolerance=0.05 verifies its bootstrap statistics and public report |
| Payload-only reminders acquire synthetic text and fail | Preserve absent content during Runner normalization | Direct Runner and HTTP cases for absent/canonical/extra text and the text alias |
| Non-object reminder payload aborts the run | Type-check structured payloads before matching; retain the text alternative | Strings, lists, numbers, null, and unrelated objects score normally with correct or absent text |
| Disclosure scanning treats metadata and JSON keys as claims | Inspect leaf values and exclude valid answer-envelope metadata | Structured, JSON, and field-line answers; malformed metadata, explanations, and attribution still fail when they disclose forbidden values |
| Hidden evaluation ignores Program ladder overrides | Share effective configuration resolution; compare at registration and validate Instances before execution | Matching three/four-rung overrides across public/private/calibration paths; mismatches rejected; string entries retain defaults |

These corrections are included in the same implementation 0.10.0 and measurement revision 0.3.0. Programs, Profiles, and reports retain their version numbers; regenerated source locks bind the corrected implementation.

## Validation evidence

The final local suite reports **299 passed, 8 skipped** on Python 3.12/macOS, including 57 new follow-up regression cases. Linux sandbox and evaluator-only private-pack checks are skipped on this public checkout. Original tests are in `tests/test_measurement_integrity.py`; the follow-up adds `tests/test_commit_673631a_regressions.py` and strengthens the cross-rung answer invariant. All 33 Scenario definitions and 62 example Scenario instances passed schema and semantic validation.

The generated engineering experiment covers 14 Programs at three rungs, with B0–B3 plus optional bounded-window and privileged-reference diagnostics. Its result must remain `same_model_engineering_stub` and `release_calibration_eligible: false`. It verifies execution and reporting, not difficulty or baseline quality.

The completed engineering run reports `fairness_valid: true` across 42 Program/rung units. Its configured schedule includes 558 condition/diagnostic runs; none establishes real-model release readiness. The committed report and lock are `examples/same-model/same-model-generated.stub.report.json` and `.stub.lock.json`.

Eight public fixture configurations were regenerated and score-verified, covering Core, M, Expanded, Session, and Load Profiles. The evidence is in `examples/validation/v02-review-fixture-validation.json`; rerun `tools/regenerate-v02-evidence.py` to reproduce it. On the Core development pack, the structured fixture scores 100, the window fixture 29.476, and the no-memory fixture 14.976. These are engineering fixtures, not empirical model baselines.

## Real-model procedure

1. Configure `examples/same-model/same-model-generated.external-http.json` with an immutable model ID and a stateless compatible endpoint. Keep credentials in the named environment variable.
2. Run `mib-same-model-calibrate <experiment> --estimate-only` and retain the experiment lock. The call estimate is a lower bound; observation decisions, action continuations, retries, and diagnostic groups consume model calls.
3. Run the experiment and validate the output against `schemas/mib-same-model-report.schema.json`. Keep telemetry, fairness checks, per-Program/rung results, and the source/configuration lock.
4. Use pilot variance and a predefined useful effect to set independent-instance and repetition counts. Test several fixed models and sensitivity to Program composition before claiming architecture-general discrimination.
5. Freeze an evaluator-owned pack/Profile only after empirical admission checks pass. The development policy's thresholds are provisional; implementing them does not scientifically validate them.

## Remaining limits

The session boundary is enforced by the fixed-model wrapper, but is a declared implementation contract for arbitrary integrated Agents. The reference service is not a production deployment or hardware attestation service. Complete external storage/write-amplification measurement, broad real-domain validity, and physical deletion from an arbitrary black-box backend cannot be inferred from the shipped behavioral tests. MIB-R retains its separate prototype result family.
