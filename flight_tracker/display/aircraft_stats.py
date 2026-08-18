"""Pure summary and formatting helpers for visible aircraft statistics."""

from collections.abc import Sequence
from dataclasses import dataclass

from flight_tracker.models import Aircraft, AircraftClassification

from .aircraft_card import aircraft_display_name, knots_to_mph


@dataclass(frozen=True, slots=True)
class AircraftStats:
    """Summary values for the aircraft visible on the radar."""

    total: int
    commercial: int
    private: int
    general_aviation: int
    military: int
    unknown: int
    fastest: Aircraft | None
    highest: Aircraft | None


def summarize_aircraft(aircraft: Sequence[Aircraft]) -> AircraftStats:
    """Return counts and the fastest and highest visible aircraft."""

    counts = {
        AircraftClassification.COMMERCIAL: 0,
        AircraftClassification.PRIVATE: 0,
        AircraftClassification.GENERAL_AVIATION: 0,
        AircraftClassification.MILITARY: 0,
        AircraftClassification.UNKNOWN: 0,
    }
    fastest: Aircraft | None = None
    fastest_speed: float | None = None
    highest: Aircraft | None = None
    highest_altitude: int | None = None

    for item in aircraft:
        counts[item.classification] += 1
        speed = item.ground_speed_knots
        if speed is not None and (
            fastest_speed is None or speed > fastest_speed
        ):
            fastest = item
            fastest_speed = speed
        altitude = item.altitude_feet
        if altitude is not None and (
            highest_altitude is None or altitude > highest_altitude
        ):
            highest = item
            highest_altitude = altitude

    return AircraftStats(
        total=len(aircraft),
        commercial=counts[AircraftClassification.COMMERCIAL],
        private=counts[AircraftClassification.PRIVATE],
        general_aviation=counts[AircraftClassification.GENERAL_AVIATION],
        military=counts[AircraftClassification.MILITARY],
        unknown=counts[AircraftClassification.UNKNOWN],
        fastest=fastest,
        highest=highest,
    )


def aircraft_stats_lines(stats: AircraftStats) -> tuple[str, ...]:
    """Return the five compact lines for the statistics display."""

    fastest_line = "Fastest Unknown"
    if stats.fastest is not None:
        speed = stats.fastest.ground_speed_knots
        if speed is not None:
            fastest_line = (
                f"Fastest {aircraft_display_name(stats.fastest)} · "
                f"{knots_to_mph(speed)} mph"
            )

    highest_line = "Highest Unknown"
    if stats.highest is not None:
        altitude = stats.highest.altitude_feet
        if altitude is not None:
            highest_line = (
                f"Highest {aircraft_display_name(stats.highest)} · "
                f"{altitude:,} ft"
            )

    return (
        f"Aircraft {stats.total}",
        (
            f"Commercial {stats.commercial} · Private {stats.private} · "
            f"GA {stats.general_aviation}"
        ),
        f"Military {stats.military} · Unknown {stats.unknown}",
        fastest_line,
        highest_line,
    )
