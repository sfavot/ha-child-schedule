"""Absolute date range rule."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from ..models import ScheduleContext, ScheduleResult
from ..utils.datetime import normalize_datetime
from .base import ScheduleRule


@dataclass(frozen=True, slots=True)
class DateRangeSlot:
    """An absolute datetime range assigned to a location (end exclusive)."""

    location: str
    start: datetime
    end: datetime
    reason: str | None = None


@dataclass
class DateRangeRule(ScheduleRule):
    """Assigns locations during absolute datetime ranges.

    Useful for one-off plans such as camps, trips, or a specific summer
    arrangement. Slot datetimes may be naive (interpreted in the
    evaluation timezone) or aware.
    """

    id: str
    slots: tuple[DateRangeSlot, ...]
    priority: int = 40

    def evaluate(self, dt: datetime, context: ScheduleContext) -> ScheduleResult | None:
        assert dt.tzinfo is not None
        for slot in self.slots:
            start = normalize_datetime(slot.start, dt.tzinfo)
            end = normalize_datetime(slot.end, dt.tzinfo)
            if start <= dt < end:
                return ScheduleResult(
                    effective_location=slot.location,
                    assigned_location=slot.location,
                    source=self.id,
                    reason=slot.reason,
                    priority=self.priority,
                    period_start=start,
                    period_end=end,
                )
        return None

    def transition_times(
        self,
        start: datetime,
        end: datetime,
        context: ScheduleContext,
    ) -> list[datetime]:
        assert start.tzinfo is not None
        times: list[datetime] = []
        for slot in self.slots:
            slot_start = normalize_datetime(slot.start, start.tzinfo)
            slot_end = normalize_datetime(slot.end, start.tzinfo)
            for moment in (slot_start, slot_end):
                if start < moment <= end:
                    times.append(moment)
        return times
