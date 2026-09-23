# MIB Specification

## Memory Intelligence Benchmark — format v0.2, measurement revision 0.5.0

**Implementation:** 0.14.1. **Status:** normative executable development specification.

This revision addresses the second September 23 design review. The detailed implementation ledger is [here](harness/MIB-v0.5-Review-Resolution.md); the preceding revision's ledger is [here](harness/MIB-v0.4-Review-Resolution.md). Scores from earlier revisions are not interchangeable with these scores. The scenario format remains `mib: "0.2"`; Core Programs and Core development Profiles are version 0.5.0 (the Mechanism Challenges Profile is 0.2.0), and new pack reports use `report_version: "0.6.0"`. Static v0.1 scenarios remain executable.

The implementation, schemas, and this specification define the executable contract. Proposals and archived documents are rationale, not competing specifications. Chinese mirrors have not been updated in this revision.

# 0. Scope and interpretation

MIB evaluates how an Agent uses historical information to improve subsequent answers and actions. Raw history is a legitimate memory implementation. Neither a long history nor a counterfactual content swap independently proves use of a persistent-memory mechanism.

Two development regimes are available:

- **Historical information use:** the declared history, task distribution, and resource conditions define the claim. The ordinary S/M/Expanded/Load Profiles use this regime.
- **Persistence across sessions:** the Session Profile exercises an explicit `session_boundary` operation. The fixed-model wrapper persists task experience and clears its transient conversation. Integrated Agents implement and declare their own persistence boundary; this is not independent proof of their internal state.

A score is conditional on its Program set, Profile version, distance rung, and resource regime. It is not a validated measure of general memory intelligence. No real-model release calibration or official generated leaderboard freeze has been completed.

# 1. Thesis and identification

## 1.1 Thesis

The past should influence future decisions when relevant, remain neutral when irrelevant, and stop controlling decisions when withdrawn or obsolete.

## 1.2 Observable distinctions

MIB distinguishes value accuracy, epistemic status, source attribution, world-state outcomes, first-attempt behavior, appropriate transfer, commitment behavior, and operational withdrawal. Correct behavior does not prove physical deletion from every internal store.

## 1.3 Identification limits

A relevant-history ablation estimates the effect of withholding that history. A content twin tests whether the answer follows changed historical content. A policy twin tests whether behavior follows a changed latent convention learned through acquisition feedback. These are different interventions.

Distance curves describe performance across declared distances. They do not, by themselves, separate storage, compression, retrieval, inference, or context-window mechanisms. Claims about persistence require the explicit boundary regime and its implementation assumptions. Claims about efficiency require cost measurements, not history length alone.

# 2. Benchmark structure

## 2.1 Tracks

**Track A — Memory System:** the evaluator owns the fixed model, prompt, decoding, tools, task environment, and reasoning policy; memory selection varies. The same-model harness implements this experiment.

**Track B — Integrated Agent:** the whole Agent may vary. The hosted external-Agent service accepts this track. It rejects attempts to submit an arbitrary external Agent as a controlled Track A experiment.

Tracks, Profile identities/versions, pack identities/versions, source bundles, and measurement regimes MUST NOT be mixed in a ranking or paired comparison.

## 2.2 Dimensions

Revision 0.5 Profiles use six dimensions: retention/retrieval, temporal memory, epistemic memory, procedural memory, prospective/self memory, and withdrawal compliance. `procedural_memory` carries both feedback-derived recurrence (the same family returns) and series-scoped applicability (a new family of a known series); both are recipe recall keyed by a visible identifier and scored by the same conjunctive world outcome, so they were one construct measured twice. The legacy `experience_memory` and `skill_learning_transfer` IDs remain valid for revision-0.4 and v0.1 artifacts; `selective_forgetting` covers an operational withdrawal lane and does not imply comprehensive deletion or budget-aware forgetting. Merging changes the composite weights, so revision-0.4 composites are not comparable.

Causal quantities are diagnostics. They do not enter a v0.2 capability dimension. The deprecated v0.1 `causal_memory_impact` dimension remains available for legacy Profiles.

## 2.3 Profiles

A Profile fixes its identity/version, track, scale, official flag, Program set and parameters, ladder, canonical rung, instance seeds or evaluator sampling policy, repetitions, dimension weights, coverage, statistics, dependence policy, and measurement regime.

Programs may override their ladder and supply `params`. Ladder precedence is the Program entry, then the pack/Profile default, then the Program's built-in default. Public generation, hidden materialization, and same-model calibration share this resolution. The interleaved recall Program accepts `fact_count` from 8 to 4096. The generated hidden-store manifest must match the Profile's Programs, parameters, effective per-Program ladders, and session regime. Registration rejects a mismatch; execution checks every Instance's Program/version, rung, and interference count and requires all of that Program's rungs for each seed.

