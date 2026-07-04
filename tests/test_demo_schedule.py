"""Tests for the demo (Alex) schedule, exercising the generic rules.

Reference dates (school year 2026-2027):
- 2026-09-04 is a Friday in even ISO week 36.
- 2026-09-06 is the following Sunday (even week).
- 2026-09-07 is a Monday in odd ISO week 37 (regular school day).
- 2026-09-09 is a Wednesday in odd ISO week 37.
"""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from custom_components.child_schedule.demo import build_demo_engine
from custom_components.child_schedule.engine import ScheduleEngine

TZ = ZoneInfo("Europe/Paris")


@pytest.fixture
def engine() -> ScheduleEngine:
    return build_demo_engine()


def at(*args: int) -> datetime:
    return datetime(*args, tzinfo=TZ)


class TestRegularWeeklySchedule:
    def test_even_week_friday_before_handover(self, engine: ScheduleEngine) -> None:
        result = engine.evaluate(at(2026, 9, 4, 16, 29))
        assert result.assigned_location == "home"

    def test_even_week_friday_at_handover(self, engine: ScheduleEngine) -> None:
        result = engine.evaluate(at(2026, 9, 4, 16, 30))
        assert result.assigned_location == "parent_b"

    def test_even_week_sunday_before_return(self, engine: ScheduleEngine) -> None:
        result = engine.evaluate(at(2026, 9, 6, 17, 59))
        assert result.assigned_location == "parent_b"

    def test_even_week_sunday_at_return(self, engine: ScheduleEngine) -> None:
        result = engine.evaluate(at(2026, 9, 6, 18, 0))
        assert result.assigned_location == "home"

    def test_odd_week_wednesday_start(self, engine: ScheduleEngine) -> None:
        result = engine.evaluate(at(2026, 9, 9, 9, 0))
        assert result.assigned_location == "parent_b"

    def test_odd_week_wednesday_end(self, engine: ScheduleEngine) -> None:
        result = engine.evaluate(at(2026, 9, 9, 18, 0))
        assert result.assigned_location == "home"


class TestSchool:
    def test_school_day_effective_location(self, engine: ScheduleEngine) -> None:
        result = engine.evaluate(at(2026, 9, 7, 9, 0))
        assert result.effective_location == "school"
        assert result.assigned_location == "home"

    def test_school_preserves_assigned_location_parent_b(
        self, engine: ScheduleEngine
    ) -> None:
        # Friday 2026-09-18 is in even ISO week 38: parent_b weekend starts
        # at 16:30 but school runs until 16:30, so at 16:00 the child is
        # at school while still assigned home.
        result = engine.evaluate(at(2026, 9, 7, 16, 0))
        assert result.effective_location == "school"
        assert result.assigned_location == "home"
        assert result.source == "school"

    def test_no_school_on_wednesday(self, engine: ScheduleEngine) -> None:
        result = engine.evaluate(at(2026, 9, 9, 10, 0))
        assert result.effective_location != "school"

    def test_no_school_during_school_holidays(self, engine: ScheduleEngine) -> None:
        # Monday 2026-10-19 is inside the autumn holidays.
        result = engine.evaluate(at(2026, 10, 19, 9, 0))
        assert result.effective_location != "school"

    def test_no_school_on_public_holiday(self, engine: ScheduleEngine) -> None:
        # Wednesday 2026-11-11 is Armistice Day; Thursday 2027-05-06 is
        # Ascension Day (a Thursday school day).
        result = engine.evaluate(at(2027, 5, 6, 9, 0))
        assert result.effective_location != "school"

    def test_no_school_on_bridge_day(self, engine: ScheduleEngine) -> None:
        # Friday 2027-05-07 is a bridge day.
        result = engine.evaluate(at(2027, 5, 7, 9, 0))
        assert result.effective_location != "school"

    def test_school_outside_hours(self, engine: ScheduleEngine) -> None:
        result = engine.evaluate(at(2026, 9, 7, 8, 29))
        assert result.effective_location != "school"
        result = engine.evaluate(at(2026, 9, 7, 16, 30))
        assert result.effective_location != "school"


