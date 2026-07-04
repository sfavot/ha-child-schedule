"""Convert schedule evaluation into calendar-friendly all-day blocks."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, tzinfo

from ..models import ScheduleResult
from .datetime import combine_local

# Reference moment used to pick one location per calendar day.
CALENDAR_DAY_REFERENCE_TIME = time(17, 0)


@dataclass(frozen=True, slots=True)
class AllDayCalendarBlock:
    """A merged all-day custody block for one location."""

    start: date
    end: date
    location: str


def build_allday_blocks(
    evaluate: Callable[[datetime], ScheduleResult],
    tzinfo: tzinfo,
    range_start: datetime,
    range_end: datetime,
) -> list[AllDayCalendarBlock]:
    """Build merged all-day blocks for a month-style calendar view.

    Each day shows a single location, evaluated at
    ``CALENDAR_DAY_REFERENCE_TIME`` (after school and typical handovers).
    Consecutive days with the same location are merged into one bar.
    """
    if range_end <= range_start:
        return []

    local_start = _as_local(range_start, tzinfo)
    local_end = _as_local(range_end, tzinfo)
    first_day = local_start.date()
    last_day = _exclusive_end_date(local_end)

    blocks: list[AllDayCalendarBlock] = []
    day = first_day
    while day < last_day:
        location = _location_on_day(evaluate, tzinfo, day)
        block_start = day
        day += timedelta(days=1)
        while day < last_day and _location_on_day(evaluate, tzinfo, day) == location:
            day += timedelta(days=1)
        blocks.append(
            AllDayCalendarBlock(start=block_start, end=day, location=location)
        )
    return blocks


def block_for_date(
    evaluate: Callable[[datetime], ScheduleResult],
    tzinfo: tzinfo,
    day: date,
) -> AllDayCalendarBlock:
    """Return the all-day block covering ``day``."""
    location = _location_on_day(evaluate, tzinfo, day)
    return AllDayCalendarBlock(
        start=day,
        end=day + timedelta(days=1),
        location=location,
    )


def _location_on_day(
    evaluate: Callable[[datetime], ScheduleResult],
    tzinfo: tzinfo,
    day: date,
) -> str:
    moment = combine_local(day, CALENDAR_DAY_REFERENCE_TIME, tzinfo)
    return evaluate(moment).assigned_location


def _as_local(moment: datetime, tzinfo: tzinfo) -> datetime:
    if moment.tzinfo is None:
        return moment.replace(tzinfo=tzinfo)
    return moment.astimezone(tzinfo)


def _exclusive_end_date(moment: datetime) -> date:
    """Return the exclusive end date for a calendar query ending at ``moment``."""
    if moment.time() == time.min:
        return moment.date()
    return moment.date() + timedelta(days=1)