Shipped development Profiles:

| Profile suffix | Programs | Ladder | Purpose |
|---|---:|---|---|
| `Dev` | 7 | 0 / 20 / 100 | Core integration and controlled experiments |
| `Dev-M` | 7 | 0 / 100 / 1000 | Longer interference; BCa intervals |
| `Expanded-Dev` | 14 | 0 / 20 / 100 | Two semantic mechanisms per dimension |
| `Session-Dev` | 14 | 0 / 20 / 100 | Explicit session boundary |
| `Load-Dev` | 14 | 0 / 20 / 100 | 64 useful facts in interleaved recall |
| `Calibration-Dev` | 14 | 0 / 20 / 100 | Evaluator-owned fixed-model experiment |
| `Horizon-Dev` | 7 | 100 / 2,000 / 10,000 | Long visible history for integrated Agents; headline only |

All are development Profiles with `official: false`. A larger number of seeds or a more elaborate interval does not establish broader construct validity.

Revision 0.5 Profiles declare `measurement_regime.intervention_rungs: "canonical"`: interventions run only at the canonical rung, because no other rung's intervention enters an aggregate, and other rungs run the full condition for retention curves. They also declare `maintenance_control: "declared_maintenance_only"`: the no-maintenance replay runs only for an Agent that declares maintenance, since otherwise it would repeat the full condition and `consolidation_benefit` is unassessable. Profiles without these fields keep every intervention. `measurement_regime.diagnostics: "off"` also skips the relevant, irrelevant, harmful, no-maintenance and negative-transfer controls: the headline (dimension scores and the dependence gate) needs only the full condition and the twins, and the controls feed causal diagnostics. Core Dev runs 377 conditions with diagnostics and 182 without, with identical headline results. `measurement_regime.session_isolation: "persisted_state"` makes session boundaries enforced (§5.2).

## 2.4 Packs

A generated pack is exactly `Programs × seeds × rungs`, with no missing or duplicated Instances. Public construction does not justify exposing semantic event roles on the participant interface. Official seeds, when configured by the evaluator, are secret and replaced with keyed aliases before delivery.

# 3. Roles and boundaries

The Program constructs the world, timeline, probes, and interventions. The Runner delivers observations, controls world transitions and tool execution, and records behavior. Evaluators compute results. The aggregation module defines the shared score functional. The service authenticates jobs and result artifacts.

Participant-visible observation, interaction, task, request, item, and static tool-call identifiers are opaque. Their distributions do not label relevant facts, distractors, retention targets, prospective probes, or scored future tasks; no participant-visible text names an item as practice, held-out, or evaluation material. Paired conditions retain stable opaque aliases for corresponding items. Actor identities and ordinary tool/data semantics remain observable because tasks need them.

Queries, oracle data, evaluator labels, support sets, and intervention labels are private. The optional oracle-supported calibration reference is an explicitly privileged diagnostic and never a participant score or release gate.

# 4. Scenario model

## 4.1 Contract

`schemas/mib-scenario.schema.json` defines the machine format. The semantic validator additionally checks execution support, references, intervention consistency, and lifecycle anchors. A schema-valid but unexecutable construct is rejected.

## 4.2 Programs and world model

`generate/` constructs deterministic Instances. Separate random streams control semantic choices, surface realization, clocks, interference, interference wording, respond-probe order, opaque identifiers, questioning controls, and content twins. Probe wording and accepted answers remain fixed across a seed's rungs.

An evaluator may supply a private surface bank (statement/mention/retraction templates, question prompts and Program phrases). It changes wording only: semantic sampling, world-model assertions and every Oracle are unchanged, and the Instance records `surface_bank_digest`. A parser of the public grammar is not expected to transfer to it. Hidden seeds protect Instance answers; only a private surface protects against public-grammar solvers. Commitment, rule and brief wording are not yet covered by the bank.

The world model records assertions with source, subject, attribute, value, kind, observation sequence, optional validity interval, supersession, and optional derivation dependencies. It separates truth-bearing assertions from statements and nonassertive mentions.

- State/update assertions describe changes.
- Corrections replace the corrected lineage's value retroactively, including chained corrections. Original statements remain available to statement-history queries until withdrawn.
- Questions and hypotheticals do not establish facts in these controlled worlds.
- Retractions remove the specified assertion lineage and dependent derivations from operational truth/evidence/history. Fresh independent authorization and assertions can establish a new value.
- `bitemporal` queries distinguish valid time from the record-availability cutoff. Future-announced facts are not automatically current.
- Scoped authority can be represented as an ordinary visible authority record. `according_to_authority` resolves the designated source; a global source weight alone does not settle a claim.

