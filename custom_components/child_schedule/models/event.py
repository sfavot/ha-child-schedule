"""Timeline segment model."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from .status import ScheduleResult


@dataclass(frozen=True, slots=True)
class TimelineSegment:
    """A contiguous period during which the schedule result is stable.

    ``end`` is exclusive.
    """

    start: datetime
    end: datetime
    result: ScheduleResult
