"""Pure serialization for persisted runtime state (overrides and exceptions)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import uuid4

from .rules.exception import ScheduleException
from .rules.override import ManualOverride


@dataclass(slots=True)
class RuntimeState:
    """Overrides and exceptions that survive Home Assistant restarts."""

    override: ManualOverride | None = None
    exceptions: list[ScheduleException] = field(default_factory=list)


def _dt_to_str(value: datetime) -> str:
    return value.isoformat()


def _dt_from_str(value: str) -> datetime:
    return datetime.fromisoformat(value)


def override_to_dict(override: ManualOverride) -> dict[str, Any]:
    return {
        "location": override.location,
        "start": _dt_to_str(override.start),
        "end": _dt_to_str(override.end) if override.end is not None else None,
        "reason": override.reason,
    }


def override_from_dict(data: dict[str, Any]) -> ManualOverride:
    end = data.get("end")
    return ManualOverride(
        location=data["location"],
        start=_dt_from_str(data["start"]),
        end=_dt_from_str(end) if end else None,
        reason=data.get("reason"),
    )


def exception_to_dict(exception: ScheduleException) -> dict[str, Any]:
    return {
        "id": exception.id,
        "location": exception.location,
        "start": _dt_to_str(exception.start),
        "end": _dt_to_str(exception.end),
        "reason": exception.reason,
    }


def exception_from_dict(data: dict[str, Any]) -> ScheduleException:
    return ScheduleException(
        id=data.get("id") or str(uuid4()),
        location=data["location"],
        start=_dt_from_str(data["start"]),
        end=_dt_from_str(data["end"]),
        reason=data.get("reason"),
    )


def runtime_to_dict(state: RuntimeState) -> dict[str, Any]:
    return {
        "override": override_to_dict(state.override) if state.override else None,
        "exceptions": [exception_to_dict(item) for item in state.exceptions],
    }


def runtime_from_dict(data: dict[str, Any] | None) -> RuntimeState:
    if not data:
        return RuntimeState()
    override_data = data.get("override")
    return RuntimeState(
        override=override_from_dict(override_data) if override_data else None,
        exceptions=[
            exception_from_dict(item) for item in data.get("exceptions") or []
        ],
    )
