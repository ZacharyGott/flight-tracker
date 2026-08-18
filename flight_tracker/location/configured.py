"""Location provider backed by a fixed position."""

from ..geo import Position


class ConfiguredLocationProvider:
    """Return a position supplied by application configuration."""

    def __init__(self, position: Position) -> None:
        self._position = position

    def get_position(self) -> Position:
        """Return the configured position."""
        return self._position
