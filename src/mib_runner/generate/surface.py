"""Surface realization of assertions, and the inverse parser used by fixture Agents.

Every template is a format string over the slots ``{label}``, ``{value}``,
``{value_title}``, ``{subject_nom}``, ``{subject_poss}``, ``{subject_title}``.
The parser compiles the same templates to regular expressions, so a fixture
Agent with "perfect structured memory" can recover ``(kind, perspective,
attribute, value, subject)`` from text without any oracle access.
"""

from __future__ import annotations

import random
import re
from dataclasses import dataclass
from typing import Any

from .pools import ATTRIBUTES, GENERIC_TEMPLATES, AttributeSpec, nominative, possessive


@dataclass(frozen=True)
class Parsed:
    kind: str          # state | update | correction | contradiction | question | hypothetical | retraction
    perspective: str   # first | third
    attribute: str
    value: str | None     # None for a retraction, which withdraws without restating
    subject: str | None   # display name for third-person forms, None for first person


def templates_for(spec: AttributeSpec, kind: str, perspective: str, bank: dict[str, Any] | None = None) -> tuple[str, ...]:
    """Public templates, or an evaluator-private surface bank when one is supplied.

    A bank (``{"attribute_templates": {attr: {key: [...]}}, "templates": {key: [...]},
    "prompts": {which: str}, "phrases": {key: str}}``) changes only surface
    realization. World-model assertions, and therefore every Oracle, are
    unchanged; public-grammar parsers must not transfer to it.
    """
    key = f"{kind}.{perspective}"
    if bank:
        private = ((bank.get("attribute_templates") or {}).get(spec.id) or {}).get(key) or (bank.get("templates") or {}).get(key)
        if private:
            return tuple(private)
    return spec.templates.get(key) or GENERIC_TEMPLATES.get(key) or ()


VALUE_KINDS = frozenset({"state", "update", "correction", "contradiction", "question", "hypothetical"})
TEMPLATE_KINDS = VALUE_KINDS | {"retraction"}
PROMPT_KINDS = frozenset({"current", "before", "first", "said_by", "status", "known"})
_SAMPLE_SLOTS = {"label": "label", "value": "VALUE-1", "value_title": "Value-1", "subject_nom": "Ann",
                 "subject_poss": "Ann's", "subject_title": "Ann", "source": "Bo"}


def validate_bank(bank: Any) -> None:
    """Reject an evaluator-private surface bank that no reader could recover the world from.

    The bank changes wording only. Every value-bearing template must still
    carry the value, generic templates must still name the attribute, and the
    status/known prompts must still state the exact answer words the Oracle
    accepts. A bank that hides information would defeat public parsers and
    every honest reader alike, which is not a measurement of memory.
    """
    if not isinstance(bank, dict):
        raise ValueError("surface bank must be an object")
    unknown = set(bank) - {"templates", "attribute_templates", "prompts", "attribute_prompts", "phrases"}
    if unknown:
        raise ValueError(f"surface bank has unknown sections: {sorted(unknown)}")

    def render(where: str, template: Any) -> str:
        if not isinstance(template, str) or not template.strip():
            raise ValueError(f"surface bank {where}: template must be a non-empty string")
        try:
            return template.format(**_SAMPLE_SLOTS)
        except (KeyError, IndexError, ValueError) as exc:
            raise ValueError(f"surface bank {where}: unsupported slot ({exc})") from exc

    def check_templates(where: str, table: Any, *, generic: bool) -> None:
        if not isinstance(table, dict):
            raise ValueError(f"surface bank {where}: must map 'kind.perspective' to template lists")
        for key, pool in table.items():
            kind, _, perspective = str(key).partition(".")
            if kind not in TEMPLATE_KINDS or perspective not in {"first", "third"}:
                raise ValueError(f"surface bank {where}: unknown template key {key!r}")
            if not isinstance(pool, list) or not pool:
                raise ValueError(f"surface bank {where}.{key}: needs a non-empty template list")
            for template in pool:
                text = render(f"{where}.{key}", template)
                if kind in VALUE_KINDS and "VALUE-1" not in text and "Value-1" not in text:
                    raise ValueError(f"surface bank {where}.{key}: template does not carry the value")
                if generic and "label" not in text:
                    raise ValueError(f"surface bank {where}.{key}: generic template does not name the attribute")

    check_templates("templates", bank.get("templates") or {}, generic=True)
    for attribute, table in (bank.get("attribute_templates") or {}).items():
        if attribute not in ATTRIBUTES:
            raise ValueError(f"surface bank attribute_templates: unknown attribute {attribute!r}")
        check_templates(f"attribute_templates.{attribute}", table, generic=False)

    def check_prompts(where: str, table: Any, *, generic: bool) -> None:
        if not isinstance(table, dict):
            raise ValueError(f"surface bank {where}: must map prompt kinds to strings")
        for which, template in table.items():
            if which not in PROMPT_KINDS:
                raise ValueError(f"surface bank {where}: unknown prompt kind {which!r}")
            text = render(f"{where}.{which}", template)
            if generic and "label" not in text:
                raise ValueError(f"surface bank {where}.{which}: generic prompt does not name the attribute")
            if which == "known" and "unknown" not in text.casefold():
                raise ValueError(f"surface bank {where}.known: must state the exact abstention word 'unknown'")
            if which == "status" and not {"resolved", "contested"} <= set(re.findall(r"[a-z]+", text.casefold())):
                raise ValueError(f"surface bank {where}.status: must state both answer words 'resolved' and 'contested'")

    check_prompts("prompts", bank.get("prompts") or {}, generic=True)
    for attribute, table in (bank.get("attribute_prompts") or {}).items():
        if attribute not in ATTRIBUTES:
            raise ValueError(f"surface bank attribute_prompts: unknown attribute {attribute!r}")
        check_prompts(f"attribute_prompts.{attribute}", table, generic=False)
    phrases = bank.get("phrases") or {}
    if not isinstance(phrases, dict) or any(not isinstance(v, str) or not v.strip() for v in phrases.values()):
        raise ValueError("surface bank phrases: must map keys to non-empty strings")


