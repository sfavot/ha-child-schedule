"""School effective-location rule."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from typing import ClassVar

from ..models import ScheduleContext, ScheduleResult
from ..utils.datetime import combine_local
from ..utils.holidays import PublicHolidayProvider
from ..utils.school_holidays import SchoolHolidayCalendar
from .base import ScheduleRule

_ONE_DAY = timedelta(days=1)


@dataclass
class SchoolRule(ScheduleRule):
    """Marks the child as effectively at school during school hours."""

    id: str
    school_days: frozenset[int]
    start_time: time
    end_time: time
    holiday_calendar: SchoolHolidayCalendar
    public_holidays: PublicHolidayProvider
    location: str = "school"
    closed_days: frozenset[date] = field(default_factory=frozenset)
    priority: int = 20
    first_school_day: date | None = None

    overrides_assigned: ClassVar[bool] = False

    def _is_school_day(self, day: date) -> bool:
        if day.weekday() not in self.school_days:
            return False
        if self.first_school_day is not None and day < self.first_school_day:
            return False
        if self.holiday_calendar.is_school_holiday(day):
            return False
        if self.public_holidays.is_public_holiday(day):
            return False
        if day in self.closed_days:
            return False
        return True

    def transition_times(
        self,
        start: datetime,
        end: datetime,
        context: ScheduleContext,
    ) -> list[datetime]:
        assert start.tzinfo is not None
        times: list[datetime] = []
        day = start.date()
        end_day = end.date()
        while day <= end_day:
            if self._is_school_day(day):
                for moment in (
                    combine_local(day, self.start_time, start.tzinfo),
                    combine_local(day, self.end_time, start.tzinfo),
                ):
                    if start < moment <= end:
                        times.append(moment)
            day += _ONE_DAY
        return times

    def evaluate(self, dt: datetime, context: ScheduleContext) -> ScheduleResult | None:
        assert dt.tzinfo is not None
        day = dt.date()
        if not self._is_school_day(day):
            return None

        start = combine_local(day, self.start_time, dt.tzinfo)
        end = combine_local(day, self.end_time, dt.tzinfo)
        if not start <= dt < end:
            return None

        return ScheduleResult(
            effective_location=self.location,
            assigned_location=self.location,
            source=self.id,
            priority=self.priority,
            period_start=start,
            period_end=end,
        )
