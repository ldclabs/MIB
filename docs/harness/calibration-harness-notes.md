# MIB v0.1 Calibration Harness + Baseline Suite

This package adds evaluator-side empirical calibration machinery for the 36 official `MIB-Core-0.1` Hidden Eval / Private Holdout Templates.

## What it adds

```text
B0 — No Memory
B1 — Full Visible History Fixture
B2 — Simple Lexical Retrieval
B3 — Structured / Agentic Memory
        ↓
Template Calibration Cards
        ↓
FC / NM / MDI
MGC_B2 / MGC_B3
Baseline separation
Causal sensitivity
Irrelevant stability
        ↓
accept / revise / redesign queue
```

The core implementation is:

```text
src/mib_runner/calibration.py
src/mib_runner/calibration_baselines.py
src/mib_runner/calibration_cli.py
```

## Important status boundary

The included B0–B3 implementations are **deterministic reference fixtures**.

They are useful for:

- validating calibration mechanics;
- detecting obvious No-Memory leakage;
- testing whether simple retrieval is enough;
- testing replay-ablation sensitivity;
- producing a concrete Scenario revision queue.

They are **not sufficient for leaderboard-release calibration** because B1 is not yet the fixed external base model used by Track A.

The generated report therefore intentionally says:

```text
release_calibration_eligible = false
```

## Official private pack

The harness does not duplicate the evaluator-only official Template bodies.

Run it against:

```text
MIB-v0.1-Official-Canonical-Pack-PRIVATE/
```

Do not publish that private pack.

## Run the reference calibration

```bash
./run-reference-calibration.sh /path/to/MIB-v0.1-Official-Canonical-Pack-PRIVATE
```

or:

```bash
PYTHONPATH=src python -m mib_runner.calibration_cli \
  /path/to/private-pack \
  --schema schemas/mib-scenario.schema.json \
  --profile profiles/MIB-Core-0.1.json \
  --seeds 101,202,303,404 \
  --bootstrap-resamples 2000 \
  --output-json examples/calibration/calibration.json \
  --output-md examples/calibration/calibration.md \
  --output-csv examples/calibration/calibration.csv
```

## Replace fixture B1 with a real fixed-model Full Context Agent

```bash
mib-calibrate ... \
  --baseline-override B1=my_eval_package:FixedModelFullContextAgent
```

The replacement Agent uses the ordinary MIB Agent Adapter boundary and must truthfully declare its calibration role.

## Current reference run

The included reference run used:

```text
36 official Templates
4 materialized instances / Template
4 full-condition baselines
1 B3 causal replay pass
2000 bootstrap resamples / Template baseline statistic
```

Executed condition runs:

```text
B0–B3 full runs      576
B3 causal runs       684
Total               1260
```

Current fixture result:

```text
B1 solvability                         36 / 36
FC / NM / MDI provisional pass        29 / 36
Full gate incl. causal sensitivity    27 / 36
Irrelevant stability                  36 / 36
```

See:

```text
examples/calibration/MIB-v0.1-reference-calibration.json
examples/calibration/MIB-v0.1-reference-calibration.md
MIB-v0.1-Calibration-Findings.md
```

## Tests

```bash
PYTHONPATH=src pytest -q
```

Expected for this snapshot:

```text
32 passed
```
