from __future__ import annotations

from datetime import datetime, timedelta, timezone

# Simple Leitner-style intervals for the first version.
# Later we can replace this with FSRS-like scheduling.
INTERVALS = {
    0: timedelta(minutes=0),
    1: timedelta(minutes=10),
    2: timedelta(hours=6),
    3: timedelta(days=1),
    4: timedelta(days=3),
    5: timedelta(days=7),
    6: timedelta(days=14),
}

MAX_LEVEL = max(INTERVALS.keys())


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def next_review_iso(level: int, is_correct: bool) -> tuple[int, str]:
    """Return updated level and next review time."""
    now = datetime.now(timezone.utc).replace(microsecond=0)
    if is_correct:
        new_level = min(level + 1, MAX_LEVEL)
    else:
        new_level = 0

    return new_level, (now + INTERVALS[new_level]).isoformat()
