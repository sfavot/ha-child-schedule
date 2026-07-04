"""Base entity for the Child Schedule integration."""

from __future__ import annotations

from typing import Any

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    ATTR_ASSIGNED_LOCATION,
    ATTR_CHILD_NAME,
    ATTR_EFFECTIVE_LOCATION,
    ATTR_ISO_WEEK,
    ATTR_METADATA,
    ATTR_NEXT_CHANGE,
    ATTR_PERIOD_END,
    ATTR_PERIOD_START,
    ATTR_PRIORITY,
    ATTR_REASON,
    ATTR_SCHOOL_HOLIDAY_SOURCE,
    ATTR_SOURCE,
    DOMAIN,
)
from .coordinator import ChildScheduleCoordinator


class ChildScheduleEntity(CoordinatorEntity[ChildScheduleCoordinator]):
    """Base entity reading schedule data from the coordinator.

    Entities contain no business logic: they only expose coordinator data.
    """

    _attr_has_entity_name = True

    def __init__(self, coordinator: ChildScheduleCoordinator, key: str) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.child_id}_{key}"
        # Stable English entity_id suffix regardless of UI language
        # (e.g. sensor.alex_location, not sensor.alex_lieu in French UI).
        self._attr_suggested_object_id = f"{coordinator.child_id}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.child_id)},
            name=coordinator.child_name,
            manufacturer="Child Schedule",
        )

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the shared schedule attributes."""
        data = self.coordinator.data
        result = data.result
        return {
            ATTR_CHILD_NAME: self.coordinator.child_name,
            ATTR_EFFECTIVE_LOCATION: result.effective_location,
            ATTR_ASSIGNED_LOCATION: result.assigned_location,
            ATTR_SOURCE: result.source,
            ATTR_REASON: result.reason,
            ATTR_PRIORITY: result.priority,
            ATTR_PERIOD_START: (
                result.period_start.isoformat() if result.period_start else None
            ),
            ATTR_PERIOD_END: (
                result.period_end.isoformat() if result.period_end else None
            ),
            ATTR_NEXT_CHANGE: (
                data.next_change.isoformat() if data.next_change else None
            ),
            ATTR_ISO_WEEK: data.iso_week,
            ATTR_METADATA: result.metadata,
            ATTR_SCHOOL_HOLIDAY_SOURCE: data.school_holiday_source,
        }
