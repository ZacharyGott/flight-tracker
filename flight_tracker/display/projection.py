"""Local geographic projection for the radar display."""

import math
from dataclasses import dataclass

from flight_tracker.models import Position


@dataclass(frozen=True, slots=True)
class RadarPoint:
    """A normalized position on the radar."""

    east: float
    north: float


def project_position(
    center: Position,
    aircraft: Position,
    search_radius_nm: int | float,
) -> RadarPoint | None:
    """Project an aircraft position onto the normalized radar."""

    north_nm = (aircraft.latitude - center.latitude) * 60
    east_nm = (
        (aircraft.longitude - center.longitude)
        * 60
        * math.cos(math.radians(center.latitude))
    )
    point = RadarPoint(
        east=east_nm / search_radius_nm,
        north=north_nm / search_radius_nm,
    )
    if point.east**2 + point.north**2 > 1:
        return None
    return point