Queries include `current`, `as_of`, `first_stated`, `said_by`, `known`, `status`, `hop`, `bitemporal`, and `according_to_authority`. A preferred current value can still have contested status. Attribution to a designated source is distinct from a claim of objective certainty.

Query oracles are derived from model results. Workflow expectations are derived from sampled recipes; prospective expectations from sampled obligations. These derivations need independent tests and semantic review: using a generator is not a proof that its interpretation is correct.

The base Programs exercise direct/multi-hop recall, updates, correction/disagreement, feedback-driven workflows, applicability boundaries, prospective/self rules, and withdrawal. Additional Programs exercise interleaved load, delayed corrections, scoped authority with identical claim wording, revised procedures, recipe composition, cancelled commitments, and authorized relearning.

## 4.3 Requirements and execution policy

Required capabilities include `observe`, `respond`, `act`, `tools`, `virtual_time`, and, for the Session Profile, `session_boundary`. A required session boundary needs an explicit capability declaration. Maintenance remains optional.

Execution limits cap Agent turns and tool calls. Cognitive/protocol failures keep their probe weight at zero performance; transport/Runner failures are separately classified. Missing support never silently becomes successful coverage.

## 4.4 Tools and worlds

The Runner owns world state. Static deployment/workspace/contextual-save simulators remain executable.

Generated experience/skill tasks use `mib.workflow.v1`. `workflow.submit` executes an ordered recipe for an opaque item family. The first recipe, first-attempt correctness, and eventual completion are recorded. A failed attempt returns corrective feedback for recovery. Neither the future request nor the tool description reveals the required recipe before that first attempt.

Experience Programs repeat one family. Procedural applicability Programs scope a recipe to a visible opaque series, and their future items are new families: a family-to-recipe table cannot solve them, while the series boundary still separates the nonmatching recipe. Applying the other series' recipe is an error. Each series has its own policy twin. Revised-workflow and composition Programs test distinct mechanisms. Task state is reset before each future task so acquisition cannot accidentally complete it.

## 4.5 Timeline and distance

Events include interactions, documents, tool results, observations, lived tasks, world updates, maintenance windows, session boundaries, and checkpoints. The Runner projects only participant-visible information.

Noise uses the full public value pool independently of target-answer exclusions. An answer value may appear for another subject or inside a question. Correct interpretation must depend on its relation and provenance. This prevents the pool-complement shortcut.

A seed's rung changes interference count while retaining its task and virtual span. Core Programs interleave noise with acquisition and place maintenance inside acquisition independently of relevance. Information-event timestamps and the future checkpoint are fixed across rungs. The original schedule reserves a 24-hour extension even at rung zero; noise is distributed through the available acquisition interval. Programs with an explicit streaming schedule retain that schedule. Interleaved recall distributes useful observations through its stream, including after maintenance, and spreads its noise across a fixed span. Its similar-subject noise excludes every primary actor, so another noise block cannot overwrite an earlier or future tested fact.

`visible_history_chars` records the characters of participant-visible history (content, JSON payloads and lived-task goals). At the Core canonical rung it is roughly 1,000–1,500 characters: the Core score measures use of a short declared history, not selection under memory pressure. `interference_tokens` is a **legacy field name for whitespace-separated words**, not tokenizer tokens. Reports must not infer a model context overflow from it. Runner input/output byte counts cover serialized arguments and results; model-provided token usage, where available, is reported separately. Different semantic/load Profiles are distinct experiments.

## 4.6 Probes and commitments

Probes are delivered through `respond`, `act`, or `observe_only`. An observe-only probe uses the ordinary observation interface and an opaque identifier.

The prospective lifecycle evaluator considers emissions from the declared creation point through the end of the run. Its `expected[]` items identify a commitment (evaluator ID and `commitment_event`), recipient, topic, and trigger event/probe. It counts misses, false alarms, and duplicate/extraneous emissions; any premature emission is therefore penalized once, by the lifecycle Probe. Near-trigger and repeated-trigger `must_not_emit` Probes are zero-weight diagnostics. The generated trigger window is zero observations: a reminder must be emitted at the triggering observation.

A reminder is either the exact normalized sentence `Reminder: ask <person> about the <topic>.` or a `type: "reminder"` payload naming `recipient` and `topic`. A payload may reference its commitment with `commitment_ref`, the opaque observation ID of the commitment the Agent saw; a reference to another observation, or an explicit `commitment_id` different from the evaluator's, is a wrong reminder. Evaluator commitment IDs are never shown to the Agent and are not required. A payload may omit `content`; the Runner preserves that absence. If text accompanies the payload, it must be the canonical sentence. A non-object payload cannot satisfy structured matching, but does not invalidate a correct text alternative or abort scoring. Merely including one correct topic among many earns no credit. The cancellation Program cancels one commitment while a second commitment for the same trigger stays active, so emitting nothing is not correct; its twin keeps the first commitment active.

