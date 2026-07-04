"""Recurring weekly schedule rule."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, tzinfo

from ..models import ScheduleContext, ScheduleResult
from ..utils.datetime import WeekParity, combine_local, week_monday, week_parity
from ..utils.holidays import PublicHolidayProvider
from .base import ScheduleRule

MONDAY = 0
TUESDAY = 1
WEDNESDAY = 2
THURSDAY = 3
FRIDAY = 4
SATURDAY = 5
SUNDAY = 6

_ONE_DAY = timedelta(days=1)


@dataclass(frozen=True, slots=True)
class WeeklySlot:
    """A recurring weekly time slot assigned to a location.

    Days are weekday numbers (0 = Monday). A slot may span several days
    within the same ISO week (e.g. Friday 16:30 to Sunday 18:00), but may
    not cross the week boundary. ``week_parity`` restricts the slot to
    even or odd ISO weeks; ``None`` means every week.

    Public holiday extension (opt-in, handover times are family-specific
    so everything is configurable per slot):
    - ``extend_start_on_holidays``: when the day(s) right before the slot
      start are public holidays, the slot starts on the first holiday of
      that chain instead.
    - ``extend_end_on_holidays``: when the day(s) right after the slot
      end are public holidays, the slot ends on the last holiday instead.
    - ``extended_start_time`` / ``extended_end_time``: handover times used
      on the extended days; ``None`` keeps the slot's regular times.
    """

    location: str
    start_day: int
    start_time: time
    end_day: int
    end_time: time
    week_parity: WeekParity | None = None
    extend_start_on_holidays: bool = False
    extend_end_on_holidays: bool = False
    extended_start_time: time | None = None
    extended_end_time: time | None = None


@dataclass
class WeeklyScheduleRule(ScheduleRule):
    """Assigns locations based on recurring weekly slots.

    ``public_holidays`` is only needed when slots use holiday extension.
    """

    id: str
    slots: tuple[WeeklySlot, ...]
    priority: int = 10
    public_holidays: PublicHolidayProvider | None = None

    def _slot_window(
        self, slot: WeeklySlot, monday: date, tz: tzinfo
    ) -> tuple[datetime, datetime]:
        start_day = monday + timedelta(days=slot.start_day)
        end_day = monday + timedelta(days=slot.end_day)
        start_time = slot.start_time
        end_time = slot.end_time

        if self.public_holidays is not None:
            if slot.extend_start_on_holidays:
                extended = False
                while self.public_holidays.is_public_holiday(start_day - _ONE_DAY):
                    start_day -= _ONE_DAY
                    extended = True
                if extended and slot.extended_start_time is not None:
                    start_time = slot.extended_start_time
            if slot.extend_end_on_holidays:
                extended = False
                while self.public_holidays.is_public_holiday(end_day + _ONE_DAY):
                    end_day += _ONE_DAY
                    extended = True
                if extended and slot.extended_end_time is not None:
                    end_time = slot.extended_end_time

        return (
            combine_local(start_day, start_time, tz),
            combine_local(end_day, end_time, tz),
        )

    def transition_times(
        self,
        start: datetime,
        end: datetime,
        context: ScheduleContext,
    ) -> list[datetime]:
        assert start.tzinfo is not None
        times: list[datetime] = []
        first_monday = week_monday(start.date()) - _ONE_DAY * 7
        last_monday = week_monday(end.date()) + _ONE_DAY * 7
        monday = first_monday
        while monday <= last_monday:
            parity = week_parity(monday)
            for slot in self.slots:
                if slot.week_parity is not None and slot.week_parity != parity:
                    continue
                slot_start, slot_end = self._slot_window(slot, monday, start.tzinfo)
                for moment in (slot_start, slot_end):
                    if start < moment <= end:
                        times.append(moment)
            monday += _ONE_DAY * 7
        return times

    def evaluate(self, dt: datetime, context: ScheduleContext) -> ScheduleResult | None:
        assert dt.tzinfo is not None
        current_monday = week_monday(dt.date())

        # Extended windows can spill outside their own ISO week, so the
        # neighbouring weeks' slots are considered too.
        for week_offset in (-1, 0, 1):
            monday = current_monday + timedelta(weeks=week_offset)
            parity = week_parity(monday)
            for slot in self.slots:
                if slot.week_parity is not None and slot.week_parity != parity:
                    continue
                start, end = self._slot_window(slot, monday, dt.tzinfo)
                if start <= dt < end:
                    return ScheduleResult(
                        effective_location=slot.location,
                        assigned_location=slot.location,
                        source=self.id,
                        priority=self.priority,
                        period_start=start,
                        period_end=end,
                    )
        return None
