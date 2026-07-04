"""Binary sensor platform shim (implementation in ``entities/binary_sensor.py``)."""

from .entities.binary_sensor import async_setup_entry

__all__ = ["async_setup_entry"]
