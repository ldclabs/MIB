from __future__ import annotations

import copy
import hashlib
import json
import random
import re
from typing import Any

from . import __version__

_PLACEHOLDER = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_.-]*)\}")


class MaterializationError(ValueError):
    pass


def _sample_parameter(spec: dict[str, Any], rng: random.Random) -> Any:
    source = spec["source"]
    if source == "fixed":
        return spec.get("value")
    if source == "choice":
        choices = spec.get("choices") or []
        if not choices:
            raise MaterializationError(f"choice parameter {spec['name']} has no choices")
        return rng.choice(choices)
    if source == "integer_range":
        return rng.randint(int(spec["minimum"]), int(spec["maximum"]))
    if source == "number_range":
        lo, hi = float(spec["minimum"]), float(spec["maximum"])
        return rng.uniform(lo, hi)
    raise MaterializationError(
        f"reference materializer does not support source={source!r}; "
        "use a materialized instance or extend the generator registry"
    )


def _substitute(value: Any, params: dict[str, Any]) -> Any:
    if isinstance(value, str):
        matches = list(_PLACEHOLDER.finditer(value))
        # Preserve non-string JSON type when the entire field is one placeholder.
        if len(matches) == 1 and matches[0].span() == (0, len(value)):
            key = matches[0].group(1)
            if key not in params:
                raise MaterializationError(f"undeclared parameter {key}")
            return copy.deepcopy(params[key])

        def repl(m: re.Match[str]) -> str:
            key = m.group(1)
            if key not in params:
                raise MaterializationError(f"undeclared parameter {key}")
            return str(params[key])

        return _PLACEHOLDER.sub(repl, value)
    if isinstance(value, list):
        return [_substitute(x, params) for x in value]
    if isinstance(value, dict):
        return {k: _substitute(v, params) for k, v in value.items()}
    return value


def materialize(scenario: dict[str, Any], seed: int | str = 0) -> dict[str, Any]:
    """Materialize a public Scenario Template. Instances are returned unchanged."""
    if "template" not in scenario:
        return copy.deepcopy(scenario)

    rng = random.Random(str(seed))
    params: dict[str, Any] = {}
    for spec in scenario["template"].get("parameters", []):
        params[spec["name"]] = _sample_parameter(spec, rng)

    instance = _substitute(copy.deepcopy(scenario), params)
    instance.pop("template", None)
    digest = hashlib.sha256(
        json.dumps(params, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    instance["instantiation"] = {
        "template_id": scenario["id"],
        "template_version": scenario["version"],
        "seed": seed,
        "parameter_digest": digest,
        "generator_version": f"mib-reference-runner-materializer/{__version__}",
    }
    return instance
