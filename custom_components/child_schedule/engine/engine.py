"""Schedule engine: evaluates rules for a child."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Sequence
from zoneinfo import ZoneInfo

from ..models import Child, ScheduleContext, ScheduleResult, TimelineSegment
from ..rules.base import ScheduleRule
from .evaluator import evaluate_rules
from .timeline import (
    NEXT_CHANGE_HORIZON,
    SAMPLE_STEP,
    build_assigned_timeline,
    build_timeline,
    find_next_change,
)


@dataclass
class ScheduleEngine:
    """Evaluates a set of independent rules for a child."""

    child: Child
    timezone: str
    rules: Sequence[ScheduleRule]
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def tzinfo(self) -> ZoneInfo:
        return ZoneInfo(self.timezone)

    def _localize(self, dt: datetime) -> datetime:
        if dt.tzinfo is None:
            return dt.replace(tzinfo=self.tzinfo)
        return dt.astimezone(self.tzinfo)

    def _context(self, now: datetime) -> ScheduleContext:
        return ScheduleContext(
            child=self.child,
            timezone=self.timezone,
            now=now,
            metadata=self.metadata,
        )

    def evaluate(self, dt: datetime) -> ScheduleResult:
        """Return the schedule result at ``dt``."""
        local_dt = self._localize(dt)
        return evaluate_rules(self.rules, local_dt, self._context(local_dt))

    def next_change(
        self,
        after: datetime,
        horizon: timedelta = NEXT_CHANGE_HORIZON,
        step: timedelta = SAMPLE_STEP,
    ) -> datetime | None:
        """Return the next datetime where the locations change."""
        local_after = self._localize(after)
        context = self._context(local_after)
        return find_next_change(
            self.evaluate,
            self.rules,
            local_after,
            context,
            horizon,
            step,
        )

    def timeline(
        self,
        start: datetime,
        end: datetime,
        step: timedelta = SAMPLE_STEP,
    ) -> list[TimelineSegment]:
        """Return the timeline of stable segments between two datetimes."""
        local_start = self._localize(start)
        local_end = self._localize(end)
        return build_timeline(
            self.evaluate,
            self.rules,
            local_start,
            self._context(local_start),
            local_end,
            step,
        )

    def assigned_timeline(
        self,
        start: datetime,
        end: datetime,
        step: timedelta = SAMPLE_STEP,
    ) -> list[TimelineSegment]:
        """Return custody segments merged by assigned location."""
        local_start = self._localize(start)
        local_end = self._localize(end)
        return build_assigned_timeline(
            self.evaluate,
            self.rules,
            local_start,
            self._context(local_start),
            local_end,
            step,
        )

    def assigned_segment_at(
        self,
        dt: datetime,
        window: timedelta = timedelta(days=90),
        step: timedelta = SAMPLE_STEP,
    ) -> TimelineSegment | None:
        """Return the assigned-location segment containing ``dt``."""
        local_dt = self._localize(dt)
        segments = self.assigned_timeline(
            local_dt - window,
            local_dt + window,
            step,
        )
        for segment in segments:
            if segment.start <= local_dt < segment.end:
                return segment
        return None
