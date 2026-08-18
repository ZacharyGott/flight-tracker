"""Start the flight tracker radar display."""

from flight_tracker.app import TrackerApplication
from flight_tracker.configuration import parse_settings
from flight_tracker.display.pygame_display import PygameRadarDisplay
from flight_tracker.flight_data import AdsbLolClient, RequestsTransport, SnapshotPoller
from flight_tracker.location import ConfiguredLocationProvider


def main() -> None:
    """Create the configured integrations and run the tracker."""

    settings = parse_settings()
    location_provider = ConfiguredLocationProvider(settings.position)
    transport = RequestsTransport(timeout_seconds=settings.api_timeout_seconds)
    flight_data_client = AdsbLolClient(
        transport=transport,
        base_url=settings.api_base_url,
    )
    flight_data_poller = SnapshotPoller(
        flight_data_provider=flight_data_client,
        refresh_seconds=settings.refresh_seconds,
    )
    display = PygameRadarDisplay(window_size=settings.window_size)
    TrackerApplication(
        flight_data_poller=flight_data_poller,
        location_provider=location_provider,
        display=display,
        settings=settings,
    ).run()


if __name__ == "__main__":
    main()
