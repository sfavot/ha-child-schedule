"""Device tracker platform shim (implementation in ``entities/device_tracker.py``)."""

from .entities.device_tracker import async_setup_entry

__all__ = ["async_setup_entry"]