def realize(
    spec: AttributeSpec,
    kind: str,
    value: str,
    *,
    subject_name: str,
    first_person: bool,
    rng: random.Random,
    template_index: int | None = None,
    bank: dict[str, Any] | None = None,
) -> tuple[str, int]:
    perspective = "first" if first_person else "third"
    pool = templates_for(spec, kind, perspective, bank)
    if not pool:
        raise ValueError(f"no surface template for {spec.id}/{kind}/{perspective}")
    index = rng.randrange(len(pool)) if template_index is None else template_index % len(pool)
    text = pool[index].format(
        label=spec.label,
        value=value,
        value_title=str(value).title(),
        subject_nom=nominative(subject_name, first_person),
        subject_poss=possessive(subject_name, first_person),
        subject_title=str(subject_name).title(),
    )
    return text[0].upper() + text[1:], index


def prompt(spec: AttributeSpec, which: str, *, subject_name: str, first_person: bool, source_name: str | None = None,
           bank: dict[str, Any] | None = None) -> str:
    template = {
        "current": spec.ask_current, "before": spec.ask_before, "first": spec.ask_first,
        "said_by": spec.ask_said_by, "status": spec.ask_status, "known": spec.ask_known,
    }[which]
    if bank:
        template = (((bank.get("attribute_prompts") or {}).get(spec.id) or {}).get(which)
                    or (bank.get("prompts") or {}).get(which) or template)
    return template.format(
        label=spec.label,
        subject_nom=nominative(subject_name, first_person) if which != "first" else ("I" if first_person else subject_name),
        subject_poss=possessive(subject_name, first_person),
        subject_title=str(subject_name).title(),
        source=source_name or "",
    )


_SLOT = {
    "label": r"(?P<label>[a-z ]+?)",
    "value": r"(?P<value>.+?)",
    "value_title": r"(?P<value_title>[A-Z][A-Za-z0-9 +:-]*?)",
    "subject_nom": r"(?P<subject_nom>I|[A-Z][a-z]+(?: [a-z]+)*)",
    "subject_poss": r"(?P<subject_poss>my|[A-Z][a-z]+'s)",
    "subject_title": r"(?P<subject_title>[A-Z][a-z]+)",
}


def _compile(template: str) -> re.Pattern[str]:
    out = ""
    pos = 0
    for m in re.finditer(r"\{(\w+)\}", template):
        out += re.escape(template[pos:m.start()])
        out += _SLOT[m.group(1)]
        pos = m.end()
    out += re.escape(template[pos:])
    return re.compile("^" + out + "$", re.IGNORECASE)


