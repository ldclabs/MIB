"""Value pools and surface-form vocabularies for generated Scenarios."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Callable

NAMES = ["Alice", "Bob", "Priya", "Mateo", "Yuki", "Lena", "Omar", "Sofia", "Chen", "Noor", "Ravi", "Ines", "Tomas", "Aiko"]

WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
THINGS = ["quarterly", "onboarding", "vendor", "roadmap", "security", "hiring", "budget", "design"]
WEATHER = ["mild", "rainy", "windy", "sunny", "cold"]


def iso_offset(zone: str) -> str:
    m = re.fullmatch(r"UTC([+-])(\d{1,2})", zone)
    if not m:
        return zone
    return f"{m.group(1)}{int(m.group(2)):02d}:00"


def zone_forms(v: str) -> list[str]:
    return [v, iso_offset(v)] if v.startswith("UTC") else [v]


def identity_forms(v: str) -> list[str]:
    return [v]


@dataclass(frozen=True)
class AttributeSpec:
    id: str
    label: str
    values: tuple[str, ...]
    forms: Callable[[str], list[str]] = identity_forms
    # Surface templates by (kind, perspective).  ``first`` = the subject speaks
    # about itself, ``third`` = another source speaks about the subject.
    templates: dict[str, tuple[str, ...]] = field(default_factory=dict)
    ask_current: str = "What is {subject_poss} {label} right now? Answer with the value only."
    ask_before: str = "What was {subject_poss} {label} immediately before the most recent change? Answer with the value only."
    ask_first: str = "What did {subject_nom} originally say {subject_poss} {label} was? Answer with the value only."
    ask_said_by: str = "What did {source} say {subject_poss} {label} is? Answer with the value only."
    ask_status: str = "Based only on what has been stated so far, is {subject_poss} {label} resolved or contested? Answer exactly one of: resolved, contested."
    ask_known: str = "What is {subject_poss} {label}? If it was never established, answer exactly: unknown."
    hop_prompt: str | None = None


GENERIC_TEMPLATES: dict[str, tuple[str, ...]] = {
    "state.first": (
        "My {label} is {value}.",
        "For the record, my {label} is {value}.",
        "Just so you know, my {label} is {value}.",
    ),
    "update.first": (
        "Update: my {label} is now {value}.",
        "Things changed. My {label} is now {value}.",
        "My {label} has changed to {value}.",
    ),
    "correction.first": (
        "Sorry, I misspoke earlier. My {label} is actually {value}.",
        "Correction: my {label} is {value}, not what I said before.",
        "I need to fix something I said: my {label} is {value}.",
    ),
    "state.third": (
        "{subject_poss} {label} is {value}.",
        "For reference, {subject_poss} {label} is {value}.",
    ),
    "contradiction.third": (
        "I am fairly sure {subject_poss} {label} is {value}.",
        "{subject_nom} told me {subject_poss} {label} is {value}.",
        "As far as I know, {subject_poss} {label} is {value}.",
    ),
    "question.first": (
        "Is my {label} {value}?",
        "Did I ever say my {label} was {value}?",
        "Would it be a problem if my {label} were {value}?",
    ),
    "question.third": (
        "Is {subject_poss} {label} {value}?",
        "Was {subject_poss} {label} {value} at some point?",
    ),
    "hypothetical.first": (
        "I am considering switching my {label} to {value}, but nothing is decided.",
        "If I ever changed my {label} to {value}, would that break anything?",
    ),
    # Selective forgetting: withdraw what was said, without restating it.
    "retraction.first": (
        "Please forget my {label}; disregard what I told you about it.",
        "Scratch what I said about my {label}. Treat it as never said.",
        "Remove my {label} from your notes and do not use it again.",
    ),
}

ATTRIBUTES: dict[str, AttributeSpec] = {
    "timezone": AttributeSpec("timezone", "timezone",
                              ("UTC+1", "UTC+2", "UTC+3", "UTC+5", "UTC+8", "UTC+9", "UTC-5", "UTC-8"), zone_forms),
    "city": AttributeSpec("city", "home city",
                          ("Lisbon", "Tokyo", "Berlin", "Toronto", "Nairobi", "Seoul", "Denver", "Warsaw")),
    "favorite_drink": AttributeSpec("favorite_drink", "usual drink order",
                                    ("green tea", "oat latte", "sparkling water", "black coffee", "ginger ale", "jasmine tea")),
    "birthday": AttributeSpec("birthday", "birthday",
                              ("May 12", "May 21", "June 3", "April 18", "June 27", "April 9", "May 30")),
    "access_code": AttributeSpec("access_code", "project access code",
                                 ("ORCHID-91", "MAPLE-27", "CEDAR-58", "LOTUS-33", "BIRCH-74", "ASTER-16")),
    "office": AttributeSpec("office", "office",
                            ("Blue Annex", "Green Annex", "North Wing", "Harbor Loft", "Red Annex", "Summit Suite")),
    "meeting_start": AttributeSpec("meeting_start", "start time",
                                   ("14:00", "15:00", "16:00", "09:30", "11:00", "13:30"),
                                   templates={
                                       "state.third": ("The {subject_nom} starts at {value}.", "{subject_nom} is scheduled for {value}."),
                                       "update.third": ("The {subject_nom} moved to {value}.", "New time for the {subject_nom}: {value}."),
                                       "contradiction.third": ("I think the {subject_nom} is at {value}.", "Pretty sure the {subject_nom} starts at {value}."),
                                       "question.third": ("Is the {subject_nom} at {value}?",),
                                   },
                                   ask_current="What start time should you use for the {subject_nom}? Answer with the time only.",
                                   ask_said_by="What time did {source} say the {subject_nom} starts? Answer with the time only.",
                                   ask_status="Based only on what has been stated so far, is the {subject_nom} start time resolved or contested? Answer exactly one of: resolved, contested."),
    # Multi-hop chain: person.project -> project.schedule_zone -> zone.utc
    "project": AttributeSpec("project", "project", ("orion", "vega", "lyra", "atlas"),
                             templates={"state.first": ("I work on project {value_title}.", "My main project is {value_title}."),
                                        "state.third": ("{subject_nom} works on project {value_title}.",)}),
    "schedule_zone": AttributeSpec("schedule_zone", "scheduling zone", ("atlantic", "pacific", "alpine", "meridian"),
                                   templates={"state.third": ("Project {subject_title} schedules all member calls using the {value_title} zone.",
                                                              "All calls for project {subject_title} follow the {value_title} zone.")}),
    "utc": AttributeSpec("utc", "UTC offset", ("UTC+1", "UTC+9", "UTC-5", "UTC+3", "UTC+8", "UTC-8"), zone_forms,
                         templates={"state.third": ("The {subject_title} zone runs on {value}.", "{subject_title} zone time is {value}.")}),
}

PERSONAL = ("timezone", "city", "favorite_drink", "birthday", "access_code", "office")

NEUTRAL_TEMPLATES = (
    "Reminder: the {thing} report is due on {weekday}.",
    "I reorganized the {thing} folder this morning.",
    "Weather looks {weather} for most of the week.",
    "The {thing} sync moved to {weekday}; nothing else changed.",
    "Filed the {thing} notes. No action needed.",
    "Lunch ran late because of the {thing} review.",
    "Someone left a {weather}-day umbrella in the {thing} room.",
    "Booked the small room for the {thing} kickoff on {weekday}.",
)

COMMITMENT_TEMPLATES = (
    "When {trigger_name} joins the call, remind me to ask about the {topic}.",
    "Next time {trigger_name} joins a call, please remind me about the {topic}.",
)
TRIGGER_TEMPLATES = (
    "{trigger_name} joined the call.",
    "{trigger_name} has just joined the call.",
)
NEAR_TRIGGER_TEMPLATES = (
    "{trigger_name} sent the agenda by email.",
    "{trigger_name} will be out on {weekday}.",
    "Heard from {trigger_name}: the {thing} draft is ready.",
)
# Self memory: a standing rule about the Agent itself, stated once and expected to hold.
LIMITATION_TEMPLATES = (
    "For your own records: you are not allowed to restart services yourself. When a task needs a restart, do everything else and hand the restart to {name}.",
    "A rule about you: you must never restart a service; {name} does restarts. Do the rest of any deployment and stop before the restart.",
)
TOPICS = ("contract renewal", "invoice backlog", "beta timeline", "audit findings", "hiring plan", "vendor quote")


def possessive(name: str, first_person: bool) -> str:
    return "my" if first_person else f"{name}'s"


def nominative(name: str, first_person: bool) -> str:
    return "I" if first_person else name
