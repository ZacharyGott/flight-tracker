"""Provider-independent flight domain models."""

from dataclasses import dataclass


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
