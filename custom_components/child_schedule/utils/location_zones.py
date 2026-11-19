"""Home Assistant zones matching schedule locations."""

from __future__ import annotations

from collections.abc import Mapping

HOME_ZONE = "zone.home"


def zone_for_location(
    location: str | None,
    zones: Mapping[str, str] | None = None,
) -> str | None:
    """Return the zone entity id of a location, if any.

    The "home" location maps to the home zone unless configured otherwise.
    """
    if not location:
        return None
    if zones and zones.get(location):
        return zones[location]
    if location == "home":
        return HOME_ZONE
    return None
