"""Binary sensor entities for the Child Schedule integration."""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from ..const import LOCATION_HOME, LOCATION_SCHOOL
from ..coordinator import ChildScheduleConfigEntry, ChildScheduleCoordinator
from ..entity import ChildScheduleEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ChildScheduleConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the binary sensor platform."""
    coordinator = entry.runtime_data
    async_add_entities(
        [
            LocationBinarySensor(coordinator, "at_home", LOCATION_HOME),
            LocationBinarySensor(coordinator, "at_school", LOCATION_SCHOOL),
        ]
    )


class LocationBinarySensor(ChildScheduleEntity, BinarySensorEntity):
    """On when the child's effective location matches a given location."""

    def __init__(
        self,
        coordinator: ChildScheduleCoordinator,
        key: str,
        location: str,
    ) -> None:
        super().__init__(coordinator, key)
        self._attr_translation_key = key
        self._location = location

    @property
    def is_on(self) -> bool:
        return self.coordinator.data.result.effective_location == self._location
