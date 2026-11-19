"""Tests for the zones of schedule locations."""

from __future__ import annotations

from custom_components.child_schedule.utils.location_zones import zone_for_location


def test_configured_zone() -> None:
    assert zone_for_location("father", {"father": "zone.chez_papa"}) == "zone.chez_papa"


def test_home_defaults_to_home_zone() -> None:
    assert zone_for_location("home") == "zone.home"


def test_home_zone_can_be_overridden() -> None:
    assert zone_for_location("home", {"home": "zone.maison"}) == "zone.maison"


def test_location_without_zone() -> None:
    assert zone_for_location("school", {"father": "zone.chez_papa"}) is None


def test_empty_zone_is_ignored() -> None:
    assert zone_for_location("school", {"school": ""}) is None


def test_no_location() -> None:
    assert zone_for_location(None) is None
