"""Generic schedule rules."""

from .base import DefaultRule, ScheduleRule
from .date_range import DateRangeRule, DateRangeSlot
from .exception import ExceptionRule, ScheduleException
from .override import ManualOverride, ManualOverrideRule
from .school import SchoolRule
from .vacation import VacationAlternationRule
from .weekly import WeeklyScheduleRule, WeeklySlot

__all__ = [
    "DateRangeRule",
    "DateRangeSlot",
    "DefaultRule",
    "ExceptionRule",
    "ManualOverride",
    "ManualOverrideRule",
    "ScheduleException",
    "ScheduleRule",
    "SchoolRule",
    "VacationAlternationRule",
    "WeeklyScheduleRule",
    "WeeklySlot",
]
