"""Radar display interfaces and implementations."""

from typing import Protocol, Sequence

from flight_tracker.models import Aircraft, Position


class RadarDisplay(Protocol):
    """The display actions used by the tracker application."""

    def process_events(self) -> bool:
        """Process display events and return whether the display should stay open."""
        ...

    def render(
        self,
        center: Position,
        aircraft: Sequence[Aircraft],
        search_radius_nm: int,
    ) -> None:
        """Render one radar frame."""
        ...

    def limit_frame_rate(self, frame_rate: int) -> None:
        """Limit the display frame rate."""
        ...

    def close(self) -> None:
        """Close the display."""
        ...
