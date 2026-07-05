"""Device tracker entity for the Child Schedule integration."""

from __future__ import annotations

from homeassistant.components.device_tracker import SourceType
from homeassistant.components.device_tracker.config_entry import TrackerEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from ..coordinator import ChildScheduleConfigEntry, ChildScheduleCoordinator
from ..entity import ChildScheduleEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ChildScheduleConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the device tracker platform."""
    async_add_entities([ScheduleTracker(entry.runtime_data)])


class ScheduleTracker(ChildScheduleEntity, TrackerEntity):
    """Schedule-based location tracker for linking a child to a Person entity."""

    _attr_translation_key = "tracker"
    _attr_source_type = SourceType.GPS

    def __init__(self, coordinator: ChildScheduleCoordinator) -> None:
        super().__init__(coordinator, "tracker")

    @property
    def location_name(self) -> str | None:
        """Return the effective schedule location as a zone-compatible name."""
        return self.coordinator.data.result.effective_location