class TestVacationAlternation:
    def test_first_vacation_weekend_keeps_regular_schedule(
        self, engine: ScheduleEngine
    ) -> None:
        # Autumn holidays start Saturday 2026-10-17 (even ISO week 42):
        # the even-week parent_b weekend still applies until Sunday 18:00.
        result = engine.evaluate(at(2026, 10, 17, 12, 0))
        assert result.assigned_location == "parent_b"
        assert result.source == "weekly_schedule"
        result = engine.evaluate(at(2026, 10, 18, 18, 0))
        assert result.assigned_location == "home"

    def test_even_year_first_vacation_week_is_parent_b(
        self, engine: ScheduleEngine
    ) -> None:
        # First Monday of the autumn 2026 holidays (even year).
        result = engine.evaluate(at(2026, 10, 19, 12, 0))
        assert result.assigned_location == "parent_b"
        assert result.source == "vacation_alternation"

    def test_alternation_second_week(self, engine: ScheduleEngine) -> None:
        result = engine.evaluate(at(2026, 10, 26, 12, 0))
        assert result.assigned_location == "home"
        assert result.source == "vacation_alternation"

    def test_alternation_ends_when_school_resumes(
        self, engine: ScheduleEngine
    ) -> None:
        # Monday 2026-11-02 school resumes: back to school + regular schedule.
        result = engine.evaluate(at(2026, 11, 2, 9, 0))
        assert result.effective_location == "school"
        assert result.assigned_location == "home"

    def test_odd_year_first_vacation_week_is_home(
        self, engine: ScheduleEngine
    ) -> None:
        # Winter 2027 holidays start 2027-02-06 (odd year); first Monday
        # is 2027-02-08 => home week, then parent_b week.
        result = engine.evaluate(at(2027, 2, 8, 12, 0))
        assert result.assigned_location == "home"
        assert result.source == "vacation_alternation"
        result = engine.evaluate(at(2027, 2, 15, 12, 0))
        assert result.assigned_location == "parent_b"


class TestSummer2026:
    def test_first_parent_b_period_start(self, engine: ScheduleEngine) -> None:
        result = engine.evaluate(at(2026, 7, 6, 9, 0))
        assert result.assigned_location == "parent_b"

    def test_first_parent_b_period_end(self, engine: ScheduleEngine) -> None:
        result = engine.evaluate(at(2026, 7, 19, 18, 0))
        assert result.assigned_location == "home"

    def test_second_parent_b_period_start(self, engine: ScheduleEngine) -> None:
        result = engine.evaluate(at(2026, 8, 10, 9, 0))
        assert result.assigned_location == "parent_b"

    def test_second_parent_b_period_end(self, engine: ScheduleEngine) -> None:
        result = engine.evaluate(at(2026, 8, 23, 18, 0))
        assert result.assigned_location == "home"

    def test_between_parent_b_periods_is_home(self, engine: ScheduleEngine) -> None:
        result = engine.evaluate(at(2026, 8, 1, 12, 0))
        assert result.assigned_location == "home"

    def test_summer_home_overrides_weekly_parent_b_weekend(
        self, engine: ScheduleEngine
    ) -> None:
        # Friday 2026-07-24 is in even ISO week 30: the weekly rule would
        # assign parent_b, but the summer 2026 schedule keeps home.
        result = engine.evaluate(at(2026, 7, 24, 17, 0))
        assert result.assigned_location == "home"
        assert result.source == "date_ranges"