Standing self rules identify permitted/prohibited operations and specify that only an explicit authorization revision changes them. A routine maintenance request is not a revocation. Compliance is conjunctive (`eval-action-strict`, a composite with `require_all`): the permitted operation must run, the prohibited one must not, and the resulting world state must match. Doing nothing earns no partial credit.

Late sampling chooses input variants only at delivery; the same variant is used across paired conditions and its digest is retained for verification.

## 4.7 Evaluation

Structured scalar values use deterministic exact equality after normalization, with explicit oracle aliases. Containers and, in generated scalar tasks, non-string values are rejected; a wrong value cannot earn status-only credit. Negating an accepted value or enumerating candidates does not count as answering. Explicit legacy text `contains` evaluators remain available.

Generated scalar evaluators use `disclosure_scope: "withdrawn"`. A withdrawn value (Oracle `withdrawn`) fails anywhere in the visible output, including inside an abstention, explanation, or attribution. Other forbidden values (superseded, contradicted, merely mentioned) fail when they are the answer; an explanation that accurately recalls history is not stale adoption, and its penalty would otherwise grow with interference. Legacy evaluators without the field keep whole-output checks for every forbidden value. Disclosure checks inspect actual leaf values, excluding JSON field names, null placeholders, and valid root-level status/confidence metadata in a recognized answer envelope. JSON and field-line answers use the same value semantics. Invalid metadata and nested auxiliary values remain subject to disclosure checks.

A Probe may declare `conditional_on`: it earns credit only when each named Probe's value was recalled in the same run. Withdrawal Probes are conditional on the retained neighbour, the epistemic abstention Probe on the corrected value, and the status Probe on the claim itself. A system that remembers nothing therefore cannot pass withdrawal, abstention, or status by default. The Probe keeps its weight; a failed prerequisite scores zero with `prerequisite_failed`, and the unconditional score is retained for diagnosis.

Structured evaluation uses a fixed rubric, normally value 0.8 and status 0.2. Missing required fields receive zero for their fixed weight; they do not disappear from the denominator. Unknown status with a definite value is inconsistent and fails. A proper abstention can be represented as null/unknown or the abstention envelope.

Confidence is the stated probability that the value answer or abstention is correct. `1 - (confidence - value_correctness)^2` is reported where supplied. When confidence has positive rubric weight, omitting it receives zero for that weight. It is not otherwise a capability bonus.

World-state evaluators check explicit conditions; `eval-world-strict` (`require_all`) makes them conjunctive. Trajectory evaluators check required/forbidden actions, ordering, counts, and recurrence requirements. Scored workflow Probes are conjunctive: the first recipe and completion must both hold. Averaging them gave in-task recovery, which every policy that reads the simulator's feedback performs without memory, half credit; `RecoverOnlyAgent` is the public fixture that must stay at zero.

Emission evaluation is based on observable emissions over the full declared lifecycle, not an Agent's claim that it remembered.

## 4.8 Interventions and evidence

- Relevant/no-memory ablation withholds specified observations or lived tasks while ordinary world resets remain fixed.
- Irrelevant ablation tests stability.
- Content swaps replace an assertion or commitment and rederive affected answers/obligations. One twin exists per pivot event and scores every Probe whose answer changes. Its value is chosen from ordinary (non-interference) events only, so it is identical at every rung: preferably a value no ordinary event mentions for the attribute, otherwise one outside the subject's own lineage. A twin is never a no-op "change" to the value the subject already had. Historical Probes have twins too.
- Policy twins (`counterfactual_policy`, `replay_policy_twin`) change a latent workflow recipe consistently in acquisition and future verification. They may change the recipe only, not family identity or operational initialization. They are matched policy-world diagnostics, not history-only Memory Benefit contrasts.
- No-maintenance replay withholds maintenance windows.
- Negative-transfer control withholds one family's acquisition while preserving support for the nonmatching task.
- Generated questioning conditions use a same-position, same-speaker, same-word-count irrelevant question as the `reference_ablation` placebo, and sample the questioned alternative from its own stream. Their harm contrast uses that placebo, not the shorter full timeline.

The symbolic support check establishes only non-derivability under the query engine. It does not establish absence of lexical, metadata, or distributional leakage. Independent adversarial tests are required for those channels.

## 4.9 Weights

Probe scores are weighted means. Scenario dimension evidence weights sum to one. Profile dimension weights define the capability score. Diagnostic/control executions do not add capability weight.

## 4.10 Validation

