"""The Child Schedule integration."""

from __future__ import annotations

import logging
from copy import deepcopy
from typing import TYPE_CHECKING, Any

from .const import (
    CONF_CHILD_NAME,
    CONF_DEFAULT_LOCATION,
    CONF_USE_DEMO_SCHEDULE,
    DEFAULT_LOCATION,
    PLATFORMS,
)
from .demo import DEMO_SCHEDULE_CONFIG
from .engine import ScheduleEngine
from .models import Child
from .schedule_builder import (
    CONF_LOCATION_LABELS,
    CONF_SCHOOL_HOLIDAYS,
    HOLIDAY_SOURCE_FR_API,
    HOLIDAY_SOURCE_STATUS_API,
    HOLIDAY_SOURCE_STATUS_API_FALLBACK,
    HOLIDAY_SOURCE_STATUS_MANUAL,
    ScheduleConfigError,
    build_rules,
    default_schedule_config,
)
from .utils.school_holidays import SchoolHolidayPeriod

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from .coordinator import ChildScheduleConfigEntry

_LOGGER = logging.getLogger(__name__)


def get_schedule_config(entry: ChildScheduleConfigEntry) -> dict[str, Any]:
    """Return the declarative schedule config for a config entry."""
    if entry.options:
        return deepcopy(dict(entry.options))
    if entry.data.get(CONF_USE_DEMO_SCHEDULE, False):
        return deepcopy(DEMO_SCHEDULE_CONFIG)
    return default_schedule_config()


async def _async_fetch_api_periods(
    hass: HomeAssistant, schedule_config: dict[str, Any]
) -> tuple[list[SchoolHolidayPeriod] | None, str | None]:
    """Fetch school holidays from the French API when configured.

    Returns ``(periods, None)`` on success, ``(None, None)`` when manual
    source is used or when falling back to manual periods, and raises
    ``ConfigEntryNotReady`` when the API is required but unavailable.
    """
    from homeassistant.exceptions import ConfigEntryNotReady
    from homeassistant.helpers.aiohttp_client import async_get_clientsession
    from homeassistant.util import dt as dt_util

    from .utils.school_holidays_api import (
        SchoolHolidayApiError,
        async_fetch_school_holidays,
        school_years_around,
    )

    holidays_config = schedule_config.get(CONF_SCHOOL_HOLIDAYS) or {}
    if holidays_config.get("source") != HOLIDAY_SOURCE_FR_API:
        return None, HOLIDAY_SOURCE_STATUS_MANUAL

    zone: str = holidays_config.get("zone", "C")
    session = async_get_clientsession(hass)
    school_years = school_years_around(dt_util.now().date())
    try:
        periods = await async_fetch_school_holidays(session, zone, school_years)
    except SchoolHolidayApiError as err:
        if holidays_config.get("periods"):
            _LOGGER.warning(
                "School holiday API unavailable, falling back to manual periods: %s",
                err,
            )
            return None, HOLIDAY_SOURCE_STATUS_API_FALLBACK
        raise ConfigEntryNotReady(
            f"Cannot fetch school holidays for zone {zone}: {err}"
        ) from err

    _LOGGER.debug(
        "Fetched %d school holiday periods for zone %s (%s)",
        len(periods),
        zone,
        ", ".join(school_years),
    )
    return periods, HOLIDAY_SOURCE_STATUS_API


async def _async_build_engine(
    hass: HomeAssistant, entry: ChildScheduleConfigEntry
) -> tuple[ScheduleEngine, str]:
    from homeassistant.exceptions import ConfigEntryError
    from homeassistant.util import slugify

    schedule_config = get_schedule_config(entry)
    api_periods, source_status = await _async_fetch_api_periods(hass, schedule_config)

    try:
        rules = build_rules(schedule_config, api_periods=api_periods)
    except ScheduleConfigError as err:
        raise ConfigEntryError(f"Invalid schedule configuration: {err}") from err

    child_name: str = entry.data[CONF_CHILD_NAME]
    child = Child(
        id=slugify(child_name),
        name=child_name,
        default_location=entry.data.get(CONF_DEFAULT_LOCATION, DEFAULT_LOCATION),
    )
    engine = ScheduleEngine(
        child=child,
        timezone=str(hass.config.time_zone),
        rules=rules,
    )
    return engine, source_status or HOLIDAY_SOURCE_STATUS_MANUAL


async def _async_update_listener(
    hass: HomeAssistant, entry: ChildScheduleConfigEntry
) -> None:
    """Reload the entry when its options change."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_setup_entry(
    hass: HomeAssistant, entry: ChildScheduleConfigEntry
) -> bool:
    """Set up Child Schedule from a config entry."""
    from .coordinator import ChildScheduleCoordinator
    from .services import async_setup_services

    engine, school_holiday_source = await _async_build_engine(hass, entry)
    schedule_config = get_schedule_config(entry)
    location_labels = schedule_config.get(CONF_LOCATION_LABELS) or {}
    coordinator = ChildScheduleCoordinator(
        hass,
        entry,
        engine,
        school_holiday_source=school_holiday_source,
        location_labels=location_labels,
    )
    await coordinator.async_load_runtime()
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    async_setup_services(hass)

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: ChildScheduleConfigEntry
) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
