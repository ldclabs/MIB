# MIB v0.2 Same-Model Calibration Report

**Experiment:** `MIB-v0.2-generated-engineering-smoke`  
**Mode:** `same_model_engineering_stub`  
**Model:** `mib-deterministic-stub/0.1`  
**Experiment lock:** `sha256:b8545abb7e59484b2d499935e73d7d43ec825f7ea30e1ac09fc7e421427aa193`\
**Fairness audit:** `PASS`  
**Leaderboard release eligible:** `false`

## Experimental Variable

The base model, system prompt, reasoning policy, tool interface, decoding parameters, Scenario instances, and pairing policy are locked. Only long-term memory policy/context varies:

- **B0** — No Memory
- **B1** — Full Visible History
- **B2** — Simple Lexical Retrieval
- **B3** — Structured Deterministic Memory

## Release Gate

- Official Templates passing full gate: **0 / 42**
- Non-stub fixed model: **False**
- Fairness valid: **True**
- Release eligible: **False**

## Condition Order

- Policy: `counterbalanced_latin_rotation_v1`
- Paired units: **42**
- Balanced: **True**
- Schedule digest: `sha256:6ced22070f9d86edb1cacefd26ccac387217829a9e15a9956de8d8dc46d18e3d`

## Dimension Matrix

| Dimension | B0 | B1 | B2 | B3 |
|---|---:|---:|---:|---:|
| retention_retrieval | 0.0 | 6.7 | 3.3 | 3.3 |
| temporal_memory | 0.0 | 0.0 | 0.0 | 0.0 |
| epistemic_memory | 8.3 | 8.3 | 8.3 | 8.3 |
| experience_memory | 0.0 | 0.0 | 0.0 | 0.0 |
| skill_learning_transfer | 0.0 | 0.0 | 0.0 | 0.0 |
| prospective_self_memory | 64.0 | 64.0 | 64.0 | 64.0 |
| selective_forgetting | 30.0 | 54.0 | 54.0 | 54.0 |

## Fairness Checks

- `single_model_identity`: **PASS**
- `single_model_client_configuration`: **PASS**
- `identical_system_prompt`: **PASS**
- `identical_reasoning_policy`: **PASS**
- `identical_tool_interface`: **PASS**
- `identical_decoding_parameters`: **PASS**
- `deterministic_or_seeded_decoding`: **PASS**
- `stateless_model_contract`: **PASS**
- `statelessness_preflight`: **PASS**
- `only_memory_policy_varies`: **PASS**
- `condition_label_not_model_visible`: **PASS**
- `counterbalanced_condition_order`: **PASS**
- `paired_agent_seed_and_future_probe`: **PASS**
- `b1_full_context_not_truncated`: **PASS**
- `no_model_transport_or_parse_errors`: **PASS**

## Model / Memory Telemetry

| Condition | Calls | Errors | Memory selections | Selected records | Truncations |
|---|---:|---:|---:|---:|---:|
| B0 | 2064 | 0 | 2064 | 0 | 0 |
| B1 | 2064 | 0 | 2064 | 90518 | 0 |
| B2 | 2064 | 0 | 2064 | 7992 | 0 |
| B3 | 17133 | 0 | 17133 | 165709 | 0 |

## Interpretation

A result is release-eligible only when a real fixed model—not the engineering stub—runs all four memory conditions under the same experiment lock, the condition schedule is balanced, paired seeds/Probes are intact, B1 is complete rather than truncated, statelessness checks pass, transport/parsing is clean, and every official Template passes the empirical admission gates.