Validation checks schema, unique IDs, all references, supported tools/methods/operators, lifecycle anchors, and world-policy constraints. A questioning injection cannot directly mutate world state. Only explicitly typed policy twins can replace the supported latent workflow policy.

# 5. Execution

## 5.1 Pack execution

Each Instance and repetition runs the full condition and its scheduled interventions (§2.3). Every ordinary intervention executes the complete future probe program; only its declared scored subset contributes to the corresponding contrast. This keeps earlier probe behavior from becoming an unrecorded difference in the schedule. Contiguous respond Probes with a shared trigger are permuted per seed (identically across rungs and conditions), because answers persist into later formation; action and emission Probes keep their declared order.

## 5.2 Isolation

Conditions use fresh Agent instances/reset contexts with paired seeds and future inputs. Hosted stdio conditions use separate sandboxed processes. Remote/HTTP state isolation remains a declared contract and development transport limitation.

A session boundary is acknowledged by default: the Agent confirms it and keeps its own process state. Under `session_isolation: "persisted_state"` the Runner closes the Agent instance at every boundary, builds a fresh one, resets it with the same seed and restores only the string the Agent returned as `persisted_state` (through the `restore` operation, which it must accept). Nothing else crosses the boundary; the Runner records the number of boundaries and the persisted UTF-8 bytes per run, and the Capability Card reports the largest persisted record. An Agent that hands nothing back starts every session empty. For a remote HTTP Agent the Runner sends the same reset/restore sequence, but the process state behind the endpoint is still the participant's declaration.

## 5.3 Lived experience and lifecycle

The Agent executes training tasks and receives actual tool feedback. Task outcomes are learning diagnostics, not capability points.

The same-model adapter records the active goal, attempted operations, feedback, and completion. B1–B3 persist the task transcript at completion or before the next task, completed public question/answer exchanges, and emitted-message receipts; B0 discards them. Outputs are not oracle feedback: their provenance remains dialogue/emission, and no hidden evaluator data enters formation. Session boundaries clear the transient conversation while preserving the selected persistent-memory condition. Observe-time decisions and maintenance are explicit model operations when enabled by the experiment.

## 5.4 Failure classification

Cognitive failures, including protocol misuse or exhausted action budgets, are scored failures. Execution failures remain in the denominator and contribute to the execution failure rate. A Profile's execution-failure ceiling also gates official eligibility; the hosted leaderboard defaults to zero tolerance.

## 5.5 Evidence artifacts

Run artifacts include probe results, task trials, causal validity, future-input digests, and sufficient statistics for aggregation. Private traces include emitted messages, action/experience traces, world outcomes, and operation telemetry. Public hidden reports omit raw runs and private identifiers.

# 6. Capability scoring

## 6.1 Probe and scenario

`S = sum(probe_weight × probe_score) / sum(probe_weight)` over scored and execution-failure attempts. An execution failure contributes zero with its weight retained.

## 6.2 Instance

Full-condition repetitions are averaged. Dimension attribution follows probe tags. An Instance also retains its rung, interference words/count, virtual distance, and counterfactual evidence counts.

## 6.3 Template/Program

Instances at the Profile's canonical rung are averaged within each Program. Other rungs contribute only to retention curves.

## 6.4 Dimension

`D[d] = 100 × weighted_mean(Program dimension scores, Program evidence weights)`.

## 6.5 MIB score

`MIB = weighted_mean(D[d], Profile weights)`. No global guardrail penalty is implemented. Coverage counts all required Programs, including unsupported ones. Insufficient coverage is partial.

The `official` field means eligible under the declared policy: official Profile, required coverage, dependence policy, and execution-failure ceiling must all pass. Only a trusted evaluator's accepted cycle and cryptographic attestation establish official publication authority; an unsigned local JSON flag does not.

## 6.6 Shared functional

`aggregation.py` is used by pack execution, paired system comparison, and policy verification. Missing evidence cannot silently change dimension weights. Legacy static scoring uses its declared Template hierarchy.

# 7. Diagnostics

## 7.1 Pairing

Pairs share Instance, repetition, Agent seed, and future-input digests. Alternate harm references must be declared matched irrelevant-memory controls on the same probe subset. Invalid pairs contribute no causal evidence.

## 7.2 Benefit and content tracking

`MB = F - R` is signed. `HMB = max(0, F-R)/(1-R)` excludes ablated scores within 0.02 of the ceiling.

Content tracking is conditional on a correct full-condition probe and requires full correctness under the changed oracle. Zero eligible probes is undefined, never evidence of zero tracking. Raw eligible/total counts and success counts are retained separately.

Content and policy twins cover all seven base dimensions, including changed commitments, self rules, and withdrawal instructions. The intervention type remains visible in evaluator-side evidence.

## 7.3 Irrelevant stability

