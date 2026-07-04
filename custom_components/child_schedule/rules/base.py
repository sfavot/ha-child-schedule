"""Rule base class and default rule."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import ClassVar

from ..models import ScheduleContext, ScheduleResult


class ScheduleRule(ABC):
    """A schedule rule evaluated by the engine.

    Rules are independent: each one either matches a datetime and returns
    a :class:`ScheduleResult`, or returns ``None``. The engine picks the
    matching result with the highest priority.

    ``overrides_assigned`` controls the rule scope:
    - ``True`` (default): the rule defines the assigned location.
    - ``False``: the rule only overrides the effective location; the
      assigned location is taken from the best assigned-scope match
      (e.g. school changes where the child is, not who is responsible).
    """

    id: str
    priority: int
    overrides_assigned: ClassVar[bool] = True

    @abstractmethod
    def evaluate(self, dt: datetime, context: ScheduleContext) -> ScheduleResult | None:
        """Return a result if the rule applies at ``dt``, else None."""

    def transition_times(
        self,
        start: datetime,
        end: datetime,
        context: ScheduleContext,
    ) -> list[datetime]:
        """Return candidate schedule change times in ``(start, end]``."""
        return []


@dataclass
class DefaultRule(ScheduleRule):
    """Always matches with the child's default location."""

    id: str = "default"
    priority: int = 0

    def evaluate(self, dt: datetime, context: ScheduleContext) -> ScheduleResult | None:
        location = context.child.default_location
        return ScheduleResult(
            effective_location=location,
            assigned_location=location,
            source=self.id,
            priority=self.priority,
        )
