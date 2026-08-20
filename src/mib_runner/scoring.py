"""Shared scoring primitives.

Kept free of Runner/report imports so both the single-Scenario report path and
the pack aggregation path can use one implementation of each formula.
"""

from __future__ import annotations

import math
from typing import Any

CAUSAL_DIM = "causal_memory_impact"


def mean(values: list[float]) -> float:
    # fsum, not sum: aggregation runs over many small weighted terms and the
    # calibration and benchmark paths must agree to the last bit.
    return math.fsum(values) / len(values) if values else 0.0


def ablation_tolerances(scenario: dict[str, Any]) -> dict[str, float]:
    """Per-ablation tolerance declared by a Scenario, keyed by ablation id."""
    return {
        a["id"]: float(a.get("tolerance") or 0.0)
        for a in (scenario.get("ablations") or [])
        if a.get("id") is not None
    }


def tolerant_stability(delta: float, tolerance: float) -> float:
    """MIB-Scoring 58: ``IMS_tau = 1 - max(0, |F-I| - tau) / (1 - tau)``, clamped.

    Stochastic wobble below the Scenario-declared tolerance is not interference.
    """
    tolerance = min(max(float(tolerance), 0.0), 0.99)
    excess = max(0.0, abs(float(delta)) - tolerance)
    return max(0.0, min(1.0, 1.0 - excess / (1.0 - tolerance)))


def tolerant_harm_resistance(harm: float, tolerance: float) -> float:
    """MIB-Scoring 62: ``HRS_tau = 1 - max(0, C-H - tau) / (1 - tau)``, clamped."""
    tolerance = min(max(float(tolerance), 0.0), 0.99)
    excess = max(0.0, float(harm) - tolerance)
    return max(0.0, min(1.0, 1.0 - excess / (1.0 - tolerance)))