class TestHolidayExtendedWeekends:
    """Public holidays adjacent to a parent_b weekend extend it.

    - Easter Monday 2027-03-29 follows the even-week (12) parent_b weekend.
    - Ascension Thursday 2027-05-06 precedes the even-week (18) parent_b
      weekend, with the Friday 2027-05-07 bridge day in between.
    """

    def test_easter_monday_extends_weekend_end(self, engine: ScheduleEngine) -> None:
        # Sunday 18:00 would normally be the handover; the weekend now
        # runs until Monday 18:00.
        result = engine.evaluate(at(2027, 3, 28, 19, 0))
        assert result.assigned_location == "parent_b"
        result = engine.evaluate(at(2027, 3, 29, 12, 0))
        assert result.assigned_location == "parent_b"
        result = engine.evaluate(at(2027, 3, 29, 18, 0))
        assert result.assigned_location == "home"

    def test_no_school_on_easter_monday(self, engine: ScheduleEngine) -> None:
        result = engine.evaluate(at(2027, 3, 29, 10, 0))
        assert result.effective_location != "school"

    def test_ascension_extends_weekend_start(self, engine: ScheduleEngine) -> None:
        # The weekend starts Thursday 16:30 (holiday) instead of Friday.
        result = engine.evaluate(at(2027, 5, 6, 16, 29))
        assert result.assigned_location == "home"
        result = engine.evaluate(at(2027, 5, 6, 17, 0))
        assert result.assigned_location == "parent_b"
        # Bridge Friday is inside the extended weekend, no school.
        result = engine.evaluate(at(2027, 5, 7, 12, 0))
        assert result.assigned_location == "parent_b"
        assert result.effective_location != "school"
        # Regular end: Sunday 18:00 (no holiday after).
        result = engine.evaluate(at(2027, 5, 9, 18, 0))
        assert result.assigned_location == "home"

    def test_whit_monday_without_preceding_parent_b_weekend(
        self, engine: ScheduleEngine
    ) -> None:
        # Whit Monday 2027-05-17 follows an odd-week (19) home weekend:
        # nothing to extend, the child stays home (and no school).
        result = engine.evaluate(at(2027, 5, 17, 12, 0))
        assert result.assigned_location == "home"
        assert result.effective_location != "school"

    def test_wednesday_slot_not_extended(self, engine: ScheduleEngine) -> None:
        # Armistice Day 2026-11-11 is a Wednesday in even week 46: the
        # odd-week Wednesday slot has no extension flags and the parity
        # does not match anyway.
        result = engine.evaluate(at(2026, 11, 11, 12, 0))
        assert result.assigned_location == "home"


class TestNextChange:
    def test_next_change_on_school_day(self, engine: ScheduleEngine) -> None:
        # Monday 2026-09-07 07:00: next change is school start at 08:30.
        change = engine.next_change(at(2026, 9, 7, 7, 0))
        assert change == at(2026, 9, 7, 8, 30)

    def test_timeline_school_day(self, engine: ScheduleEngine) -> None:
        segments = engine.timeline(at(2026, 9, 7, 0, 0), at(2026, 9, 8, 0, 0))
        locations = [s.result.effective_location for s in segments]
        assert locations == ["home", "school", "home"]

    def test_assigned_timeline_merges_school(self, engine: ScheduleEngine) -> None:
        segments = engine.assigned_timeline(
            at(2026, 9, 7, 0, 0), at(2026, 9, 8, 0, 0)
        )
        assert len(segments) == 1
        assert segments[0].result.assigned_location == "home"

    def test_assigned_timeline_weekend_parent_b(self, engine: ScheduleEngine) -> None:
        # Even week 36: Fri 2026-09-04 16:30 to Sun 2026-09-06 18:00.
        segments = engine.assigned_timeline(
            at(2026, 9, 4, 0, 0), at(2026, 9, 7, 0, 0)
        )
        parent_b_segments = [
            s for s in segments if s.result.assigned_location == "parent_b"
        ]
        assert len(parent_b_segments) == 1
        assert parent_b_segments[0].start == at(2026, 9, 4, 16, 30)
        assert parent_b_segments[0].end == at(2026, 9, 6, 18, 0)
