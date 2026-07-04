"""Tests for the generic engine behavior (no Home Assistant)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import ClassVar
from zoneinfo import ZoneInfo

from custom_components.child_schedule.engine import ScheduleEngine
from custom_components.child_schedule.models import (
    Child,
    ScheduleContext,
    ScheduleResult,
)
from custom_components.child_schedule.rules import (
    DefaultRule,
    ManualOverride,
    ManualOverrideRule,
    ScheduleRule,
)

TZ = ZoneInfo("Europe/Paris")

CHILD = Child(id="test", name="Test", default_location="home")


@dataclass
class StaticRule(ScheduleRule):
    """Test rule that always matches with a fixed location."""

    id: str
    priority: int
    location: str

    def evaluate(self, dt: datetime, context: ScheduleContext) -> ScheduleResult | None:
        return ScheduleResult(
            effective_location=self.location,
            assigned_location=self.location,
            source=self.id,
            priority=self.priority,
        )


@dataclass
class EffectiveOnlyStaticRule(StaticRule):
    """Static rule that only overrides the effective location."""

    overrides_assigned: ClassVar[bool] = False


def make_engine(rules: list[ScheduleRule]) -> ScheduleEngine:
    return ScheduleEngine(child=CHILD, timezone="Europe/Paris", rules=rules)


def test_no_rule_returns_default_location() -> None:
    engine = make_engine([])
    result = engine.evaluate(datetime(2026, 9, 7, 12, 0, tzinfo=TZ))
    assert result.effective_location == "home"
    assert result.assigned_location == "home"
    assert result.source == "default"


def test_default_rule_matches_everywhere() -> None:
    engine = make_engine([DefaultRule()])
    result = engine.evaluate(datetime(2026, 9, 7, 12, 0, tzinfo=TZ))
    assert result.effective_location == "home"
    assert result.assigned_location == "home"


def test_highest_priority_wins() -> None:
    engine = make_engine(
        [
            StaticRule(id="low", priority=10, location="grandparents"),
            StaticRule(id="high", priority=50, location="camp"),
        ]
    )
    result = engine.evaluate(datetime(2026, 9, 7, 12, 0, tzinfo=TZ))
    assert result.effective_location == "camp"
    assert result.source == "high"


def test_tie_breaker_is_stable_rule_order() -> None:
    engine = make_engine(
        [
            StaticRule(id="first", priority=10, location="daycare"),
            StaticRule(id="second", priority=10, location="camp"),
        ]
    )
    result = engine.evaluate(datetime(2026, 9, 7, 12, 0, tzinfo=TZ))
    assert result.source == "first"
    assert result.effective_location == "daycare"


def test_effective_only_rule_preserves_assigned_location() -> None:
    engine = make_engine(
        [
            StaticRule(id="assigned", priority=10, location="grandparents"),
            EffectiveOnlyStaticRule(id="activity", priority=20, location="activity"),
        ]
    )
    result = engine.evaluate(datetime(2026, 9, 7, 12, 0, tzinfo=TZ))
    assert result.effective_location == "activity"
    assert result.assigned_location == "grandparents"
    assert result.metadata["assigned_source"] == "assigned"


def test_effective_only_rule_falls_back_to_default_assigned() -> None:
    engine = make_engine(
        [EffectiveOnlyStaticRule(id="activity", priority=20, location="activity")]
    )
    result = engine.evaluate(datetime(2026, 9, 7, 12, 0, tzinfo=TZ))
    assert result.effective_location == "activity"
    assert result.assigned_location == "home"


def test_manual_override_wins_over_everything() -> None:
    override_rule = ManualOverrideRule()
    override_rule.set_override(
        ManualOverride(
            location="grandparents",
            start=datetime(2026, 9, 7, 0, 0, tzinfo=TZ),
            reason="surprise visit",
        )
    )
    engine = make_engine(
        [StaticRule(id="planned", priority=50, location="camp"), override_rule]
    )
    result = engine.evaluate(datetime(2026, 9, 7, 12, 0, tzinfo=TZ))
    assert result.effective_location == "grandparents"
    assert result.source == "manual_override"

    override_rule.clear_override()
    result = engine.evaluate(datetime(2026, 9, 7, 12, 0, tzinfo=TZ))
    assert result.effective_location == "camp"


def test_next_change_finds_override_start() -> None:
    override_rule = ManualOverrideRule()
    override_rule.set_override(
        ManualOverride(
            location="grandparents",
            start=datetime(2026, 9, 7, 15, 0, tzinfo=TZ),
            end=datetime(2026, 9, 7, 18, 0, tzinfo=TZ),
        )
    )
    engine = make_engine([DefaultRule(), override_rule])
    change = engine.next_change(datetime(2026, 9, 7, 12, 0, tzinfo=TZ))
    assert change == datetime(2026, 9, 7, 15, 0, tzinfo=TZ)


def test_next_change_returns_none_when_stable() -> None:
    engine = make_engine([DefaultRule()])
    change = engine.next_change(
        datetime(2026, 9, 7, 12, 0, tzinfo=TZ), horizon=timedelta(days=2)
    )
    assert change is None


def test_timeline_produces_segments() -> None:
    override_rule = ManualOverrideRule()
    override_rule.set_override(
        ManualOverride(
            location="grandparents",
            start=datetime(2026, 9, 7, 15, 0, tzinfo=TZ),
            end=datetime(2026, 9, 7, 18, 0, tzinfo=TZ),
        )
    )
    engine = make_engine([DefaultRule(), override_rule])
    segments = engine.timeline(
        datetime(2026, 9, 7, 12, 0, tzinfo=TZ),
        datetime(2026, 9, 7, 22, 0, tzinfo=TZ),
    )
    assert [s.result.effective_location for s in segments] == [
        "home",
        "grandparents",
        "home",
    ]
    assert segments[1].start == datetime(2026, 9, 7, 15, 0, tzinfo=TZ)
    assert segments[1].end == datetime(2026, 9, 7, 18, 0, tzinfo=TZ)
    assert segments[0].start == datetime(2026, 9, 7, 12, 0, tzinfo=TZ)
    assert segments[-1].end == datetime(2026, 9, 7, 22, 0, tzinfo=TZ)


def test_assigned_timeline_merges_effective_only_changes() -> None:
    override_rule = ManualOverrideRule()
    override_rule.set_override(
        ManualOverride(
            location="grandparents",
            start=datetime(2026, 9, 7, 15, 0, tzinfo=TZ),
            end=datetime(2026, 9, 7, 18, 0, tzinfo=TZ),
        )
    )
    engine = make_engine([DefaultRule(), override_rule])
    segments = engine.assigned_timeline(
        datetime(2026, 9, 7, 12, 0, tzinfo=TZ),
        datetime(2026, 9, 7, 22, 0, tzinfo=TZ),
    )
    assert [s.result.assigned_location for s in segments] == [
        "home",
        "grandparents",
        "home",
    ]
