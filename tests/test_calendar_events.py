"""Tests for all-day calendar block building."""

from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo

from custom_components.child_schedule.demo import build_demo_engine
from custom_components.child_schedule.utils.calendar_events import build_allday_blocks

TZ = ZoneInfo("Europe/Paris")


def _blocks_for(start: date, end: date):
    engine = build_demo_engine()
    return build_allday_blocks(
        engine.evaluate,
        TZ,
        datetime.combine(start, datetime.min.time(), TZ),
        datetime.combine(end, datetime.min.time(), TZ),
    )


def test_one_block_per_run_without_time_labels() -> None:
    blocks = _blocks_for(date(2026, 9, 7), date(2026, 9, 11))
    assert blocks
    assert all(block.location in {"home", "parent_b"} for block in blocks)


def test_wednesday_parent_b_shows_single_day_block() -> None:
    blocks = _blocks_for(date(2026, 9, 9), date(2026, 9, 10))
    assert len(blocks) == 1
    assert blocks[0].location == "parent_b"
    assert blocks[0].start == date(2026, 9, 9)
    assert blocks[0].end == date(2026, 9, 10)


def test_weekend_parent_b_merged_with_friday_handover() -> None:
    blocks = _blocks_for(date(2026, 9, 4), date(2026, 9, 8))
    assert len(blocks) == 2
    assert blocks[0].location == "parent_b"
    assert blocks[0].start == date(2026, 9, 4)
    assert blocks[0].end == date(2026, 9, 7)
    assert blocks[1].location == "home"
    assert blocks[1].start == date(2026, 9, 7)


def test_july_wednesday_not_split_into_three_bars() -> None:
    blocks = _blocks_for(date(2026, 7, 1), date(2026, 7, 2))
    assert len(blocks) == 1
    assert blocks[0].location == "parent_b"
