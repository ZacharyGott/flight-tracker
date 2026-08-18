"""Offline tests for configuration, projection, and the tracker loop."""

import io
import unittest
from collections.abc import Sequence
from contextlib import redirect_stdout
from datetime import datetime, timezone
from math import cos, radians

from flight_tracker.app import TrackerApplication
from flight_tracker.configuration import TrackerSettings, parse_settings
from flight_tracker.display.pygame_display import calculate_radar_radius
from flight_tracker.display.projection import RadarPoint, project_position
from flight_tracker.flight_data import NearbyQuery, NearbySnapshot, TransportError
from flight_tracker.location import ConfiguredLocationProvider
from flight_tracker.models import Aircraft, Position


class ConfigurationTests(unittest.TestCase):
    def test_default_values(self) -> None:
        settings = parse_settings([])

        self.assertEqual(settings, TrackerSettings())
        self.assertEqual(settings.position, Position(40.0, -70.0))

    def test_command_line_overrides(self) -> None:
        settings = parse_settings(
            [
                "--latitude",
                "41.5",
                "--longitude",
                "-71.5",
                "--radius",
                "50",
                "--refresh-seconds",
                "2.5",
                "--api-base-url",
                "https://example.test",
                "--api-timeout-seconds",
                "1.5",
                "--window-size",
                "600",
                "--frame-rate",
                "20",
            ]
        )

        self.assertEqual(settings.position, Position(41.5, -71.5))
        self.assertEqual(settings.search_radius_nm, 50)
        self.assertEqual(settings.refresh_seconds, 2.5)
        self.assertEqual(settings.api_base_url, "https://example.test")
        self.assertEqual(settings.api_timeout_seconds, 1.5)
        self.assertEqual(settings.window_size, 600)
        self.assertEqual(settings.frame_rate, 20)


class LocationProviderTests(unittest.TestCase):
    def test_returns_configured_position(self) -> None:
        position = Position(41.0, -71.0)

        provider = ConfiguredLocationProvider(position)

        self.assertEqual(provider.get_position(), position)


class ProjectionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.center = Position(40.0, -70.0)

    def test_projects_cardinal_directions(self) -> None:
        self.assertEqual(
            project_position(self.center, Position(40.0, -70.0), 60),
            RadarPoint(east=0.0, north=0.0),
        )
        self.assertEqual(
            project_position(self.center, Position(41.0, -70.0), 60),
            RadarPoint(east=0.0, north=1.0),
        )
        self.assertEqual(
            project_position(self.center, Position(39.0, -70.0), 60),
            RadarPoint(east=0.0, north=-1.0),
        )

        east = project_position(self.center, Position(40.0, -69.0), 60)
        west = project_position(self.center, Position(40.0, -71.0), 60)
        self.assertIsNotNone(east)
        self.assertIsNotNone(west)
        assert east is not None
        assert west is not None
        self.assertAlmostEqual(east.east, cos(radians(40)))
        self.assertAlmostEqual(east.north, 0.0)
        self.assertAlmostEqual(west.east, -cos(radians(40)))
        self.assertAlmostEqual(west.north, 0.0)

    def test_returns_none_outside_radar_circle(self) -> None:
        self.assertIsNone(project_position(self.center, Position(42.0, -70.0), 60))


class DisplayBoundsTests(unittest.TestCase):
    def test_800_pixel_radar_stays_inside_window(self) -> None:
        radius = calculate_radar_radius((800, 800))
        center = 400

        self.assertEqual(radius, 380)
        self.assertEqual((center - radius, center + radius), (20, 780))


class FakeFlightDataProvider:
    def __init__(self, responses: list[NearbySnapshot | Exception]) -> None:
        self.responses = responses
        self.queries: list[NearbyQuery] = []

    def nearby(self, query: NearbyQuery) -> NearbySnapshot:
        self.queries.append(query)
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


class FakeLocationProvider:
    def __init__(self, position: Position) -> None:
        self.position = position
        self.calls = 0

    def get_position(self) -> Position:
        self.calls += 1
        return self.position


class FakeDisplay:
    def __init__(self, frames: int) -> None:
        self.frames = frames
        self.rendered: list[tuple[Position, tuple[Aircraft, ...], int]] = []
        self.frame_rates: list[int] = []
        self.closed = False

    def process_events(self) -> bool:
        if self.frames == 0:
            return False
        self.frames -= 1
        return True

    def render(
        self,
        center: Position,
        aircraft: Sequence[Aircraft],
        search_radius_nm: int,
    ) -> None:
        self.rendered.append((center, tuple(aircraft), search_radius_nm))

    def limit_frame_rate(self, frame_rate: int) -> None:
        self.frame_rates.append(frame_rate)

    def close(self) -> None:
        self.closed = True


class TrackerApplicationTests(unittest.TestCase):
    OBSERVED_AT = datetime.fromtimestamp(1_725_000_000, tz=timezone.utc)

    def test_refresh_uses_location_coordinates_and_radius(self) -> None:
        position = Position(41.0, -71.0)
        snapshot = NearbySnapshot(
            query=NearbyQuery(41.0, -71.0, 50),
            aircraft=(),
            observed_at=self.OBSERVED_AT,
        )
        flight_data = FakeFlightDataProvider([snapshot])
        location = FakeLocationProvider(position)
        display = FakeDisplay(frames=1)
        settings = TrackerSettings(
            position=Position(40.0, -70.0),
            search_radius_nm=50,
            refresh_seconds=10.0,
            frame_rate=30,
        )

        TrackerApplication(
            flight_data,
            location,
            display,
            settings,
            clock=lambda: 0.0,
        ).run()

        self.assertEqual(flight_data.queries, [NearbyQuery(41.0, -71.0, 50)])
        self.assertEqual(location.calls, 1)
        self.assertEqual(display.rendered[0][0], position)
        self.assertTrue(display.closed)

    def test_failed_refresh_preserves_last_successful_data(self) -> None:
        aircraft = (Aircraft(icao_hex="abc123", position=None),)
        snapshot = NearbySnapshot(
            query=NearbyQuery(40.0, -70.0, 100),
            aircraft=aircraft,
            observed_at=self.OBSERVED_AT,
        )
        flight_data = FakeFlightDataProvider([snapshot, TransportError("offline")])
        display = FakeDisplay(frames=2)
        clock_values = iter((0.0, 11.0))
        settings = TrackerSettings()

        output = io.StringIO()
        with redirect_stdout(output):
            TrackerApplication(
                flight_data,
                FakeLocationProvider(settings.position),
                display,
                settings,
                clock=lambda: next(clock_values),
            ).run()

        self.assertEqual(display.rendered[0][1], aircraft)
        self.assertEqual(display.rendered[1][1], aircraft)
        self.assertIn("flight-data refresh failed: offline", output.getvalue())
        self.assertTrue(display.closed)


if __name__ == "__main__":
    unittest.main()
