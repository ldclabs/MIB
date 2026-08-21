"""Deterministic fixture Agents for the MIB-R Ledger Codes domain.

They are fixtures, not baselines.  Each one has a specific memory behaviour so
that the paired MIB-R conditions can be shown to measure what they claim:

    RuleLearningRealityAgent   forms conventions from verifier feedback and
                               applies them within their stated boundary
    NaiveRealityAgent          never retains anything across tasks
    OverGeneralizingRealityAgent  learns the standard-family convention and
                               applies it past its boundary

An Agent that has learned no convention covering a record's family answers
``unknown``.  That is the epistemically correct answer, and it is what makes
the unsupported-task control a neutrality measurement rather than a guess.
"""

from __future__ import annotations

import re
from typing import Any

from ..reality_domains.ledger_codes import (
    ABILITY_DROP_CK,
    ABILITY_LEGACY_MOD100,
    ABILITY_MOD97,
    ABILITY_NORMALIZE,
    LEGACY_FAMILY,
    MODULUS,
    PROVISIONAL_FAMILY,
    RULE_TEXT,
    STANDARD_FAMILY,
    UNKNOWN_ANSWER,
    base36_value,
)
from ..types import AgentOutput, Observation

_RECORD = re.compile(r"class\s+([A-Z])\s+\((\w+)\s+family\)", re.I)
_IDENTIFIER = re.compile(r"identifier\s+(.+?)\.\s", re.I)
_BATCH = re.compile(r"identifiers\s+(\S+)\s+and\s+(\S+)\s", re.I)
_SEPARATORS = re.compile(r"[^0-9A-Za-z]")

#: Text that establishes each convention, whether it arrives as reviewer
#: feedback during acquisition or as an evaluator-routed oracle artifact.
_RULE_CUES = {
    ABILITY_NORMALIZE: ("normalize the identifier", "uppercase it and"),
    ABILITY_MOD97: ("standard-family transfer codes use modulo 97", "reduce the identifier value modulo 97"),
    ABILITY_LEGACY_MOD100: ("legacy family keeps modulo 100",),
    ABILITY_DROP_CK: ("leading ck is a check marker",),
}

#: A plausible over-generalization injected by the wrong-ability condition.
_WRONG_CUE = "every record class, legacy classes included, uses the modulo 97"


class RuleLearningRealityAgent:
    """Forms conventions from feedback and respects their declared boundary."""

    fixture_name = "MIB-R Rule Learning Fixture"
    over_generalizes = False
    retains_experience = True

    def __init__(self) -> None:
        self.run_id = ""
        self.observations: list[Observation] = []
        self.seen_requests: set[tuple[str, str]] = set()

    def describe(self) -> dict[str, Any]:
        return {
            "protocol": "mib-agent/0.1",
            "implementation": {"name": self.fixture_name, "version": "0.1.0", "vendor": "MIB"},
            "track_support": ["integrated_agent"],
            "capabilities": {
                "observe": True, "respond": True, "act": False,
                "spontaneous_emissions": False, "maintenance": False,
                "runner_managed_tools": False, "structured_output": False,
                "virtual_time": False, "seedable": True,
            },
            "state": {"run_isolation": "hard", "observe_visibility": "read_after_write", "request_idempotency": True},
        }

    def reset(self, *, run_id: str, seed, virtual_time: str | None) -> dict[str, Any]:
        self.run_id = run_id
        self.observations = []
        self.seen_requests = set()
        return {"accepted": True}

    def observe(self, *, run_id: str, request_id: str, observation: Observation) -> dict[str, Any]:
        key = (run_id, request_id)
        if key in self.seen_requests:
            return {"accepted": True, "emissions": []}
        self.seen_requests.add(key)
        if self.retains_experience:
            self.observations.append(observation)
        return {"accepted": True, "emissions": []}

    def respond(self, *, run_id: str, request_id: str, interaction_id: str, input_data: dict[str, Any], virtual_time: str | None) -> AgentOutput:
        return AgentOutput(type="message", content=self._answer(str(input_data.get("content") or "")))

    # -- Internals --------------------------------------------------------

    def _memory(self) -> str:
        return "\n".join(o.content or "" for o in self.observations).casefold()

    def _known(self) -> set[str]:
        memory = self._memory()
        return {a for a, cues in _RULE_CUES.items() if any(c in memory for c in cues)}

    def _answer(self, prompt: str) -> str:
        record = _RECORD.search(prompt)
        if not record:
            return UNKNOWN_ANSWER
        record_class, family = record.group(1).upper(), record.group(2).casefold()
        if "how many records" in prompt.casefold():
            return UNKNOWN_ANSWER

        known = self._known()
        memory = self._memory()
        over_generalized = self.over_generalizes or (_WRONG_CUE in memory)

        if family == STANDARD_FAMILY:
            if ABILITY_MOD97 not in known:
                return UNKNOWN_ANSWER
            modulus = MODULUS[STANDARD_FAMILY]
        elif family == LEGACY_FAMILY:
            if over_generalized and ABILITY_MOD97 in known:
                # Fires the standard-family convention outside its boundary.
                modulus = MODULUS[STANDARD_FAMILY]
            elif ABILITY_LEGACY_MOD100 in known:
                modulus = MODULUS[LEGACY_FAMILY]
            else:
                return UNKNOWN_ANSWER
        else:
            # No learned convention covers a provisional family.
            return UNKNOWN_ANSWER

        batch = _BATCH.search(prompt)
        if batch:
            parts = [batch.group(1), batch.group(2)]
        else:
            identifier = _IDENTIFIER.search(prompt)
            if not identifier:
                return UNKNOWN_ANSWER
            parts = [identifier.group(1).strip()]

        total = 0
        for raw in parts:
            value = raw
            if ABILITY_NORMALIZE in known:
                value = _SEPARATORS.sub("", value).upper()
            if ABILITY_DROP_CK in known and value.upper().startswith("CK"):
                value = value[2:]
            total += base36_value(value)
        return f"{record_class}-{total % modulus:02d}"


class NaiveRealityAgent(RuleLearningRealityAgent):
    """Retains nothing across tasks, so no convention is ever available."""

    fixture_name = "MIB-R Naive Fixture"
    retains_experience = False


class OverGeneralizingRealityAgent(RuleLearningRealityAgent):
    """Learns the standard-family convention and fires it past its boundary."""

    fixture_name = "MIB-R Over-Generalizing Fixture"
    over_generalizes = True


__all__ = [
    "RuleLearningRealityAgent",
    "NaiveRealityAgent",
    "OverGeneralizingRealityAgent",
    "RULE_TEXT",
    "PROVISIONAL_FAMILY",
]
