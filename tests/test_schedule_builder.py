"""Tests for the declarative schedule builder (no Home Assistant)."""

from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo

import pytest

from custom_components.child_schedule.demo import DEMO_SCHEDULE_CONFIG
from custom_components.child_schedule.engine import ScheduleEngine
from custom_components.child_schedule.models import Child
from custom_components.child_schedule.rules import (
    DateRangeRule,
    DefaultRule,
    ExceptionRule,
    ManualOverrideRule,
    SchoolRule,
    VacationAlternationRule,
    WeeklyScheduleRule,
)
from custom_components.child_schedule.schedule_builder import (
    ScheduleConfigError,
    build_rules,
    default_schedule_config,
    validate_schedule_config,
)
from custom_components.child_schedule.utils.school_holidays import SchoolHolidayPeriod

TZ = ZoneInfo("Europe/Paris")


def test_default_config_builds_minimal_rules() -> None:
    rules = build_rules(default_schedule_config())
    assert [type(rule) for rule in rules] == [
        DefaultRule,
        ExceptionRule,
        ManualOverrideRule,
    ]


def test_demo_config_builds_all_rules() -> None:
    rules = build_rules(DEMO_SCHEDULE_CONFIG)
    assert [type(rule) for rule in rules] == [
        DefaultRule,
        WeeklyScheduleRule,
        SchoolRule,
        VacationAlternationRule,
        DateRangeRule,
        ExceptionRule,
        ManualOverrideRule,
    ]


def test_demo_config_is_valid() -> None:
    validate_schedule_config(DEMO_SCHEDULE_CONFIG)


def test_built_rules_behave_like_engine_rules() -> None:
    engine = ScheduleEngine(
        child=Child(id="test", name="Test", default_location="home"),
        timezone="Europe/Paris",
        rules=build_rules(DEMO_SCHEDULE_CONFIG),
    )
    # Monday 2026-09-07 09:00 is a school day.
    result = engine.evaluate(datetime(2026, 9, 7, 9, 0, tzinfo=TZ))
    assert result.effective_location == "school"
    assert result.assigned_location == "home"


def test_summer_period_excluded_from_alternation() -> None:
    rules = build_rules(DEMO_SCHEDULE_CONFIG)
    vacation = next(r for r in rules if isinstance(r, VacationAlternationRule))
    school = next(r for r in rules if isinstance(r, SchoolRule))
    # Summer 2027 closes school but does not alternate.
    summer_day = date(2027, 7, 15)
    assert school.holiday_calendar.is_school_holiday(summer_day)
    assert not vacation.vacations.is_school_holiday(summer_day)


def test_api_periods_override_manual_periods() -> None:
    api_periods = [
        SchoolHolidayPeriod(date(2026, 10, 17), date(2026, 11, 2), "Vacances de la Toussaint"),
        SchoolHolidayPeriod(
            date(2027, 7, 3),
            date(2027, 9, 1),
            "Début des Vacances d'Été",
            alternate=False,
        ),
    ]
    rules = build_rules(DEMO_SCHEDULE_CONFIG, api_periods=api_periods)
    school = next(r for r in rules if isinstance(r, SchoolRule))
    vacation = next(r for r in rules if isinstance(r, VacationAlternationRule))
    assert school.holiday_calendar.is_school_holiday(date(2026, 10, 20))
    # Christmas (manual period) is replaced by the API data.
    assert not school.holiday_calendar.is_school_holiday(date(2026, 12, 24))
    # Summer from the API is excluded from alternation by name.
    assert not vacation.vacations.is_school_holiday(date(2027, 7, 15))
    assert vacation.vacations.is_school_holiday(date(2026, 10, 20))


