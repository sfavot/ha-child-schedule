"""Config flow for the Child Schedule integration."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.core import callback
from homeassistant.util import slugify

from .const import (
    CONF_CHILD_NAME,
    CONF_DEFAULT_LOCATION,
    CONF_USE_DEMO_SCHEDULE,
    DEFAULT_LOCATION,
    DOMAIN,
)
from .demo import DEMO_SCHEDULE_CONFIG
from .options_flow import ChildScheduleOptionsFlow
from .schedule_builder import default_schedule_config

USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_CHILD_NAME): str,
        vol.Required(CONF_DEFAULT_LOCATION, default=DEFAULT_LOCATION): str,
        vol.Optional(CONF_USE_DEMO_SCHEDULE, default=False): bool,
    }
)


class ChildScheduleConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the initial config flow (one entry per child)."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Return the options flow (schedule editor)."""
        return ChildScheduleOptionsFlow()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            child_name = user_input[CONF_CHILD_NAME].strip()
            if not child_name:
                errors[CONF_CHILD_NAME] = "invalid_child_name"
            else:
                await self.async_set_unique_id(slugify(child_name))
                self._abort_if_unique_id_configured()
                use_demo = user_input.get(CONF_USE_DEMO_SCHEDULE, False)
                return self.async_create_entry(
                    title=child_name,
                    data={
                        CONF_CHILD_NAME: child_name,
                        CONF_DEFAULT_LOCATION: user_input[
                            CONF_DEFAULT_LOCATION
                        ].strip(),
                        CONF_USE_DEMO_SCHEDULE: use_demo,
                    },
                    options=(
                        deepcopy(DEMO_SCHEDULE_CONFIG)
                        if use_demo
                        else default_schedule_config()
                    ),
                )

        return self.async_show_form(
            step_id="user", data_schema=USER_SCHEMA, errors=errors
        )
