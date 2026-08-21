"""Reference MIB-R domain: Ledger Codes.

A deterministic algorithmic-reasoning environment with an upstream-style
verifier.  It exists to validate the MIB-R transfer-intervention methodology
end to end — experience acquisition, held-out transfer, paired memory
conditions, private transfer graph — not to maximize task prestige.

It is *not* an external benchmark and redistributes no third-party data.  An
external benchmark integrates through the same ``RealityTaskAdapter`` contract
and is referenced by immutable id plus content digest, so MIB never has to
carry a payload it cannot license.

The task
--------

Each record names a class, its family, and an identifier, and the operator
wants the record's transfer code.  Four conventions govern the computation and
none of them appears in the task prompt.  They are learnable only from the
corrective feedback a verifier and reviewer produce during acquisition:

    A1  normalize_identifier          uppercase and drop separators first
    A2  mod97_for_standard_family     standard-family codes use modulo 97
    A3  legacy_family_keeps_mod100    the legacy family is the boundary of A2
    A4  drop_ck_prefix                a leading CK is not part of the value

A system that has learned no convention cannot produce a code at all and must
say so.  A system that over-generalizes A2 past its boundary computes a
confident wrong answer on a legacy record — which is the point of the
near-match control.
"""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any

DOMAIN = "algorithmic_reasoning"

ABILITY_NORMALIZE = "ability.normalize_identifier"
ABILITY_MOD97 = "ability.mod97_for_standard_family"
ABILITY_LEGACY_MOD100 = "ability.legacy_family_keeps_mod100"
ABILITY_DROP_CK = "ability.drop_ck_prefix"

STANDARD_FAMILY = "standard"
LEGACY_FAMILY = "legacy"
#: A family the acquisition set never covers.  Its modulus is genuinely unknown.
PROVISIONAL_FAMILY = "provisional"

FAMILY_OF_CLASS = {
    "A": STANDARD_FAMILY, "B": STANDARD_FAMILY, "C": STANDARD_FAMILY,
    "D": STANDARD_FAMILY, "E": STANDARD_FAMILY,
    "L": LEGACY_FAMILY,
    "Z": PROVISIONAL_FAMILY, "Q": PROVISIONAL_FAMILY,
}

MODULUS = {STANDARD_FAMILY: 97, LEGACY_FAMILY: 100}

_SEPARATORS = re.compile(r"[^0-9A-Za-z]")

#: Answer expected when no learned convention covers the record's family.
UNKNOWN_ANSWER = "unknown"

RULE_TEXT = {
    ABILITY_NORMALIZE: "Reviewer note: normalize the identifier before computing — uppercase it and drop every separator.",
    ABILITY_MOD97: "Reviewer note: standard-family transfer codes use modulo 97.",
    ABILITY_LEGACY_MOD100: "Reviewer note: the legacy family keeps modulo 100. Do not apply the standard-family modulo 97 convention to it.",
    ABILITY_DROP_CK: "Reviewer note: a leading CK is a check marker, not part of the identifier. Drop it before computing.",
}

ORACLE_ARTIFACT = {
    ABILITY_NORMALIZE: {
        "artifact_type": "rule",
        "content": "Before computing a transfer code, normalize the identifier: uppercase it and remove every separator.",
        "format": "natural_language_procedure",
    },
    ABILITY_MOD97: {
        "artifact_type": "rule",
        "content": "For a standard-family record, reduce the identifier value modulo 97 when forming the transfer code.",
        "format": "natural_language_procedure",
    },
    ABILITY_LEGACY_MOD100: {
        "artifact_type": "rule",
        "content": "The legacy family keeps modulo 100. The standard-family modulo 97 convention does not apply to it.",
        "format": "natural_language_procedure",
    },
    ABILITY_DROP_CK: {
        "artifact_type": "rule",
        "content": "A leading CK on an identifier is a check marker. Drop it before computing the value.",
        "format": "natural_language_procedure",
    },
}


def family_of(record_class: str) -> str:
    return FAMILY_OF_CLASS.get(record_class, PROVISIONAL_FAMILY)


def normalize_identifier(identifier: str) -> str:
    normalized = _SEPARATORS.sub("", identifier).upper()
    return normalized[2:] if normalized.startswith("CK") else normalized


