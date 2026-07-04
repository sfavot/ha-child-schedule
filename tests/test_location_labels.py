"""Tests for location display labels."""

from __future__ import annotations

from custom_components.child_schedule.utils.location_labels import (
    calendar_color,
    display_location,
)


def test_display_location_uses_config_labels() -> None:
    assert display_location("father", {"father": "Chez papa"}) == "Chez papa"


def test_display_location_default_french() -> None:
    assert display_location("home") == "Maison"


def test_display_location_unknown_code() -> None:
    assert display_location("grandparents") == "Grandparents"


def test_calendar_color_known_location() -> None:
    assert calendar_color("parent_b") == "#FB8C00"


def test_calendar_color_unknown_location() -> None:
    assert calendar_color("unknown") is None