`IMS = clamp(1 - max(0, abs(F-I)-tolerance)/(1-tolerance), 0, 1)`.

## 7.4 Harm

`memory_harm_effect = C-H` is the signed paired effect. `MH = max(0, C-H)` is retained as a separate clipped downside-loss diagnostic, not an unbiased estimate of an average harmful effect. The generated questioning lane uses its matched placebo as C. `HRS = clamp(1 - max(0, C-H-tolerance)/(1-tolerance), 0, 1)`. These are contrasts under the declared construction; they do not establish all real-world forms of memory poisoning.

## 7.5 Net gain

`NMG = MB - MH`, diagnostic only.

## 7.6 Legacy causal dimension

For v0.1 Profiles, the existing benefit-gated causal composite is retained. A v0.2 Profile does not weight it as a capability dimension.

## 7.7 Evidence and uncertainty

Do not substitute the number of Programs for the number of eligible probe pairs. Aggregation retains counts, and the dependence block additionally records independent Instance units. Descriptive rates and causal contrasts have different interpretations.

## 7.8 Negative transfer

Compare the same nonmatching task with and without the other family's acquisition: `negative_transfer_effect = without_skill - with_skill` is signed; `NT = max(0, without_skill - with_skill)` is clipped downside loss. Report the accompanying behavioral failure rate and resistance. Nonmatching probes precede matching probes so the control cannot first re-teach the withheld procedure.

## 7.9 Behavioral diagnostics

Recurrence requires that the Agent actually experienced the corresponding failure. Workflow recurrence matches family and required recipe; an unseen revised rule is not a previously experienced error. First-attempt failure and eventual completion are separate conditions. Learning gain is last minus first trial score, and the reported curve area is the mean trial score.

The new `memory_related_error_rate` is a descriptive error-pattern rate. It does not claim causal attribution. `memory_induced_error_rate` is a legacy name accepted in old reports. Source attribution, historical fidelity, authority confusion, and self-rule continuity remain descriptive diagnostics.

## 7.10 Dependence eligibility

Revision 0.5 Profiles use `content_following_effect` (CFE). The Runner freezes all declared changed-probe opportunities on every run. In the full condition it also evaluates each output against every twin oracle of that Probe (`counterfactual_cross`); in the twin run it records whether the output carries the twin oracle's value (`counterfactual.follows`). For each opportunity, `CFE = follows_twin − follows_full`, using the value component of structured answers and the complete score of action/emission evaluators. Missing and invalid pairs contribute zero and stay in the denominator; correctness never selects eligibility. A system with no memory, a constant answer, or a guess from the public value pool has an expected CFE of zero whatever its accuracy; a system whose answers follow the history has CFE near one even when it is not perfectly accurate.

Repetitions are averaged inside an Instance. The gate averages Instance values within each fixed Program stratum, then averages strata within the dimension. Each weighted dimension requires five complete independent Instances, 100% valid planned-pair coverage, and an Instance-cluster percentile-bootstrap lower bound of at least 0.2 (95%, 2,000 draws by default). Resampling keeps Program strata fixed. Duplicate repetitions cannot increase independent sample count. A missing contrast is unassessable. The floor is chosen for power under the declared sample: with one opportunity per Instance, a system that follows 90% of changes passes all seven dimensions in at least 80% of simulated five-seed packs, while pool guessing passes in at most 5% (regression-tested; about 97% and 0% in a 200-pack simulation). A system that follows 70% of changes passes about a third of the time: five seeds still cannot certify weak dependence.

`joint_twin_success` (full and twin both fully correct) is reported per dimension as a diagnostic. It approximates accuracy squared, so as a gate it was a capability threshold: at five seeds, a system with 90% joint success passed the revision-0.4 gate in about 15% of packs. Conditional content tracking is still reported separately. Revision 0.4 Profiles retain `joint_twin_success`, and legacy Profiles retain their explicitly declared conditional/Wilson policy.

These are development policy choices, not calibrated psychometric thresholds. CFE establishes that answers follow the declared history under the declared construction; it does not identify a persistent-memory mechanism. A degenerate empirical bootstrap interval is explicitly flagged and does not establish population certainty; five uniformly successful Instances are not proof of broad generality. Formal sample size and useful-effect thresholds still require a preregistered pilot.

# 8. Statistics

## 8.1 Retention

Every rung is reported per Program. `retention_index` is the arithmetic mean of rung scores, not a scale-invariant area under a physical distance curve. Half-distance is interpolated relative to rung-zero performance when the ladder crosses half that value. A score that never crosses is reported as beyond the ladder.

## 8.2 Bootstrap

