# MIB Capability Card

```text
MIB — Memory Intelligence Benchmark
════════════════════════════════════════════

Profile   MIB-Core-0.2-Dev 0.3.0
Track     integrated_agent
Scale     MIB-S
Agent     MIB Overgeneralizing Fixture 0.10.0

MIB Score 96.5
95% CI    [96.5, 96.5]

Capability
  Retention & Retrieval        100.0  coverage 100.0%
  Temporal Memory              100.0  coverage 100.0%
  Epistemic Memory             100.0  coverage 100.0%
  Experience Memory            100.0  coverage 100.0%
  Skill Learning & Transfer     75.0  coverage 100.0%
  Prospective & Self Memory    100.0  coverage 100.0%
  Selective Forgetting         100.0  coverage 100.0%

Causal Diagnostics
  Memory Benefit               +80.4 pp
  Memory Harm                   +0.0 pp
  Net Memory Gain              +80.4 pp
  Irrelevant Stability         100.0
  Harm Resistance              100.0
  Content Tracking             100.0
  Stale Adoption                 0.0%
  Error Recurrence              25.0%
  Consolidation Benefit         +0.0 pp

Behaviour Diagnostics
  Negative Transfer            +50.0 pp
  Negative Transfer Rate       100.0%
  Learning Gain                +25.0 pp
  Learning Curve Area           70.8
  Historical Fidelity          100.0
  Source Attribution           100.0
  Authority Confusion            0.0%
  Self-Rule Continuity         100.0
  Memory-Related Error Patterns (descriptive)   7.1%

Retention (score by interference distance)
  MIB-GEN-EPISTEMIC-V1         @0:100.0  @20:100.0  @100:100.0  index 100.0  half >ladder
  MIB-GEN-EXPERIENCE-V1        @0:100.0  @20:100.0  @100:100.0  index 100.0  half >ladder
  MIB-GEN-FORGETTING-V1        @0:100.0  @20:100.0  @100:100.0  index 100.0  half >ladder
  MIB-GEN-PROSPECTIVE-V1       @0:100.0  @20:100.0  @100:100.0  index 100.0  half >ladder
  MIB-GEN-RECALL-V1            @0:100.0  @20:100.0  @100:100.0  index 100.0  half >ladder
  MIB-GEN-SKILL-V1             @0: 75.0  @20: 75.0  @100: 75.0  index  75.0  half >ladder
  MIB-GEN-TEMPORAL-V1          @0:100.0  @20:100.0  @100:100.0  index 100.0  half >ladder
  Capability score read at rung 1.

Memory Dependence
  content_tracking_rate        100.0  floor  50.0  (64/64 eligible changed-probe pairs)
  meets the declared dependence policy
  Retention & Retrieval        5 Instances; 10/10 pairs; lower bound 56.6%; pass
  Temporal Memory              5 Instances; 5/5 pairs; lower bound 56.6%; pass
  Epistemic Memory             5 Instances; 14/14 pairs; lower bound 56.6%; pass
  Experience Memory            5 Instances; 5/5 pairs; lower bound 56.6%; pass
  Skill Learning & Transfer    5 Instances; 5/5 pairs; lower bound 56.6%; pass
  Prospective & Self Memory    5 Instances; 10/10 pairs; lower bound 56.6%; pass
  Selective Forgetting         5 Instances; 15/15 pairs; lower bound 56.6%; pass
  Regime: historical_information_use; internal mechanism is not independently identified.

Runner operations (all evaluation conditions; UTF-8 bytes, not tokens)
  act                2040 calls; 38.4 ms; 897285 input bytes; 346605 output bytes
  maintain            756 calls; 3.5 ms; 104328 input bytes; 27972 output bytes
  observe           40188 calls; 438.4 ms; 15783172 input bytes; 1414935 output bytes
  reset               861 calls; 5.7 ms; 80934 input bytes; 15498 output bytes
  respond            2031 calls; 2569.6 ms; 837870 input bytes; 266469 output bytes

Coverage  100.0%
Execution Failure Rate  0.00%

Development profile — not an official Hidden Eval leaderboard score.
```
