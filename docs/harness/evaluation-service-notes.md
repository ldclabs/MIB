# MIB Evaluation Service

**Scope:** Leaderboard / Evaluation Service

The evaluation service wraps the hidden evaluator in a persistent service that registers external Agents, freezes and signs evaluation jobs, executes hidden cycles, attests results, maintains a leaderboard, and compares systems with paired statistics.

## Architecture

```text
Submission Registry
        ↓
Active Hidden Evaluation Cycle
        ↓
Ed25519-signed Job Manifest
        ↓
Backend-routed Worker Queue
        ↓
Sandboxed external Agent
        ↓
MIB Hidden Evaluation
        ↓
Internal + Public Reports
        ↓
Ed25519 Result Attestation
        ↓
SQLite Leaderboard
        ↓
Paired System Comparison
```

The Runner, pack executor, and hidden evaluator are included and regression-tested.

## Capabilities

- SQLite Submission / Cycle / Job / Result registry.
- Evaluation-cycle activation and isolation.
- Immutable Job Manifest bound to Submission, Store, Profile, Scenario schema, and Report schema digests.
- Ed25519 Job Manifest signatures.
- HMAC-secret hidden Instance generation remains evaluator-only.
- Persistent stdio Agent process per Job, with fresh `run_id` isolation per condition.
- Backend-routed workers (`local_namespace` implemented; OCI/microVM IDs reserved for dedicated workers).
- Public/Internal Report artifact store.
- Ed25519 service Result Attestation.
- Public attestation verification without access to evaluator secrets.
- Cycle-scoped leaderboard.
- Paired hierarchical system comparison.
- Local HTTP service API.
- Worker crash recovery for the reference single-node queue.

See [MIB-Leaderboard-Evaluation-Service.md](MIB-Leaderboard-Evaluation-Service.md) for the trust and service model.

## Install

```bash
python -m pip install --no-build-isolation -e .
```

Dependencies:

```text
jsonschema >= 4.18
cryptography >= 46
```

## Configure

The included development config is:

```text
service/service-config.json
```

Provide the root service secret through the environment:

```bash
export MIB_SERVICE_ROOT_SECRET='use-a-real-secret-manager-in-production'
```

The secret is used to derive independent keys for hidden Instance generation, redaction, Job signing, and Result signing. It is never persisted by the reference service.

## Initialize and inspect service identity

```bash
mib-service --config service/service-config.json init
```

The output contains public Ed25519 keys and `key_id` values that should be pinned through a trusted MIB release channel.

## Register submissions

```bash
mib-service --config service/service-config.json register-submission \
  examples/submissions/reference-stdio.json \
  --name 'Reference Fixture'
```

A second deliberately memoryless fixture is included:

```text
examples/submissions/no-memory-stdio.json
```

It exists only to validate leaderboard discrimination.

## Register and activate a hidden cycle

```bash
mib-service --config service/service-config.json register-cycle \
  cycle-m5-demo-001 \
  --store private-eval-store-demo \
  --profile profiles/MIB-Core-0.1-Hidden-M4-Demo.json \
  --activate
```

The included store is an infrastructure fixture, not the canonical future MIB leaderboard Hidden Eval set.

## Enqueue and execute

```bash
mib-service --config service/service-config.json enqueue mib-reference-fixture-stdio
mib-service --config service/service-config.json worker-once
```

A Job is signed at enqueue time. The worker refuses to run it if the Submission, private Store, Profile, or signature no longer matches the frozen Manifest.

## Leaderboard

```bash
mib-service --config service/service-config.json leaderboard
```

The demo run included in this package produces two entries:

```text
1. Reference Fixture    100.0
2. No-Memory Fixture     13.33
```

These are infrastructure fixtures, not published MIB baselines.

## Paired comparison

```bash
mib-service --config service/service-config.json compare \
  result_A result_B \
  --resamples 5000
```

Because both systems run the same hidden cycle, the service pairs the same opaque Scenario Instances before bootstrapping.

## Verify a service result

Service-side verification:

```bash
mib-service --config service/service-config.json verify-result result_xxx
```

Public verification, with no evaluator secret:

```bash
mib-service verify-attestation-file \
  service/artifacts/job_xxx/result-attestation.json \
  --public-report service/artifacts/job_xxx/public.report.json \
  --expected-key-id ed25519:...
```

## HTTP API

```bash
mib-service --config service/service-config.json serve \
  --host 127.0.0.1 \
  --port 8088
```

Reference endpoints:

```text
GET  /health
GET  /submissions
GET  /cycles
GET  /jobs
GET  /leaderboard
POST /submissions
POST /jobs
POST /worker/once
POST /compare
```

This API is a localhost/development service and does not yet include production auth or multi-tenant controls.

## Execution backend status

The service recognizes backend routing IDs:

```text
local_namespace   implemented + tested
oci_command       routing contract only
microvm_command   routing contract only
```

Docker/Podman/Firecracker are not installed in the current reference environment, so this package does not claim OCI or microVM execution validation.

## Validation

The package includes the full regression suite:

```bash
PYTHONPATH=src pytest -q
```

See:

```text
examples/validation/harness-validation.json
```

for the final executed validation summary.

## Important security boundary

The Result signature is a **service attestation**, not hardware attestation. It proves that the pinned MIB service signing key signed a Result bound to declared artifact digests. Future OCI/microVM/TEE backends may add platform attestations under `backend_evidence`.

## Demo snapshot

The package includes a completed local service snapshot under `service/state/` and `service/artifacts/` solely for inspection. It uses no embedded service root secret. To start a fresh service, remove those two directories (or point the config at new paths), set `MIB_SERVICE_ROOT_SECRET`, and run `mib-service init`.