Generated packs keep the Program set fixed, resample canonical-rung Instances, and resample paired repetitions inside each Instance. Static packs resample Templates as documented. Intervals are percentile or BCa with explicit fallback for degeneracy.

Intervals are conditional on the declared Program set and sufficient sample count. They do not measure uncertainty about the choice of semantic designs. Increasing resample count does not compensate for a tiny number of real observations.

## 8.3 Canonical rung

The capability score, dependence gate, and score interval use the same canonical rung. The complete retention curve remains separate.

The canonical rung of the 0 / 20 / 100 development Profiles shows about 970–1,500 visible history characters (Core) and at most about 5,400 at the top rung. An integrated Agent whose context holds that much history is in a raw-context regime: the score does not separate memory from reading the transcript, and the Capability Card states the visible history range with the score. The `Horizon-Dev` Profile reads the score at 2,000 interference events (about 90,000 visible characters) with a 10,000-event retention rung (about 450,000). Long visible history is the only pressure the Runner can put on an integrated Agent.

## 8.4 Paired comparison

Comparisons require matching Profile/version, track, scale, pack, scoring revision, policy, weights, canonical rung, and complete paired Instance coverage. Generated comparisons do not resample away Programs or mix other rungs. Both point differences and intervals use the same shared score functional.

# 9. Reports and verification

## 9.1 Identity

A result names its Profile/version, track, pack/version, canonical rung, measurement regime, Agent identity, and executable source digest. Same-model experiments also lock model configuration, prompts, decoding, runtime memory policy, and source hashes.

## 9.2 Verification levels

New reports embed the score-relevant evaluation policy and required Program evidence weights. Full verification recomputes run/Instance aggregates, causal evidence, dependence decisions, coverage, official eligibility, retention, and available intervals. Public redacted verification checks the policy and retained aggregates; it cannot recreate private execution.

Bootstrap estimation and replay use the effective ablation tolerances carried by Run Artifacts. A reduced Template descriptor lacking private ablation definitions does not imply zero tolerance. Legacy artifacts without a carried tolerance may use the Scenario declaration during estimation.

Displayed intervals must match the statistics block. Tampering with a dependence gate, official flag, aggregate causal value, retention curve, or interval is rejected. New reports require the matching executable source bundle to reproduce their interpretation.

Arithmetic consistency, source identity, service attestation, trusted Profile admission, and scientific validity are distinct claims.

## 9.3 Cost

Runner telemetry records calls, input/output UTF-8 bytes, and wall-clock milliseconds for observe, respond, act, maintenance, and reset. Tool calls and probe latency remain available. Same-model telemetry additionally records provider-supplied token usage and memory truncation.

The bundle does not independently measure every external system's storage, write amplification, or backend compute. Bounded built-in and external contexts share a hard final rendered-character limit, including prefixes and separators. Same-model experiments report `memory_pressure`: rendered visible-observation characters divided by each bounded arm's budget (a lower bound, since lived-task transcripts and dialogue add more). Oversize records are omitted whole and reported; null limits explicitly mean unbounded references. Characters are not tokenizer tokens. Core signed and clipped score differences use JSON unit `normalized_delta`; displays multiply by 100 to show percentage points. Use budget-controlled experiments and report quality/cost pairs; do not interpret whitespace words or probe latency alone as memory efficiency.

# 10. Calibration

Generated calibration materializes every Program/rung/seed and counterbalances B0 no memory, B1 full visible history, B2 lexical retrieval, and B3 heuristic salience selection with a fixed model/prompt/tool/decoding setup. It includes content and policy twins and matched harmful/placebo controls.

Optional additional groups measure an unbounded complete-history reference, bounded recent context and a privileged oracle-supported reference. The unbounded reference is the full-context arm of the release gate whenever B1 is bounded; the other two are diagnostic only, do not enter core scores, and are not guaranteed mathematical upper bounds.

A comparison of memory arms under a budget is informative only when the budget binds in every arm. When any B1–B3 arm is bounded and the purpose is not `smoke`, the preflight requires every bounded arm's median history/budget ratio to reach `calibration.min_memory_pressure` (default 1), and requires that each arm's selection policy could fill its budget: B2 keeps `retrieval_top_k` records and B3 at most `structured_top_k + structured_salient_k`, so `top_k` times the median rendered record must reach the budget (`selection_capacity_chars`, `budget_binds`). Otherwise the arms differ in capacity rather than policy, and the run is refused. A bounded B1 is labelled `most_recent_visible_history_within_budget` and is a recency window, not full context: the `full_context` gate, the memory-discriminativeness index and the memory-gap denominators then use the `unbounded_reference` additional baseline (B1 without a budget), which must run untruncated; without it those gates are unassessable. Experiments with unbounded arms are `unbounded_reference` regimes: B1 is then a complete-history reference and B2/B3 differ only by selection policy, which is not a budgeted architecture comparison.

