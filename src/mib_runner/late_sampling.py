from __future__ import annotations

import copy
import hashlib
import json
from typing import Any


class ProbeSamplingError(ValueError):
    pass


def _stable_index(*, scenario: dict[str, Any], probe_id: str, repetition: int, count: int) -> int:
    if count <= 0:
        raise ProbeSamplingError("probe variant list is empty")
    inst = scenario.get("instantiation") or {}
    # The instance seed may itself be an opaque HMAC alias for hidden evaluation.
    seed = inst.get("seed", "instance")
    material = f"mib-probe-v1|{scenario.get('id')}|{seed}|{repetition}|{probe_id}".encode("utf-8")
    digest = hashlib.sha256(material).digest()
    return int.from_bytes(digest[:8], "big") % count


def sample_probe_for_delivery(
    *, scenario: dict[str, Any], probe: dict[str, Any], repetition: int
) -> tuple[dict[str, Any], str | None]:
    """Late-sample only Agent-visible Probe input.

    Oracle/evaluator/scoring fields are never sampled here.  This keeps the
    semantic task fixed while allowing wording/context variants to be chosen
    only when the Probe actually fires.

    Probe extension format:

      extensions:
        mib.probe_sampling:
          input_variants:
            - {content: "..."}
            - {content: "..."}

    The selected variant is deterministic for scenario instance + repetition +
    probe_id and deliberately independent of causal condition, so Full and
    Ablation runs receive the exact same future Probe.
    """
    policy = ((scenario.get("leakage") or {}).get("probe_sampling") or "fixed")
    if policy not in {"late", "hidden_late"}:
        return copy.deepcopy(probe), None

    ext = (probe.get("extensions") or {}).get("mib.probe_sampling") or {}
    variants = ext.get("input_variants") or []
    if not variants:
        # A late policy is still valid without wording variants: the Probe is
        # not delivered until its trigger.  Returning a digest lets causal-pair
        # validation prove that the same current task was used.
        p = copy.deepcopy(probe)
        digest = hashlib.sha256(
            json.dumps(p.get("input") or {}, sort_keys=True, ensure_ascii=False).encode("utf-8")
        ).hexdigest()
        return p, digest

    index = _stable_index(scenario=scenario, probe_id=probe["id"], repetition=repetition, count=len(variants))
    selected = copy.deepcopy(variants[index])
    if not isinstance(selected, dict):
        raise ProbeSamplingError(f"probe {probe['id']} input variant must be an object")

    p = copy.deepcopy(probe)
    base_input = copy.deepcopy(p.get("input") or {})
    base_input.update(selected)
    p["input"] = base_input

    # Do not expose the index; only a digest is recorded in runner-private trace.
    digest = hashlib.sha256(
        json.dumps(base_input, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()
    return p, digest
