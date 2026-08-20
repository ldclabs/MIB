#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PACK="${1:-${MIB_OFFICIAL_PACK:-$ROOT/private/MIB-v0.1-Official-Canonical-Pack-r2}}"

export PYTHONPATH="$ROOT/src${PYTHONPATH:+:$PYTHONPATH}"
python -m mib_runner.calibration_cli \
  "$PACK" \
  --schema "$ROOT/schemas/mib-scenario.schema.json" \
  --profile "$ROOT/profiles/MIB-Core-0.1.json" \
  --seeds 101,202,303,404 \
  --repetitions 1 \
  --bootstrap-resamples 2000 \
  --causal-baseline B3 \
  --causal-seeds 101,202,303,404 \
  --causal-repetitions 1 \
  --output-json "$ROOT/examples/calibration/MIB-v0.1-reference-calibration.json" \
  --output-md "$ROOT/examples/calibration/MIB-v0.1-reference-calibration.md" \
  --output-csv "$ROOT/examples/calibration/MIB-v0.1-reference-calibration.csv"
