"""Device tracker entity for the Child Schedule integration."""

from __future__ import annotations

from homeassistant.components.device_tracker import SourceType
from homeassistant.components.device_tracker.config_entry import TrackerEntity
from homeassistant.const import ATTR_LATITUDE, ATTR_LONGITUDE
from homeassistant.core import HomeAssistant, State
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from ..coordinator import ChildScheduleConfigEntry, ChildScheduleCoordinator
from ..entity import ChildScheduleEntity
from ..utils.location_zones import zone_for_location


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ChildScheduleConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the device tracker platform."""
    async_add_entities([ScheduleTracker(entry.runtime_data)])


class ScheduleTracker(ChildScheduleEntity, TrackerEntity):
    """Schedule-based location tracker for linking a child to a Person entity.

    When the effective location has a zone, the tracker reports the zone's
    coordinates, so the child shows on the map and its state is the zone.
    Otherwise it reports the location code as its state.
    """

    _attr_translation_key = "tracker"
    _attr_source_type = SourceType.GPS

    def __init__(self, coordinator: ChildScheduleCoordinator) -> None:
        super().__init__(coordinator, "tracker")

    def _zone(self) -> State | None:
        """Return the state of the zone of the effective location, if it exists."""
        zone_id = zone_for_location(
            self.coordinator.data.result.effective_location,
            self.coordinator.location_zones,
        )
        zone = self.hass.states.get(zone_id) if zone_id else None
        if zone is None or zone.attributes.get(ATTR_LATITUDE) is None:
            return None
        return zone

    @property
    def latitude(self) -> float | None:
        """Return the latitude of the location's zone."""
        zone = self._zone()
        return zone.attributes[ATTR_LATITUDE] if zone else None

    @property
    def longitude(self) -> float | None:
        """Return the longitude of the location's zone."""
        zone = self._zone()
        return zone.attributes.get(ATTR_LONGITUDE) if zone else None

    @property
    def location_name(self) -> str | None:
        """Return the location code when it has no zone.

        With a zone, Home Assistant derives the state from the coordinates.
        """
        if self._zone() is not None:
            return None
        return self.coordinator.data.result.effective_location
