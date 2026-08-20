"""Canonical filesystem locations used by the MIB test-suite.

The 24 public dev Templates live in exactly one place (``scenarios/dev/``).
Milestone slices are expressed as Scenario-family subsets of that pack instead
of as duplicated Template copies, so a Template body is never stored twice.

Evaluator-only content (the official Hidden Eval / Private Holdout pack) is not
part of this repository.  Tests that need it resolve it through
``MIB_OFFICIAL_PACK`` and skip when it is absent.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]

SCHEMAS = BASE / "schemas"
SCENARIO_SCHEMA_PATH = SCHEMAS / "mib-scenario.schema.json"
REPORT_SCHEMA_PATH = SCHEMAS / "mib-report.schema.json"

DEV_PACK = BASE / "scenarios" / "dev"
PROFILES = BASE / "profiles"
EXAMPLES = BASE / "examples"
PRIVATE_EVAL_STORE_DEMO = BASE / "fixtures" / "private-eval-store-demo"

# Scenario families delivered by each public dev slice.
SLICE_1 = ("recall", "time", "epistemic")
SLICE_2 = ("experience", "skill", "causal")
SLICE_3 = ("cross",)

# Evaluator-only pack, absent from the participant-visible repository.
OFFICIAL_PACK = Path(
    os.environ.get(
        "MIB_OFFICIAL_PACK",
        BASE / "private" / "MIB-v0.1-Official-Canonical-Pack-r2",
    )
)

# The submission sandbox needs Linux user/mount/network namespaces (via `unshare`)
# and a workable RLIMIT_AS.  Neither holds on macOS, where setting RLIMIT_AS kills
# the child before it can exec.  Tests that spawn sandboxed submissions are gated
# on this rather than failing on unsupported platforms.
SANDBOX_AVAILABLE = sys.platform.startswith("linux")
SANDBOX_REASON = "submission sandbox requires Linux namespaces; unavailable on " + sys.platform


def slice_files(families: tuple[str, ...]) -> list[Path]:
    """Template files belonging to the given Scenario families."""
    return sorted(p for family in families for p in (DEV_PACK / family).rglob("MIB-*.json"))
