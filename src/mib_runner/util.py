"""Small shared helpers with no benchmark semantics."""

from __future__ import annotations

import hashlib
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path


def runner_source_digest() -> str:
    """Bind executable Python sources; runtime caches never affect identity."""
    root = Path(__file__).resolve().parent
    digest = hashlib.sha256()
    for path in sorted(root.rglob('*.py')):
        digest.update(str(path.relative_to(root)).encode())
        digest.update(b'\0')
        digest.update(path.read_bytes())
        digest.update(b'\0')
    return 'sha256:' + digest.hexdigest()

_DURATION = re.compile(
    r"^P(?:(?P<weeks>\d+)W)?(?:(?P<days>\d+)D)?"
    r"(?:T(?:(?P<hours>\d+)H)?(?:(?P<minutes>\d+)M)?(?:(?P<seconds>\d+)S)?)?$"
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def parse_iso_duration(text: str) -> timedelta:
    """Parse the ISO 8601 duration subset ``PnW``, ``PnD``, ``PTnHnMnS`` (combinable)."""
    m = _DURATION.match(str(text).strip())
    if not m or not any(m.groupdict().values()):
        raise ValueError(f"unsupported ISO 8601 duration: {text!r}")
    g = {k: int(v or 0) for k, v in m.groupdict().items()}
    return timedelta(weeks=g["weeks"], days=g["days"], hours=g["hours"], minutes=g["minutes"], seconds=g["seconds"])


def advance_iso_time(current: str, duration: str) -> str:
    """Advance an ISO 8601 UTC timestamp by an ISO 8601 duration."""
    base = datetime.fromisoformat(str(current).replace("Z", "+00:00"))
    if base.tzinfo is None:
        base = base.replace(tzinfo=timezone.utc)
    moved = base + parse_iso_duration(duration)
    return moved.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
