# MIB Capability Card

```text
MIB — Memory Intelligence Benchmark
════════════════════════════════════════════

Profile   MIB-Core-0.2-Dev 0.3.0
Track     integrated_agent
Scale     MIB-S
Agent     MIB Window Memory Fixture (window 12) 0.10.0

MIB Score 29.5
95% CI    [28.9, 30.1]

Capability
  Retention & Retrieval          0.0  coverage 100.0%
  Temporal Memory                0.0  coverage 100.0%
  Epistemic Memory              16.7  coverage 100.0%
  Experience Memory             50.0  coverage 100.0%
  Skill Learning & Transfer     50.0  coverage 100.0%
  Prospective & Self Memory     44.8  coverage 100.0%
  Selective Forgetting          60.0  coverage 100.0%

Causal Diagnostics
  Memory Benefit                +0.0 pp
  Memory Harm                   +0.0 pp
  Net Memory Gain               +0.0 pp
  Irrelevant Stability         100.0
  Harm Resistance              100.0
  Content Tracking               0.0
  Stale Adoption               100.0%
  Error Recurrence             100.0%
  Consolidation Benefit         +0.0 pp

Behaviour Diagnostics
  Negative Transfer             +0.0 pp
  Negative Transfer Rate         0.0%
  Learning Gain                +25.0 pp
  Learning Curve Area           70.8
  Historical Fidelity            0.0
  Source Attribution             0.0
  Authority Confusion            0.0%
  Self-Rule Continuity          62.0
  Memory-Related Error Patterns (descriptive)  21.4%

Retention (score by interference distance)
  MIB-GEN-EPISTEMIC-V1         @0:100.0  @20: 16.7  @100: 16.7  index  44.4  half 12
  MIB-GEN-EXPERIENCE-V1        @0:100.0  @20: 50.0  @100: 50.0  index  66.7  half 20
  MIB-GEN-FORGETTING-V1        @0:100.0  @20: 60.0  @100: 60.0  index  73.3  half >ladder
  MIB-GEN-PROSPECTIVE-V1       @0:100.0  @20: 44.8  @100: 44.8  index  63.2  half 18
  MIB-GEN-RECALL-V1            @0:100.0  @20:  0.0  @100:  0.0  index  33.3  half 10
  MIB-GEN-SKILL-V1             @0:100.0  @20: 50.0  @100: 50.0  index  66.7  half 20
  MIB-GEN-TEMPORAL-V1          @0:100.0  @20:  0.0  @100:  0.0  index  33.3  half 10
  Capability score read at rung 1.

Memory Dependence
  content_tracking_rate          0.0  floor  50.0  (10/64 eligible changed-probe pairs)
  insufficient evidence or below a policy threshold
  Retention & Retrieval        0 Instances; 0/10 pairs; lower bound n/a; unassessable
  Temporal Memory              0 Instances; 0/5 pairs; lower bound n/a; unassessable
  Epistemic Memory             0 Instances; 0/14 pairs; lower bound n/a; unassessable
  Experience Memory            0 Instances; 0/5 pairs; lower bound n/a; unassessable
  Skill Learning & Transfer    0 Instances; 0/5 pairs; lower bound n/a; unassessable
  Prospective & Self Memory    0 Instances; 0/10 pairs; lower bound n/a; unassessable
  Selective Forgetting         5 Instances; 10/15 pairs; lower bound -0.0%; below policy
  Regime: historical_information_use; internal mechanism is not independently identified.

Runner operations (all evaluation conditions; UTF-8 bytes, not tokens)
  act                2205 calls; 37.9 ms; 935565 input bytes; 364640 output bytes
  maintain            756 calls; 3.4 ms; 104328 input bytes; 27972 output bytes
  observe           40353 calls; 428.8 ms; 15849237 input bytes; 1415140 output bytes
  reset               861 calls; 5.4 ms; 80934 input bytes; 15498 output bytes
  respond            2031 calls; 579.0 ms; 837870 input bytes; 266083 output bytes

Coverage  100.0%
Execution Failure Rate  0.00%

Development profile — not an official Hidden Eval leaderboard score.
```
