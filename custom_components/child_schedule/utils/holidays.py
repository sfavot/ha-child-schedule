"""Public holiday helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Protocol


class PublicHolidayProvider(Protocol):
    """Anything that can tell whether a date is a public holiday."""

    def is_public_holiday(self, day: date) -> bool:
        """Return True if the date is a public holiday."""
        ...


@dataclass(frozen=True, slots=True)
class StaticPublicHolidays:
    """Public holiday provider backed by a static set of dates."""

    days: frozenset[date]

    def is_public_holiday(self, day: date) -> bool:
        return day in self.days


FRENCH_PUBLIC_HOLIDAYS_2026_2027: frozenset[date] = frozenset(
    {
        date(2026, 1, 1),
        date(2026, 4, 6),
        date(2026, 5, 1),
        date(2026, 5, 8),
        date(2026, 5, 14),
        date(2026, 5, 25),
        date(2026, 7, 14),
        date(2026, 8, 15),
        date(2026, 11, 1),
        date(2026, 11, 11),
        date(2026, 12, 25),
        date(2027, 1, 1),
        date(2027, 3, 29),
        date(2027, 5, 1),
        date(2027, 5, 6),
        date(2027, 5, 8),
        date(2027, 5, 17),
        date(2027, 7, 14),
        date(2027, 8, 15),
        date(2027, 11, 1),
        date(2027, 11, 11),
        date(2027, 12, 25),
    }
)


@dataclass(frozen=True, slots=True)
class PackagePublicHolidays:
    """Public holidays from the ``holidays`` PyPI package."""

    country: str
    _years: tuple[int, ...] = (2024, 2025, 2026, 2027, 2028, 2029, 2030)

    def is_public_holiday(self, day: date) -> bool:
        import holidays

        calendar = holidays.country_holidays(self.country, years=self._years)
        return day in calendar


def french_public_holidays() -> PublicHolidayProvider:
    """Return a French public holiday provider.

    Uses the ``holidays`` package when installed, otherwise the static
    2026-2027 fallback.
    """
    try:
        return PackagePublicHolidays(country="FR")
    except ImportError:
        return StaticPublicHolidays(days=FRENCH_PUBLIC_HOLIDAYS_2026_2027)
