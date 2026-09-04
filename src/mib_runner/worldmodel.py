"""Bitemporal, per-source world model: MIB's computed Oracle.

A generated Scenario is a program over this model.  Every timeline event that
says something about the world is registered as an ``Assertion`` (who said what
about which subject/attribute, when, with what kind of commitment).  Probes are
*queries* over the model, and the Oracle, the minimal relevant-memory set, the
leak proof and the counterfactual replacement are all derived from evaluating
those queries — never written by hand.

Two layers are kept apart, because the benchmark's thesis is about keeping them
apart:

``truth``
    what is actually the case over time.  Only *truth-bearing* assertions move
    it: a subject speaking about itself, an authoritative tool observation, and
    a correction (which rewrites the value of the statement it corrects, i.e. a
    retroactive epistemic fix, not a world transition).

``evidence``
    what each source said.  A contradiction by a third party, a question, or a
    hypothetical is evidence (or not even that) but never truth.

Time is the timeline sequence number.  ``current`` is truth at the end,
``as_of`` is truth just before an event, ``said_by`` is a source's statement,
``first_stated`` is the historical record including mistakes.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Any, Iterable

ASSERTING_KINDS = {"state", "update", "correction", "contradiction", "observation"}
MENTION_KINDS = {"question", "hypothetical"}
RETRACTING_KINDS = {"retraction"}   # "forget what I said": withdraws an earlier assertion from the record
KINDS = ASSERTING_KINDS | MENTION_KINDS | RETRACTING_KINDS


class WorldModelError(ValueError):
    pass


@dataclass(frozen=True)
class Source:
    id: str
    kind: str = "person"
    authority: float = 0.5
    display_name: str | None = None


@dataclass
class Assertion:
    event_id: str
    seq: int
    source: str
    subject: str
    attribute: str
    value: Any
    kind: str = "state"
    truth_bearing: bool = True
    supersedes: str | None = None

    def asserts(self) -> bool:
        return self.kind in ASSERTING_KINDS


@dataclass(frozen=True)
class QueryResult:
    kind: str                 # "value" | "unknown" | "status"
    value: Any = None
    status: str | None = None

    def as_json(self) -> dict[str, Any]:
        return {"kind": self.kind, "value": self.value, "status": self.status}


@dataclass
class SupportSet:
    """Events whose removal changes a query's answer.

    ``necessary`` lists events that are individually necessary.  When several
    events redundantly carry the answer, none is individually necessary and the
    whole group is the causal information set; it is reported in ``groups``.
    ``minimal`` is what a relevant-memory ablation must withhold.
    """
    necessary: list[str] = field(default_factory=list)
    groups: list[list[str]] = field(default_factory=list)

    @property
    def minimal(self) -> list[str]:
        if self.necessary:
            return list(self.necessary)
        return [e for g in self.groups for e in g]

    @property
    def empty(self) -> bool:
        return not self.necessary and not self.groups


class WorldModel:
    def __init__(self) -> None:
        self.sources: dict[str, Source] = {}
        self.assertions: list[Assertion] = []

    # ------------------------------------------------------------------ build
    def add_source(self, source: Source) -> Source:
        self.sources[source.id] = source
        return source

    def add(self, assertion: Assertion) -> Assertion:
        if assertion.kind not in KINDS:
            raise WorldModelError(f"unknown assertion kind {assertion.kind!r}")
        if assertion.source not in self.sources:
            raise WorldModelError(f"unknown source {assertion.source!r}")
        if any(a.event_id == assertion.event_id for a in self.assertions):
            raise WorldModelError(f"duplicate assertion event id {assertion.event_id!r}")
        self.assertions.append(assertion)
        return assertion

    def copy(self) -> "WorldModel":
        return copy.deepcopy(self)

    def with_value(self, event_id: str, value: Any) -> "WorldModel":
        """A counterfactual twin in which one assertion carries another value."""
        twin = self.copy()
        for a in twin.assertions:
            if a.event_id == event_id:
                a.value = value
                break
        else:
            raise WorldModelError(f"no assertion for event {event_id!r}")
        return twin

    def assertion(self, event_id: str) -> Assertion | None:
        return next((a for a in self.assertions if a.event_id == event_id), None)

    # ------------------------------------------------------------ evaluation
    def _live(self, exclude: Iterable[str] = ()) -> list[Assertion]:
        """Assertions still on the record: not withheld, and not withdrawn by a live retraction.

        A retraction (MIB-Specification §4.2, selective forgetting) removes the
        assertion it supersedes from every layer — truth, evidence, and history —
        and asserts nothing itself.  Withholding the retraction restores the
        assertion, which is exactly what its relevant-memory Ablation tests.
        """
        gone = set(exclude)
        rows = sorted((a for a in self.assertions if a.event_id not in gone), key=lambda a: a.seq)
        retracted = {a.supersedes for a in rows if a.kind in RETRACTING_KINDS and a.supersedes}
        return [a for a in rows if a.event_id not in retracted and a.kind not in RETRACTING_KINDS]

    def retracted_values(self, subject: str, attribute: str, exclude: Iterable[str] = ()) -> list[Any]:
        """Values withdrawn by live retractions: forbidden in an Oracle, since using them is the failure."""
        gone = set(exclude)
        rows = [a for a in self.assertions if a.event_id not in gone]
        retracted = {a.supersedes for a in rows if a.kind in RETRACTING_KINDS and a.supersedes}
        out: list[Any] = []
        for a in rows:
            if a.event_id in retracted and (a.subject, a.attribute) == (subject, attribute) and a.value is not None and a.value not in out:
                out.append(a.value)
        return out

    def truth_series(self, subject: str, attribute: str, exclude: Iterable[str] = ()) -> list[tuple[int, Any, str]]:
        """``(seq, value, event_id)`` rows of world truth for one attribute.

        Corrections rewrite the value of the statement they supersede.  When
        that statement was withheld (ablated), the correction still stands on
        its own as a truth-bearing statement from its own position.
        """
        live = self._live(exclude)
        live_ids = {a.event_id for a in live}
        corrected: dict[str, Any] = {}
        for a in live:
            if a.kind == "correction" and a.supersedes in live_ids:
                corrected[a.supersedes] = a.value
        rows: list[tuple[int, Any, str]] = []
        for a in live:
            if (a.subject, a.attribute) != (subject, attribute) or not a.truth_bearing:
                continue
            if a.kind == "correction" and a.supersedes in live_ids:
                continue
            rows.append((a.seq, corrected.get(a.event_id, a.value), a.event_id))
        return rows

    def _last_truth_seq(self, subject: str, attribute: str, exclude: Iterable[str] = ()) -> int | None:
        seqs = [a.seq for a in self._live(exclude)
                if (a.subject, a.attribute) == (subject, attribute) and a.truth_bearing]
        return max(seqs) if seqs else None

    def truth_at(self, subject: str, attribute: str, seq: int | float, exclude: Iterable[str] = ()) -> tuple[Any, str | None]:
        rows = [r for r in self.truth_series(subject, attribute, exclude) if r[0] <= seq]
        if not rows:
            return None, None
        _, value, eid = rows[-1]
        return value, eid

    def current(self, subject: str, attribute: str, exclude: Iterable[str] = ()) -> tuple[Any, str | None]:
        return self.truth_at(subject, attribute, float("inf"), exclude)

    def said_by(self, source: str, subject: str, attribute: str, exclude: Iterable[str] = (), which: str = "latest") -> Any:
        rows = [a for a in self._live(exclude)
                if a.source == source and (a.subject, a.attribute) == (subject, attribute) and a.asserts()]
        if not rows:
            return None
        return (rows[-1] if which == "latest" else rows[0]).value

    def first_stated(self, subject: str, attribute: str, exclude: Iterable[str] = ()) -> Any:
        rows = [a for a in self._live(exclude) if (a.subject, a.attribute) == (subject, attribute) and a.asserts()]
        return rows[0].value if rows else None

    def known(self, subject: str, attribute: str, exclude: Iterable[str] = ()) -> bool:
        return any((a.subject, a.attribute) == (subject, attribute) and a.asserts() for a in self._live(exclude))

    def status(self, subject: str, attribute: str, exclude: Iterable[str] = ()) -> str:
        """``unknown`` | ``resolved`` | ``contested``.

        Contested means at least two sources currently disagree and no
        truth-bearing statement has been made since the disagreement.
        """
        latest_by_source: dict[str, Assertion] = {}
        for a in self._live(exclude):
            if (a.subject, a.attribute) == (subject, attribute) and a.asserts():
                latest_by_source[a.source] = a
        if not latest_by_source:
            return "unknown"
        truth_value, _ = self.current(subject, attribute, exclude)
        distinct = {repr(a.value) for a in latest_by_source.values()}
        if len(distinct) <= 1:
            return "resolved"
        last_truth = self._last_truth_seq(subject, attribute, exclude)
        if last_truth is None:
            return "contested"
        disagree = [a.seq for a in latest_by_source.values() if a.value != truth_value]
        return "resolved" if not disagree or last_truth > max(disagree) else "contested"

    def values_seen(self, subject: str, attribute: str, exclude: Iterable[str] = (), mentions: bool = True) -> list[Any]:
        out: list[Any] = []
        for a in self._live(exclude):
            if (a.subject, a.attribute) != (subject, attribute):
                continue
            if not mentions and not a.asserts():
                continue
            if a.value not in out:
                out.append(a.value)
        return out

    def hop(self, subject: str, attributes: list[str], exclude: Iterable[str] = ()) -> tuple[Any, list[str]]:
        """Follow ``subject --attr0--> value0 --attr1--> value1 ...`` on current truth."""
        current_subject = subject
        used: list[str] = []
        value: Any = None
        for attr in attributes:
            value, eid = self.current(str(current_subject), attr, exclude)
            if value is None:
                return None, used
            used.append(eid or "")
            current_subject = value
        return value, used

    # ---------------------------------------------------------------- queries
    def evaluate(self, query: dict[str, Any], exclude: Iterable[str] = ()) -> QueryResult:
        op = query.get("op")
        s, a = query.get("subject"), query.get("attribute")
        if op == "current":
            value, _ = self.current(s, a, exclude)
            return QueryResult("value", value) if value is not None else QueryResult("unknown")
        if op == "as_of":
            anchor = self.assertion(query["before_event"])
            if anchor is None:
                # The anchor was withheld: truth at the anchor's position is unknowable from the record.
                anchor_seq = self._seq_of(query["before_event"])
            else:
                anchor_seq = anchor.seq
            value, _ = self.truth_at(s, a, anchor_seq - 1, exclude)
            return QueryResult("value", value) if value is not None else QueryResult("unknown")
        if op == "said_by":
            value = self.said_by(query["source"], s, a, exclude, which=query.get("which", "latest"))
            return QueryResult("value", value) if value is not None else QueryResult("unknown")
        if op == "first_stated":
            value = self.first_stated(s, a, exclude)
            return QueryResult("value", value) if value is not None else QueryResult("unknown")
        if op == "known":
            if self.known(s, a, exclude):
                value, _ = self.current(s, a, exclude)
                return QueryResult("value", value) if value is not None else QueryResult("status", status="known")
            return QueryResult("unknown")
        if op == "status":
            return QueryResult("status", status=self.status(s, a, exclude))
        if op == "hop":
            value, _ = self.hop(s, list(query["attributes"]), exclude)
            return QueryResult("value", value) if value is not None else QueryResult("unknown")
        raise WorldModelError(f"unknown query op {op!r}")

    def _seq_of(self, event_id: str) -> int:
        a = self.assertion(event_id)
        if a is None:
            raise WorldModelError(f"unknown event {event_id!r}")
        return a.seq

    def candidates(self, query: dict[str, Any]) -> list[str]:
        """Assertions that could possibly influence a query (same subject/attribute chain)."""
        op = query.get("op")
        if op == "hop":
            attrs = set(query["attributes"])
            return [a.event_id for a in self.assertions if a.attribute in attrs]
        key = (query.get("subject"), query.get("attribute"))
        return [a.event_id for a in self.assertions if (a.subject, a.attribute) == key]

    def support_set(self, query: dict[str, Any], exclude: Iterable[str] = ()) -> SupportSet:
        """Minimal set of events a relevant-memory ablation must withhold (MIB-Specification §4.8).

        Necessary events are found by single removal.  When the answer survives
        every single removal, the redundant group carrying the answer is the
        causal information set, verified by removing it whole.
        """
        base = self.evaluate(query, exclude)
        gone = set(exclude)
        cands = [e for e in self.candidates(query) if e not in gone]
        necessary = [e for e in cands if self.evaluate(query, gone | {e}) != base]
        if necessary:
            return SupportSet(necessary=necessary)
        if base.kind == "unknown":
            return SupportSet()
        carriers = [e for e in cands if (a := self.assertion(e)) and a.asserts() and self._carries(a, base)]
        if carriers and self.evaluate(query, gone | set(carriers)) != base:
            return SupportSet(groups=[carriers])
        if cands and self.evaluate(query, gone | set(cands)) != base:
            return SupportSet(groups=[cands])
        return SupportSet()

    @staticmethod
    def _carries(assertion: Assertion, result: QueryResult) -> bool:
        if result.kind == "value":
            return assertion.value == result.value
        return True

    def leak_free(self, query: dict[str, Any], withheld: Iterable[str]) -> bool:
        """True when the answer is no longer derivable once ``withheld`` is gone."""
        return self.evaluate(query, withheld) != self.evaluate(query)


def oracle_from_result(
    result: QueryResult,
    *,
    forms: Any,
    other_values: Iterable[Any] = (),
    historical: bool = False,
    codes: dict[Any, str] | None = None,
) -> dict[str, Any]:
    """Turn a query result into a Probe Oracle.

    ``forms(value)`` returns every accepted surface form of a value.  Every
    other value ever mentioned for the attribute becomes ``forbidden``, so a
    stale, superseded, or merely-asked-about value is detected as such.
    """
    if result.kind == "value":
        accepted = list(forms(result.value))
        forbidden: list[str] = []
        for v in other_values:
            if v == result.value:
                continue
            for f in forms(v):
                if f not in accepted and f not in forbidden:
                    forbidden.append(f)
        return {
            "expected_status": "historical" if historical else "known",
            "accepted": accepted,
            **({"forbidden": forbidden} if forbidden else {}),
            **_codes_block(forbidden, forms, codes),
        }
    if result.kind == "unknown":
        forbidden = []
        for v in other_values:
            for f in forms(v):
                if f not in forbidden and str(f).casefold() != "unknown":
                    forbidden.append(f)
        return {
            "expected_status": "unknown", "accepted": ["unknown"],
            **({"forbidden": forbidden} if forbidden else {}),
            **_codes_block(forbidden, forms, codes),
        }
    if result.kind == "status":
        status = result.status or "resolved"
        return {
            "expected_status": "contested" if status == "contested" else "known",
            "accepted": [status],
            "forbidden": [s for s in ("contested", "resolved", "unknown") if s != status],
        }
    raise WorldModelError(f"cannot derive an oracle from {result!r}")


def _codes_block(forbidden: list[str], forms: Any, codes: dict[Any, str] | None) -> dict[str, Any]:
    """``failure_code_by_value``: why each forbidden value is wrong (MIB-Specification §4.7)."""
    if not codes:
        return {}
    by_form = {}
    for value, code in codes.items():
        for f in forms(value):
            if f in forbidden:
                by_form[f] = code
    return {"failure_code_by_value": by_form} if by_form else {}
