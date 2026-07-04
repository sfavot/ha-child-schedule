"""School vacation alternation rule."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from ..models import ScheduleContext, ScheduleResult
from ..utils.datetime import combine_local, first_monday_on_or_after
from ..utils.school_holidays import SchoolHolidayCalendar
from .base import ScheduleRule

_MIDNIGHT_WEEK = timedelta(days=7)


@dataclass
class VacationAlternationRule(ScheduleRule):
    """Alternates the assigned location week by week during vacations.

    The regular weekly schedule keeps applying until the first Monday of
    each vacation period (this rule does not match before it). From that
    Monday, full weeks alternate between two locations until the end of
    the vacation.

    The location of the first alternation week depends on the parity of
    the calendar year in which the vacation starts:
    ``even_year_first_location`` for even years,
    ``odd_year_first_location`` for odd years.
    """

    id: str
    vacations: SchoolHolidayCalendar
    even_year_first_location: str
    odd_year_first_location: str
    priority: int = 30

    def evaluate(self, dt: datetime, context: ScheduleContext) -> ScheduleResult | None:
        assert dt.tzinfo is not None
        period = self.vacations.period_for(dt.date())
        if period is None:
            return None

        first_monday = first_monday_on_or_after(period.start)
        alternation_start = combine_local(
            first_monday, datetime.min.time(), dt.tzinfo
        )
        vacation_end = combine_local(period.end, datetime.min.time(), dt.tzinfo)
        if not alternation_start <= dt < vacation_end:
            return None

        week_index = (dt - alternation_start).days // 7
        if period.start.year % 2 == 0:
            first_location = self.even_year_first_location
            other_location = self.odd_year_first_location
        else:
            first_location = self.odd_year_first_location
            other_location = self.even_year_first_location
        location = first_location if week_index % 2 == 0 else other_location

        week_start = alternation_start + week_index * _MIDNIGHT_WEEK
        week_end = min(week_start + _MIDNIGHT_WEEK, vacation_end)

        return ScheduleResult(
            effective_location=location,
            assigned_location=location,
            source=self.id,
            reason=period.name,
            priority=self.priority,
            period_start=week_start,
            period_end=week_end,
        )

    def transition_times(
        self,
        start: datetime,
        end: datetime,
        context: ScheduleContext,
    ) -> list[datetime]:
        assert start.tzinfo is not None
        times: list[datetime] = []
        for period in self.vacations.periods:
            first_monday = first_monday_on_or_after(period.start)
            alternation_start = combine_local(
                first_monday, datetime.min.time(), start.tzinfo
            )
            vacation_end = combine_local(period.end, datetime.min.time(), start.tzinfo)
            if alternation_start >= end or vacation_end <= start:
                continue
            moment = alternation_start
            while moment < vacation_end:
                if start < moment <= end:
                    times.append(moment)
                next_moment = moment + _MIDNIGHT_WEEK
                if next_moment <= moment:
                    break
                moment = next_moment
            if start < vacation_end <= end:
                times.append(vacation_end)
        return times
