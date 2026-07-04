"""Client for the official French school holiday calendar API.

Data source: the "fr-en-calendrier-scolaire" dataset published on
data.education.gouv.fr (Opendatasoft Explore API v2.1), which provides
school holiday periods per zone (A, B, C, Corse, overseas) and school
year.

The parsing is pure and unit-testable; only ``async_fetch_school_holidays``
performs network I/O, through a caller-provided aiohttp session.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import TYPE_CHECKING, Any, Iterable, Mapping
from zoneinfo import ZoneInfo

from .school_holidays import SchoolHolidayPeriod

if TYPE_CHECKING:
    import aiohttp

API_URL = (
    "https://data.education.gouv.fr/api/explore/v2.1/catalog/datasets/"
    "fr-en-calendrier-scolaire/records"
)
API_TIMEOUT_SECONDS = 30

# Config flow zone value -> dataset "zones" field value.
ZONE_LABELS: dict[str, str] = {
    "A": "Zone A",
    "B": "Zone B",
    "C": "Zone C",
    "corse": "Corse",
}

# Records applying to pupils; "-" means everyone.
_PUPIL_POPULATIONS = (None, "", "-", "Élèves")

_FRANCE_TZ = ZoneInfo("Europe/Paris")


class SchoolHolidayApiError(Exception):
    """Raised when the school holiday API cannot be used."""


def school_years_around(today: date) -> list[str]:
    """Return the current and next school years for a date.

    A French school year "YYYY-YYYY+1" starts in September; from July
    onward the upcoming year is considered current.
    """
    start_year = today.year if today.month >= 7 else today.year - 1
    return [f"{start_year}-{start_year + 1}", f"{start_year + 1}-{start_year + 2}"]


def build_query_params(zone: str, school_year: str) -> dict[str, str]:
    """Return the Explore API query parameters for a zone and school year."""
    try:
        zone_label = ZONE_LABELS[zone]
    except KeyError as err:
        raise SchoolHolidayApiError(
            f"Unknown zone {zone!r}, expected one of {sorted(ZONE_LABELS)}"
        ) from err
    return {
        "where": f'zones="{zone_label}" AND annee_scolaire="{school_year}"',
        "limit": "50",
    }


def _record_date(value: Any, field: str) -> date:
    if not isinstance(value, str):
        raise SchoolHolidayApiError(f"Missing or invalid {field!r} in API record: {value!r}")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as err:
        raise SchoolHolidayApiError(f"Invalid {field!r} in API record: {value!r}") from err
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(_FRANCE_TZ)
    return parsed.date()


def _infer_alternate(description: str | None) -> bool:
    """Return whether a vacation period should use week/week alternation."""
    name = (description or "").lower()
    if "pont" in name:
        return False
    if "début" in name and ("été" in name or "ete" in name):
        return False
    if "été" in name or "ete" in name or "summer" in name:
        return False
    return True


def parse_records(records: Iterable[Mapping[str, Any]]) -> list[SchoolHolidayPeriod]:
    """Parse API records into sorted, deduplicated holiday periods.

    The dataset's ``start_date`` is the first day without school and
    ``end_date`` the day school resumes, matching the exclusive-end
    convention of :class:`SchoolHolidayPeriod`.

    Some records are zero-length markers rather than ranges:
    - "Début des Vacances d'Été": only the summer start is known; the
      period is extended to September 1st as a placeholder until the
      next school year calendar is published.
    - "Pont de l'Ascension" (and similar bridge days): treated as a
      single closed day.
    """
    periods: dict[tuple[date, date], SchoolHolidayPeriod] = {}
    for record in records:
        if record.get("population") not in _PUPIL_POPULATIONS:
            continue
        description = record.get("description")
        start = _record_date(record.get("start_date"), "start_date")
        end = _record_date(record.get("end_date"), "end_date")
        if start == end:
            if "début" in (description or "").lower():
                end = date(start.year, 9, 1)
            else:
                end = start + timedelta(days=1)
        if start >= end:
            continue
        periods.setdefault(
            (start, end),
            SchoolHolidayPeriod(
                start=start,
                end=end,
                name=description,
                alternate=_infer_alternate(description),
            ),
        )
    return sorted(periods.values(), key=lambda period: period.start)


async def async_fetch_school_holidays(
    session: aiohttp.ClientSession,
    zone: str,
    school_years: Iterable[str],
) -> list[SchoolHolidayPeriod]:
    """Fetch the holiday periods for a zone over several school years."""
    import aiohttp  # local import to keep the module importable without HA deps

    timeout = aiohttp.ClientTimeout(total=API_TIMEOUT_SECONDS)
    all_records: list[Mapping[str, Any]] = []
    for school_year in school_years:
        params = build_query_params(zone, school_year)
        try:
            async with session.get(API_URL, params=params, timeout=timeout) as response:
                response.raise_for_status()
                payload = await response.json()
        except Exception as err:
            raise SchoolHolidayApiError(
                f"Failed to fetch school holidays for zone {zone!r}, "
                f"year {school_year!r}: {err}"
            ) from err
        all_records.extend(payload.get("results") or [])

    periods = parse_records(all_records)
    if not periods:
        raise SchoolHolidayApiError(
            f"The school holiday API returned no periods for zone {zone!r}"
        )
    return periods
