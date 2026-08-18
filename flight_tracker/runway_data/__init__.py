"""Runway data models and repository interfaces."""

from dataclasses import dataclass
from typing import Protocol

from flight_tracker.models import Position


@dataclass(frozen=True, slots=True)
class RunwaySegment:
    """A drawable runway segment with two geographic endpoints."""

    low: Position
    high: Position


class RunwayRepository(Protocol):
    """Read nearby runway segments from a runway data store."""

    def get_nearby_runways(
        self, center: Position, radius_nm: int | float
    ) -> tuple[RunwaySegment, ...]:
        """Return runway segments whose bounds overlap the search area."""
        ...


__all__ = ["RunwayRepository", "RunwaySegment"]
