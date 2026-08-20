# MIB v0.1 Calibration Report

**Profile:** `MIB-Core-0.1`  
**Mode:** `reference_fixture`  
**Release calibration eligible:** `false`

> This report uses deterministic reference fixtures to validate benchmark discrimination mechanics. It is not yet the release-grade fixed-LLM Full Context calibration.

## Summary

- Templates: **36**
- FC/NM/MDI provisional pass: **36 / 36**
- Full fixture gate including causal sensitivity: **36 / 36**
- `provisional_pass`: **36**

## Dimension Baseline Matrix

| Dimension | B0 | B1 | B2 | B3 |
|---|---:|---:|---:|---:|
| retention_retrieval | 0.8 | 100.0 | 75.1 | 100.0 |
| temporal_memory | 9.0 | 100.0 | 66.9 | 100.0 |
| epistemic_memory | 8.8 | 100.0 | 65.0 | 100.0 |
| experience_memory | 14.4 | 100.0 | 49.4 | 100.0 |
| skill_learning_transfer | 35.1 | 100.0 | 84.6 | 100.0 |
| causal_memory_impact | 14.6 | 100.0 | 70.1 | 100.0 |

## Template Calibration Cards

| Template | FC | NM | MDI | B2 | B3 | IMS | Recommendation |
|---|---:|---:|---:|---:|---:|---:|---|
| MIB-CAUSAL-004 | 100 | 43 | 57 | 100 | 100 | 100 | `provisional_pass` |
| MIB-CAUSAL-005 | 100 | 43 | 57 | 100 | 100 | 100 | `provisional_pass` |
| MIB-CAUSAL-006 | 100 | 0 | 100 | 0 | 100 | 100 | `provisional_pass` |
| MIB-CAUSAL-007 | 100 | 0 | 100 | 100 | 100 | 100 | `provisional_pass` |
| MIB-CAUSAL-008 | 100 | 0 | 100 | 100 | 100 | 100 | `provisional_pass` |
| MIB-EPI-005 | 100 | 50 | 50 | 100 | 100 | 100 | `provisional_pass` |
| MIB-EPI-006 | 100 | 0 | 100 | 100 | 100 | 100 | `provisional_pass` |
| MIB-EPI-007 | 100 | 0 | 100 | 50 | 100 | 100 | `provisional_pass` |
| MIB-EPI-008 | 100 | 0 | 100 | 67 | 100 | 100 | `provisional_pass` |
| MIB-EPI-009 | 100 | 0 | 100 | 50 | 100 | 100 | `provisional_pass` |
| MIB-EPI-010 | 100 | 0 | 100 | 67 | 100 | 100 | `provisional_pass` |
| MIB-EXP-004 | 100 | 13 | 87 | 13 | 100 | 100 | `provisional_pass` |
| MIB-EXP-005 | 100 | 20 | 80 | 20 | 100 | 100 | `provisional_pass` |
| MIB-EXP-006 | 100 | 13 | 87 | 100 | 100 | 100 | `provisional_pass` |
| MIB-EXP-007 | 100 | 43 | 57 | 100 | 100 | 100 | `provisional_pass` |
| MIB-EXP-008 | 100 | 10 | 90 | 100 | 100 | 100 | `provisional_pass` |
| MIB-RET-005 | 100 | 0 | 100 | 100 | 100 | 100 | `provisional_pass` |
| MIB-RET-006 | 100 | 0 | 100 | 100 | 100 | 100 | `provisional_pass` |
| MIB-RET-007 | 100 | 0 | 100 | 62 | 100 | 100 | `provisional_pass` |
| MIB-RET-008 | 100 | 0 | 100 | 100 | 100 | 100 | `provisional_pass` |
| MIB-RET-009 | 100 | 0 | 100 | 100 | 100 | 100 | `provisional_pass` |
| MIB-RET-010 | 100 | 0 | 100 | 0 | 100 | 100 | `provisional_pass` |
| MIB-SKILL-004 | 100 | 43 | 57 | 100 | 100 | 100 | `provisional_pass` |
| MIB-SKILL-005 | 100 | 47 | 53 | 100 | 100 | — | `provisional_pass` |
| MIB-SKILL-006 | 100 | 43 | 57 | 100 | 100 | 100 | `provisional_pass` |
| MIB-SKILL-007 | 100 | 43 | 57 | 100 | 100 | 100 | `provisional_pass` |
| MIB-SKILL-008 | 100 | 25 | 75 | 25 | 100 | 100 | `provisional_pass` |
| MIB-TIME-005 | 100 | 0 | 100 | 33 | 100 | 100 | `provisional_pass` |
| MIB-TIME-006 | 100 | 0 | 100 | 50 | 100 | 100 | `provisional_pass` |
| MIB-TIME-007 | 100 | 0 | 100 | 100 | 100 | 100 | `provisional_pass` |
| MIB-TIME-008 | 100 | 0 | 100 | 100 | 100 | 100 | `provisional_pass` |
| MIB-TIME-009 | 100 | 22 | 78 | 50 | 100 | 100 | `provisional_pass` |
| MIB-TIME-010 | 100 | 33 | 67 | 100 | 100 | 100 | `provisional_pass` |
| MIB-X-004 | 100 | 0 | 100 | 0 | 100 | 100 | `provisional_pass` |
| MIB-X-005 | 100 | 0 | 100 | 0 | 100 | 100 | `provisional_pass` |
| MIB-X-006 | 100 | 0 | 100 | 0 | 100 | 100 | `provisional_pass` |

## Interpretation

- **FC**: B1 Full Visible History Fixture.
- **NM**: B0 No Memory.
- **MDI**: `FC - NM`.
- **B2**: simple lexical top-k retrieval.
- **B3**: structured/agentic salient-memory retrieval.
- **IMS**: irrelevant-memory stability from B3 causal replay where available.

A `provisional_pass` means the scenario passes the fixture gate. It does **not** mean the scenario has completed release-grade empirical calibration.