@pytest.mark.parametrize(
    "mutation, path_fragment",
    [
        (
            {"weekly_slots": [{"location": "x", "start_day": 9, "start_time": "09:00", "end_day": 1, "end_time": "10:00"}]},
            "start_day",
        ),
        (
            {"weekly_slots": [{"location": "x", "start_day": 1, "start_time": "18:00", "end_day": 1, "end_time": "09:00"}]},
            "weekly_slots[0]",
        ),
        (
            {"weekly_slots": [{"location": "x", "start_day": 1, "start_time": "bad", "end_day": 1, "end_time": "10:00"}]},
            "start_time",
        ),
        (
            {"weekly_slots": [{"location": "x", "start_day": 1, "start_time": "09:00", "end_day": 1, "end_time": "10:00", "week_parity": "weird"}]},
            "week_parity",
        ),
        (
            {"school": {"enabled": True, "days": [], "start_time": "08:30", "end_time": "16:30"}},
            "school.days",
        ),
        (
            {"school_holidays": {"source": "manual", "periods": [{"start": "2026-11-02", "end": "2026-10-17"}]}},
            "periods[0]",
        ),
        (
            {"school_holidays": {"source": "unknown_source"}},
            "source",
        ),
        (
            {"date_ranges": [{"location": "x", "start": "2026-07-19T18:00", "end": "2026-07-06T09:00"}]},
            "date_ranges[0]",
        ),
        (
            {"public_holidays": {"country": "XX"}},
            "country",
        ),
        (
            {"vacation_alternation": {"enabled": True, "even_year_first_location": "", "odd_year_first_location": "home"}},
            "even_year_first_location",
        ),
    ],
)
def test_invalid_configs_raise_with_path(mutation: dict, path_fragment: str) -> None:
    config = default_schedule_config()
    config.update(mutation)
    with pytest.raises(ScheduleConfigError) as excinfo:
        validate_schedule_config(config)
    assert path_fragment in str(excinfo.value)


def test_holiday_extension_with_custom_handover_times() -> None:
    """Extended days can use family-specific handover times."""
    config = default_schedule_config()
    config["weekly_slots"] = [
        {
            "location": "father",
            "start_day": 4,
            "start_time": "16:30",
            "end_day": 6,
            "end_time": "18:00",
            "week_parity": "even",
            "extend_start_on_holidays": True,
            "extend_end_on_holidays": True,
            "extended_start_time": "09:00",
            "extended_end_time": "10:00",
        }
    ]
    engine = ScheduleEngine(
        child=Child(id="test", name="Test", default_location="home"),
        timezone="Europe/Paris",
        rules=build_rules(config),
    )
    # Ascension Thursday 2027-05-06 (before even-week-18 weekend):
    # extended start uses 09:00 instead of 16:30.
    assert engine.evaluate(datetime(2027, 5, 6, 9, 0, tzinfo=TZ)).assigned_location == "father"
    assert engine.evaluate(datetime(2027, 5, 6, 8, 59, tzinfo=TZ)).assigned_location == "home"
    # Easter Monday 2027-03-29 (after even-week-12 weekend):
    # extended end uses 10:00 instead of 18:00.
    assert engine.evaluate(datetime(2027, 3, 29, 9, 59, tzinfo=TZ)).assigned_location == "father"
    assert engine.evaluate(datetime(2027, 3, 29, 10, 0, tzinfo=TZ)).assigned_location == "home"


def test_holiday_extension_disabled_by_default() -> None:
    config = default_schedule_config()
    config["weekly_slots"] = [
        {
            "location": "father",
            "start_day": 4,
            "start_time": "16:30",
            "end_day": 6,
            "end_time": "18:00",
            "week_parity": "even",
        }
    ]
    engine = ScheduleEngine(
        child=Child(id="test", name="Test", default_location="home"),
        timezone="Europe/Paris",
        rules=build_rules(config),
    )
    # Easter Monday 2027-03-29: without extension the child is home.
    assert engine.evaluate(datetime(2027, 3, 29, 12, 0, tzinfo=TZ)).assigned_location == "home"


def test_time_accepts_seconds_and_datetime_accepts_space() -> None:
    """The options flow selectors produce HH:MM:SS and 'date time' formats."""
    config = default_schedule_config()
    config["weekly_slots"] = [
        {
            "location": "grandparents",
            "start_day": 5,
            "start_time": "09:00:00",
            "end_day": 5,
            "end_time": "12:00:00",
            "week_parity": None,
        }
    ]
    config["date_ranges"] = [
        {
            "location": "camp",
            "start": "2026-07-06 09:00:00",
            "end": "2026-07-19 18:00:00",
        }
    ]
    rules = build_rules(config)
    engine = ScheduleEngine(
        child=Child(id="test", name="Test", default_location="home"),
        timezone="Europe/Paris",
        rules=rules,
    )
    assert (
        engine.evaluate(datetime(2026, 9, 5, 10, 0, tzinfo=TZ)).effective_location
        == "grandparents"
    )
    assert (
        engine.evaluate(datetime(2026, 7, 10, 10, 0, tzinfo=TZ)).effective_location
        == "camp"
    )
