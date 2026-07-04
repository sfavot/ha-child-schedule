"""School holiday calendar helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True, slots=True)
class SchoolHolidayPeriod:
    """A school holiday period.

    ``start`` is the first day without school (inclusive) and ``end`` is
    the day school resumes (exclusive). ``alternate`` controls whether
    the period participates in week/week alternation.
    """

    start: date
    end: date
    name: str | None = None
    alternate: bool = True

    def contains(self, day: date) -> bool:
        return self.start <= day < self.end


@dataclass(frozen=True, slots=True)
class SchoolHolidayCalendar:
    """A collection of school holiday periods."""

    periods: tuple[SchoolHolidayPeriod, ...]

    def is_school_holiday(self, day: date) -> bool:
        return self.period_for(day) is not None

    def period_for(self, day: date) -> SchoolHolidayPeriod | None:
        for period in self.periods:
            if period.contains(day):
                return period
        return None
