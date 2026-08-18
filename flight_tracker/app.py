"""Application loop for the flight tracker."""

import time
from collections.abc import Callable
from typing import Protocol

from flight_tracker.configuration import TrackerSettings
from flight_tracker.display import RadarDisplay
from flight_tracker.flight_data import FlightDataError, NearbyQuery, NearbySnapshot
from flight_tracker.location import LocationProvider
from flight_tracker.models import Aircraft, Position


class FlightDataProvider(Protocol):
    """Retrieve nearby flight data."""

    def nearby(self, query: NearbyQuery) -> NearbySnapshot:
        """Return the aircraft near the query position."""
        ...


class TrackerApplication:
    """Coordinate location, flight-data retrieval, and radar rendering."""

    def __init__(
        self,
        flight_data_provider: FlightDataProvider,
        location_provider: LocationProvider,
        display: RadarDisplay,
        settings: TrackerSettings,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._flight_data_provider = flight_data_provider
        self._location_provider = location_provider
        self._display = display
        self._settings = settings
        self._clock = clock

    def run(self) -> None:
        """Run until the display receives an exit event."""

        aircraft: tuple[Aircraft, ...] = ()
        position = self._settings.position
        next_refresh = 0.0
        try:
            while self._display.process_events():
                now = self._clock()
                if now >= next_refresh:
                    position, aircraft = self._refresh(aircraft)
                    next_refresh = now + self._settings.refresh_seconds
                self._display.render(position, aircraft, self._settings.search_radius_nm)
                self._display.limit_frame_rate(self._settings.frame_rate)
        finally:
            self._display.close()

    def _refresh(
        self,
        previous_aircraft: tuple[Aircraft, ...],
    ) -> tuple[Position, tuple[Aircraft, ...]]:
        position = self._location_provider.get_position()
        query = NearbyQuery(
            latitude=position.latitude,
            longitude=position.longitude,
            radius_nm=self._settings.search_radius_nm,
        )
        try:
            snapshot = self._flight_data_provider.nearby(query)
        except FlightDataError as error:
            print(f"flight-data refresh failed: {error}")
            return position, previous_aircraft
        return position, snapshot.aircraft
