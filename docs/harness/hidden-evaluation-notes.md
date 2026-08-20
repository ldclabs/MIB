# MIB Hidden Evaluation Infrastructure

**Scope:** Hidden evaluation infrastructure, late Probe sampling, external Agent transports, and submission isolation.

The hidden evaluation layer turns the pack executor into an evaluation service boundary that runs **external memory-enabled Agents** against evaluator-only Scenarios without revealing hidden benchmark content.

## Components

It comprises four major systems:

```text
Private Evaluation Store
        ↓
HMAC Hidden Instance Generator
        ↓
late / hidden_late Probe Sampling
        ↓
External Agent Adapter
   ├── stdio JSONL
   └── HTTP JSON
        ↓
Submission Sandbox
        ↓
Pack Execution / Ablations / Bootstrap
        ↓
Internal Report
        ↓
Public Redacted Report
        ↓
verify-score
```


## 1. Private Evaluation Store

Evaluator-only content lives outside participant-visible scenario directories.

Reference demo layout:

```text
private-eval-store-demo/
├── manifest.private.json
└── templates/
    ├── hidden/
    └── holdout/
```

Two visibility classes are supported:

```text
hidden_eval
    broad family may be disclosed publicly

private_holdout
    exact composition / generator / Oracle / Probe variants remain evaluator-only
```

`mib public-eval-manifest` derives a participant-safe manifest that does not expose private paths or holdout composition.

> The included private store is an **infrastructure fixture only**. It is not the future canonical MIB leaderboard Hidden Eval set.

## 2. Secret deterministic hidden instances

Hidden instances are generated from:

```text
HMAC-SHA256(
  evaluator_key,
  cycle_id + template_id + instance_index
)
```

The real generation seed never enters the Agent request or public report.

Reports receive only an opaque alias such as:

```text
hs_dcd0faa610141950
```

Properties:

```text
same evaluator key + cycle + Template + index
    → reproducible instance

different cycle
    → different hidden instances

participant cannot infer the generation seed
```

## 3. `late` / `hidden_late` Probe sampling

A Probe may declare evaluator-side Agent-visible input variants:

```json
{
  "extensions": {
    "mib.probe_sampling": {
      "input_variants": [
        {"content": "What is my current timezone?"},
        {"content": "Which timezone is current for me?"}
      ]
    }
  }
}
```

The Runner selects the future wording **only when the Probe fires**.

Selection is deterministic from:

```text
Scenario Instance
+ repetition
+ Probe ID
```

and deliberately excludes:

```text
causal condition
```

Therefore:

```text
Full
Relevant Ablation
Irrelevant Ablation
```

receive the same future Probe wording.

Causal pair validation checks the Probe-variant digest.

`hidden_late` means the variant set itself may be evaluator-only.

## 4. External stdio Agent Adapter

Reference transport:

```text
stdin  → one JSON request per line
stdout → one JSON response per line
stderr → diagnostics only
```

Supported operations:

```text
describe
reset
observe
respond
act
close
```

Example submission:

```json
{
  "id": "my-agent",
  "transport": "stdio",
  "command": ["python", "agent_server.py"]
}
```

Run a smoke test:

```bash
PYTHONPATH=src python -m mib_runner.cli agent-smoke-test \
  --submission examples/submissions/reference-stdio.json
```

## 5. External HTTP Agent Adapter

Reference endpoints:

```text
GET  /mib-agent/v0.1/describe
POST /mib-agent/v0.1/reset
POST /mib-agent/v0.1/observe
POST /mib-agent/v0.1/respond
POST /mib-agent/v0.1/act
POST /mib-agent/v0.1/close
```

Start the reference HTTP fixture:

```bash
python examples/agents/http_reference_agent.py --port 8765
```

Then:

```bash
PYTHONPATH=src python -m mib_runner.cli agent-smoke-test \
  --submission examples/submissions/reference-http.json
```

## 6. Submission sandbox

The local stdio sandbox now supports, on Linux hosts where unprivileged namespaces are available:

```text
user namespace
mount namespace
network namespace
resource limits
scrubbed environment
ephemeral working directory
staged submission code
private evaluator-path masking
process-group termination
```

For hidden evaluation, the private evaluation store path is automatically added to the filesystem hide list.

The reference implementation uses a private mount namespace and covers hidden evaluator directories with `tmpfs` before launching the submission.

