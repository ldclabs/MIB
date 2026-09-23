# Runtime memory backend and lifecycle contract

Implementation **0.14.0** provides a Track A runtime backend seam. It uses the existing `SameModelAgent`, runner, World tools, deterministic evaluators and score aggregation. The experimental AO `MemoryAdapter` remains a separate diagnostic interface. A participant's integrated Bot belongs to Track B even when it exposes this additional memory-only endpoint.

## Success gates and report versions

Pack reports are now **0.6.0**; single-scenario reports are **0.1.1**. Scenario format remains **0.2**; the measurement revision is **0.5.0**. Old artifacts retain their original report version and cannot establish compliance with the new lifecycle or dependence contract.

Every run calls `describe`. Required capabilities must be explicitly `true`; an omitted capability is not inferred. Public pack execution reports unsupported coverage when a required capability is not declared. During a scheduled run, `reset`, `observe`, declared `maintain`, and `session_boundary` must return an object with `accepted: true` and no error. Observe success means the write is available to subsequent reads; maintain success means its advertised work reached a terminal successful state, not just that it entered a queue. The participant is responsible for that implementation; receipts alone cannot prove an honest remote service.

An optional maintenance operation declared `false` is explicitly recorded as skipped. Undeclared maintenance at a delivered maintenance window, negative acknowledgement, exception or transport timeout invalidates the condition. All scheduled probes retain their weights and become `execution_failure` with score 0, including probes answered correctly before the failure. Those earlier results remain in `adapter_contract.pre_invalidation_probe_results` for diagnosis. Invalid conditions cannot become causal evidence or earn consolidation benefit. Cleanup failures also invalidate the run. Ordinary cognitive mistakes remain scored failures; an isolated business-model timeout remains a failed probe unless the backend state itself is unknown.

`adapter_contract` version **1.0.0** retains the declared capabilities, scheduled denominator, ordered success/failure/skip receipts and a digest. `mib verify-score` recomputes contract/status/denominator/causal eligibility as well as score aggregation. An honestly reported failed run can pass verification: verification is evidence consistency, not benchmark success or remote attestation. Public reports without raw runs remain `aggregates_only` and cannot verify lifecycle receipts.

## Memory-only HTTP protocol

Protocol: `mib-memory-backend/0.1`. Prefix: `/mib-memory/v0.1`. Operations:

| Operation | Request body | Required result |
| --- | --- | --- |
| describe (GET) | none | protocol, implementation name/version, nonempty identity, explicit capabilities |
| reset | `{mode:"fresh",seed,virtual_time}` | `accepted:true` |
| observe | `{observation: Observation}` | `accepted:true`, Formation completed |
| retrieve | `{query,limit_chars}` | `{items:[{id,content}],truncated}` |
| maintain | `{budget}` | `accepted:true`, Maintenance completed |
| session_boundary | `{}` | `accepted:true`, transient state cleared |
| close | `{reason:"run_complete"}` | `closed:true` |

The POST envelope carries `{mib:"0.1",protocol,run_id,request_id,operation,virtual_time,body}`. Replies must echo `mib`, `protocol`, `run_id`, and `request_id`, with `status:"ok"` and `body`, or `status:"error"` and `error`. GET describe only echoes protocol identity. Required backend capabilities are `observe`, `retrieve`, `maintenance`, `session_boundary`, `virtual_time`, and `run_isolation`.

Each backend run receives a fresh opaque ID, separate from the evaluator agent run and any integrated-agent run. A new backend instance is created for every full/ablation/repetition. The HTTP client does not retry uncertain mutations. Successful operations carry `cost_scope:"cumulative_run"` and `costs:{receipts,unreported_stages,accounting_complete}`. A failed response may retain a cost snapshot in `extensions`. Costs are captured only when correlation matches. Last snapshots are used once per run; they are never summed across operations. Missing counters remain null or absent, and the combined report always keeps `total_cost:null`/`accounting_complete:false` because provider retries and pricing are not generally observable.

`retrieve` is strictly bounded: the backend must respect the requested content limit, and the evaluator additionally bounds rendered context including item prefixes. A failed or malformed retrieval cannot become an empty memory result. In the Brain integration, these items are Recall summaries. Their IDs identify return receipts, not source graph elements or citations. Recall must not invoke business tools or form the retrieval question as new experience.

## Fixed business harness

