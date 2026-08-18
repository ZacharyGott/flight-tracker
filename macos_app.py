"""Small macOS entry point for testing Core Location."""

from flight_tracker.configuration import TrackerSettings
from flight_tracker.location import MacOSLocationProvider


SETTINGS = TrackerSettings(
    search_radius_nm=20,
    refresh_seconds=5,
    location_timeout_seconds=10,
)


def main() -> None:
    """Print one position from macOS Core Location."""
    provider = MacOSLocationProvider(
        timeout_seconds=SETTINGS.location_timeout_seconds
    )
    position = provider.get_position()
    print(f"{position.latitude}, {position.longitude}")


if __name__ == "__main__":
    main()
