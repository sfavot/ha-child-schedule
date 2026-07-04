"""Tests for runtime state serialization."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from custom_components.child_schedule.runtime_state import (
    RuntimeState,
    exception_from_dict,
    exception_to_dict,
    override_from_dict,
    override_to_dict,
    runtime_from_dict,
    runtime_to_dict,
)
from custom_components.child_schedule.rules import ManualOverride, ScheduleException

TZ = ZoneInfo("Europe/Paris")


def test_runtime_roundtrip_with_override_and_exceptions() -> None:
    state = RuntimeState(
        override=ManualOverride(
            location="grandparents",
            start=datetime(2026, 9, 7, 15, 0, tzinfo=TZ),
            end=datetime(2026, 9, 7, 18, 0, tzinfo=TZ),
            reason="visit",
        ),
        exceptions=[
            ScheduleException(
                id="exc-1",
                location="camp",
                start=datetime(2026, 7, 10, 9, 0, tzinfo=TZ),
                end=datetime(2026, 7, 19, 18, 0, tzinfo=TZ),
                reason="summer camp",
            )
        ],
    )
    restored = runtime_from_dict(runtime_to_dict(state))
    assert restored.override is not None
    assert restored.override.location == "grandparents"
    assert len(restored.exceptions) == 1
    assert restored.exceptions[0].id == "exc-1"
    assert restored.exceptions[0].location == "camp"


def test_override_helpers() -> None:
    override = ManualOverride(
        location="home",
        start=datetime(2026, 1, 1, 12, 0, tzinfo=TZ),
    )
    restored = override_from_dict(override_to_dict(override))
    assert restored.end is None
    assert restored.location == "home"


def test_exception_helpers_assign_id_when_missing() -> None:
    data = {
        "location": "father",
        "start": "2026-07-06T09:00:00+02:00",
        "end": "2026-07-19T18:00:00+02:00",
    }
    exception = exception_from_dict(data)
    assert exception.id
    roundtrip = exception_to_dict(exception)
    assert roundtrip["id"] == exception.id
