"""Sensor entities for the Child Schedule integration."""

from __future__ import annotations

from datetime import datetime

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from ..coordinator import ChildScheduleConfigEntry, ChildScheduleCoordinator
from ..entity import ChildScheduleEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ChildScheduleConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensor platform."""
    coordinator = entry.runtime_data
    async_add_entities(
        [
            LocationSensor(coordinator),
            AssignedLocationSensor(coordinator),
            NextChangeSensor(coordinator),
        ]
    )


class LocationSensor(ChildScheduleEntity, SensorEntity):
    """Current effective location of the child."""

    _attr_translation_key = "location"

    def __init__(self, coordinator: ChildScheduleCoordinator) -> None:
        super().__init__(coordinator, "location")

    @property
    def native_value(self) -> str:
        return self.coordinator.data.result.effective_location


class AssignedLocationSensor(ChildScheduleEntity, SensorEntity):
    """Current assigned (planned) location of the child."""

    _attr_translation_key = "assigned_location"

    def __init__(self, coordinator: ChildScheduleCoordinator) -> None:
        super().__init__(coordinator, "assigned_location")

    @property
    def native_value(self) -> str:
        return self.coordinator.data.result.assigned_location


class NextChangeSensor(ChildScheduleEntity, SensorEntity):
    """Next datetime at which the schedule changes."""

    _attr_translation_key = "next_change"
    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(self, coordinator: ChildScheduleCoordinator) -> None:
        super().__init__(coordinator, "next_change")

    @property
    def native_value(self) -> datetime | None:
        return self.coordinator.data.next_change
