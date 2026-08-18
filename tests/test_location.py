"""Tests for the portable location layer."""

import unittest

from flight_tracker.geo import Position
from flight_tracker.location import (
    ConfiguredLocationProvider,
    LocationPermissionError,
    LocationProvider,
    LocationTimeoutError,
    LocationUnavailableError,
    MacOSLocationProvider,
)
from flight_tracker.location.macos import position_from_native_location


class FakeCoordinate:
    def __init__(self, latitude: float, longitude: float) -> None:
        self.latitude = latitude
        self.longitude = longitude


class FakeNativeLocation:
    def __init__(self, latitude: float, longitude: float) -> None:
        self._coordinate = FakeCoordinate(latitude, longitude)

    def coordinate(self) -> FakeCoordinate:
        return self._coordinate


class FakeSession:
    def __init__(self, result: Position | Exception) -> None:
        self.result = result

    def get_position(self, timeout_seconds: float) -> Position:
        del timeout_seconds
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


class LocationTests(unittest.TestCase):
    def test_configured_provider_returns_position(self) -> None:
        position = Position(40.7, -74.0)

        provider: LocationProvider = ConfiguredLocationProvider(position)

        self.assertEqual(provider.get_position(), position)

    def test_converts_native_location(self) -> None:
        native_location = FakeNativeLocation(40.7, -74.0)

        self.assertEqual(
            position_from_native_location(native_location),
            Position(40.7, -74.0),
        )

    def test_mac_provider_returns_session_position(self) -> None:
        position = Position(40.7, -74.0)
        provider = MacOSLocationProvider(
            timeout_seconds=3,
            session_factory=lambda: FakeSession(position),
        )

        self.assertEqual(provider.get_position(), position)

    def test_mac_provider_preserves_permission_error(self) -> None:
        provider = MacOSLocationProvider(
            session_factory=lambda: FakeSession(
                LocationPermissionError("permission denied")
            )
        )

        with self.assertRaises(LocationPermissionError):
            provider.get_position()

    def test_mac_provider_preserves_timeout_error(self) -> None:
        provider = MacOSLocationProvider(
            session_factory=lambda: FakeSession(LocationTimeoutError("timed out"))
        )

        with self.assertRaises(LocationTimeoutError):
            provider.get_position()

    def test_mac_provider_preserves_unavailable_error(self) -> None:
        provider = MacOSLocationProvider(
            session_factory=lambda: FakeSession(
                LocationUnavailableError("unavailable")
            )
        )

        with self.assertRaises(LocationUnavailableError):
            provider.get_position()


if __name__ == "__main__":
    unittest.main()
