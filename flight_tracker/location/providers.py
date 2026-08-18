"""Portable location-provider interfaces."""

from typing import Protocol

from ..geo import Position


class LocationProvider(Protocol):
    """Return the current position of the tracker device."""

    def get_position(self) -> Position:
        """Return the current tracker position."""
        ...
