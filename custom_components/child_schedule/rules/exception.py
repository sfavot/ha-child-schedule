"""One-off exception rule."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import uuid4

from ..models import ScheduleContext, ScheduleResult
from ..utils.datetime import normalize_datetime
from .base import ScheduleRule


@dataclass(slots=True)
class ScheduleException:
    """A one-off exception to the planned schedule (end exclusive)."""

    location: str
    start: datetime
    end: datetime
    reason: str | None = None
    id: str = field(default_factory=lambda: str(uuid4()))


@dataclass
class ExceptionRule(ScheduleRule):
    """Applies one-off exceptions on top of the planned schedule."""

    id: str = "exception"
    exceptions: list[ScheduleException] = field(default_factory=list)
    priority: int = 80

    def set_exceptions(self, exceptions: list[ScheduleException]) -> None:
        self.exceptions = list(exceptions)

    def add(self, exception: ScheduleException) -> None:
        self.exceptions.append(exception)

    def remove(self, exception_id: str) -> None:
        self.exceptions = [item for item in self.exceptions if item.id != exception_id]

    def transition_times(
        self,
        start: datetime,
        end: datetime,
        context: ScheduleContext,
    ) -> list[datetime]:
        assert start.tzinfo is not None
        times: list[datetime] = []
        for exception in self.exceptions:
            slot_start = normalize_datetime(exception.start, start.tzinfo)
            slot_end = normalize_datetime(exception.end, start.tzinfo)
            for moment in (slot_start, slot_end):
                if start < moment <= end:
                    times.append(moment)
        return times

    def evaluate(self, dt: datetime, context: ScheduleContext) -> ScheduleResult | None:
        assert dt.tzinfo is not None
        for exception in self.exceptions:
            slot_start = normalize_datetime(exception.start, dt.tzinfo)
            slot_end = normalize_datetime(exception.end, dt.tzinfo)
            if slot_start <= dt < slot_end:
                return ScheduleResult(
                    effective_location=exception.location,
                    assigned_location=exception.location,
                    source=self.id,
                    reason=exception.reason,
                    priority=self.priority,
                    period_start=slot_start,
                    period_end=slot_end,
                )
        return None
