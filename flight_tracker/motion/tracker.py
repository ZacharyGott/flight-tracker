"""Track observations and derive display geometry on the display thread."""

from dataclasses import dataclass

from flight_tracker.flight_data.models import NearbySnapshot
from flight_tracker.models import Aircraft, Position

from .prediction import predict_position


@dataclass(frozen=True, slots=True)
class _AircraftTrack:
    aircraft: Aircraft
    reference_time: float


@dataclass(frozen=True, slots=True)
class TrackedAircraft:
    """An observation and its current display-only motion state."""

    aircraft: Aircraft
    estimated_position: Position | None
    potential_radius_nm: float | None
    is_stale: bool

    @property
    def position(self) -> Position | None:
        """Return the last position reported by the provider."""

        return self.aircraft.position


class AircraftMotionTracker:
    """Store the latest observation and derive its current display state."""

    def __init__(self, stale_after_seconds: float, remove_after_seconds: float) -> None:
        self._stale_after_seconds = stale_after_seconds
        self._remove_after_seconds = remove_after_seconds
        self._tracks: dict[str, _AircraftTrack] = {}

    def update(self, snapshot: NearbySnapshot, received_at: float) -> None:
        """Apply the latest provider observations."""

        for aircraft in snapshot.aircraft:
            if aircraft.position is None:
                continue
            if aircraft.position_observed_at is None:
                reference_time = received_at
            else:
                position_age = (
                    snapshot.observed_at - aircraft.position_observed_at
                ).total_seconds()
                reference_time = received_at - position_age
            self._tracks[aircraft.icao_hex] = _AircraftTrack(
                aircraft=aircraft,
                reference_time=reference_time,
            )

    def current_aircraft(self, now: float) -> tuple[TrackedAircraft, ...]:
        """Return display state derived for the current frame."""

        current: list[TrackedAircraft] = []
        removed: list[str] = []
        for icao_hex, track in self._tracks.items():
            age = now - track.reference_time
            if age > self._remove_after_seconds:
                removed.append(icao_hex)
                continue

            aircraft = track.aircraft
            position = aircraft.position
            estimated_position = None
            potential_radius_nm = None
            if (
                position is not None
                and aircraft.position_observed_at is not None
            ):
                if aircraft.ground_speed_knots is not None:
                    potential_radius_nm = aircraft.ground_speed_knots * age / 3600
                    if aircraft.track_degrees is not None:
                        estimated_position = predict_position(
                            position,
                            aircraft.ground_speed_knots,
                            aircraft.track_degrees,
                            age,
                        )
            current.append(
                TrackedAircraft(
                    aircraft=aircraft,
                    estimated_position=estimated_position,
                    potential_radius_nm=potential_radius_nm,
                    is_stale=age > self._stale_after_seconds,
                )
            )

        for icao_hex in removed:
            del self._tracks[icao_hex]

        return tuple(current)
