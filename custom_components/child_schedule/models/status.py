"""Schedule evaluation result."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(slots=True)
class ScheduleResult:
    """Result of a schedule evaluation.

    ``assigned_location`` is the underlying planned location/responsibility.
    ``effective_location`` is the actual current display location.

    Example: a child assigned to "home" but currently at school has
    ``assigned_location == "home"`` and ``effective_location == "school"``.
    """

    effective_location: str
    assigned_location: str
    source: str
    reason: str | None = None
    priority: int = 0
    period_start: datetime | None = None
    period_end: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