def base36_value(text: str) -> int:
    """Character value of an identifier exactly as written.

    Case and separators both count, which is what makes A1 load-bearing: an
    identifier that was never normalized computes to a different value, not to
    the same one.
    """
    total = 0
    for ch in text:
        if ch.isdigit():
            total += ord(ch) - 48
        elif "A" <= ch <= "Z":
            total += ord(ch) - 55
        elif "a" <= ch <= "z":
            total += ord(ch) - 87 + 26
        else:
            total += 1
    return total


def format_code(record_class: str, value: int, modulus: int) -> str:
    return f"{record_class}-{value % modulus:02d}"


def reference_code(*, record_class: str, identifier: str) -> str:
    """The verifier's ground truth for one record."""
    family = family_of(record_class)
    if family == PROVISIONAL_FAMILY:
        return UNKNOWN_ANSWER
    return format_code(record_class, base36_value(normalize_identifier(identifier)), MODULUS[family])


def required_abilities(*, record_class: str, identifier: str) -> tuple[str, ...]:
    """Conventions whose absence changes the answer for this record."""
    family = family_of(record_class)
    if family == PROVISIONAL_FAMILY:
        return ()
    needed: list[str] = []
    stripped = _SEPARATORS.sub("", identifier)
    if stripped != identifier or stripped.upper() != stripped:
        needed.append(ABILITY_NORMALIZE)
    if stripped.upper().startswith("CK"):
        needed.append(ABILITY_DROP_CK)
    needed.append(ABILITY_MOD97 if family == STANDARD_FAMILY else ABILITY_LEGACY_MOD100)
    return tuple(needed)


def content_digest(task: dict[str, Any]) -> str:
    payload = {k: task[k] for k in ("task_id", "record_class", "family", "identifier", "prompt", "expected")}
    blob = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _task(task_id: str, record_class: str, identifier: str, *, tags: tuple[str, ...] = ()) -> dict[str, Any]:
    family = family_of(record_class)
    task = {
        "task_id": task_id,
        "record_class": record_class,
        "family": family,
        "identifier": identifier,
        "prompt": (
            f"Record class {record_class} ({family} family), identifier {identifier}. "
            "Reply with the transfer code only, or with 'unknown' if no convention you know covers this family."
        ),
        "expected": reference_code(record_class=record_class, identifier=identifier),
        "required_abilities": list(required_abilities(record_class=record_class, identifier=identifier)),
        "tags": list(tags),
    }
    task["content_digest"] = content_digest(task)
    return task


def _batch_task(task_id: str, record_class: str, first: str, second: str) -> dict[str, Any]:
    """A structurally different framing of the same latent conventions."""
    family = family_of(record_class)
    value = base36_value(normalize_identifier(first)) + base36_value(normalize_identifier(second))
    task = {
        "task_id": task_id,
        "record_class": record_class,
        "family": family,
        "identifier": f"{first}+{second}",
        "prompt": (
            f"Batch reconciliation for class {record_class} ({family} family): identifiers {first} and {second} "
            "are merged into one record. Reply with the transfer code of the merged record only, "
            "or with 'unknown' if no convention you know covers this family."
        ),
        "expected": format_code(record_class, value, MODULUS[family]),
        "required_abilities": [ABILITY_MOD97],
        "tags": ["structural"],
        "batch": [first, second],
    }
    task["content_digest"] = content_digest(task)
    return task


def _count_task(task_id: str, batch: str) -> dict[str, Any]:
    task = {
        "task_id": task_id,
        "record_class": "A",
        "family": STANDARD_FAMILY,
        "identifier": batch,
        "prompt": (
            f"How many records were archived in batch {batch}? "
            "Reply with the count only, or with 'unknown' if the batch is not recorded."
        ),
        "expected": UNKNOWN_ANSWER,
        "required_abilities": [],
        "tags": ["irrelevant"],
        "kind": "archive_count",
    }
    task["content_digest"] = content_digest(task)
    return task


