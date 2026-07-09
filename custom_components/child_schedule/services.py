"""Services for the Child Schedule integration."""

from __future__ import annotations

import voluptuous as vol
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.util import dt as dt_util

from .const import (
    ATTR_CHILD_ID,
    ATTR_END,
    ATTR_EXCEPTION_ID,
    ATTR_LOCATION,
    ATTR_REASON,
    ATTR_START,
    DOMAIN,
    SERVICE_ADD_EXCEPTION,
    SERVICE_CLEAR_OVERRIDE,
    SERVICE_REMOVE_EXCEPTION,
    SERVICE_SET_OVERRIDE,
)
from .coordinator import ChildScheduleCoordinator
from .options_flow.selectors import ha_datetime
from .rules import ManualOverride, ScheduleException

SET_OVERRIDE_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_CHILD_ID): cv.string,
        vol.Required(ATTR_LOCATION): cv.string,
        vol.Optional(ATTR_START): ha_datetime,
        vol.Optional(ATTR_END): ha_datetime,
        vol.Optional(ATTR_REASON): cv.string,
    }
)

CLEAR_OVERRIDE_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_CHILD_ID): cv.string,
    }
)

ADD_EXCEPTION_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_CHILD_ID): cv.string,
        vol.Required(ATTR_LOCATION): cv.string,
        vol.Required(ATTR_START): ha_datetime,
        vol.Required(ATTR_END): ha_datetime,
        vol.Optional(ATTR_REASON): cv.string,
    }
)

REMOVE_EXCEPTION_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_CHILD_ID): cv.string,
        vol.Required(ATTR_EXCEPTION_ID): cv.string,
    }
)


def _find_coordinator(hass: HomeAssistant, child_id: str) -> ChildScheduleCoordinator:
    for entry in hass.config_entries.async_loaded_entries(DOMAIN):
        coordinator: ChildScheduleCoordinator = entry.runtime_data
        if coordinator.child_id == child_id:
            return coordinator
    raise ServiceValidationError(
        translation_domain=DOMAIN,
        translation_key="unknown_child",
        translation_placeholders={"child_id": child_id},
    )


def async_setup_services(hass: HomeAssistant) -> None:
    """Register the integration services (idempotent)."""
    if hass.services.has_service(DOMAIN, SERVICE_SET_OVERRIDE):
        return

    async def handle_set_override(call: ServiceCall) -> None:
        coordinator = _find_coordinator(hass, call.data[ATTR_CHILD_ID])
        await coordinator.async_set_override(
            ManualOverride(
                location=call.data[ATTR_LOCATION],
                start=call.data.get(ATTR_START, dt_util.now()),
                end=call.data.get(ATTR_END),
                reason=call.data.get(ATTR_REASON),
            )
        )

    async def handle_clear_override(call: ServiceCall) -> None:
        coordinator = _find_coordinator(hass, call.data[ATTR_CHILD_ID])
        await coordinator.async_clear_override()

    async def handle_add_exception(call: ServiceCall) -> None:
        coordinator = _find_coordinator(hass, call.data[ATTR_CHILD_ID])
        await coordinator.async_add_exception(
            ScheduleException(
                location=call.data[ATTR_LOCATION],
                start=call.data[ATTR_START],
                end=call.data[ATTR_END],
                reason=call.data.get(ATTR_REASON),
            )
        )

    async def handle_remove_exception(call: ServiceCall) -> None:
        coordinator = _find_coordinator(hass, call.data[ATTR_CHILD_ID])
        await coordinator.async_remove_exceptions({call.data[ATTR_EXCEPTION_ID]})

    hass.services.async_register(
        DOMAIN, SERVICE_SET_OVERRIDE, handle_set_override, schema=SET_OVERRIDE_SCHEMA
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_CLEAR_OVERRIDE,
        handle_clear_override,
        schema=CLEAR_OVERRIDE_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN, SERVICE_ADD_EXCEPTION, handle_add_exception, schema=ADD_EXCEPTION_SCHEMA
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_REMOVE_EXCEPTION,
        handle_remove_exception,
        schema=REMOVE_EXCEPTION_SCHEMA,
    )
