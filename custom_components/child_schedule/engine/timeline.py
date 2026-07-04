"""Timeline computation from rule boundaries and optional sampling fallback."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Callable, Iterator, Sequence

from ..models import ScheduleContext, ScheduleResult, TimelineSegment
from ..rules.base import ScheduleRule

SAMPLE_STEP = timedelta(minutes=15)
NEXT_CHANGE_HORIZON = timedelta(days=90)

Evaluator = Callable[[datetime], ScheduleResult]


def _locations_changed(previous: ScheduleResult, current: ScheduleResult) -> bool:
    return (
        previous.effective_location != current.effective_location
        or previous.assigned_location != current.assigned_location
    )


def _assigned_changed(previous: ScheduleResult, current: ScheduleResult) -> bool:
    return previous.assigned_location != current.assigned_location


def _merge_segments(
    segments: list[TimelineSegment],
    same: Callable[[ScheduleResult, ScheduleResult], bool],
) -> list[TimelineSegment]:
    """Merge consecutive segments for which ``same`` returns True."""
    if not segments:
        return []
    merged: list[TimelineSegment] = [segments[0]]
    for segment in segments[1:]:
        previous = merged[-1]
        if same(previous.result, segment.result):
            merged[-1] = TimelineSegment(
                start=previous.start,
                end=segment.end,
                result=previous.result,
            )
        else:
            merged.append(segment)
    return merged


def collect_transition_times(
    rules: Sequence[ScheduleRule],
    start: datetime,
    end: datetime,
    context: ScheduleContext,
) -> list[datetime]:
    """Collect candidate change times from all rules in ``(start, end]``."""
    times: set[datetime] = set()
    for rule in rules:
        for moment in rule.transition_times(start, end, context):
            if start < moment <= end:
                times.add(moment)
    return sorted(times)


def _sample_points(start: datetime, end: datetime, step: timedelta) -> Iterator[datetime]:
    dt = start
    while dt < end:
        yield dt
        dt += step


def find_next_change(
    evaluate: Evaluator,
    rules: Sequence[ScheduleRule],
    start: datetime,
    context: ScheduleContext,
    horizon: timedelta = NEXT_CHANGE_HORIZON,
    step: timedelta = SAMPLE_STEP,
) -> datetime | None:
    """Return the first datetime where the locations change."""
    reference = evaluate(start)
    end = start + horizon
    for moment in collect_transition_times(rules, start, end, context):
        if _locations_changed(reference, evaluate(moment)):
            return moment

    # Fallback when no rule exposes boundaries (should be rare).
    dt = start + step
    while dt <= end:
        if _locations_changed(reference, evaluate(dt)):
            return dt
        dt += step
    return None


def build_timeline(
    evaluate: Evaluator,
    rules: Sequence[ScheduleRule],
    start: datetime,
    context: ScheduleContext,
    end: datetime,
    step: timedelta = SAMPLE_STEP,
) -> list[TimelineSegment]:
    """Build a timeline of stable segments between ``start`` and ``end``."""
    boundaries = [start, *collect_transition_times(rules, start, end, context), end]
    unique_boundaries: list[datetime] = []
    for moment in boundaries:
        if not unique_boundaries or moment > unique_boundaries[-1]:
            unique_boundaries.append(moment)

    if len(unique_boundaries) < 2:
        return [
            TimelineSegment(start=start, end=end, result=evaluate(start)),
        ]

    segments: list[TimelineSegment] = []
    for index in range(len(unique_boundaries) - 1):
        segment_start = unique_boundaries[index]
        segment_end = unique_boundaries[index + 1]
        if segment_start >= segment_end:
            continue
        segments.append(
            TimelineSegment(
                start=segment_start,
                end=segment_end,
                result=evaluate(segment_start),
            )
        )
    if segments:
        return segments

    for dt in _sample_points(start, end, step):
        result = evaluate(dt)
        if not segments:
            segments.append(TimelineSegment(start=dt, end=end, result=result))
            break
    return segments


def build_assigned_timeline(
    evaluate: Evaluator,
    rules: Sequence[ScheduleRule],
    start: datetime,
    context: ScheduleContext,
    end: datetime,
    step: timedelta = SAMPLE_STEP,
) -> list[TimelineSegment]:
    """Build a timeline merged by ``assigned_location`` only.

    Segments where only ``effective_location`` changes (e.g. school hours)
    are combined into a single custody block.
    """
    segments = build_timeline(evaluate, rules, start, context, end, step)
    return _merge_segments(
        segments,
        lambda left, right: left.assigned_location == right.assigned_location,
    )