`same-model-generated.stub.json` is an engineering smoke configuration. `same-model-generated.external-http.json` is a ready-to-configure real-model experiment with unbounded references. `same-model-generated.pilot.json` runs at 100 interference events with a 3,500-character budget per memory arm (median history/budget ratio about 4.2, required at least 4), selection sizes that can fill that budget (B2 top-30, B3 24+8 records of about 140 rendered characters), and the unbounded reference arm. A model endpoint, immutable model identity, and credentials are external inputs. Stub execution cannot establish difficulty, discriminativeness, or release readiness. The statelessness preflight can detect some violations; it is not a proof that a remote service retains no state.

Choose real sample counts, repetitions, and admission thresholds from pilot variance and a preregistered minimum useful effect. Run multiple fixed models before making architecture-general claims. An official freeze remains contingent on those empirical results. Missing or incomplete necessary causal metrics are `unassessable`, not passes. Invalid full/causal lifecycles block admission. Smoke and pilot configurations never grant release admission. Calibration seed/repetition/threshold/purpose settings are bound in the experiment lock.

When bounded B1 uses the unbounded reference for admission, that reference's invocations and runs also enter model/prompt/decoding identity checks, transport/parse error counts, lifecycle checks, and the paired seed/future-Probe audit. Fairness invocation totals include it; its telemetry remains in `additional_baselines.unbounded_reference`. The condition-order audit remains the B0–B3 counterbalance. An extra reference that is unused for admission remains diagnostic.

# 11. Governance and hidden evaluation

Generated private stores use secret keyed seeds and public Program construction. Store and Profile configuration must agree. Jobs bind the private store, Profile, schemas, and executable source bundle. Results bind report digests and are signed by the service.

The service rejects track mismatches and excludes partial, unofficial, failed-policy, or invalid reports from ranking. Hosted external submissions are Track B; Track A uses the evaluator-controlled same-model harness.

Public reports redact raw runs, seeds, private Template IDs, transfer support details, and evaluator-only content. Linux-only process isolation remains a platform limitation. HTTP reset and remote model statelessness remain declared contracts. The implementation does not claim hardware attestation or a completed production deployment.

# 12. Invariants and remaining empirical work

1. Architecture neutrality does not mean unspecified experimental resources.
2. Ordinary participant metadata does not reveal probe or relevance roles.
3. Withholding history keeps ordinary future world resets fixed.
4. Policy twins are explicitly typed changes to latent conventions, not disguised memory-only ablations.
5. First-attempt correctness and actual experienced failures are observable.
6. Missing scored fields do not shrink a rubric.
7. Withdrawal is evaluated across visible output, not self-reported status.
8. Prospective memory includes false alarms throughout the declared lifecycle.
9. Capability, dependence, and comparisons use consistent aggregation and canonical rungs.
10. Missing causal evidence remains missing; counts keep their statistical units.
11. A generated oracle needs independent validation.
12. Fixture ordering is plumbing evidence, not real-model calibration.
13. A policy that remembers nothing earns no structural credit: `GrammarOnlyAgent` (public-grammar defaults, no history) scores at most 10 in every Core and Expanded dimension and fails the dependence gate (regression-tested; currently 0).
14. A budgeted memory comparison requires a budget that binds; the dependence gate measures content following, not accuracy.

Further empirical validation, real-system storage/cost instrumentation, broader independent domains, and an official freeze are not implied by implementing these constructs. Transfer Intelligence remains supplemental; its early/late artifact contrast measures availability across formation, survival, and retrieval unless stronger routing assumptions are justified. MIB-R remains an independent prototype result family whose external-task utility needs its own calibration.

# 13. Development challenges and entry points

`MIB-Mechanism-Challenges-0.1-Dev` adds feature-based recipe composition for unseen families and multiple commitment/cancellation/renewal/repeated-trigger behavior. It is a separate Profile, not an expansion of the Core score. The feature task supplies the composition convention, but operations must come from actual feedback; it tests bounded composition, not open-ended rule discovery.

Use `mib run` with a Scenario, generated Profile, same-model configuration, memory-backend configuration, or longitudinal configuration. `mib compare` compares compatible verified pack reports; `mib verify` aliases `verify-score`. Existing commands remain supported. Scenario/Profile runs require `--schema`; configured experiments resolve their own schemas and prompts. `same-model-generated.pilot.json` is a bounded seven-mechanism, one-rung pilot under memory pressure; the existing stub/full configurations remain separate.

The optional `observe_decision_types` routes business-model observation decisions by public observation type. All observations still reach memory formation. The same declared router applies to every memory arm and never reads probe, relevance, oracle, or trigger labels.
