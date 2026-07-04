"""DataUpdateCoordinator for the Child Schedule integration."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .const import DOMAIN, UPDATE_INTERVAL
from .engine import ScheduleEngine
from .models import ScheduleResult, TimelineSegment
from .rules import ExceptionRule, ManualOverride, ManualOverrideRule, ScheduleException
from .runtime_state import RuntimeState
from .runtime_store import ChildScheduleRuntimeStore
from .utils.datetime import iso_week

if TYPE_CHECKING:
    pass

_LOGGER = logging.getLogger(__name__)

type ChildScheduleConfigEntry = ConfigEntry[ChildScheduleCoordinator]


@dataclass(slots=True)
class ChildScheduleData:
    """Data exposed to entities by the coordinator."""

    result: ScheduleResult
    next_change: datetime | None
    iso_week: int
    school_holiday_source: str
    assigned_segment: TimelineSegment | None = None


class ChildScheduleCoordinator(DataUpdateCoordinator[ChildScheduleData]):
    """Evaluates the schedule engine periodically."""

    config_entry: ChildScheduleConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ChildScheduleConfigEntry,
        engine: ScheduleEngine,
        school_holiday_source: str,
        location_labels: dict[str, str] | None = None,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=config_entry,
            name=f"{DOMAIN}_{engine.child.id}",
            update_interval=UPDATE_INTERVAL,
        )
        self.engine = engine
        self.school_holiday_source = school_holiday_source
        self.location_labels = location_labels or {}
        self._runtime_store = ChildScheduleRuntimeStore(hass, config_entry.entry_id)
        self._cached_next_change: datetime | None = None

    @property
    def child_id(self) -> str:
        return self.engine.child.id

    @property
    def child_name(self) -> str:
        return self.engine.child.name

    async def async_load_runtime(self) -> None:
        """Load persisted overrides and exceptions into the engine."""
        state = await self._runtime_store.async_load()
        self._apply_runtime_state(state)

    def _apply_runtime_state(self, state: RuntimeState) -> None:
        override_rule = self._override_rule()
        if override_rule is not None:
            if state.override is not None:
                override_rule.set_override(state.override)
            else:
                override_rule.clear_override()
        exception_rule = self._exception_rule()
        if exception_rule is not None:
            exception_rule.set_exceptions(state.exceptions)
        self._invalidate_next_change_cache()

    def _invalidate_next_change_cache(self) -> None:
        self._cached_next_change = None

    async def _async_update_data(self) -> ChildScheduleData:
        now = dt_util.now()
        return await self.hass.async_add_executor_job(self._compute, now)

    def _compute(self, now: datetime) -> ChildScheduleData:
        result = self.engine.evaluate(now)
        if self._cached_next_change is not None and now < self._cached_next_change:
            next_change = self._cached_next_change
        else:
            next_change = self.engine.next_change(now)
            self._cached_next_change = next_change
        return ChildScheduleData(
            result=result,
            next_change=next_change,
            iso_week=iso_week(now.date()),
            school_holiday_source=self.school_holiday_source,
            assigned_segment=self.engine.assigned_segment_at(now),
        )

    async def async_get_timeline(
        self, start: datetime, end: datetime
    ) -> list[TimelineSegment]:
        """Return the effective schedule timeline between two datetimes."""
        return await self.hass.async_add_executor_job(
            self.engine.timeline, start, end
        )

    async def async_get_calendar_timeline(
        self, start: datetime, end: datetime
    ) -> list[TimelineSegment]:
        """Return custody segments for the calendar (assigned location only)."""
        return await self.hass.async_add_executor_job(
            self.engine.assigned_timeline, start, end
        )

    async def async_get_runtime_state(self) -> RuntimeState:
        return await self._runtime_store.async_load()

    def _override_rule(self) -> ManualOverrideRule | None:
        for rule in self.engine.rules:
            if isinstance(rule, ManualOverrideRule):
                return rule
        return None

    def _exception_rule(self) -> ExceptionRule | None:
        for rule in self.engine.rules:
            if isinstance(rule, ExceptionRule):
                return rule
        return None

    async def async_set_override(self, override: ManualOverride) -> None:
        """Set the manual override, persist it, and refresh."""
        rule = self._override_rule()
        if rule is None:
            raise ValueError("No manual override rule configured for this child")
        await self._runtime_store.async_set_override(override)
        rule.set_override(override)
        self._invalidate_next_change_cache()
        await self.async_request_refresh()

    async def async_clear_override(self) -> None:
        """Clear the manual override, persist, and refresh."""
        rule = self._override_rule()
        if rule is None:
            return
        await self._runtime_store.async_clear_override()
        rule.clear_override()
        self._invalidate_next_change_cache()
        await self.async_request_refresh()

    async def async_add_exception(self, exception: ScheduleException) -> str:
        """Add a persisted exception and refresh."""
        rule = self._exception_rule()
        if rule is None:
            raise ValueError("No exception rule configured for this child")
        await self._runtime_store.async_add_exception(exception)
        rule.add(exception)
        self._invalidate_next_change_cache()
        await self.async_request_refresh()
        return exception.id

    async def async_remove_exceptions(self, exception_ids: set[str]) -> None:
        """Remove persisted exceptions and refresh."""
        rule = self._exception_rule()
        if rule is None:
            return
        await self._runtime_store.async_remove_exceptions(exception_ids)
        for exception_id in exception_ids:
            rule.remove(exception_id)
        self._invalidate_next_change_cache()
        await self.async_request_refresh()
