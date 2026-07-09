"""Datetime helpers for the schedule engine."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta, tzinfo
from enum import StrEnum


class WeekParity(StrEnum):
    """Parity of an ISO week number."""

    EVEN = "even"
    ODD = "odd"


def iso_week(day: date) -> int:
    """Return the ISO week number of a date."""
    return day.isocalendar().week


def week_parity(day: date) -> WeekParity:
    """Return the parity of the ISO week containing a date."""
    return WeekParity.EVEN if iso_week(day) % 2 == 0 else WeekParity.ODD


def week_monday(day: date) -> date:
    """Return the Monday of the ISO week containing a date."""
    return day - timedelta(days=day.weekday())


def first_monday_on_or_after(day: date) -> date:
    """Return the first Monday on or after a date."""
    return day + timedelta(days=(7 - day.weekday()) % 7)


def normalize_datetime(dt: datetime, tz: tzinfo) -> datetime:
    """Return an aware datetime in the given timezone.

    Naive datetimes are assumed to already be local to ``tz``.
    """
    if dt.tzinfo is None:
        return dt.replace(tzinfo=tz)
    return dt.astimezone(tz)


def combine_local(day: date, at: time, tz: tzinfo) -> datetime:
    """Combine a date and a time into an aware local datetime."""
    return datetime.combine(day, at, tzinfo=tz)


def normalize_ha_datetime_string(value: str) -> str:
    """Normalize malformed HA DateTimeSelector output.

    The UI sometimes submits ``YYYY-MM-DDTHH:MM:SS HH:MM:SS`` (date at midnight
    in ISO form, plus the chosen time). ``cv.datetime`` expects a single value.
    """
    if " " not in value:
        return value
    date_part, time_part = value.rsplit(" ", 1)
    if "T" not in date_part:
        return value
    return f"{date_part.split('T', 1)[0]} {time_part}"