`mib-memory-backend-benchmark` compares `B0` (NullBackend) with `candidate` (HTTP). Both use the same stateless business model client, system and reasoning prompts, tool definitions from the same materialized scenarios, sampling/paired seeds, parsing policy, task budgets and memory character limit. Only memory operations and returned context differ. Fairness also requires a successful A–B–A identical-output preflight under deterministic or seeded decoding; matching response digests are checked rather than trusting a passed flag. This finite check is evidence of consistency, not proof that an arbitrary remote model service has no hidden state. Backend labels and experiment oracle/score/support annotations are not delivered to the model or memory service.

Current-task actions and actual tool replies remain in evaluator transient state until the task finishes. At completion the lived trajectory is delivered through ordinary backend observations. B0 discards it. A session boundary clears active goal, tools, task transcript and response caches while preserving the backend's persistent memory. Ordinary observations, including public feedback, are delivered directly; hidden evaluators and aggregate scores are never converted into feedback.

Brain can use additional Formation, Recall and Maintenance models. Fixing the business model does not equalize that internal work, latency or cost. The outer `MIBMemoryBackendReport` **0.2.0** includes two standard Track A reports, a frozen experiment lock, business invocation fingerprints, backend operation/cost receipts, the alternating paired schedule, and a recomputed fairness audit. It is a development report and does not grant empirical calibration/admission or claim a memory advantage. The lock binds source, schema/profile/templates, backend identity, business model, prompts, decoding and budgets. Verifiers compare observed model/prompt/decoding fingerprints with the lock and check lifecycle/cost/retrieval/schedule evidence. Digests detect inconsistent edits; they do not authenticate a fabricated report. Signed evaluation-service attestation remains separate.

## Commands

The new entry point takes the existing same-model path/model configuration, plus:

```json
{
  "agent": {
    "system_prompt": "../../prompts/same-model-agent-v0.1.txt",
    "reasoning_policy": "../../prompts/reasoning-policy-v0.1.txt",
    "max_memory_chars": 32000,
    "parse_retries": 1,
    "observe_decisions": false,
    "maintenance_decisions": false
  },
  "memory_backend": {"base_url":"http://127.0.0.1:18043","timeout_seconds":120},
  "execution": {"instance_seeds":[101],"repetitions":1,"include_ablations":true}
}
```

The configuration also requires `id`, `pack`, `profile`, `scenario_schema`, and `model`, as in `examples/same-model/same-model-experiment.dev.json`. Agent options must be common to both arms; per-condition character limits are rejected. Set observation/maintenance business decisions when required by the chosen profile. `max_memory_chars` defaults to 32768. Remote backends require `allow_remote_http:true` and HTTPS. Tokens use `api_key_env`; token values are not written into locks.

```bash
mib-memory-backend-benchmark experiment.json --output-json backend-report.json
mib verify-score backend-report.json
```

Without installation, use `PYTHONPATH=src python -m mib_runner.backend_benchmark` and `PYTHONPATH=src python -m mib_runner.cli verify-score`. The outer report is not a plain `MIBReport`, so do not pass `--report-schema schemas/mib-report.schema.json` for it. Its two child reports use that schema. The backend command exits 3 when report verification or fairness fails and still writes the report.

The public integrated-agent CLI now directly accepts a standard submission JSON:

```bash
mib benchmark scenarios/dev --profile profiles/MIB-Core-0.1-Dev-M3.json \
  --schema schemas/mib-scenario.schema.json --report-schema schemas/mib-report.schema.json \
  --submission bot-submission.json --seeds 101 --repetitions 1 \
  --bootstrap-resamples 0 --output-report bot-report.json
mib verify-score bot-report.json
```

`bot-submission.json` contains `{ "id":"anda-bot", "transport":"http", "base_url":"http://127.0.0.1:18043", "timeout_seconds":120 }`. `--agent` and `--submission` are mutually exclusive. Remote HTTP requires `--allow-remote-http` and HTTPS; stdio retains the existing strict sandbox unless explicitly using the development flag `--allow-degraded-sandbox`. Integrated HTTP costs, including respond/act/close and correlated error extensions, are retained in `adapter_contract.reported_cost_snapshots` and `reported_costs_last`. Missing cost scope is unknown, not a delta or permission to sum.

Generated backend experiments now share Core Program identities and complete rung validation. The lock freezes every episode/repetition and verification rejects missing schedule units. Public completed dialogues and spontaneous-output receipts are formation inputs, with their original provenance. A common `observe_decision_types` router and final rendered-context cap apply to both arms. See [the resolution ledger](MIB-v0.4-Review-Resolution.md).
