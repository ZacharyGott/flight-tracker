"""Models used to query and return nearby flight data."""

from dataclasses import dataclass
from datetime import datetime

from flight_tracker.models import Aircraft


@dataclass(frozen=True, slots=True)
class NearbyQuery:
    """The point and radius used for a nearby-aircraft query."""

    latitude: float
    longitude: float
    radius_nm: int

    def __post_init__(self) -> None:
        if not -90 <= self.latitude <= 90:
            raise ValueError("latitude must be between -90 and 90 degrees")
        if not -180 <= self.longitude <= 180:
            raise ValueError("longitude must be between -180 and 180 degrees")
        if type(self.radius_nm) is not int:
            raise ValueError("radius_nm must be an integer")
        if not 0 <= self.radius_nm <= 250:
            raise ValueError("radius_nm must be between 0 and 250 nautical miles")


@dataclass(frozen=True, slots=True)
class NearbySnapshot:
    """A provider-independent nearby-aircraft response."""

    query: NearbyQuery
    aircraft: tuple[Aircraft, ...]
    observed_at: datetime
