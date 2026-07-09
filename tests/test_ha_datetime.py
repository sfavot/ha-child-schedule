"""Tests for Home Assistant datetime normalization."""

from __future__ import annotations

from custom_components.child_schedule.utils.datetime import normalize_ha_datetime_string


def test_normalize_ha_datetime_string_fixes_malformed_ui_value() -> None:
    assert (
        normalize_ha_datetime_string("2026-07-09T00:00:00 09:00:00")
        == "2026-07-09 09:00:00"
    )


def test_normalize_ha_datetime_string_leaves_valid_values() -> None:
    assert normalize_ha_datetime_string("2026-07-09 09:00:00") == "2026-07-09 09:00:00"
    assert normalize_ha_datetime_string("2026-07-09T09:00:00") == "2026-07-09T09:00:00"
