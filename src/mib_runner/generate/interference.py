"""Generated interference on the distance ladder (MIB-Specification §4.5, §8).

Three confusability classes, so that retention can be decomposed by the *type*
of interference rather than by white-box hooks:

``neutral``     unrelated notes — capacity pressure only
``similar``     the same attribute for other subjects — routing pressure
``confusable``  questions and hypotheticals about the target attribute with
                other values — the interrogation lane: mentions that assert nothing
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any

from .pools import ATTRIBUTES, NAMES, NEUTRAL_TEMPLATES, THINGS, WEATHER, WEEKDAYS, AttributeSpec
from .surface import realize

DEFAULT_MIX = {"neutral": 0.6, "similar": 0.25, "confusable": 0.15}


@dataclass
class InterferenceEvent:
    kind: str                       # neutral | similar | confusable
    content: str
    actor: str                      # actor id
    assertion: dict[str, Any] | None = None   # world-model registration for similar/confusable


def neutral_sentence(rng: random.Random) -> str:
    return rng.choice(NEUTRAL_TEMPLATES).format(
        thing=rng.choice(THINGS), weekday=rng.choice(WEEKDAYS), weather=rng.choice(WEATHER),
    )


def plan(
    rng: random.Random,
    count: int,
    *,
    subject_id: str,
    subject_name: str,
    spec: AttributeSpec,
    exclude_values: set[str],
    other_actors: list[tuple[str, str]],
    mix: dict[str, float] | None = None,
) -> list[InterferenceEvent]:
    """Plan ``count`` interference events for one target attribute.

    ``exclude_values`` are answer values that must not appear in interference,
    so a string-matching evaluator cannot reward a guess.
    """
    mix = mix or DEFAULT_MIX
    kinds = list(mix)
    weights = [mix[k] for k in kinds]
    pool_values = [v for v in spec.values if v not in exclude_values]
    out: list[InterferenceEvent] = []
    for _ in range(count):
        kind = rng.choices(kinds, weights=weights, k=1)[0]
        if kind == "similar" and other_actors and pool_values:
            actor_id, actor_name = rng.choice(other_actors)
            value = rng.choice(pool_values)
            text, _ = realize(spec, "state", value, subject_name=actor_name, first_person=True, rng=rng)
            out.append(InterferenceEvent("similar", text, actor_id, {
                "source": actor_id, "subject": actor_id, "attribute": spec.id, "value": value,
                "kind": "state", "truth_bearing": True,
            }))
        elif kind == "confusable" and pool_values:
            value = rng.choice(pool_values)
            mention_kind = rng.choice(["question", "hypothetical"])
            text, _ = realize(spec, mention_kind, value, subject_name=subject_name, first_person=True, rng=rng)
            out.append(InterferenceEvent("confusable", text, subject_id, {
                "source": subject_id, "subject": subject_id, "attribute": spec.id, "value": value,
                "kind": mention_kind, "truth_bearing": False,
            }))
        else:
            out.append(InterferenceEvent("neutral", neutral_sentence(rng), subject_id))
    return out


def other_actors(rng: random.Random, exclude_names: set[str], count: int = 3) -> list[tuple[str, str]]:
    names = [n for n in NAMES if n not in exclude_names]
    rng.shuffle(names)
    return [(n.lower(), n) for n in names[:count]]


def spec_for(attribute: str) -> AttributeSpec:
    return ATTRIBUTES[attribute]
