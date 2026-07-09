"""Shared selectors for the schedule editor."""

from __future__ import annotations

from datetime import datetime
from typing import Any

import voluptuous as vol
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.selector import (
    DateTimeSelector,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TimeSelector,
)

from ..utils.datetime import normalize_ha_datetime_string

PARITY_EVERY = "every"


def ha_datetime(value: Any) -> datetime:
    """Validate a datetime from HA selectors, tolerating malformed UI output."""
    if isinstance(value, str):
        value = normalize_ha_datetime_string(value)
    return cv.datetime(value)


class FlexibleDateTimeSelector(DateTimeSelector):
    """DateTimeSelector that tolerates malformed frontend values."""

    def __call__(self, data: Any) -> datetime:
        return ha_datetime(data)


def weekday_selector(multiple: bool = False) -> SelectSelector:
    return SelectSelector(
        SelectSelectorConfig(
            options=[str(day) for day in range(7)],
            multiple=multiple,
            mode=SelectSelectorMode.DROPDOWN,
            translation_key="weekday",
        )
    )


def location_selector(locations: list[str]) -> SelectSelector:
    return SelectSelector(
        SelectSelectorConfig(
            options=locations,
            custom_value=True,
            mode=SelectSelectorMode.DROPDOWN,
        )
    )


def index_removal_selector(labels: list[str]) -> SelectSelector:
    return SelectSelector(
        SelectSelectorConfig(
            options=[
                {"value": str(index), "label": label}
                for index, label in enumerate(labels)
            ],
            multiple=True,
            mode=SelectSelectorMode.LIST,
        )
    )


def remove_indices(items: list[Any], raw_indices: list[str]) -> None:
    for index in sorted((int(raw) for raw in raw_indices), reverse=True):
        items.pop(index)
