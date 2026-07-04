"""Single-instant rule evaluation."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime
from typing import Sequence

from ..models import ScheduleContext, ScheduleResult
from ..rules.base import ScheduleRule


def _pick_best(
    current: ScheduleResult | None, candidate: ScheduleResult
) -> ScheduleResult:
    if current is None or candidate.priority > current.priority:
        return candidate
    return current


def evaluate_rules(
    rules: Sequence[ScheduleRule],
    dt: datetime,
    context: ScheduleContext,
) -> ScheduleResult:
    """Evaluate all rules at ``dt`` and combine the results.

    Two passes:
    1. Best assigned-scope match (rules with ``overrides_assigned``).
    2. Best overall match (any rule).

    Effective-only winners keep the assigned location from pass 1.
    """
    default_location = context.child.default_location

    best_assigned: ScheduleResult | None = None
    best_overall: ScheduleResult | None = None
    best_overall_rule: ScheduleRule | None = None

    for rule in rules:
        result = rule.evaluate(dt, context)
        if result is None:
            continue
        best_overall = _pick_best(best_overall, result)
        if best_overall is result:
            best_overall_rule = rule
        if rule.overrides_assigned:
            best_assigned = _pick_best(best_assigned, result)

    if best_overall is None:
        return ScheduleResult(
            effective_location=default_location,
            assigned_location=default_location,
            source="default",
            reason="no rule matched",
        )

    if best_overall_rule is not None and not best_overall_rule.overrides_assigned:
        if best_assigned is not None:
            assigned_location = best_assigned.assigned_location
            assigned_source = best_assigned.source
        else:
            assigned_location = default_location
            assigned_source = "default"
        return replace(
            best_overall,
            assigned_location=assigned_location,
            metadata={**best_overall.metadata, "assigned_source": assigned_source},
        )

    return best_overall
