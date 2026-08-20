# MIB Leaderboard / Evaluation Service

**Version:** 0.5.0  
**Status:** Reference service prototype

## 1. Purpose

The evaluation service wraps the hidden evaluator in a persistent service with:

```text
Submission Registry
        ↓
Evaluation Cycle Registry
        ↓
Signed Evaluation Job
        ↓
Backend-routed Worker Queue
        ↓
Hidden Evaluation
        ↓
Signed Result Attestation
        ↓
Leaderboard Database
        ↓
Paired System Comparison
```

The service is intentionally separate from memory-system internals. A submission still participates only through the MIB Agent Adapter.

## 2. Persistent Objects

The SQLite reference database stores four primary object classes:

```text
Submission
Cycle
Job
Result
```

### Submission

A Submission binds a stable submission ID to:

```text
Agent Adapter spec
spec digest
display name
owner
track
status
optional Adapter descriptor
```

The source submission spec is re-digested before execution. A participant cannot enqueue one artifact and silently replace it before the worker starts.

### Evaluation Cycle

A Cycle binds:

```text
cycle ID
Profile
Private Evaluation Store
store digest
profile digest
public-safe evaluation manifest
active / retired state
```

Only results produced under the same cycle are directly ranked together.

Activating a new cycle retires the previous active cycle for the same Profile.

### Evaluation Job

A Job is not merely a mutable queue row. At enqueue time the service creates an immutable manifest containing:

```text
job ID
submission ID
submission spec digest
cycle ID
Profile ID
private store digest
Profile digest
Scenario schema digest
Report schema digest
execution backend
Runner version
creation time
nonce
```

The manifest is signed with a dedicated Ed25519 Job signing key.

The worker verifies the signature and every bound artifact digest before hidden evaluation begins.

### Result

A successful Result stores:

```text
score
confidence interval
Internal Report path + digest
Public Report path + digest
Service Result Attestation
Ed25519 signature
```

## 3. Key Separation

The service derives separate cryptographic material from one service root secret:

```text
root secret
   ├── HMAC evaluation seed key
   ├── HMAC public-redaction key
   ├── Ed25519 Job signing key
   └── Ed25519 Result signing key
```

The root secret is provided by environment variable and is never written to the database or reports.

Production deployments SHOULD use a KMS/HSM or equivalent secret manager rather than a process environment variable.

## 4. Publicly Verifiable Signatures

Ed25519 is used for public verification rather than service-local integrity only.

A signature envelope contains:

```json
{
  "scheme": "ed25519",
  "context": "mib-service-result-attestation/v1",
  "payload_digest": "sha256:...",
  "signature": "...",
  "public_key": "...",
  "key_id": "ed25519:..."
}
```

Anyone can verify the mathematical signature without the service secret.

Authenticity still requires pinning the official MIB Evaluation Service public key or `key_id` through a trusted channel such as the official repository/domain.

## 5. Service Attestation, Not Hardware Attestation

The current Result object is explicitly:

```text
service_attestation
```

It means:

> The configured MIB Evaluation Service cryptographically asserts that this Result came from the signed Job and these Report digests.

It does **not** mean:

```text
hardware attestation
TEE attestation
confidential-computing proof
microVM measurement proof
```

Future execution backends can add those proofs to `backend_evidence` without changing the top-level Result model.

## 6. Execution Backend Routing

Job manifests currently recognize:

```text
local_namespace
oci_command
microvm_command
```

The included reference worker implements:

```text
local_namespace
```

using the submission sandbox.

The queue is backend-routed: a worker claims only jobs addressed to its backend. This allows future OCI or microVM workers to use the same registry/database/job/result protocol.

The current environment does not include Docker/Podman/Firecracker, so the package does not claim that OCI or microVM execution has been validated.

## 7. Persistent stdio Agent Process

Spawning one stdio process per condition creates unnecessary startup overhead in a service.

A persistent stdio transport mode is therefore available:

```text
one sandboxed Agent Host process per evaluation Job
        ↓
multiple isolated run_id namespaces
        ↓
fresh reset per Full/Ablation condition
```

This preserves cognitive isolation while avoiding repeated process startup.

The process is terminated after the complete Pack evaluation.

