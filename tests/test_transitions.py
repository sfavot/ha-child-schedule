"""Tests for boundary-based next change detection."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from custom_components.child_schedule.demo import build_demo_rules
from custom_components.child_schedule.engine import ScheduleEngine, collect_transition_times, find_next_change
from custom_components.child_schedule.models import Child, ScheduleContext

TZ = ZoneInfo("Europe/Paris")

CHILD = Child(id="alex", name="Alex", default_location="home")


def _engine() -> ScheduleEngine:
    return ScheduleEngine(child=CHILD, timezone="Europe/Paris", rules=build_demo_rules())


def test_collect_transition_times_includes_school_start() -> None:
    engine = _engine()
    start = datetime(2026, 9, 7, 7, 0, tzinfo=TZ)
    end = datetime(2026, 9, 7, 18, 0, tzinfo=TZ)
    context = ScheduleContext(child=CHILD, timezone="Europe/Paris", now=start)
    times = collect_transition_times(engine.rules, start, end, context)
    assert datetime(2026, 9, 7, 8, 30, tzinfo=TZ) in times


def test_find_next_change_uses_boundaries_not_full_sampling() -> None:
    engine = _engine()
    start = datetime(2026, 9, 7, 7, 0, tzinfo=TZ)
    context = ScheduleContext(child=CHILD, timezone="Europe/Paris", now=start)
    change = find_next_change(engine.evaluate, engine.rules, start, context)
    assert change == datetime(2026, 9, 7, 8, 30, tzinfo=TZ)


def test_exception_changes_next_change() -> None:
    from custom_components.child_schedule.rules import ExceptionRule, ScheduleException

    rules = build_demo_rules()
    exception_rule = next(rule for rule in rules if isinstance(rule, ExceptionRule))
    exception_rule.add(
        ScheduleException(
            location="grandparents",
            start=datetime(2026, 9, 7, 10, 0, tzinfo=TZ),
            end=datetime(2026, 9, 7, 12, 0, tzinfo=TZ),
        )
    )
    engine = ScheduleEngine(child=CHILD, timezone="Europe/Paris", rules=rules)
    start = datetime(2026, 9, 7, 9, 0, tzinfo=TZ)
    context = ScheduleContext(child=CHILD, timezone="Europe/Paris", now=start)
    change = find_next_change(engine.evaluate, engine.rules, start, context)
    assert change == datetime(2026, 9, 7, 10, 0, tzinfo=TZ)
