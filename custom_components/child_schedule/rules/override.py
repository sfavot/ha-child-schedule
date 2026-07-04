"""Manual override rule."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from ..models import ScheduleContext, ScheduleResult
from ..utils.datetime import normalize_datetime
from .base import ScheduleRule


@dataclass(frozen=True, slots=True)
class ManualOverride:
    """A manual override of the schedule.

    ``end`` is optional: an open-ended override applies until cleared.
    """

    location: str
    start: datetime
    end: datetime | None = None
    reason: str | None = None


@dataclass
class ManualOverrideRule(ScheduleRule):
    """Applies a user-set manual override with the highest priority."""

    id: str = "manual_override"
    priority: int = 100
    override: ManualOverride | None = None

    def set_override(self, override: ManualOverride) -> None:
        self.override = override

    def clear_override(self) -> None:
        self.override = None

    def transition_times(
        self,
        start: datetime,
        end: datetime,
        context: ScheduleContext,
    ) -> list[datetime]:
        assert start.tzinfo is not None
        if self.override is None:
            return []
        times: list[datetime] = []
        slot_start = normalize_datetime(self.override.start, start.tzinfo)
        if start < slot_start <= end:
            times.append(slot_start)
        if self.override.end is not None:
            slot_end = normalize_datetime(self.override.end, start.tzinfo)
            if start < slot_end <= end:
                times.append(slot_end)
        return times

    def evaluate(self, dt: datetime, context: ScheduleContext) -> ScheduleResult | None:
        assert dt.tzinfo is not None
        if self.override is None:
            return None

        slot_start = normalize_datetime(self.override.start, dt.tzinfo)
        slot_end = (
            normalize_datetime(self.override.end, dt.tzinfo)
            if self.override.end is not None
            else None
        )
        if dt < slot_start or (slot_end is not None and dt >= slot_end):
            return None

        return ScheduleResult(
            effective_location=self.override.location,
            assigned_location=self.override.location,
            source=self.id,
            reason=self.override.reason,
            priority=self.priority,
            period_start=slot_start,
            period_end=slot_end,
        )
