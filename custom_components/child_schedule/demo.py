"""Demo/sample schedule configuration.

Fictional example only: a declarative schedule (see ``schedule_builder``)
for a made-up child ("Alex"). Useful for development and as a reference
for the configuration format. Not based on any real person or household.

School holiday dates follow a typical French zone B layout for the
2026-2027 school year; with the ``fr_api`` holiday source they would be
fetched automatically instead.
"""

from __future__ import annotations

from typing import Any

from .engine import ScheduleEngine
from .models import Child
from .rules import ScheduleRule
from .schedule_builder import build_rules

DEMO_TIMEZONE = "Europe/Paris"

DEMO_CHILD_ID = "alex"
DEMO_CHILD_NAME = "Alex"

LOCATION_HOME = "home"
LOCATION_SCHOOL = "school"
LOCATION_PARENT_B = "parent_b"

DEMO_SCHEDULE_CONFIG: dict[str, Any] = {
    "locations": [LOCATION_HOME, LOCATION_SCHOOL, LOCATION_PARENT_B],
    "weekly_slots": [
        # Odd ISO weeks: Wednesday 09:00-18:00 with parent B.
        {
            "location": LOCATION_PARENT_B,
            "start_day": 2,
            "start_time": "09:00",
            "end_day": 2,
            "end_time": "18:00",
            "week_parity": "odd",
        },
        # Even ISO weeks: Friday 16:30 to Sunday 18:00 with parent B.
        # Adjacent public holidays can extend the slot (same handover times).
        {
            "location": LOCATION_PARENT_B,
            "start_day": 4,
            "start_time": "16:30",
            "end_day": 6,
            "end_time": "18:00",
            "week_parity": "even",
            "extend_start_on_holidays": True,
            "extend_end_on_holidays": True,
        },
    ],
    "school": {
        "enabled": True,
        "location": LOCATION_SCHOOL,
        "days": [0, 1, 3, 4],  # Mon, Tue, Thu, Fri
        "start_time": "08:30",
        "end_time": "16:30",
        "first_school_day": "2026-09-01",
        # Example bridge day (no school).
        "closed_days": ["2027-05-07"],
    },
    "vacation_alternation": {
        "enabled": True,
        "even_year_first_location": LOCATION_PARENT_B,
        "odd_year_first_location": LOCATION_HOME,
    },
    "school_holidays": {
        "source": "manual",
        "zone": "B",
        "periods": [
            # ``end`` is the day school resumes.
            {"start": "2026-10-17", "end": "2026-11-02", "name": "autumn break"},
            {"start": "2026-12-19", "end": "2027-01-04", "name": "winter break"},
            {"start": "2027-02-06", "end": "2027-02-22", "name": "spring break 1"},
            {"start": "2027-04-03", "end": "2027-04-19", "name": "spring break 2"},
            {
                "start": "2027-07-03",
                "end": "2027-09-01",
                "name": "summer break",
                "alternate": False,
            },
        ],
    },
    "date_ranges": [
        # Example summer arrangement before school resumes on 2026-09-01.
        # Earlier ranges win when they overlap.
        {
            "location": LOCATION_PARENT_B,
            "start": "2026-07-06T09:00",
            "end": "2026-07-19T18:00",
            "reason": "Example summer stay (block 1)",
        },
        {
            "location": LOCATION_PARENT_B,
            "start": "2026-08-10T09:00",
            "end": "2026-08-23T18:00",
            "reason": "Example summer stay (block 2)",
        },
        {
            "location": LOCATION_HOME,
            "start": "2026-07-04T00:00",
            "end": "2026-09-01T00:00",
            "reason": "Example summer default",
        },
    ],
    "public_holidays": {"country": "FR"},
    "location_labels": {
        "home": "Home",
        "parent_b": "Parent B",
        "school": "School",
    },
    "location_colors": {
        "home": "#43A047",
        "parent_b": "#FB8C00",
    },
}


def build_demo_child() -> Child:
    """Return the fictional demo child."""
    return Child(id=DEMO_CHILD_ID, name=DEMO_CHILD_NAME, default_location=LOCATION_HOME)


def build_demo_rules() -> list[ScheduleRule]:
    """Return the demo rule set, built from the declarative config."""
    return build_rules(DEMO_SCHEDULE_CONFIG)


def build_demo_engine() -> ScheduleEngine:
    """Return a fully wired demo engine."""
    return ScheduleEngine(
        child=build_demo_child(),
        timezone=DEMO_TIMEZONE,
        rules=build_demo_rules(),
    )
