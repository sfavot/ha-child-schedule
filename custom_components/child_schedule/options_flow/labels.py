"""Translated labels for the schedule editor summaries."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class EditorLabels:
    weekdays: tuple[str, ...]
    parity_odd: str
    parity_even: str
    holiday_extend_start: str
    holiday_extend_end: str
    no_alternate: str
    arrow: str


_LABELS_EN = EditorLabels(
    weekdays=("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"),
    parity_odd="odd weeks",
    parity_even="even weeks",
    holiday_extend_start="holiday start",
    holiday_extend_end="holiday end",
    no_alternate="no alternation",
    arrow="→",
)

_LABELS_FR = EditorLabels(
    weekdays=("lun", "mar", "mer", "jeu", "ven", "sam", "dim"),
    parity_odd="semaines impaires",
    parity_even="semaines paires",
    holiday_extend_start="prolong. début",
    holiday_extend_end="prolong. fin",
    no_alternate="sans alternance",
    arrow="→",
)


def get_editor_labels(language: str) -> EditorLabels:
    if language.startswith("fr"):
        return _LABELS_FR
    return _LABELS_EN


def format_slot_label(slot: dict[str, Any], labels: EditorLabels) -> str:
    parity = slot.get("week_parity")
    if parity == "odd":
        parity_label = f", {labels.parity_odd}"
    elif parity == "even":
        parity_label = f", {labels.parity_even}"
    else:
        parity_label = ""
    extensions: list[str] = []
    if slot.get("extend_start_on_holidays"):
        extensions.append(labels.holiday_extend_start)
    if slot.get("extend_end_on_holidays"):
        extensions.append(labels.holiday_extend_end)
    extension_label = f" [{', '.join(extensions)}]" if extensions else ""
    return (
        f"{slot['location']}: "
        f"{labels.weekdays[int(slot['start_day'])]} {slot['start_time']} "
        f"{labels.arrow} "
        f"{labels.weekdays[int(slot['end_day'])]} {slot['end_time']}"
        f"{parity_label}{extension_label}"
    )


def format_period_label(period: dict[str, Any], labels: EditorLabels) -> str:
    name = f" ({period['name']})" if period.get("name") else ""
    alternate = "" if period.get("alternate", True) else f" [{labels.no_alternate}]"
    return f"{period['start']} {labels.arrow} {period['end']}{name}{alternate}"


def format_range_label(date_range: dict[str, Any], labels: EditorLabels) -> str:
    reason = f" ({date_range['reason']})" if date_range.get("reason") else ""
    return (
        f"{date_range['location']}: {date_range['start']} "
        f"{labels.arrow} {date_range['end']}{reason}"
    )


def format_exception_label(exception: Any, labels: EditorLabels) -> str:
    reason = f" ({exception.reason})" if getattr(exception, "reason", None) else ""
    return (
        f"{exception.location}: {exception.start.isoformat()} "
        f"{labels.arrow} {exception.end.isoformat()}{reason}"
    )
