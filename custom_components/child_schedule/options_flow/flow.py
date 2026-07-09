"""Options flow for the Child Schedule integration."""

from __future__ import annotations

from copy import deepcopy
from datetime import date, datetime
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigFlowResult, OptionsFlow
from homeassistant.helpers.selector import (
    BooleanSelector,
    DateSelector,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
    TimeSelector,
)

from ..const import CONF_CHILD_NAME, CONF_DEFAULT_LOCATION, DEFAULT_LOCATION
from ..coordinator import ChildScheduleCoordinator
from ..rules import ScheduleException
from ..runtime_store import ChildScheduleRuntimeStore
from ..schedule_builder import (
    CONF_DATE_RANGES,
    CONF_LOCATIONS,
    CONF_SCHOOL,
    CONF_SCHOOL_HOLIDAYS,
    CONF_VACATION_ALTERNATION,
    CONF_WEEKLY_SLOTS,
    HOLIDAY_SOURCE_FR_API,
    HOLIDAY_SOURCE_MANUAL,
    ScheduleConfigError,
    validate_schedule_config,
)
from .labels import (
    EditorLabels,
    format_exception_label,
    format_period_label,
    format_range_label,
    format_slot_label,
    get_editor_labels,
)
from .selectors import (
    PARITY_EVERY,
    FlexibleDateTimeSelector,
    index_removal_selector,
    location_selector,
    remove_indices,
    weekday_selector,
)
class ChildScheduleOptionsFlow(OptionsFlow):
    """Schedule editor: edits the declarative schedule configuration.

    Changes are applied immediately to the integration options.
    """

    _config: dict[str, Any]

    def _ensure_config(self) -> None:
        if hasattr(self, "_config"):
            return
        from .. import get_schedule_config

        self._config = get_schedule_config(self.config_entry)

    def _options_payload(self, config: dict[str, Any]) -> dict[str, Any]:
        """Return a JSON-serializable copy of the schedule config."""
        payload = deepcopy(config)
        for item in payload.get(CONF_DATE_RANGES) or []:
            for key in ("start", "end"):
                value = item.get(key)
                if isinstance(value, datetime):
                    item[key] = value.isoformat()
        return payload

    async def _async_apply_config(self) -> str | None:
        """Validate, persist options, and reload. Returns an error message or None."""
        try:
            validate_schedule_config(self._config)
        except ScheduleConfigError as err:
            return str(err)
        payload = self._options_payload(self._config)
        self.hass.config_entries.async_update_entry(
            self.config_entry,
            options=payload,
        )
        self._config = deepcopy(payload)
        self.hass.config_entries.async_schedule_reload(self.config_entry.entry_id)
        return None

    def _locations(self) -> list[str]:
        return list(self._config.get(CONF_LOCATIONS) or [])

    def _labels(self) -> EditorLabels:
        return get_editor_labels(self.hass.config.language)

    async def _async_get_exceptions(self) -> list[ScheduleException]:
        coordinator: ChildScheduleCoordinator | None = self.config_entry.runtime_data
        if coordinator is not None:
            state = await coordinator.async_get_runtime_state()
            return list(state.exceptions)
        store = ChildScheduleRuntimeStore(self.hass, self.config_entry.entry_id)
        state = await store.async_load()
        return list(state.exceptions)

    async def _async_add_exception(self, exception: ScheduleException) -> None:
        coordinator: ChildScheduleCoordinator | None = self.config_entry.runtime_data
        if coordinator is not None:
            await coordinator.async_add_exception(exception)
            return
        store = ChildScheduleRuntimeStore(self.hass, self.config_entry.entry_id)
        await store.async_add_exception(exception)
        self.hass.config_entries.async_schedule_reload(self.config_entry.entry_id)

    async def _async_remove_exceptions(self, exception_ids: set[str]) -> None:
        coordinator: ChildScheduleCoordinator | None = self.config_entry.runtime_data
        if coordinator is not None:
            await coordinator.async_remove_exceptions(exception_ids)
            return
        store = ChildScheduleRuntimeStore(self.hass, self.config_entry.entry_id)
        await store.async_remove_exceptions(exception_ids)
        self.hass.config_entries.async_schedule_reload(self.config_entry.entry_id)

    # --- Main menu -------------------------------------------------

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Show the editor main menu."""
        self._ensure_config()
        return self.async_show_menu(
            step_id="init",
            menu_options=[
                "general",
                "locations",
                "weekly",
                "school",
                "vacations",
                "date_ranges",
                "exceptions",
                "done",
            ],
        )

    # --- General ---------------------------------------------------

    async def async_step_general(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Edit child name and default location."""
        errors: dict[str, str] = {}
        if user_input is not None:
            child_name = user_input[CONF_CHILD_NAME].strip()
            if not child_name:
                errors[CONF_CHILD_NAME] = "invalid_child_name"
            else:
                self.hass.config_entries.async_update_entry(
                    self.config_entry,
                    title=child_name,
                    data={
                        **dict(self.config_entry.data),
                        CONF_CHILD_NAME: child_name,
                        CONF_DEFAULT_LOCATION: user_input[CONF_DEFAULT_LOCATION].strip(),
                    },
                )
                self.hass.config_entries.async_schedule_reload(self.config_entry.entry_id)
                return await self.async_step_init()

        return self.async_show_form(
            step_id="general",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_CHILD_NAME,
                        default=self.config_entry.data.get(CONF_CHILD_NAME, ""),
                    ): TextSelector(),
                    vol.Required(
                        CONF_DEFAULT_LOCATION,
                        default=self.config_entry.data.get(
                            CONF_DEFAULT_LOCATION, DEFAULT_LOCATION
                        ),
                    ): TextSelector(),
                }
            ),
            errors=errors,
        )

    # --- Locations -------------------------------------------------

    async def async_step_locations(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Edit the list of known locations."""
        errors: dict[str, str] = {}
        if user_input is not None:
            locations: list[str] = []
            for raw in user_input[CONF_LOCATIONS].split(","):
                location = raw.strip()
                if location and location not in locations:
                    locations.append(location)
            if not locations:
                errors[CONF_LOCATIONS] = "no_locations"
            else:
                self._config[CONF_LOCATIONS] = locations
                if save_error := await self._async_apply_config():
                    errors["base"] = "apply_failed"
                    return self.async_show_form(
                        step_id="locations",
                        data_schema=vol.Schema(
                            {
                                vol.Required(
                                    CONF_LOCATIONS,
                                    default=", ".join(self._locations()),
                                ): TextSelector(),
                            }
                        ),
                        errors=errors,
                        description_placeholders={"error": save_error},
                    )
                return await self.async_step_init()

        return self.async_show_form(
            step_id="locations",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_LOCATIONS,
                        default=", ".join(self._locations()),
                    ): TextSelector(),
                }
            ),
            errors=errors,
        )

    # --- Weekly slots ----------------------------------------------

    async def async_step_weekly(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Weekly slots submenu."""
        slots = self._config.get(CONF_WEEKLY_SLOTS) or []
        summary = "\n".join(f"- {format_slot_label(slot, self._labels())}" for slot in slots) or "-"
        return self.async_show_menu(
            step_id="weekly",
            menu_options=["weekly_add", "weekly_remove", "init"],
            description_placeholders={"slots": summary},
        )

    async def async_step_weekly_add(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Add a weekly slot."""
        errors: dict[str, str] = {}
        if user_input is not None:
            start = (int(user_input["start_day"]), user_input["start_time"])
            end = (int(user_input["end_day"]), user_input["end_time"])
            if start >= end:
                errors["base"] = "slot_order"
            else:
                parity = user_input["week_parity"]
                self._config.setdefault(CONF_WEEKLY_SLOTS, []).append(
                    {
                        "location": user_input["location"],
                        "start_day": int(user_input["start_day"]),
                        "start_time": user_input["start_time"],
                        "end_day": int(user_input["end_day"]),
                        "end_time": user_input["end_time"],
                        "week_parity": None if parity == PARITY_EVERY else parity,
                        "extend_start_on_holidays": user_input[
                            "extend_start_on_holidays"
                        ],
                        "extend_end_on_holidays": user_input["extend_end_on_holidays"],
                        "extended_start_time": user_input.get("extended_start_time"),
                        "extended_end_time": user_input.get("extended_end_time"),
                    }
                )
                if save_error := await self._async_apply_config():
                    self._config[CONF_WEEKLY_SLOTS].pop()
                    errors["base"] = "apply_failed"
                    return self.async_show_form(
                        step_id="weekly_add",
                        data_schema=vol.Schema(
                            {
                                vol.Required("location"): location_selector(
                                    self._locations()
                                ),
                                vol.Required("start_day"): weekday_selector(),
                                vol.Required(
                                    "start_time", default="09:00:00"
                                ): TimeSelector(),
                                vol.Required("end_day"): weekday_selector(),
                                vol.Required(
                                    "end_time", default="18:00:00"
                                ): TimeSelector(),
                                vol.Required(
                                    "week_parity", default=PARITY_EVERY
                                ): SelectSelector(
                                    SelectSelectorConfig(
                                        options=[PARITY_EVERY, "odd", "even"],
                                        mode=SelectSelectorMode.DROPDOWN,
                                        translation_key="week_parity",
                                    )
                                ),
                                vol.Required(
                                    "extend_start_on_holidays", default=False
                                ): BooleanSelector(),
                                vol.Required(
                                    "extend_end_on_holidays", default=False
                                ): BooleanSelector(),
                                vol.Optional("extended_start_time"): TimeSelector(),
                                vol.Optional("extended_end_time"): TimeSelector(),
                            }
                        ),
                        errors=errors,
                        description_placeholders={"error": save_error},
                    )
                return await self.async_step_weekly()

        return self.async_show_form(
            step_id="weekly_add",
            data_schema=vol.Schema(
                {
                    vol.Required("location"): location_selector(self._locations()),
                    vol.Required("start_day"): weekday_selector(),
                    vol.Required("start_time", default="09:00:00"): TimeSelector(),
                    vol.Required("end_day"): weekday_selector(),
                    vol.Required("end_time", default="18:00:00"): TimeSelector(),
                    vol.Required("week_parity", default=PARITY_EVERY): SelectSelector(
                        SelectSelectorConfig(
                            options=[PARITY_EVERY, "odd", "even"],
                            mode=SelectSelectorMode.DROPDOWN,
                            translation_key="week_parity",
                        )
                    ),
                    vol.Required("extend_start_on_holidays", default=False): (
                        BooleanSelector()
                    ),
                    vol.Required("extend_end_on_holidays", default=False): (
                        BooleanSelector()
                    ),
                    vol.Optional("extended_start_time"): TimeSelector(),
                    vol.Optional("extended_end_time"): TimeSelector(),
                }
            ),
            errors=errors,
        )

    async def async_step_weekly_remove(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Remove weekly slots."""
        slots: list[dict[str, Any]] = self._config.get(CONF_WEEKLY_SLOTS) or []
        if user_input is not None:
            remove_indices(slots, user_input.get("slots", []))
            if save_error := await self._async_apply_config():
                return self.async_show_form(
                    step_id="weekly_remove",
                    data_schema=vol.Schema(
                        {
                            vol.Optional("slots", default=[]): index_removal_selector(
                                [
                                    format_slot_label(slot, self._labels())
                                    for slot in slots
                                ]
                            ),
                        }
                    ),
                    errors={"base": "apply_failed"},
                    description_placeholders={"error": save_error},
                )
            return await self.async_step_weekly()

        return self.async_show_form(
            step_id="weekly_remove",
            data_schema=vol.Schema(
                {
                    vol.Optional("slots", default=[]): index_removal_selector(
                        [format_slot_label(slot, self._labels()) for slot in slots]
                    ),
                }
            ),
        )

    # --- School -----------------------------------------------------

    async def async_step_school(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Edit the school settings."""
        school = self._config.get(CONF_SCHOOL) or {}
        errors: dict[str, str] = {}
        save_error: str | None = None

        if user_input is not None:
            closed_days: list[str] = []
            for raw in user_input.get("closed_days", "").split(","):
                day = raw.strip()
                if not day:
                    continue
                try:
                    date.fromisoformat(day)
                except ValueError:
                    errors["closed_days"] = "invalid_date"
                    break
                closed_days.append(day)

            if not errors:
                self._config[CONF_SCHOOL] = {
                    "enabled": user_input["enabled"],
                    "location": user_input["location"],
                    "days": [int(day) for day in user_input["days"]],
                    "start_time": user_input["start_time"],
                    "end_time": user_input["end_time"],
                    "first_school_day": user_input.get("first_school_day"),
                    "closed_days": closed_days,
                }
                save_error = await self._async_apply_config()
                if save_error:
                    errors["base"] = "apply_failed"
                else:
                    return await self.async_step_init()

        schema = vol.Schema(
            {
                vol.Required("enabled", default=school.get("enabled", False)): (
                    BooleanSelector()
                ),
                vol.Required(
                    "location", default=school.get("location", "school")
                ): location_selector(self._locations()),
                vol.Required(
                    "days",
                    default=[str(day) for day in school.get("days", [0, 1, 3, 4])],
                ): weekday_selector(multiple=True),
                vol.Required(
                    "start_time", default=school.get("start_time", "08:30")
                ): TimeSelector(),
                vol.Required(
                    "end_time", default=school.get("end_time", "16:30")
                ): TimeSelector(),
                vol.Optional(
                    "first_school_day",
                    description={
                        "suggested_value": school.get("first_school_day")
                    },
                ): DateSelector(),
                vol.Optional(
                    "closed_days",
                    description={
                        "suggested_value": ", ".join(school.get("closed_days") or [])
                    },
                ): TextSelector(),
            }
        )
        return self.async_show_form(
            step_id="school",
            data_schema=schema,
            errors=errors,
            description_placeholders={"error": save_error} if save_error else {},
        )

    # --- Vacations ---------------------------------------------------

    async def async_step_vacations(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Edit vacation alternation and the school holiday source."""
        vacation = self._config.get(CONF_VACATION_ALTERNATION) or {}
        holidays = self._config.get(CONF_SCHOOL_HOLIDAYS) or {}

        if user_input is not None:
            self._config[CONF_VACATION_ALTERNATION] = {
                "enabled": user_input["enabled"],
                "even_year_first_location": user_input["even_year_first_location"],
                "odd_year_first_location": user_input["odd_year_first_location"],
            }
            holidays_config = self._config.setdefault(CONF_SCHOOL_HOLIDAYS, {})
            holidays_config["source"] = user_input["source"]
            holidays_config["zone"] = user_input["zone"]
            holidays_config.setdefault("periods", [])
            if save_error := await self._async_apply_config():
                locations = self._locations()
                schema = vol.Schema(
                    {
                        vol.Required("enabled", default=vacation.get("enabled", False)): (
                            BooleanSelector()
                        ),
                        vol.Required(
                            "even_year_first_location",
                            default=vacation.get(
                                "even_year_first_location", DEFAULT_LOCATION
                            ),
                        ): location_selector(locations),
                        vol.Required(
                            "odd_year_first_location",
                            default=vacation.get(
                                "odd_year_first_location", DEFAULT_LOCATION
                            ),
                        ): location_selector(locations),
                        vol.Required(
                            "source",
                            default=holidays.get("source", HOLIDAY_SOURCE_MANUAL),
                        ): SelectSelector(
                            SelectSelectorConfig(
                                options=[HOLIDAY_SOURCE_MANUAL, HOLIDAY_SOURCE_FR_API],
                                mode=SelectSelectorMode.DROPDOWN,
                                translation_key="holiday_source",
                            )
                        ),
                        vol.Required(
                            "zone", default=holidays.get("zone", "C")
                        ): SelectSelector(
                            SelectSelectorConfig(
                                options=["A", "B", "C", "corse"],
                                mode=SelectSelectorMode.DROPDOWN,
                                translation_key="holiday_zone",
                            )
                        ),
                    }
                )
                return self.async_show_form(
                    step_id="vacations",
                    data_schema=schema,
                    errors={"base": "apply_failed"},
                    description_placeholders={"error": save_error},
                )
            if user_input["source"] == HOLIDAY_SOURCE_MANUAL:
                return await self.async_step_holiday_periods()
            return await self.async_step_init()

        locations = self._locations()
        schema = vol.Schema(
            {
                vol.Required("enabled", default=vacation.get("enabled", False)): (
                    BooleanSelector()
                ),
                vol.Required(
                    "even_year_first_location",
                    default=vacation.get("even_year_first_location", DEFAULT_LOCATION),
                ): location_selector(locations),
                vol.Required(
                    "odd_year_first_location",
                    default=vacation.get("odd_year_first_location", DEFAULT_LOCATION),
                ): location_selector(locations),
                vol.Required(
                    "source",
                    default=holidays.get("source", HOLIDAY_SOURCE_MANUAL),
                ): SelectSelector(
                    SelectSelectorConfig(
                        options=[HOLIDAY_SOURCE_MANUAL, HOLIDAY_SOURCE_FR_API],
                        mode=SelectSelectorMode.DROPDOWN,
                        translation_key="holiday_source",
                    )
                ),
                vol.Required(
                    "zone", default=holidays.get("zone", "C")
                ): SelectSelector(
                    SelectSelectorConfig(
                        options=["A", "B", "C", "corse"],
                        mode=SelectSelectorMode.DROPDOWN,
                        translation_key="holiday_zone",
                    )
                ),
            }
        )
        return self.async_show_form(step_id="vacations", data_schema=schema)

    async def async_step_holiday_periods(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manual school holiday periods submenu."""
        periods = (self._config.get(CONF_SCHOOL_HOLIDAYS) or {}).get("periods") or []
        summary = "\n".join(f"- {format_period_label(period, self._labels())}" for period in periods) or "-"
        return self.async_show_menu(
            step_id="holiday_periods",
            menu_options=["holiday_add", "holiday_remove", "init"],
            description_placeholders={"periods": summary},
        )

    async def async_step_holiday_add(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Add a manual school holiday period."""
        errors: dict[str, str] = {}
        if user_input is not None:
            if user_input["start"] >= user_input["end"]:
                errors["base"] = "period_order"
            else:
                periods = self._config.setdefault(CONF_SCHOOL_HOLIDAYS, {}).setdefault(
                    "periods", []
                )
                periods.append(
                    {
                        "start": user_input["start"],
                        "end": user_input["end"],
                        "name": user_input.get("name") or None,
                        "alternate": user_input["alternate"],
                    }
                )
                if save_error := await self._async_apply_config():
                    periods.pop()
                    return self.async_show_form(
                        step_id="holiday_add",
                        data_schema=vol.Schema(
                            {
                                vol.Required("start"): DateSelector(),
                                vol.Required("end"): DateSelector(),
                                vol.Optional("name"): TextSelector(),
                                vol.Required("alternate", default=True): BooleanSelector(),
                            }
                        ),
                        errors={"base": "apply_failed"},
                        description_placeholders={"error": save_error},
                    )
                return await self.async_step_holiday_periods()

        return self.async_show_form(
            step_id="holiday_add",
            data_schema=vol.Schema(
                {
                    vol.Required("start"): DateSelector(),
                    vol.Required("end"): DateSelector(),
                    vol.Optional("name"): TextSelector(),
                    vol.Required("alternate", default=True): BooleanSelector(),
                }
            ),
            errors=errors,
        )

    async def async_step_holiday_remove(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Remove manual school holiday periods."""
        periods: list[dict[str, Any]] = (
            self._config.get(CONF_SCHOOL_HOLIDAYS) or {}
        ).get("periods") or []
        if user_input is not None:
            remove_indices(periods, user_input.get("periods", []))
            if save_error := await self._async_apply_config():
                return self.async_show_form(
                    step_id="holiday_remove",
                    data_schema=vol.Schema(
                        {
                            vol.Optional("periods", default=[]): index_removal_selector(
                                [
                                    format_period_label(period, self._labels())
                                    for period in periods
                                ]
                            ),
                        }
                    ),
                    errors={"base": "apply_failed"},
                    description_placeholders={"error": save_error},
                )
            return await self.async_step_holiday_periods()

        return self.async_show_form(
            step_id="holiday_remove",
            data_schema=vol.Schema(
                {
                    vol.Optional("periods", default=[]): index_removal_selector(
                        [format_period_label(period, self._labels()) for period in periods]
                    ),
                }
            ),
        )

    # --- Date ranges --------------------------------------------------

    async def async_step_date_ranges(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Date ranges submenu."""
        ranges = self._config.get(CONF_DATE_RANGES) or []
        summary = "\n".join(f"- {format_range_label(r, self._labels())}" for r in ranges) or "-"
        return self.async_show_menu(
            step_id="date_ranges",
            menu_options=["date_range_add", "date_range_remove", "init"],
            description_placeholders={"ranges": summary},
        )

    async def async_step_date_range_add(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Add a date range."""
        errors: dict[str, str] = {}
        if user_input is not None:
            if user_input["start"] >= user_input["end"]:
                errors["base"] = "period_order"
            else:
                self._config.setdefault(CONF_DATE_RANGES, []).append(
                    {
                        "location": user_input["location"],
                        "start": user_input["start"],
                        "end": user_input["end"],
                        "reason": user_input.get("reason") or None,
                    }
                )
                if save_error := await self._async_apply_config():
                    self._config[CONF_DATE_RANGES].pop()
                    return self.async_show_form(
                        step_id="date_range_add",
                        data_schema=vol.Schema(
                            {
                                vol.Required("location"): location_selector(
                                    self._locations()
                                ),
                                vol.Required("start"): FlexibleDateTimeSelector(),
                                vol.Required("end"): FlexibleDateTimeSelector(),
                                vol.Optional("reason"): TextSelector(),
                            }
                        ),
                        errors={"base": "apply_failed"},
                        description_placeholders={"error": save_error},
                    )
                return await self.async_step_date_ranges()

        return self.async_show_form(
            step_id="date_range_add",
            data_schema=vol.Schema(
                {
                    vol.Required("location"): location_selector(self._locations()),
                    vol.Required("start"): FlexibleDateTimeSelector(),
                    vol.Required("end"): FlexibleDateTimeSelector(),
                    vol.Optional("reason"): TextSelector(),
                }
            ),
            errors=errors,
        )

    async def async_step_date_range_remove(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Remove date ranges."""
        ranges: list[dict[str, Any]] = self._config.get(CONF_DATE_RANGES) or []
        if user_input is not None:
            remove_indices(ranges, user_input.get("ranges", []))
            if save_error := await self._async_apply_config():
                return self.async_show_form(
                    step_id="date_range_remove",
                    data_schema=vol.Schema(
                        {
                            vol.Optional("ranges", default=[]): index_removal_selector(
                                [
                                    format_range_label(r, self._labels())
                                    for r in ranges
                                ]
                            ),
                        }
                    ),
                    errors={"base": "apply_failed"},
                    description_placeholders={"error": save_error},
                )
            return await self.async_step_date_ranges()

        return self.async_show_form(
            step_id="date_range_remove",
            data_schema=vol.Schema(
                {
                    vol.Optional("ranges", default=[]): index_removal_selector(
                        [format_range_label(r, self._labels()) for r in ranges]
                    ),
                }
            ),
        )

    # --- Exceptions (persisted immediately) -------------------------

    async def async_step_exceptions(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """One-off exceptions submenu."""
        exceptions = await self._async_get_exceptions()
        labels = self._labels()
        summary = (
            "\n".join(
                f"- {format_exception_label(exception, labels)}"
                for exception in exceptions
            )
            or "-"
        )
        return self.async_show_menu(
            step_id="exceptions",
            menu_options=["exception_add", "exception_remove", "init"],
            description_placeholders={"exceptions": summary},
        )

    async def async_step_exception_add(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Add a persisted one-off exception."""
        errors: dict[str, str] = {}
        if user_input is not None:
            if user_input["start"] >= user_input["end"]:
                errors["base"] = "period_order"
            else:
                await self._async_add_exception(
                    ScheduleException(
                        location=user_input["location"],
                        start=user_input["start"],
                        end=user_input["end"],
                        reason=user_input.get("reason") or None,
                    )
                )
                return await self.async_step_exceptions()

        return self.async_show_form(
            step_id="exception_add",
            data_schema=vol.Schema(
                {
                    vol.Required("location"): location_selector(self._locations()),
                    vol.Required("start"): FlexibleDateTimeSelector(),
                    vol.Required("end"): FlexibleDateTimeSelector(),
                    vol.Optional("reason"): TextSelector(),
                }
            ),
            errors=errors,
        )

    async def async_step_exception_remove(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Remove persisted exceptions."""
        exceptions = await self._async_get_exceptions()
        labels = self._labels()
        if user_input is not None:
            await self._async_remove_exceptions(set(user_input.get("exceptions", [])))
            return await self.async_step_exceptions()

        return self.async_show_form(
            step_id="exception_remove",
            data_schema=vol.Schema(
                {
                    vol.Optional("exceptions", default=[]): SelectSelector(
                        SelectSelectorConfig(
                            options=[
                                {
                                    "value": exception.id,
                                    "label": format_exception_label(exception, labels),
                                }
                                for exception in exceptions
                            ],
                            multiple=True,
                            mode=SelectSelectorMode.LIST,
                        )
                    ),
                }
            ),
        )

    # --- Done -------------------------------------------------------

    async def async_step_done(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Close the schedule editor."""
        self._ensure_config()
        return self.async_create_entry(
            title="", data=self._options_payload(self._config)
        )
