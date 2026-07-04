"""Declarative schedule configuration and rule builder.

A schedule is described as a plain JSON-serializable dict (stored in the
config entry options and edited through the options flow). This module
validates that format and translates it into engine rules.

It is pure Python: no Home Assistant dependency, fully unit-testable.

Schema overview::

    {
        "locations": ["home", "school", "father"],
        "weekly_slots": [
            {
                "location": "father",
                "start_day": 2, "start_time": "09:00",
                "end_day": 2, "end_time": "18:00",
                "week_parity": "odd",  # "odd" | "even" | null
                # Optional: extend the slot across adjacent public
                # holidays, with configurable handover times.
                "extend_start_on_holidays": false,
                "extend_end_on_holidays": false,
                "extended_start_time": null,  # "HH:MM" or null (slot time)
                "extended_end_time": null
            }
        ],
        "school": {
            "enabled": true,
            "location": "school",
            "days": [0, 1, 3, 4],
            "start_time": "08:30",
            "end_time": "16:30",
            "first_school_day": "2026-09-01",  # optional
            "closed_days": ["2027-05-07"]
        },
        "vacation_alternation": {
            "enabled": true,
            "even_year_first_location": "father",
            "odd_year_first_location": "home"
        },
        "school_holidays": {
            "source": "manual",  # "manual" | "fr_api"
            "zone": "C",         # for "fr_api"
            "periods": [
                {
                    "start": "2026-10-17", "end": "2026-11-02",
                    "name": "autumn", "alternate": true
                }
            ]
        },
        "date_ranges": [
            {
                "location": "father",
                "start": "2026-07-06T09:00", "end": "2026-07-19T18:00",
                "reason": "summer"
            }
        ],
        "public_holidays": {"country": "FR"}
    }
"""

from __future__ import annotations

from datetime import date, datetime, time
from typing import Any, Mapping, Sequence

from .rules import (
    DateRangeRule,
    DateRangeSlot,
    DefaultRule,
    ExceptionRule,
    ManualOverrideRule,
    ScheduleRule,
    SchoolRule,
    VacationAlternationRule,
    WeeklyScheduleRule,
    WeeklySlot,
)
from .utils.datetime import WeekParity
from .utils.holidays import PublicHolidayProvider, StaticPublicHolidays, french_public_holidays
from .utils.school_holidays import SchoolHolidayCalendar, SchoolHolidayPeriod

CONF_LOCATIONS = "locations"
CONF_WEEKLY_SLOTS = "weekly_slots"
CONF_SCHOOL = "school"
CONF_VACATION_ALTERNATION = "vacation_alternation"
CONF_SCHOOL_HOLIDAYS = "school_holidays"
CONF_DATE_RANGES = "date_ranges"
CONF_PUBLIC_HOLIDAYS = "public_holidays"
CONF_LOCATION_LABELS = "location_labels"
CONF_LOCATION_COLORS = "location_colors"

HOLIDAY_SOURCE_MANUAL = "manual"
HOLIDAY_SOURCE_FR_API = "fr_api"
HOLIDAY_SOURCES = (HOLIDAY_SOURCE_MANUAL, HOLIDAY_SOURCE_FR_API)

HOLIDAY_SOURCE_STATUS_MANUAL = "manual"
HOLIDAY_SOURCE_STATUS_API = "api"
HOLIDAY_SOURCE_STATUS_API_FALLBACK = "api_fallback"

PRIORITY_WEEKLY = 10
PRIORITY_SCHOOL = 20
PRIORITY_VACATION = 30
PRIORITY_DATE_RANGE = 40


class ScheduleConfigError(ValueError):
    """Raised when a schedule configuration is invalid."""

    def __init__(self, message: str, path: str | None = None) -> None:
        self.path = path
        super().__init__(f"{path}: {message}" if path else message)


