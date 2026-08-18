"""Track and predict aircraft positions on the display thread."""

from dataclasses import dataclass, replace

from flight_tracker.flight_data.models import NearbySnapshot
from flight_tracker.models import Aircraft

from .prediction import predict_position


@dataclass(frozen=True, slots=True)
class _AircraftTrack:
    aircraft: Aircraft
    reference_time: float


class AircraftMotionTracker:
    """Store the latest observation and predict its current position."""

    def __init__(self, max_prediction_seconds: float) -> None:
        self._max_prediction_seconds = max_prediction_seconds
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

    def current_aircraft(self, now: float) -> tuple[Aircraft, ...]:
        """Return aircraft positions predicted for the current frame."""

        current: list[Aircraft] = []
        for track in self._tracks.values():
            age = now - track.reference_time

            aircraft = track.aircraft
            position = aircraft.position
            if (
                position is not None
                and aircraft.position_observed_at is not None
                and aircraft.ground_speed_knots is not None
                and aircraft.track_degrees is not None
            ):
                position = predict_position(
                    position,
                    aircraft.ground_speed_knots,
                    aircraft.track_degrees,
                    age,
                )
            aircraft = replace(
                aircraft,
                position=position,
                is_stale=age > self._max_prediction_seconds,
            )
            current.append(aircraft)

        return tuple(current)