#: Identifiers are eight characters long on purpose.  A short identifier sums to
#: less than 97, where modulo 97 and modulo 100 agree and the whole
#: standard-versus-legacy distinction would be invisible.
_ACQUISITION_CLEAN = ["E6T6VSMT", "4XMG9Y5H", "DSBWDFMP", "9TDBSBHT", "E29YRPR7", "5BNRU6MK"]
_ACQUISITION_UNNORMALIZED = ["xuvr-72wg", "cgv8 lman", "ru2n-geda", "jkma-jzhl", "9nbs x3l3"]
_ACQUISITION_PREFIXED = ["CKCDUMYXZK", "CK6EAFV6UZ", "CKKZSJW9BS", "CK4HWWG5M8"]
_ACQUISITION_LEGACY = ["TQFGKC4L", "KANDH3VA", "ESJCTAXN"]
_ACQUISITION_LEGACY_UNNORMALIZED = "aj5b-l3rt"

_HELD_OUT_CLEAN = ["JWXTXFF2", "5JU2LDLY", "FQBJNK27"]
_HELD_OUT_BATCH = ("NKXZ6T6M", "JCVC8UP7")
_HELD_OUT_UNNORMALIZED = ["lhhh-bsek", "88qa xamm"]
_HELD_OUT_PREFIXED = "CKE6T6VSMT"
_HELD_OUT_PREFIXED_UNNORMALIZED = "ck-4xmg 9y5h"
_HELD_OUT_LEGACY = "DSBWDFMP"
_HELD_OUT_LEGACY_UNNORMALIZED = "9tdb-sbht"
_HELD_OUT_PROVISIONAL = ["E29YRPR7", "5BNRU6MK"]


def train_tasks() -> list[dict[str, Any]]:
    """22 acquisition tasks: 19 carrying a convention, 4 carrying none.

    The legacy family gets one unnormalized identifier of its own, so that
    ablating standard-family experience removes the modulus convention under
    test without also removing normalization from the legacy Probes.
    """
    rows: list[dict[str, Any]] = []
    for i, ident in enumerate(_ACQUISITION_CLEAN, start=1):
        rows.append(_task(f"train-mod97-{i:02d}", "A", ident, tags=("supports:mod97",)))
    for i, ident in enumerate(_ACQUISITION_UNNORMALIZED, start=1):
        rows.append(_task(f"train-normalize-{i:02d}", "B", ident, tags=("supports:normalize", "supports:mod97")))
    for i, ident in enumerate(_ACQUISITION_PREFIXED, start=1):
        rows.append(_task(f"train-prefix-{i:02d}", "C", ident, tags=("supports:drop_ck", "supports:mod97")))
    for i, ident in enumerate(_ACQUISITION_LEGACY, start=1):
        rows.append(_task(f"train-legacy-{i:02d}", "L", ident, tags=("supports:legacy_mod100",)))
    rows.append(_task(
        f"train-legacy-{len(_ACQUISITION_LEGACY) + 1:02d}", "L", _ACQUISITION_LEGACY_UNNORMALIZED,
        tags=("supports:legacy_mod100", "supports:normalize"),
    ))
    for i, batch in enumerate(["1111", "2222", "3333", "4444"], start=1):
        rows.append(_count_task(f"train-unrelated-{i:02d}", batch))
    return rows


def test_tasks() -> list[dict[str, Any]]:
    """12 held-out tasks spanning supported transfer and both negative controls."""
    rows = [
        _task("test-01", "A", _HELD_OUT_CLEAN[0]),
        _task("test-02", "D", _HELD_OUT_CLEAN[1]),
        _task("test-03", "B", _HELD_OUT_UNNORMALIZED[0]),
        _task("test-04", "C", _HELD_OUT_PREFIXED),
        _task("test-05", "C", _HELD_OUT_PREFIXED_UNNORMALIZED),
        _batch_task("test-06", "E", *_HELD_OUT_BATCH),
        _task("test-07", "A", _ACQUISITION_CLEAN[0]),
        _task("test-08", "L", _HELD_OUT_LEGACY),
        _task("test-09", "L", _HELD_OUT_LEGACY_UNNORMALIZED),
        _task("test-10", "Z", _HELD_OUT_PROVISIONAL[0]),
        _task("test-11", "Q", _HELD_OUT_PROVISIONAL[1]),
        _task("test-12", "A", _HELD_OUT_UNNORMALIZED[1]),
    ]
    return sorted(rows, key=lambda t: t["task_id"])


