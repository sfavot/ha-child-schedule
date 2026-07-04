"""Child model."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Child:
    """A child whose schedule is tracked.

    ``default_location`` is used when no rule matches.
    """

    id: str
    name: str
    default_location: str
