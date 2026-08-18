"""Predict aircraft positions between provider updates."""

import math

from flight_tracker.models import Position


EARTH_RADIUS_NM = 3440.065


def predict_position(
    position: Position,
    ground_speed_knots: float,
    track_degrees: float,
    elapsed_seconds: float,
) -> Position:
    """Return the position reached after travelling on a great circle."""

    if elapsed_seconds == 0:
        return position

    distance_nm = ground_speed_knots * elapsed_seconds / 3600
    angular_distance = distance_nm / EARTH_RADIUS_NM
    latitude = math.radians(position.latitude)
    longitude = math.radians(position.longitude)
    bearing = math.radians(track_degrees)

    predicted_latitude = math.asin(
        math.sin(latitude) * math.cos(angular_distance)
        + math.cos(latitude) * math.sin(angular_distance) * math.cos(bearing)
    )
    predicted_longitude = longitude + math.atan2(
        math.sin(bearing) * math.sin(angular_distance) * math.cos(latitude),
        math.cos(angular_distance)
        - math.sin(latitude) * math.sin(predicted_latitude),
    )
    longitude_degrees = (math.degrees(predicted_longitude) + 180) % 360 - 180
    return Position(
        latitude=math.degrees(predicted_latitude),
        longitude=longitude_degrees,
    )
