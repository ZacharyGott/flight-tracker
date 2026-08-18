"""Local geographic projection for the radar display."""

import math
from dataclasses import dataclass

from flight_tracker.models import Position
from flight_tracker.runway_data import RunwaySegment


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

    point = project_position_unclipped(center, aircraft, search_radius_nm)
    if point.east**2 + point.north**2 > 1:
        return None
    return point


def project_position_unclipped(
    center: Position,
    aircraft: Position,
    search_radius_nm: int | float,
) -> RadarPoint:
    """Project an aircraft position without applying the radar boundary."""

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
    return point


def clip_segment_to_unit_circle(
    start: RadarPoint, end: RadarPoint
) -> tuple[RadarPoint, RadarPoint] | None:
    """Return the part of a normalized line segment inside the radar."""

    delta_east = end.east - start.east
    delta_north = end.north - start.north
    squared_length = delta_east**2 + delta_north**2
    if squared_length == 0:
        if start.east**2 + start.north**2 <= 1:
            return (start, end)
        return None

    b = 2 * (start.east * delta_east + start.north * delta_north)
    c = start.east**2 + start.north**2 - 1
    discriminant = b**2 - 4 * squared_length * c
    if discriminant < 0:
        return None

    root = math.sqrt(discriminant)
    first = (-b - root) / (2 * squared_length)
    second = (-b + root) / (2 * squared_length)
    lower = max(0.0, min(first, second))
    upper = min(1.0, max(first, second))
    if lower > upper:
        return None

    return (
        RadarPoint(
            east=start.east + delta_east * lower,
            north=start.north + delta_north * lower,
        ),
        RadarPoint(
            east=start.east + delta_east * upper,
            north=start.north + delta_north * upper,
        ),
    )


def project_runway_segment(
    center: Position,
    runway: RunwaySegment,
    search_radius_nm: int | float,
) -> tuple[RadarPoint, RadarPoint] | None:
    """Project and clip a runway segment to the radar circle."""

    start = project_position_unclipped(center, runway.low, search_radius_nm)
    end = project_position_unclipped(center, runway.high, search_radius_nm)
    return clip_segment_to_unit_circle(start, end)