def default_schedule_config() -> dict[str, Any]:
    """Return an empty but valid schedule configuration."""
    return {
        CONF_LOCATIONS: ["home", "school"],
        CONF_WEEKLY_SLOTS: [],
        CONF_SCHOOL: {
            "enabled": False,
            "location": "school",
            "days": [0, 1, 3, 4],
            "start_time": "08:30",
            "end_time": "16:30",
            "first_school_day": None,
            "closed_days": [],
        },
        CONF_VACATION_ALTERNATION: {
            "enabled": False,
            "even_year_first_location": "home",
            "odd_year_first_location": "home",
        },
        CONF_SCHOOL_HOLIDAYS: {
            "source": HOLIDAY_SOURCE_MANUAL,
            "zone": "C",
            "periods": [],
        },
        CONF_DATE_RANGES: [],
        CONF_PUBLIC_HOLIDAYS: {"country": "FR"},
        CONF_LOCATION_LABELS: {},
        CONF_LOCATION_COLORS: {},
    }


def _parse_time(value: Any, path: str) -> time:
    if isinstance(value, time):
        return value
    if not isinstance(value, str):
        raise ScheduleConfigError(f"expected a time string, got {value!r}", path)
    try:
        return time.fromisoformat(value)
    except ValueError as err:
        raise ScheduleConfigError(f"invalid time {value!r}", path) from err


def _parse_date(value: Any, path: str) -> date:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if not isinstance(value, str):
        raise ScheduleConfigError(f"expected a date string, got {value!r}", path)
    try:
        return date.fromisoformat(value)
    except ValueError as err:
        raise ScheduleConfigError(f"invalid date {value!r}", path) from err


def _parse_datetime(value: Any, path: str) -> datetime:
    if isinstance(value, datetime):
        return value
    if not isinstance(value, str):
        raise ScheduleConfigError(f"expected a datetime string, got {value!r}", path)
    try:
        return datetime.fromisoformat(value)
    except ValueError as err:
        raise ScheduleConfigError(f"invalid datetime {value!r}", path) from err


def _parse_weekday(value: Any, path: str) -> int:
    try:
        day = int(value)
    except (TypeError, ValueError) as err:
        raise ScheduleConfigError(f"invalid weekday {value!r}", path) from err
    if not 0 <= day <= 6:
        raise ScheduleConfigError(f"weekday must be 0-6 (Monday=0), got {day}", path)
    return day


