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

from mib_runner.sandbox import _namespace_supported

BASE = Path(__file__).resolve().parents[1]

SCHEMAS = BASE / "schemas"
SCENARIO_SCHEMA_PATH = SCHEMAS / "mib-scenario.schema.json"
REPORT_SCHEMA_PATH = SCHEMAS / "mib-report.schema.json"

DEV_PACK = BASE / "scenarios" / "dev"
# Transfer diagnostic Templates live outside scenarios/dev/ on purpose: the
# MIB-Core-0.1-Dev-M3 pack must stay exactly its 24 Templates so that installing
# the transfer extension cannot move a MIB-Core score.
TRANSFER_PACK = BASE / "scenarios" / "transfer"
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

# The submission sandbox needs usable Linux user/mount/network namespaces (via
# `unshare`), not merely a Linux kernel. Hosted runners and containers can disable
# those namespaces, so gate integration tests on the same runtime probe used by
# the sandbox itself.
SANDBOX_AVAILABLE = _namespace_supported()
SANDBOX_REASON = (
    "submission sandbox requires usable Linux user/mount/network namespaces; "
    "unavailable or disabled on " + sys.platform
)


def slice_files(families: tuple[str, ...]) -> list[Path]:
    """Template files belonging to the given Scenario families."""
    return sorted(p for family in families for p in (DEV_PACK / family).rglob("MIB-*.json"))
