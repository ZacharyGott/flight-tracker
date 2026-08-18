"""Location provider boundaries."""

from typing import Protocol

from flight_tracker.models import Position


class LocationProvider(Protocol):
    """Provide the current tracker position."""

    def get_position(self) -> Position:
        """Return the current tracker position."""
        ...


class ConfiguredLocationProvider:
    """Return the position selected in tracker settings."""

    def __init__(self, position: Position) -> None:
        self._position = position

    def get_position(self) -> Position:
        """Return the configured position."""
        return self._position
