"""Tests for the French school holiday API parsing (no network)."""

from __future__ import annotations

from datetime import date

import pytest

from custom_components.child_schedule.utils.school_holidays_api import (
    SchoolHolidayApiError,
    build_query_params,
    parse_records,
    school_years_around,
)

# Real payload shape from data.education.gouv.fr (zone C, 2026-2027).
SAMPLE_RECORDS = [
    {
        "description": "Vacances de la Toussaint",
        "population": "-",
        "start_date": "2026-10-16T22:00:00+00:00",
        "end_date": "2026-11-01T23:00:00+00:00",
        "zones": "Zone C",
    },
    {
        "description": "Vacances de la Toussaint",
        "population": "-",
        "start_date": "2026-10-16T22:00:00+00:00",
        "end_date": "2026-11-01T23:00:00+00:00",
        "zones": "Zone C",
    },
    {
        "description": "Vacances de Noël",
        "population": "-",
        "start_date": "2026-12-18T23:00:00+00:00",
        "end_date": "2027-01-03T23:00:00+00:00",
        "zones": "Zone C",
    },
    {
        "description": "Pont de l'Ascension",
        "population": "-",
        "start_date": "2027-05-06T22:00:00+00:00",
        "end_date": "2027-05-06T22:00:00+00:00",
        "zones": "Zone C",
    },
    {
        "description": "Début des Vacances d'Été",
        "population": "-",
        "start_date": "2027-07-02T22:00:00+00:00",
        "end_date": "2027-07-02T22:00:00+00:00",
        "zones": "Zone C",
    },
    {
        "description": "Vacances d'Été",
        "population": "Enseignants",
        "start_date": "2026-07-03T22:00:00+00:00",
        "end_date": "2026-08-30T22:00:00+00:00",
        "zones": "Zone C",
    },
]


def test_parse_records_converts_utc_to_local_dates() -> None:
    periods = parse_records(SAMPLE_RECORDS)
    toussaint = periods[0]
    # 2026-10-16T22:00 UTC is Saturday 2026-10-17 in Paris; resume Monday 2026-11-02.
    assert toussaint.start == date(2026, 10, 17)
    assert toussaint.end == date(2026, 11, 2)
    assert toussaint.name == "Vacances de la Toussaint"


def test_parse_records_deduplicates() -> None:
    periods = parse_records(SAMPLE_RECORDS)
    toussaint_periods = [p for p in periods if p.name == "Vacances de la Toussaint"]
    assert len(toussaint_periods) == 1


def test_parse_records_expands_bridge_day() -> None:
    periods = parse_records(SAMPLE_RECORDS)
    bridge = next(p for p in periods if p.name == "Pont de l'Ascension")
    assert bridge.start == date(2027, 5, 7)
    assert bridge.end == date(2027, 5, 8)


def test_parse_records_extends_summer_start_marker() -> None:
    periods = parse_records(SAMPLE_RECORDS)
    summer = next(p for p in periods if p.name == "Début des Vacances d'Été")
    assert summer.start == date(2027, 7, 3)
    assert summer.end == date(2027, 9, 1)


def test_parse_records_ignores_teacher_records() -> None:
    periods = parse_records(SAMPLE_RECORDS)
    assert not any(p.name == "Vacances d'Été" for p in periods)


def test_parse_records_sorted_by_start() -> None:
    periods = parse_records(SAMPLE_RECORDS)
    starts = [p.start for p in periods]
    assert starts == sorted(starts)


def test_school_years_around() -> None:
    assert school_years_around(date(2026, 7, 3)) == ["2026-2027", "2027-2028"]
    assert school_years_around(date(2026, 3, 1)) == ["2025-2026", "2026-2027"]
    assert school_years_around(date(2026, 9, 15)) == ["2026-2027", "2027-2028"]


def test_build_query_params() -> None:
    params = build_query_params("C", "2026-2027")
    assert params["where"] == 'zones="Zone C" AND annee_scolaire="2026-2027"'


def test_build_query_params_unknown_zone() -> None:
    with pytest.raises(SchoolHolidayApiError):
        build_query_params("Z", "2026-2027")


def test_infer_alternate_for_api_descriptions() -> None:
    from custom_components.child_schedule.utils.school_holidays_api import _infer_alternate

    assert _infer_alternate("Début des Vacances d'Été") is False
    assert _infer_alternate("Pont de l'Ascension") is False
    assert _infer_alternate("Vacances de la Toussaint") is True


def test_parse_records_sets_alternate_flag() -> None:
    periods = parse_records(SAMPLE_RECORDS)
    summer = next(p for p in periods if p.name == "Début des Vacances d'Été")
    bridge = next(p for p in periods if p.name == "Pont de l'Ascension")
    toussaint = next(p for p in periods if p.name == "Vacances de la Toussaint")
    assert summer.alternate is False
    assert bridge.alternate is False
    assert toussaint.alternate is True
