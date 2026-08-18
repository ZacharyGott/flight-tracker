"""Pure rules for filtering aircraft by display classification."""

from collections.abc import Collection, Sequence

from flight_tracker.models import AircraftClassification
from flight_tracker.motion import TrackedAircraft


AIRCRAFT_FILTER_CATEGORIES = (
    AircraftClassification.COMMERCIAL,
    AircraftClassification.PRIVATE,
    AircraftClassification.GENERAL_AVIATION,
    AircraftClassification.MILITARY,
    AircraftClassification.UNKNOWN,
)


def filter_aircraft(
    aircraft: Sequence[TrackedAircraft],
    enabled: Collection[AircraftClassification],
) -> tuple[TrackedAircraft, ...]:
    """Return aircraft whose display classification is enabled."""

    return tuple(
        item for item in aircraft if item.aircraft.classification in enabled
    )
