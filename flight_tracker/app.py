"""Application loop for the flight tracker."""

import time
from collections.abc import Callable
from typing import Protocol

from flight_tracker.configuration import TrackerSettings
from flight_tracker.display import RadarDisplay
from flight_tracker.flight_data import NearbyQuery, PollResult
from flight_tracker.location import LocationProvider
from flight_tracker.motion import AircraftMotionTracker


class SnapshotPoller(Protocol):
    """Poll nearby flight data without blocking the display loop."""

    def start(self, query: NearbyQuery) -> None:
        """Start polling for the query."""
        ...

    def drain(self) -> tuple[PollResult, ...]:
        """Return poll results that are ready for the main thread."""
        ...

    def stop(self) -> None:
        """Stop polling."""
        ...


class TrackerApplication:
    """Coordinate location, flight-data retrieval, and radar rendering."""

    def __init__(
        self,
        flight_data_poller: SnapshotPoller,
        location_provider: LocationProvider,
        display: RadarDisplay,
        settings: TrackerSettings,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._flight_data_poller = flight_data_poller
        self._location_provider = location_provider
        self._display = display
        self._settings = settings
        self._clock = clock

    def run(self) -> None:
        """Run until the display receives an exit event."""

        position = self._location_provider.get_position()
        query = NearbyQuery(
            latitude=position.latitude,
            longitude=position.longitude,
            radius_nm=self._settings.search_radius_nm,
        )
        try:
            self._flight_data_poller.start(query)
            motion_tracker = AircraftMotionTracker(
                max_prediction_seconds=self._settings.refresh_seconds * 2,
            )
            while self._display.process_events():
                now = self._clock()
                for result in self._flight_data_poller.drain():
                    if result.snapshot is not None:
                        motion_tracker.update(result.snapshot, result.received_at)
                    if result.error_message is not None:
                        print(f"flight-data refresh failed: {result.error_message}")
                aircraft = motion_tracker.current_aircraft(now)
                self._display.render(position, aircraft, self._settings.search_radius_nm)
                self._display.limit_frame_rate(self._settings.frame_rate)
        finally:
            self._flight_data_poller.stop()
            self._display.close()
