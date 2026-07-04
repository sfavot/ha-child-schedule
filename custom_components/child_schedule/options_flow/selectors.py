"""Shared selectors for the schedule editor."""

from __future__ import annotations

from typing import Any

from homeassistant.helpers.selector import (
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

PARITY_EVERY = "every"


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
