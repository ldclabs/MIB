# MIB v0.1 Same-Model Empirical Calibration Report

**Experiment:** `MIB-Core-0.1-same-model-engineering-smoke`  
**Mode:** `same_model_engineering_stub`  
**Model:** `mib-deterministic-stub/0.1`  
**Experiment lock:** `sha256:a2cbbeaf1d684205001bafb452059bf0752a85029c799b29bf12fda44ecae63f`  
**Fairness audit:** `PASS`  
**Leaderboard release eligible:** `false`

## Experimental Variable

The base model, system prompt, reasoning policy, tool interface, decoding parameters, Scenario instances, and pairing policy are locked. Only long-term memory policy/context varies:

- **B0** — No Memory
- **B1** — Full Visible History
- **B2** — Simple Lexical Retrieval
- **B3** — Structured Deterministic Memory

## Release Gate

- Official Templates passing full gate: **0 / 36**
- Non-stub fixed model: **False**
- Fairness valid: **True**
- Release eligible: **False**

## Condition Order

- Policy: `counterbalanced_latin_rotation_v1`
- Paired units: **36**
- Balanced: **True**
- Schedule digest: `sha256:1802152023da1cb8c0339af2ee991a1730b8339e37f01feea92eeb16e39571f7`

## Dimension Matrix

| Dimension | B0 | B1 | B2 | B3 |
|---|---:|---:|---:|---:|
| retention_retrieval | 0.4 | 0.4 | 0.4 | 0.4 |
| temporal_memory | 5.6 | 5.6 | 5.6 | 5.6 |
| epistemic_memory | 1.1 | 1.1 | 1.1 | 1.1 |
| experience_memory | 10.2 | 10.2 | 10.2 | 10.2 |
| skill_learning_transfer | 23.6 | 23.6 | 23.6 | 23.6 |
| causal_memory_impact | 9.2 | 9.2 | 9.2 | 9.2 |

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
| B0 | 56 | 0 | 56 | 0 | 0 |
| B1 | 56 | 0 | 56 | 1325 | 0 |
| B2 | 56 | 0 | 56 | 216 | 0 |
| B3 | 226 | 0 | 226 | 1786 | 0 |

## Interpretation

A result is release-eligible only when a real fixed model—not the engineering stub—runs all four memory conditions under the same experiment lock, the condition schedule is balanced, paired seeds/Probes are intact, B1 is complete rather than truncated, statelessness checks pass, transport/parsing is clean, and every official Template passes the empirical admission gates.
