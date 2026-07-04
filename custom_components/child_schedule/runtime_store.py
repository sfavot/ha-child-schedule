"""Home Assistant persistence for runtime schedule state."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .runtime_state import RuntimeState, runtime_from_dict, runtime_to_dict
from .rules.exception import ScheduleException
from .rules.override import ManualOverride

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

STORAGE_VERSION = 1
STORAGE_KEY = "child_schedule.runtime.{entry_id}"


class ChildScheduleRuntimeStore:
    """Persists overrides and exceptions for one config entry."""

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        from homeassistant.helpers.storage import Store

        self._store: Store = Store(
            hass,
            STORAGE_VERSION,
            STORAGE_KEY.format(entry_id=entry_id),
        )

    async def async_load(self) -> RuntimeState:
        data = await self._store.async_load()
        return runtime_from_dict(data)

    async def async_save(self, state: RuntimeState) -> None:
        await self._store.async_save(runtime_to_dict(state))

    async def async_set_override(self, override: ManualOverride) -> RuntimeState:
        state = await self.async_load()
        state.override = override
        await self.async_save(state)
        return state

    async def async_clear_override(self) -> RuntimeState:
        state = await self.async_load()
        state.override = None
        await self.async_save(state)
        return state

    async def async_add_exception(self, exception: ScheduleException) -> RuntimeState:
        state = await self.async_load()
        state.exceptions.append(exception)
        await self.async_save(state)
        return state

    async def async_remove_exceptions(self, exception_ids: set[str]) -> RuntimeState:
        state = await self.async_load()
        state.exceptions = [
            item for item in state.exceptions if item.id not in exception_ids
        ]
        await self.async_save(state)
        return state