_PARSERS: list[tuple[re.Pattern[str], str, str, str]] = []
for _spec in ATTRIBUTES.values():
    for _kind in ("state", "update", "correction", "contradiction", "question", "hypothetical", "retraction"):
        for _persp in ("first", "third"):
            for _t in templates_for(_spec, _kind, _persp):
                _PARSERS.append((_compile(_t), _spec.id, _kind, _persp))


def parse(text: str) -> Parsed | None:
    """Recover the assertion a surface sentence encodes, or ``None`` for interference."""
    text = (text or "").strip()
    for pattern, attribute, kind, perspective in _PARSERS:
        m = pattern.match(text)
        if not m:
            continue
        g = m.groupdict()
        spec = ATTRIBUTES[attribute]
        if "label" in g and g["label"] and g["label"].lower() != spec.label.lower():
            continue
        value = g.get("value") or g.get("value_title") or ""
        value = value.strip().rstrip(".")
        if attribute in ("project", "schedule_zone") and value:
            value = value.lower()
        subject = None
        for key in ("subject_poss", "subject_nom", "subject_title"):
            raw = g.get(key)
            if raw and raw.lower() not in ("my", "i"):
                subject = raw[:-2] if raw.endswith("'s") else raw
                break
        if kind == "retraction":
            return Parsed(kind, perspective, attribute, None, subject)
        # Values are canonical pool members; reject sentences whose value is not one.
        canonical = _canonical_value(spec, value)
        if canonical is None:
            continue
        return Parsed(kind, perspective, attribute, canonical, subject)
    return None


def _canonical_value(spec: AttributeSpec, value: str) -> str | None:
    for v in spec.values:
        if value.lower() == str(v).lower():
            return v
        if any(value.lower() == f.lower() for f in spec.forms(v)):
            return v
    return None


@dataclass(frozen=True)
class ParsedPrompt:
    which: str           # current | before | first | said_by | status | known | hop
    attribute: str
    subject: str | None  # display name for third-person prompts, None for first person
    source: str | None   # display name for said_by prompts


_PROMPT_PARSERS: list[tuple[re.Pattern[str], str, str]] = []
_PROMPT_SLOT = {
    **_SLOT,
    "source": r"(?P<source>[A-Z][a-z]+)",
}


def _compile_prompt(template: str) -> re.Pattern[str]:
    out = ""
    pos = 0
    for m in re.finditer(r"\{(\w+)\}", template):
        out += re.escape(template[pos:m.start()])
        out += _PROMPT_SLOT[m.group(1)]
        pos = m.end()
    out += re.escape(template[pos:])
    return re.compile("^" + out + "$", re.IGNORECASE)


for _spec in ATTRIBUTES.values():
    for _which, _tpl in (("current", _spec.ask_current), ("before", _spec.ask_before), ("first", _spec.ask_first),
                         ("said_by", _spec.ask_said_by), ("status", _spec.ask_status), ("known", _spec.ask_known)):
        _PROMPT_PARSERS.append((_compile_prompt(_tpl), _spec.id, _which))

HOP_PROMPT = "Which UTC offset should I use when scheduling a call with my project team? Answer with the offset only."


def parse_prompt(text: str) -> ParsedPrompt | None:
    """Recover which query a generated Probe prompt asks (used by fixture Agents)."""
    text = (text or "").strip()
    if text == HOP_PROMPT:
        return ParsedPrompt("hop", "utc", None, None)
    for pattern, attribute, which in _PROMPT_PARSERS:
        m = pattern.match(text)
        if not m:
            continue
        g = m.groupdict()
        spec = ATTRIBUTES[attribute]
        if g.get("label") and g["label"].lower() != spec.label.lower():
            continue
        subject = None
        for key in ("subject_poss", "subject_nom", "subject_title"):
            raw = g.get(key)
            if raw and raw.lower() not in ("my", "i"):
                subject = raw[:-2] if raw.endswith("'s") else raw
                break
        return ParsedPrompt(which, attribute, subject, g.get("source"))
    return None


def tool_payload(tool: str, subject: str, attribute: str, value: Any) -> dict[str, Any]:
    return {"kind": "lookup", "tool": tool, "subject": subject, "attribute": attribute, "value": value, "status": "confirmed"}
