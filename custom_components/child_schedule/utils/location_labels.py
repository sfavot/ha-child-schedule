"""Human-readable labels for location codes."""

from __future__ import annotations

from typing import Mapping

DEFAULT_LOCATION_LABELS: dict[str, str] = {
    "home": "Maison",
    "school": "École",
}

CALENDAR_LOCATION_COLORS: dict[str, str] = {
    "home": "#43A047",
    "father": "#FB8C00",
    "parent_b": "#FB8C00",
    "mother": "#8E24AA",
    "school": "#1E88E5",
    "grandparents": "#6D4C41",
}


def display_location(
    location: str,
    labels: Mapping[str, str] | None = None,
) -> str:
    """Return a display label for a location code."""
    if labels and location in labels:
        return labels[location]
    if location in DEFAULT_LOCATION_LABELS:
        return DEFAULT_LOCATION_LABELS[location]
    return location.replace("_", " ").capitalize()


def calendar_color(
    location: str,
    colors: Mapping[str, str] | None = None,
) -> str | None:
    """Return a calendar color for a location code."""
    if colors and location in colors:
        return colors[location]
    return CALENDAR_LOCATION_COLORS.get(location)
