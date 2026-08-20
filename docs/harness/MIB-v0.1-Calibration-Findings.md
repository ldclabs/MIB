# MIB v0.1 Calibration Findings

**Status:** Reference-fixture calibration  
**Profile:** `MIB-Core-0.1`  
**Scope:** 36 official Hidden Eval / Private Holdout Templates

## Result

The complete calibration suite runs with four instance seeds over all 36 official Templates and passes the provisional full gate including causal sensitivity at **36 / 36**.

This is **fixture calibration**, not release-grade empirical calibration with a fixed external model. `release_calibration_eligible` therefore remains `false`.

Per-Template metrics are in `examples/calibration/MIB-v0.1-reference-calibration.json`.

## Design constraints

1. Future action goals do not disclose semantic applicability labels such as `global` / `contextual`; opaque class/version tokens are used instead.
2. No single universal no-memory default action is safe across a Scenario's probes.
3. Relevant ablation removes the complete critical information set, never a redundant subset.
4. Multi-branch Skill Scenarios use probe-specific relevant ablations.
5. The calibration fixture treats missing historical evidence as `unknown`, not as a negative fact.

## Final gate matrix

```text
baseline_span            36 / 36
causal_sensitivity       36 / 36
full_context             36 / 36
irrelevant_stability     36 / 36
mdi                      36 / 36
no_memory                36 / 36
provisional gate all three   36 / 36
full gate incl. causal      36 / 36
```

## Baseline dimension surface

| Dimension | B0 No Memory | B1 Full History Fixture | B2 Retrieval | B3 Structured |
|---|---:|---:|---:|---:|
| `retention_retrieval` | 0.8 | 100.0 | 75.1 | 100.0 |
| `temporal_memory` | 9.0 | 100.0 | 66.9 | 100.0 |
| `epistemic_memory` | 8.8 | 100.0 | 65.0 | 100.0 |
| `experience_memory` | 14.4 | 100.0 | 49.4 | 100.0 |
| `skill_learning_transfer` | 35.1 | 100.0 | 84.6 | 100.0 |
| `causal_memory_impact` | 14.6 | 100.0 | 70.1 | 100.0 |

Skill No-Memory stays low because action goals carry no explicit applicability leakage.

## Interpretation

Passing this fixture gate means the current Scenario design is internally memory-dependent and the declared causal interventions are sensitive under the deterministic calibration fixtures. It does **not** yet establish external validity, human-level difficulty, or fixed-model leaderboard suitability. The next calibration stage should replace fixture B0/B1/B2/B3 with same-model empirical baselines.
