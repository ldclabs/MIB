# MIB Capability Card

```text
MIB — Memory Intelligence Benchmark
════════════════════════════════════════════

Profile   MIB-Core-0.2-Load-Dev 0.3.0
Track     integrated_agent
Scale     MIB-S
Agent     MIB Structured Memory Fixture 0.10.0

MIB Score 100.0
95% CI    [100.0, 100.0]

Capability
  Retention & Retrieval        100.0  coverage 100.0%
  Temporal Memory              100.0  coverage 100.0%
  Epistemic Memory             100.0  coverage 100.0%
  Experience Memory            100.0  coverage 100.0%
  Skill Learning & Transfer    100.0  coverage 100.0%
  Prospective & Self Memory    100.0  coverage 100.0%
  Selective Forgetting         100.0  coverage 100.0%

Causal Diagnostics
  Memory Benefit               +80.6 pp
  Memory Harm                   +0.0 pp
  Net Memory Gain              +80.6 pp
  Irrelevant Stability         100.0
  Harm Resistance              100.0
  Content Tracking             100.0
  Stale Adoption                 0.0%
  Error Recurrence               0.0%
  Consolidation Benefit         +0.0 pp

Behaviour Diagnostics
  Negative Transfer             +0.0 pp
  Negative Transfer Rate         0.0%
  Learning Gain                +12.5 pp
  Learning Curve Area           68.8
  Historical Fidelity          100.0
  Source Attribution           100.0
  Authority Confusion            0.0%
  Self-Rule Continuity         100.0
  Memory-Related Error Patterns (descriptive)   0.0%

Retention (score by interference distance)
  MIB-GEN-AUTHORITY-V1         @0:100.0  @20:100.0  @100:100.0  index 100.0  half >ladder
  MIB-GEN-BITEMPORAL-V1        @0:100.0  @20:100.0  @100:100.0  index 100.0  half >ladder
  MIB-GEN-CANCELLED-COMMITMENT-V1 @0:100.0  @20:100.0  @100:100.0  index 100.0  half >ladder
  MIB-GEN-COMPOSED-SKILL-V1    @0:100.0  @20:100.0  @100:100.0  index 100.0  half >ladder
  MIB-GEN-EPISTEMIC-V1         @0:100.0  @20:100.0  @100:100.0  index 100.0  half >ladder
  MIB-GEN-EXPERIENCE-V1        @0:100.0  @20:100.0  @100:100.0  index 100.0  half >ladder
  MIB-GEN-FORGETTING-V1        @0:100.0  @20:100.0  @100:100.0  index 100.0  half >ladder
  MIB-GEN-INTERLEAVED-RECALL-V1 @0:100.0  @20:100.0  @100:100.0  index 100.0  half >ladder
  MIB-GEN-PROSPECTIVE-V1       @0:100.0  @20:100.0  @100:100.0  index 100.0  half >ladder
  MIB-GEN-RECALL-V1            @0:100.0  @20:100.0  @100:100.0  index 100.0  half >ladder
  MIB-GEN-RELEARNING-V1        @0:100.0  @20:100.0  @100:100.0  index 100.0  half >ladder
  MIB-GEN-REVISED-EXPERIENCE-V1 @0:100.0  @20:100.0  @100:100.0  index 100.0  half >ladder
  MIB-GEN-SKILL-V1             @0:100.0  @20:100.0  @100:100.0  index 100.0  half >ladder
  MIB-GEN-TEMPORAL-V1          @0:100.0  @20:100.0  @100:100.0  index 100.0  half >ladder
  Capability score read at rung 1.

Memory Dependence
  content_tracking_rate        100.0  floor  50.0  (169/169 eligible changed-probe pairs)
  meets the declared dependence policy
  Retention & Retrieval        10 Instances; 50/50 pairs; lower bound 72.2%; pass
  Temporal Memory              10 Instances; 20/20 pairs; lower bound 72.2%; pass
  Epistemic Memory             10 Instances; 19/19 pairs; lower bound 72.2%; pass
  Experience Memory            10 Instances; 10/10 pairs; lower bound 72.2%; pass
  Skill Learning & Transfer    10 Instances; 10/10 pairs; lower bound 72.2%; pass
  Prospective & Self Memory    10 Instances; 20/20 pairs; lower bound 72.2%; pass
  Selective Forgetting         10 Instances; 40/40 pairs; lower bound 72.2%; pass
  Regime: historical_information_use; internal mechanism is not independently identified.

Runner operations (all evaluation conditions; UTF-8 bytes, not tokens)
  act                4230 calls; 116.3 ms; 1888590 input bytes; 710430 output bytes
  maintain           1656 calls; 7.9 ms; 228528 input bytes; 61557 output bytes
  observe          104328 calls; 1152.0 ms; 41020152 input bytes; 3662151 output bytes
  reset              1866 calls; 12.4 ms; 175404 input bytes; 33588 output bytes
  respond            5421 calls; 9866.7 ms; 2198280 input bytes; 715881 output bytes

Coverage  100.0%
Execution Failure Rate  0.00%

Development profile — not an official Hidden Eval leaderboard score.
```