## 8. Worker Crash Recovery

A worker claims:

```text
queued → running
```

The service includes an administrative recovery operation:

```text
recover-running
```

which requeues jobs left in `running` state after a worker crash.

This is intentionally a prototype mechanism. A distributed production service SHOULD replace it with:

```text
lease expiry
worker heartbeat
attempt count
idempotent result commit
```

## 9. Hidden Evaluation Path

```text
Signed Job
   ↓ verify signature
verify Submission digest
verify Store digest
verify Profile digest
   ↓
HMAC-secret Scenario instances
   ↓
External Agent in sandbox
   ↓
Full / Ablation conditions
   ↓
Template / Dimension aggregation
   ↓
Bootstrap statistics
   ↓
Internal Report
   ↓
Public redaction
   ↓
verify-score
```

A Result is not committed unless the redacted Public Report can be score-verified.

## 10. Result Attestation

The signed Result Attestation binds:

```text
Result ID
Job ID
Job Manifest digest
Submission ID
Cycle ID
Profile ID
MIB Score
Public Report digest
Internal Report digest
execution backend
backend evidence
start/completion times
```

Changing either Report after evaluation invalidates verification.

## 11. Leaderboard Semantics

The reference leaderboard selects:

> the most recent successful Result for each Submission in one evaluation Cycle.

Then ranks by:

```text
MIB Score descending
```

Each entry also includes:

```text
confidence interval
Result ID
Public Report
Result Attestation signature
```

Different cycles are not silently mixed.

## 12. Paired System Comparison

Ranking and statistical distinguishability are different questions.

When two systems were evaluated on the same hidden cycle, their public reports retain matching opaque Scenario Instance aliases.

The service performs a paired hierarchical bootstrap over:

```text
Template
  ↓
paired Instance
```

while using the same hidden Instance on both sides.

Output includes:

```text
MIB Score delta
paired 95% CI
paired Template count
paired Instance count
Dimension deltas
statistically distinguishable flag
```

The public-report comparison cannot resample raw repetitions because public redaction intentionally removes per-run evidence. It therefore operates on the aggregate evidence that remains publicly auditable.

## 13. HTTP Service API

Reference endpoints:

```text
GET  /health
GET  /submissions
GET  /cycles
GET  /jobs
GET  /jobs/{job_id}
GET  /leaderboard

POST /submissions
POST /jobs
POST /worker/once
POST /compare
```

The reference API is intended for localhost/development infrastructure. It does not yet implement production authentication/authorization, rate limiting, multi-tenant isolation, or remote artifact upload.

## 14. CLI

```bash
mib-service init

mib-service register-submission submission.json

mib-service register-cycle cycle-2026-08 \
  --store /private/mib-eval-store \
  --profile MIB-Core-0.1.json \
  --activate

mib-service enqueue my-agent
mib-service worker-once
mib-service leaderboard

mib-service verify-result result_xxx

mib-service compare result_A result_B \
  --resamples 5000
```

Public verification requires no service secret:

```bash
mib-service verify-attestation-file \
  result-attestation.json \
  --public-report public.report.json \
  --expected-key-id ed25519:...
```

## 15. Trust Chain

```text
Trusted MIB Service public key
        ↓
Signed Job Manifest
        ↓
immutable Submission / Store / Profile digests
        ↓
Hidden Evaluation Cycle
        ↓
Sandboxed Agent execution
        ↓
score-verifiable Public Report
        ↓
Report SHA-256 digest
        ↓
Signed Result Attestation
        ↓
Leaderboard entry
```

The trust chain does not prove that benchmark maintainers selected perfect Scenarios. It proves which declared benchmark artifacts and service identity produced a published Result.

## 16. Production Gaps

The reference service deliberately leaves several production concerns for the next stage:

```text
authenticated API / accounts
artifact upload/object storage
KMS/HSM key custody
worker leases + retries
OCI backend implementation
microVM backend implementation
network policy enforcement for HTTP submissions
multi-node queue
rate limiting
submission quotas
signed canonical Scenario Pack releases
public key rotation policy
leaderboard web UI
```

These are operational hardening tasks rather than changes to the MIB cognitive model.
