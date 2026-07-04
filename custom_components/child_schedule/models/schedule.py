"""Schedule evaluation context."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from .child import Child


@dataclass(slots=True)
class ScheduleContext:
    """Context passed to every rule during evaluation."""

    child: Child
    timezone: str
    now: datetime
    metadata: dict[str, Any] = field(default_factory=dict)