def ability_is_load_bearing(task: dict[str, Any], ability: str) -> bool:
    """Would omitting this convention change the answer for this task?

    A calibration gate, not a metric: an annotated support edge that no
    behaviour depends on measures nothing.
    """
    record_class, identifier = task["record_class"], task["identifier"]
    family = family_of(record_class)
    if family == PROVISIONAL_FAMILY:
        return False
    parts = task.get("batch") or [identifier]

    def value(*, normalize: bool, drop_ck: bool) -> int:
        total = 0
        for raw in parts:
            text = _SEPARATORS.sub("", raw).upper() if normalize else raw
            if drop_ck and text.upper().startswith("CK"):
                text = text[2:]
            total += base36_value(text)
        return total

    correct_modulus = MODULUS[family]
    correct = format_code(record_class, value(normalize=True, drop_ck=True), correct_modulus)
    if ability == ABILITY_NORMALIZE:
        return format_code(record_class, value(normalize=False, drop_ck=True), correct_modulus) != correct
    if ability == ABILITY_DROP_CK:
        return format_code(record_class, value(normalize=True, drop_ck=False), correct_modulus) != correct
    if ability in {ABILITY_MOD97, ABILITY_LEGACY_MOD100}:
        other = 100 if correct_modulus == 97 else 97
        return format_code(record_class, value(normalize=True, drop_ck=True), other) != correct
    return False


class LedgerCodesAdapter:
    """Reference ``RealityTaskAdapter`` for the Ledger Codes domain."""

    adapter_id = "mib.reality.ledger_codes.v1"
    domain = DOMAIN

    def __init__(self) -> None:
        self._tasks = {t["task_id"]: t for t in (*train_tasks(), *test_tasks())}

    def describe(self) -> dict[str, Any]:
        return {
            "adapter": self.adapter_id,
            "domain": self.domain,
            "verifier": "local_deterministic",
            "verifier_version": "0.1.0",
            "redistributes_external_data": False,
            "train_task_count": len(train_tasks()),
            "test_task_count": len(test_tasks()),
        }

    def load_task(self, task_ref: dict[str, Any]) -> dict[str, Any]:
        task_id = str(task_ref.get("task_id"))
        task = self._tasks.get(task_id)
        if task is None:
            raise KeyError(f"unknown Reality Task: {task_id}")
        declared = task_ref.get("content_digest")
        if declared and declared != task["content_digest"]:
            # A drifted environment revision would silently change what every
            # paired condition was measured against.
            raise ValueError(
                f"content digest mismatch for {task_id}: "
                f"manifest {declared} != environment {task['content_digest']}"
            )
        return dict(task)

    def run_task(self, task: dict[str, Any], agent: Any, *, seed: int | str, request_id: str) -> dict[str, Any]:
        output = agent.respond(
            run_id=str(seed),
            request_id=request_id,
            interaction_id=f"reality_{task['task_id']}",
            input_data={"content": task["prompt"]},
            virtual_time=None,
        )
        answer = output.content if output.content is not None else output.value
        return {
            "task_id": task["task_id"],
            "answer": "" if answer is None else str(answer),
            "expected": task["expected"],
            "output_type": output.type,
        }

    def normalize_score(self, result: dict[str, Any]) -> float:
        return 1.0 if str(result["answer"]).strip().casefold() == str(result["expected"]).strip().casefold() else 0.0

    def collect_trajectory(self, result: dict[str, Any]) -> list[dict[str, Any]]:
        return [{"kind": "answer", "task_id": result["task_id"], "answer": result["answer"]}]

    def feedback(self, task: dict[str, Any], result: dict[str, Any], *, score: float) -> list[str]:
        """Verifier verdict plus, on failure, the reviewer correction.

        This is the Experience a MIB-R run forms memory from: goal, action,
        observation, feedback, outcome.
        """
        if score >= 1.0:
            return [f"Verifier: task {task['task_id']} accepted. {task['expected']} is correct."]
        lines = [
            f"Verifier: task {task['task_id']} rejected. Submitted {result['answer']!r}; "
            f"the correct answer is {task['expected']}."
        ]
        rules = task.get("required_abilities") or ()
        lines.extend(RULE_TEXT[a] for a in rules)
        if not rules:
            lines.append("Reviewer note: this request is not a transfer-code computation; answer 'unknown'.")
        return lines
