"""Calendar entity for the Child Schedule integration."""

from __future__ import annotations

from datetime import datetime

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from ..coordinator import ChildScheduleConfigEntry, ChildScheduleCoordinator
from ..entity import ChildScheduleEntity
from ..utils.calendar_events import AllDayCalendarBlock, block_for_date, build_allday_blocks
from ..utils.location_labels import display_location


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ChildScheduleConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the calendar platform."""
    async_add_entities([ScheduleCalendar(entry.runtime_data)])


class ScheduleCalendar(ChildScheduleEntity, CalendarEntity):
    """Read-only calendar showing custody blocks as all-day events."""

    _attr_translation_key = "schedule"

    def __init__(self, coordinator: ChildScheduleCoordinator) -> None:
        super().__init__(coordinator, "schedule")

    def _label(self, location: str) -> str:
        return display_location(location, self.coordinator.location_labels)

    def _block_event(self, block: AllDayCalendarBlock) -> CalendarEvent:
        return CalendarEvent(
            start=block.start,
            end=block.end,
            summary=self._label(block.location),
            uid=(
                f"{self.coordinator.child_id}-"
                f"{block.location}-{block.start.isoformat()}"
            ),
        )

    @property
    def event(self) -> CalendarEvent | None:
        """Return today as an all-day custody event."""
        data = self.coordinator.data
        if data is None:
            return None
        now = dt_util.now()
        block = block_for_date(
            self.coordinator.engine.evaluate,
            self.coordinator.engine.tzinfo,
            now.date(),
        )
        return self._block_event(block)

    async def async_get_events(
        self,
        hass: HomeAssistant,
        start_date: datetime,
        end_date: datetime,
    ) -> list[CalendarEvent]:
        """Return merged all-day custody blocks between two datetimes."""
        blocks = await self.hass.async_add_executor_job(
            self._build_blocks,
            start_date,
            end_date,
        )
        return [self._block_event(block) for block in blocks]

    def _build_blocks(
        self, start_date: datetime, end_date: datetime
    ) -> list[AllDayCalendarBlock]:
        return build_allday_blocks(
            self.coordinator.engine.evaluate,
            self.coordinator.engine.tzinfo,
            start_date,
            end_date,
        )
