"""Provider-independent flight-data models."""

from dataclasses import dataclass
from datetime import datetime


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
class Position:
    """A geographic position in decimal degrees."""

    latitude: float
    longitude: float

    def __post_init__(self) -> None:
        if not -90 <= self.latitude <= 90:
            raise ValueError("latitude must be between -90 and 90 degrees")
        if not -180 <= self.longitude <= 180:
            raise ValueError("longitude must be between -180 and 180 degrees")


@dataclass(frozen=True, slots=True)
class Aircraft:
    """The aircraft data needed by the first flight-tracker milestone."""

    icao_hex: str
    position: Position | None = None
    callsign: str | None = None
    registration: str | None = None
    aircraft_type: str | None = None
    altitude_feet: int | None = None
    track_degrees: float | None = None


@dataclass(frozen=True, slots=True)
class NearbySnapshot:
    """A provider-independent nearby-aircraft response."""

    query: NearbyQuery
    aircraft: tuple[Aircraft, ...]
    observed_at: datetime