def _parse_location(value: Any, path: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ScheduleConfigError(f"expected a non-empty location string, got {value!r}", path)
    return value.strip()


def _parse_parity(value: Any, path: str) -> WeekParity | None:
    if value in (None, "", "every"):
        return None
    try:
        return WeekParity(value)
    except ValueError as err:
        raise ScheduleConfigError(
            f"week_parity must be 'odd', 'even' or null, got {value!r}", path
        ) from err


def _build_weekly_rule(
    config: Mapping[str, Any], public_holidays: PublicHolidayProvider
) -> WeeklyScheduleRule | None:
    raw_slots = config.get(CONF_WEEKLY_SLOTS) or []
    if not isinstance(raw_slots, Sequence) or isinstance(raw_slots, str):
        raise ScheduleConfigError("expected a list", CONF_WEEKLY_SLOTS)
    if not raw_slots:
        return None

    slots: list[WeeklySlot] = []
    for index, raw in enumerate(raw_slots):
        path = f"{CONF_WEEKLY_SLOTS}[{index}]"
        start_day = _parse_weekday(raw.get("start_day"), f"{path}.start_day")
        end_day = _parse_weekday(raw.get("end_day"), f"{path}.end_day")
        start_time = _parse_time(raw.get("start_time"), f"{path}.start_time")
        end_time = _parse_time(raw.get("end_time"), f"{path}.end_time")
        if (start_day, start_time) >= (end_day, end_time):
            raise ScheduleConfigError("slot start must be before slot end", path)
        raw_extended_start = raw.get("extended_start_time")
        raw_extended_end = raw.get("extended_end_time")
        slots.append(
            WeeklySlot(
                location=_parse_location(raw.get("location"), f"{path}.location"),
                start_day=start_day,
                start_time=start_time,
                end_day=end_day,
                end_time=end_time,
                week_parity=_parse_parity(raw.get("week_parity"), f"{path}.week_parity"),
                extend_start_on_holidays=bool(raw.get("extend_start_on_holidays", False)),
                extend_end_on_holidays=bool(raw.get("extend_end_on_holidays", False)),
                extended_start_time=(
                    _parse_time(raw_extended_start, f"{path}.extended_start_time")
                    if raw_extended_start
                    else None
                ),
                extended_end_time=(
                    _parse_time(raw_extended_end, f"{path}.extended_end_time")
                    if raw_extended_end
                    else None
                ),
            )
        )
    return WeeklyScheduleRule(
        id="weekly_schedule",
        priority=PRIORITY_WEEKLY,
        slots=tuple(slots),
        public_holidays=public_holidays,
    )


def _build_holiday_periods(
    config: Mapping[str, Any],
    api_periods: Sequence[SchoolHolidayPeriod] | None,
) -> tuple[SchoolHolidayCalendar, SchoolHolidayCalendar]:
    """Return the (closed, alternation) school holiday calendars.

    ``closed`` contains every period during which school is closed.
    ``alternation`` contains only the periods eligible for week/week
    alternation.
    """
    holidays_config = config.get(CONF_SCHOOL_HOLIDAYS) or {}
    source = holidays_config.get("source", HOLIDAY_SOURCE_MANUAL)
    if source not in HOLIDAY_SOURCES:
        raise ScheduleConfigError(
            f"source must be one of {HOLIDAY_SOURCES}, got {source!r}",
            f"{CONF_SCHOOL_HOLIDAYS}.source",
        )

    closed: list[SchoolHolidayPeriod] = []
    alternating: list[SchoolHolidayPeriod] = []

    if api_periods is not None:
        for period in api_periods:
            closed.append(period)
            if period.alternate:
                alternating.append(period)
    else:
        raw_periods = holidays_config.get("periods") or []
        for index, raw in enumerate(raw_periods):
            path = f"{CONF_SCHOOL_HOLIDAYS}.periods[{index}]"
            start = _parse_date(raw.get("start"), f"{path}.start")
            end = _parse_date(raw.get("end"), f"{path}.end")
            if start >= end:
                raise ScheduleConfigError("period start must be before its end", path)
            period = SchoolHolidayPeriod(
                start=start,
                end=end,
                name=raw.get("name"),
                alternate=bool(raw.get("alternate", True)),
            )
            closed.append(period)
            if period.alternate:
                alternating.append(period)

    return (
        SchoolHolidayCalendar(periods=tuple(closed)),
        SchoolHolidayCalendar(periods=tuple(alternating)),
    )


def _build_public_holidays(config: Mapping[str, Any]) -> PublicHolidayProvider:
    holidays_config = config.get(CONF_PUBLIC_HOLIDAYS) or {}
    country = holidays_config.get("country", "FR")
    if country == "FR":
        return french_public_holidays()
    if country in (None, "", "none"):
        return StaticPublicHolidays(days=frozenset())
    raise ScheduleConfigError(
        f"unsupported country {country!r} (only 'FR' or 'none' in V0)",
        f"{CONF_PUBLIC_HOLIDAYS}.country",
    )


def _build_school_rule(
    config: Mapping[str, Any],
    closed_calendar: SchoolHolidayCalendar,
    public_holidays: PublicHolidayProvider,
) -> SchoolRule | None:
    school_config = config.get(CONF_SCHOOL) or {}
    if not school_config.get("enabled", False):
        return None

    days = school_config.get("days") or []
    if not days:
        raise ScheduleConfigError("school is enabled but has no days", f"{CONF_SCHOOL}.days")
    school_days = frozenset(
        _parse_weekday(day, f"{CONF_SCHOOL}.days[{index}]") for index, day in enumerate(days)
    )
    start_time = _parse_time(school_config.get("start_time"), f"{CONF_SCHOOL}.start_time")
    end_time = _parse_time(school_config.get("end_time"), f"{CONF_SCHOOL}.end_time")
    if start_time >= end_time:
        raise ScheduleConfigError("school start_time must be before end_time", CONF_SCHOOL)

    raw_first_day = school_config.get("first_school_day")
    first_school_day = (
        _parse_date(raw_first_day, f"{CONF_SCHOOL}.first_school_day")
        if raw_first_day
        else None
    )
    closed_days = frozenset(
        _parse_date(day, f"{CONF_SCHOOL}.closed_days[{index}]")
        for index, day in enumerate(school_config.get("closed_days") or [])
    )

    return SchoolRule(
        id="school",
        priority=PRIORITY_SCHOOL,
        school_days=school_days,
        start_time=start_time,
        end_time=end_time,
        holiday_calendar=closed_calendar,
        public_holidays=public_holidays,
        location=_parse_location(school_config.get("location", "school"), f"{CONF_SCHOOL}.location"),
        closed_days=closed_days,
        first_school_day=first_school_day,
    )


def _build_vacation_rule(
    config: Mapping[str, Any],
    alternation_calendar: SchoolHolidayCalendar,
) -> VacationAlternationRule | None:
    vacation_config = config.get(CONF_VACATION_ALTERNATION) or {}
    if not vacation_config.get("enabled", False):
        return None
    return VacationAlternationRule(
        id="vacation_alternation",
        priority=PRIORITY_VACATION,
        vacations=alternation_calendar,
        even_year_first_location=_parse_location(
            vacation_config.get("even_year_first_location"),
            f"{CONF_VACATION_ALTERNATION}.even_year_first_location",
        ),
        odd_year_first_location=_parse_location(
            vacation_config.get("odd_year_first_location"),
            f"{CONF_VACATION_ALTERNATION}.odd_year_first_location",
        ),
    )


def _build_date_range_rule(config: Mapping[str, Any]) -> DateRangeRule | None:
    raw_ranges = config.get(CONF_DATE_RANGES) or []
    if not raw_ranges:
        return None

    slots: list[DateRangeSlot] = []
    for index, raw in enumerate(raw_ranges):
        path = f"{CONF_DATE_RANGES}[{index}]"
        start = _parse_datetime(raw.get("start"), f"{path}.start")
        end = _parse_datetime(raw.get("end"), f"{path}.end")
        if start >= end:
            raise ScheduleConfigError("range start must be before its end", path)
        slots.append(
            DateRangeSlot(
                location=_parse_location(raw.get("location"), f"{path}.location"),
                start=start,
                end=end,
                reason=raw.get("reason"),
            )
        )
    return DateRangeRule(id="date_ranges", priority=PRIORITY_DATE_RANGE, slots=tuple(slots))


def build_rules(
    config: Mapping[str, Any],
    api_periods: Sequence[SchoolHolidayPeriod] | None = None,
) -> list[ScheduleRule]:
    """Build the engine rules from a declarative schedule configuration.

    ``api_periods`` replaces the configured manual periods when school
    holidays come from an external source (e.g. the French official API).

    Raises :class:`ScheduleConfigError` if the configuration is invalid.
    """
    closed_calendar, alternation_calendar = _build_holiday_periods(config, api_periods)
    public_holidays = _build_public_holidays(config)

    rules: list[ScheduleRule] = [DefaultRule()]

    weekly = _build_weekly_rule(config, public_holidays)
    if weekly is not None:
        rules.append(weekly)

    school = _build_school_rule(config, closed_calendar, public_holidays)
    if school is not None:
        rules.append(school)

    vacation = _build_vacation_rule(config, alternation_calendar)
    if vacation is not None:
        rules.append(vacation)

    date_ranges = _build_date_range_rule(config)
    if date_ranges is not None:
        rules.append(date_ranges)

    rules.append(ExceptionRule())
    rules.append(ManualOverrideRule())
    return rules


def validate_schedule_config(
    config: Mapping[str, Any],
    api_periods: Sequence[SchoolHolidayPeriod] | None = None,
) -> None:
    """Validate a schedule configuration, raising on the first error."""
    build_rules(config, api_periods=api_periods)