The report records actual enforcement:

```json
{
  "submission_sandbox": {
    "transport": "stdio",
    "network_isolated": true,
    "filesystem_isolated": true,
    "warnings": []
  }
}
```

If namespace isolation is unavailable and policy is `disabled_best_effort`, execution explicitly reports a warning.

For hostile public submissions, hosted MIB should still prefer a hardened container or microVM runtime. The local sandbox is the **reference enforcement layer**, not a claim that one Python process launcher replaces production isolation.

## 7. Staging submission code

Because evaluator storage may be hidden from the subprocess mount namespace, code needed by the submission is first copied into an ephemeral working directory.

Example:

```json
{
  "stage": [
    {
      "source": "../stdio_reference_agent.py",
      "dest": "examples/agents/stdio_reference_agent.py"
    },
    {
      "source": "../../src",
      "dest": "src"
    }
  ],
  "command": [
    "python",
    "examples/agents/stdio_reference_agent.py"
  ]
}
```

The evaluator's private Scenario files are never staged.

## 8. Hidden evaluation CLI

```bash
export MIB_EVAL_KEY='replace-with-evaluator-secret'

PYTHONPATH=src python -m mib_runner.cli evaluate-hidden \
  private-eval-store-demo \
  --profile profiles/MIB-Core-0.1-Hidden-M4-Demo.json \
  --submission examples/submissions/reference-stdio.json \
  --schema schemas/mib-scenario.schema.json \
  --report-schema schemas/mib-report.schema.json \
  --cycle cycle-2026-08 \
  --bootstrap-resamples 200 \
  --output-internal internal-report.json \
  --output-public public-report.json \
  --card capability-card.md
```

Do not pass production evaluator secrets on a command line. Use `MIB_EVAL_KEY` or a hosted secret manager.

## 9. Internal vs public report

Internal report contains evaluator identifiers required for investigation.

Public report deliberately removes:

```text
raw Run / Probe records
secret instance seeds
Agent seeds
private Template IDs
ablation IDs
private file paths
```

It preserves:

```text
Scenario Instance aggregate scores
opaque public Template aliases
Dimension scores
causal aggregate metrics
coverage
bootstrap confidence intervals
sandbox enforcement facts
```

This is sufficient for:

```bash
mib verify-score public-report.json
```

without exposing hidden Probe structure.

## 10. Demo hidden evaluation result

The bundled external stdio Reference Fixture Agent was evaluated through the complete hidden evaluation path:

```text
6 evaluator-only Templates
12 HMAC-derived hidden Instances
40 Full/Ablation condition runs
200 hierarchical bootstrap resamples
100% profile coverage
```

The fixture scores 100/100 because it is a **Runner correctness fixture**, not a real memory-system baseline.

See:

```text
examples/service/MIB-M4-Hidden-Demo.internal.report.json
examples/service/MIB-M4-Hidden-Demo.public.report.json
examples/service/MIB-M4-Hidden-Demo-Capability-Card.md
examples/service/MIB-M4-Hidden-Demo.verify-score.json
```

## 11. Machine-readable configuration schemas

```text
schemas/mib-submission.schema.json
schemas/mib-private-eval-store.schema.json
schemas/mib-public-eval-manifest.schema.json
schemas/mib-scenario.schema.json
schemas/mib-report.schema.json
```

## 12. CLI summary

```text
mib validate
mib run
mib run-pack
mib benchmark
mib capability-card
mib verify-score

mib public-eval-manifest
mib agent-smoke-test
mib evaluate-hidden
```

## 13. Security / leakage boundary

The evaluated Agent receives only:

```text
Agent-visible Observation
Virtual Time
Probe input / goal
visible tool schemas
visible constraints
```

It never receives:

```text
private Template
Oracle
Evaluator
Dimension weights
ablation labels
relevance labels
hidden ground truth
secret generation seed
private Probe variant set
```

The Runner remains the sole owner of benchmark World truth and scoring state.

## 14. Validation

Current package regression tests cover:

```text
Runner and pack regression
Hidden store validation
HMAC generation determinism
cycle seed rotation
public manifest redaction
hidden_late Probe pairing
stdio Agent protocol
HTTP Agent protocol
namespace filesystem hiding
network namespace isolation
external-process hidden evaluation
public report redaction
report schema validation
score recomputation
```

See `examples/validation/harness-validation.json`.
