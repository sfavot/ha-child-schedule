"""Constants for the Child Schedule integration."""

from __future__ import annotations

from datetime import timedelta

DOMAIN = "child_schedule"

CONF_CHILD_NAME = "child_name"
CONF_DEFAULT_LOCATION = "default_location"
CONF_USE_DEMO_SCHEDULE = "use_demo_schedule"

DEFAULT_CHILD_NAME = "Child"
DEFAULT_LOCATION = "home"

LOCATION_HOME = "home"
LOCATION_SCHOOL = "school"

PLATFORMS = ["sensor", "binary_sensor", "calendar", "device_tracker"]

UPDATE_INTERVAL = timedelta(minutes=1)

ATTR_CHILD_NAME = "child_name"
ATTR_EFFECTIVE_LOCATION = "effective_location"
ATTR_ASSIGNED_LOCATION = "assigned_location"
ATTR_SOURCE = "source"
ATTR_REASON = "reason"
ATTR_PRIORITY = "priority"
ATTR_PERIOD_START = "period_start"
ATTR_PERIOD_END = "period_end"
ATTR_NEXT_CHANGE = "next_change"
ATTR_ISO_WEEK = "iso_week"
ATTR_METADATA = "metadata"
ATTR_SCHOOL_HOLIDAY_SOURCE = "school_holiday_source"

SERVICE_SET_OVERRIDE = "set_override"
SERVICE_CLEAR_OVERRIDE = "clear_override"
SERVICE_ADD_EXCEPTION = "add_exception"
SERVICE_REMOVE_EXCEPTION = "remove_exception"

ATTR_CHILD_ID = "child_id"
ATTR_LOCATION = "location"
ATTR_START = "start"
ATTR_END = "end"
ATTR_EXCEPTION_ID = "exception_id"
