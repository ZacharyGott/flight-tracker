"""Offline tests for configuration, projection, and the tracker loop."""

import io
import unittest
from collections.abc import Sequence
from contextlib import redirect_stdout
from datetime import datetime, timezone
from math import cos, radians

from flight_tracker.app import TrackerApplication
from flight_tracker.configuration import TrackerSettings, parse_settings
from flight_tracker.display.pygame_display import (
    DARK_GREEN,
    DARK_GREY,
    calculate_radar_radius,
    prediction_color,
)
from flight_tracker.display.projection import (
    RadarPoint,
    clip_segment_to_unit_circle,
    project_position,
)
from flight_tracker.flight_data import NearbyQuery, NearbySnapshot, PollResult
from flight_tracker.location import ConfiguredLocationProvider
from flight_tracker.models import Aircraft, Position
from flight_tracker.motion import TrackedAircraft


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
                "--stale-after-seconds",
                "15",
                "--remove-after-seconds",
                "45",
            ]
        )

        self.assertEqual(settings.position, Position(41.5, -71.5))
        self.assertEqual(settings.search_radius_nm, 50)
        self.assertEqual(settings.refresh_seconds, 2.5)
        self.assertEqual(settings.api_base_url, "https://example.test")
        self.assertEqual(settings.api_timeout_seconds, 1.5)
        self.assertEqual(settings.window_size, 600)
        self.assertEqual(settings.frame_rate, 20)
        self.assertEqual(settings.stale_after_seconds, 15)
        self.assertEqual(settings.remove_after_seconds, 45)


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

    def test_clips_line_at_radar_boundary(self) -> None:
        segment = clip_segment_to_unit_circle(
            RadarPoint(east=0, north=0), RadarPoint(east=2, north=0)
        )

        self.assertEqual(segment, (RadarPoint(east=0, north=0), RadarPoint(east=1, north=0)))


class DisplayBoundsTests(unittest.TestCase):
    def test_800_pixel_radar_stays_inside_window(self) -> None:
        radius = calculate_radar_radius((800, 800))
        center = 400

        self.assertEqual(radius, 380)
        self.assertEqual((center - radius, center + radius), (20, 780))


class PredictionDisplayColorTests(unittest.TestCase):
    def test_current_prediction_uses_dark_green(self) -> None:
        self.assertEqual(prediction_color(False), DARK_GREEN)

    def test_stale_prediction_uses_dark_grey(self) -> None:
        self.assertEqual(prediction_color(True), DARK_GREY)


class FakeSnapshotPoller:
    def __init__(self, results: list[PollResult] | None = None) -> None:
        self.results = results or []
        self.queries: list[NearbyQuery] = []
        self.stopped = False

    def start(self, query: NearbyQuery) -> None:
        self.queries.append(query)

    def drain(self) -> tuple[PollResult, ...]:
        results = tuple(self.results)
        self.results.clear()
        return results

    def stop(self) -> None:
        self.stopped = True


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
        self.rendered: list[tuple[Position, tuple[TrackedAircraft, ...], int]] = []
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
        aircraft: Sequence[TrackedAircraft],
        search_radius_nm: int,
    ) -> None:
        self.rendered.append((center, tuple(aircraft), search_radius_nm))

    def limit_frame_rate(self, frame_rate: int) -> None:
        self.frame_rates.append(frame_rate)

    def close(self) -> None:
        self.closed = True


class TrackerApplicationTests(unittest.TestCase):
    OBSERVED_AT = datetime.fromtimestamp(1_725_000_000, tz=timezone.utc)

    def test_starts_poller_with_location_coordinates_and_radius(self) -> None:
        position = Position(41.0, -71.0)
        flight_data = FakeSnapshotPoller()
        location = FakeLocationProvider(position)
        display = FakeDisplay(frames=1)
        settings = TrackerSettings(
            position=Position(40.0, -70.0),
            search_radius_nm=50,
            refresh_seconds=10.0,
            frame_rate=30,
        )

        TrackerApplication(
            flight_data_poller=flight_data,
            location_provider=location,
            display=display,
            settings=settings,
            clock=lambda: 0.0,
        ).run()

        self.assertEqual(flight_data.queries, [NearbyQuery(41.0, -71.0, 50)])
        self.assertEqual(location.calls, 1)
        self.assertEqual(display.rendered[0][0], position)
        self.assertTrue(display.closed)
        self.assertTrue(flight_data.stopped)

    def test_renders_when_poller_has_no_result(self) -> None:
        settings = TrackerSettings()
        flight_data = FakeSnapshotPoller()
        display = FakeDisplay(frames=1)

        TrackerApplication(
            flight_data_poller=flight_data,
            location_provider=FakeLocationProvider(settings.position),
            display=display,
            settings=settings,
            clock=lambda: 0.0,
        ).run()

        self.assertEqual(display.rendered[0][1], ())

    def test_applies_successful_snapshot(self) -> None:
        aircraft = (Aircraft(icao_hex="abc123", position=Position(40.5, -70.5)),)
        snapshot = NearbySnapshot(
            query=NearbyQuery(40.0, -70.0, 100),
            aircraft=aircraft,
            observed_at=self.OBSERVED_AT,
        )
        flight_data = FakeSnapshotPoller(
            [PollResult(received_at=0.0, snapshot=snapshot)]
        )
        display = FakeDisplay(frames=1)
        settings = TrackerSettings()

        TrackerApplication(
            flight_data_poller=flight_data,
            location_provider=FakeLocationProvider(settings.position),
            display=display,
            settings=settings,
            clock=lambda: 0.0,
        ).run()

        self.assertEqual(display.rendered[0][1][0].aircraft, aircraft[0])

    def test_prints_poll_error_and_keeps_rendering(self) -> None:
        flight_data = FakeSnapshotPoller(
            [PollResult(received_at=0.0, error_message="offline")]
        )
        display = FakeDisplay(frames=1)
        settings = TrackerSettings()

        output = io.StringIO()
        with redirect_stdout(output):
            TrackerApplication(
                flight_data_poller=flight_data,
                location_provider=FakeLocationProvider(settings.position),
                display=display,
                settings=settings,
                clock=lambda: 0.0,
            ).run()

        self.assertEqual(len(display.rendered), 1)
        self.assertIn("flight-data refresh failed: offline", output.getvalue())
        self.assertTrue(display.closed)
        self.assertTrue(flight_data.stopped)


if __name__ == "__main__":
    unittest.main()
