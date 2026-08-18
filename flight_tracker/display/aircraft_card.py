"""Pure formatting and geometry helpers for the selected-aircraft card."""

from collections.abc import Sequence
from math import hypot

from flight_tracker.models import Aircraft, AircraftClassification


MPH_PER_KNOT = 1.15078
DEFAULT_HIT_RADIUS = 14
CARD_GAP = 12


def knots_to_mph(knots: float) -> int:
    """Convert knots to rounded miles per hour."""

    return round(knots * MPH_PER_KNOT)


def aircraft_card_lines(aircraft: Aircraft) -> tuple[str, ...]:
    """Return the display lines for one aircraft."""

    classification = _classification_label(aircraft.classification)
    aircraft_type = _text_or_unknown(aircraft.aircraft_type)
    registration = _text_or_unknown(aircraft.registration)

    return (
        aircraft_display_name(aircraft),
        f"{classification} · {aircraft_type}",
        f"Registration: {registration}",
        f"Altitude: {_format_altitude(aircraft.altitude_feet)}",
        f"Ground speed: {_format_speed(aircraft.ground_speed_knots)}",
        f"Track: {_format_track(aircraft.track_degrees)}",
        f"ICAO: {_format_icao(aircraft.icao_hex)}",
    )


def nearest_marker(
    click_position: tuple[int, int],
    markers: Sequence[tuple[str, tuple[int, int]]],
    hit_radius: int = DEFAULT_HIT_RADIUS,
) -> str | None:
    """Return the nearest marker ICAO within the hit radius."""

    click_x, click_y = click_position
    radius_squared = hit_radius**2
    nearest: tuple[int, int, str] | None = None
    for index, (icao_hex, (marker_x, marker_y)) in enumerate(markers):
        distance_squared = (click_x - marker_x) ** 2 + (click_y - marker_y) ** 2
        if distance_squared > radius_squared:
            continue
        candidate = (distance_squared, index, icao_hex)
        if nearest is None or candidate < nearest:
            nearest = candidate
    return None if nearest is None else nearest[2]


def card_rect_near_aircraft(
    anchor: tuple[int, int],
    card_size: tuple[int, int],
    radar_center: tuple[int, int],
    radar_radius: int,
    gap: int = CARD_GAP,
) -> tuple[int, int, int, int]:
    """Return a card rectangle near the aircraft and inside the radar circle.

    The helper tries the side toward the radar center first. If no nearby side
    fits, it places the card at the center of the radar.
    """

    anchor_x, anchor_y = anchor
    center_x, center_y = radar_center
    card_width, card_height = card_size
    horizontal_direction = 1 if anchor_x <= center_x else -1
    vertical_direction = 1 if anchor_y <= center_y else -1
    horizontal_x = (
        anchor_x + gap if horizontal_direction > 0 else anchor_x - gap - card_width
    )
    vertical_y = (
        anchor_y + gap if vertical_direction > 0 else anchor_y - gap - card_height
    )
    candidates = (
        (horizontal_x, anchor_y - card_height // 2),
        (anchor_x - card_width // 2, vertical_y),
        (
            anchor_x - gap - card_width
            if horizontal_direction > 0
            else anchor_x + gap,
            anchor_y - card_height // 2,
        ),
        (
            anchor_x - card_width // 2,
            anchor_y - gap - card_height
            if vertical_direction > 0
            else anchor_y + gap,
        ),
    )
    for x, y in candidates:
        rectangle = (x, y, card_width, card_height)
        if _rectangle_inside_circle(rectangle, radar_center, radar_radius):
            return rectangle

    return (
        center_x - card_width // 2,
        center_y - card_height // 2,
        card_width,
        card_height,
    )


def _text_or_unknown(value: str | None) -> str:
    if value is None or not value.strip():
        return "Unknown"
    return value.strip()


def aircraft_display_name(aircraft: Aircraft) -> str:
    """Return the display name with provider identifiers as fallbacks."""

    for value in (aircraft.callsign, aircraft.registration):
        if value is not None and value.strip():
            return value.strip()
    return _format_icao(aircraft.icao_hex)


def _classification_label(classification: AircraftClassification) -> str:
    labels = {
        AircraftClassification.UNKNOWN: "Unknown",
        AircraftClassification.MILITARY: "Military",
        AircraftClassification.COMMERCIAL: "Commercial",
        AircraftClassification.PRIVATE: "Private",
        AircraftClassification.GENERAL_AVIATION: "General aviation",
    }
    return labels[classification]


def _format_altitude(altitude_feet: int | None) -> str:
    if altitude_feet is None:
        return "Unknown"
    return f"{altitude_feet:,} ft"


def _format_speed(ground_speed_knots: float | None) -> str:
    if ground_speed_knots is None:
        return "Unknown"
    return f"{ground_speed_knots:g} kt · {knots_to_mph(ground_speed_knots)} mph"


def _format_track(track_degrees: float | None) -> str:
    if track_degrees is None:
        return "Unknown"
    return f"{round(track_degrees) % 360}°"


def _format_icao(icao_hex: str) -> str:
    value = _text_or_unknown(icao_hex)
    return value if value == "Unknown" else value.upper()


def _rectangle_inside_circle(
    rectangle: tuple[int, int, int, int],
    center: tuple[int, int],
    radius: int,
) -> bool:
    x, y, width, height = rectangle
    center_x, center_y = center
    corners = (
        (x, y),
        (x + width, y),
        (x, y + height),
        (x + width, y + height),
    )
    return all(
        hypot(corner_x - center_x, corner_y - center_y) <= radius
        for corner_x, corner_y in corners
    )
