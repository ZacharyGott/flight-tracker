"""Offline tests for configuration, projection, and the tracker loop."""

import io
import os
import unittest
from collections.abc import Sequence
from contextlib import redirect_stdout
from datetime import datetime, timezone
from math import cos, radians
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame

from flight_tracker.app import TrackerApplication
from flight_tracker.configuration import TrackerSettings, parse_settings
from flight_tracker.display.pygame_display import (
    BLUE,
    CHERRY_RED,
    DARK_GREEN,
    DARK_GREY,
    GREEN,
    LIGHT_GREY,
    STATS_FONT_SIZE,
    calculate_radar_radius,
    has_dual_highlight_ring,
    marker_color,
    marker_draw_priority,
    prediction_color,
    statistics_text_rectangles,
)
from flight_tracker.display.aircraft_stats import summarize_aircraft
from flight_tracker.display.aircraft_card import (
    aircraft_card_lines,
    card_rect_near_aircraft,
    knots_to_mph,
    nearest_marker,
)
from flight_tracker.display.projection import (
    RadarPoint,
    clip_segment_to_unit_circle,
    project_position,
)
from flight_tracker.flight_data import NearbyQuery, NearbySnapshot, PollResult
from flight_tracker.location import ConfiguredLocationProvider
from flight_tracker.models import Aircraft, AircraftClassification, Position
from flight_tracker.motion import TrackedAircraft
from flight_tracker.runway_data import RunwaySegment


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
                "--runway-database",
                "/tmp/test-runways.sqlite3",
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
        self.assertEqual(settings.runway_database, Path("/tmp/test-runways.sqlite3"))


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


class AircraftMarkerColorTests(unittest.TestCase):
    @staticmethod
    def tracked(aircraft: Aircraft, is_stale: bool = False) -> TrackedAircraft:
        return TrackedAircraft(
            aircraft=aircraft,
            estimated_position=None,
            potential_radius_nm=None,
            is_stale=is_stale,
        )

    def test_normal_current_marker_is_green(self) -> None:
        item = self.tracked(Aircraft(icao_hex="current"))

        self.assertEqual(marker_color(item, summarize_aircraft((item.aircraft,))), GREEN)

    def test_normal_stale_marker_is_grey(self) -> None:
        item = self.tracked(Aircraft(icao_hex="stale"), is_stale=True)

        self.assertEqual(
            marker_color(item, summarize_aircraft((item.aircraft,))), LIGHT_GREY
        )

    def test_fastest_marker_is_cherry_red(self) -> None:
        aircraft = Aircraft(icao_hex="fastest", ground_speed_knots=200)
        item = self.tracked(aircraft)

        self.assertEqual(marker_color(item, summarize_aircraft((aircraft,))), CHERRY_RED)

    def test_highest_marker_is_blue(self) -> None:
        aircraft = Aircraft(icao_hex="highest", altitude_feet=20000)
        item = self.tracked(aircraft)

        self.assertEqual(marker_color(item, summarize_aircraft((aircraft,))), BLUE)

    def test_both_extremes_use_cherry_red_and_a_blue_ring(self) -> None:
        aircraft = Aircraft(
            icao_hex="both",
            ground_speed_knots=200,
            altitude_feet=20000,
        )
        item = self.tracked(aircraft)
        stats = summarize_aircraft((aircraft,))

        self.assertEqual(marker_color(item, stats), CHERRY_RED)
        self.assertTrue(has_dual_highlight_ring(item, stats))

    def test_highlighted_markers_draw_after_normal_markers(self) -> None:
        normal = Aircraft(icao_hex="normal")
        highest = Aircraft(icao_hex="highest", altitude_feet=20000)
        fastest = Aircraft(icao_hex="fastest", ground_speed_knots=200)
        stats = summarize_aircraft((normal, highest, fastest))

        self.assertLess(
            marker_draw_priority(self.tracked(normal), stats),
            marker_draw_priority(self.tracked(highest), stats),
        )
        self.assertLess(
            marker_draw_priority(self.tracked(normal), stats),
            marker_draw_priority(self.tracked(fastest), stats),
        )


class StatisticsDisplayBoundsTests(unittest.TestCase):
    def test_statistics_text_rectangles_stay_outside_800_pixel_circle(self) -> None:
        pygame.font.init()
        font = pygame.font.Font(None, STATS_FONT_SIZE)
        lines = (
            "Aircraft 12",
            "Commercial 4 · Private 2 · GA 3",
            "Military 1 · Unknown 2",
            "Fastest AAL2741 · 483 mph",
            "Highest N123AA · 35,000 ft",
        )
        rectangles = statistics_text_rectangles(
            (800, 800), tuple(font.size(line) for line in lines)
        )

        for x, y, width, height in rectangles:
            nearest_x = max(x, min(400, x + width))
            nearest_y = max(y, min(400, y + height))
            self.assertGreaterEqual(
                (nearest_x - 400) ** 2 + (nearest_y - 400) ** 2,
                380**2,
            )


class AircraftCardTests(unittest.TestCase):
    def test_formats_aircraft_details_and_converts_speed(self) -> None:
        aircraft = Aircraft(
            icao_hex="abc123",
            callsign="AAL2741",
            classification=AircraftClassification.COMMERCIAL,
            aircraft_type="B738",
            registration="N123AA",
            altitude_feet=35000,
            ground_speed_knots=420,
            track_degrees=271,
        )

        self.assertEqual(
            aircraft_card_lines(aircraft),
            (
                "AAL2741",
                "Commercial · B738",
                "Registration: N123AA",
                "Altitude: 35,000 ft",
                "Ground speed: 420 kt · 483 mph",
                "Track: 271°",
                "ICAO: ABC123",
            ),
        )
        self.assertEqual(knots_to_mph(420), 483)

    def test_uses_unknown_for_missing_values(self) -> None:
        self.assertEqual(
            aircraft_card_lines(Aircraft(icao_hex="")),
            (
                "Unknown",
                "Unknown · Unknown",
                "Registration: Unknown",
                "Altitude: Unknown",
                "Ground speed: Unknown",
                "Track: Unknown",
                "ICAO: Unknown",
            ),
        )

    def test_uses_registration_when_callsign_is_missing(self) -> None:
        lines = aircraft_card_lines(
            Aircraft(icao_hex="abc123", registration=" N123AA ")
        )

        self.assertEqual(lines[0], "N123AA")

    def test_uses_uppercase_icao_when_callsign_and_registration_are_missing(
        self,
    ) -> None:
        lines = aircraft_card_lines(Aircraft(icao_hex="abc123"))

        self.assertEqual(lines[0], "ABC123")

    def test_nearest_marker_wins_for_overlapping_hit_areas(self) -> None:
        self.assertEqual(
            nearest_marker(
                (100, 100),
                (("far", (108, 100)), ("near", (103, 100))),
            ),
            "near",
        )
        self.assertIsNone(nearest_marker((100, 100), (("aircraft", (120, 100)),)))

    def test_card_rectangle_stays_inside_radar_circle(self) -> None:
        for anchor in ((400, 20), (780, 400), (400, 780), (20, 400), (400, 400)):
            rectangle = card_rect_near_aircraft(
                anchor,
                (160, 100),
                (400, 400),
                380,
            )

            x, y, width, height = rectangle
            for corner_x, corner_y in (
                (x, y),
                (x + width, y),
                (x, y + height),
                (x + width, y + height),
            ):
                self.assertLessEqual(
                    (corner_x - 400) ** 2 + (corner_y - 400) ** 2,
                    380**2,
                )

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
        self.rendered: list[
            tuple[
                Position,
                tuple[TrackedAircraft, ...],
                tuple[RunwaySegment, ...],
                int,
            ]
        ] = []
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
        runways: Sequence[RunwaySegment],
        search_radius_nm: int,
    ) -> None:
        self.rendered.append(
            (center, tuple(aircraft), tuple(runways), search_radius_nm)
        )

    def limit_frame_rate(self, frame_rate: int) -> None:
        self.frame_rates.append(frame_rate)

    def close(self) -> None:
        self.closed = True


class FakeRunwayRepository:
    def __init__(self, runways: tuple[RunwaySegment, ...] = ()) -> None:
        self.runways = runways
        self.calls: list[tuple[Position, int | float]] = []

    def get_nearby_runways(
        self, center: Position, radius_nm: int | float
    ) -> tuple[RunwaySegment, ...]:
        self.calls.append((center, radius_nm))
        return self.runways


class TrackerApplicationTests(unittest.TestCase):
    OBSERVED_AT = datetime.fromtimestamp(1_725_000_000, tz=timezone.utc)

    def test_starts_poller_with_location_coordinates_and_radius(self) -> None:
        position = Position(41.0, -71.0)
        flight_data = FakeSnapshotPoller()
        location = FakeLocationProvider(position)
        display = FakeDisplay(frames=1)
        runway_repository = FakeRunwayRepository()
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
            runway_repository=runway_repository,
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
        runway_repository = FakeRunwayRepository()

        TrackerApplication(
            flight_data_poller=flight_data,
            location_provider=FakeLocationProvider(settings.position),
            display=display,
            settings=settings,
            runway_repository=runway_repository,
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
        runway_repository = FakeRunwayRepository()

        TrackerApplication(
            flight_data_poller=flight_data,
            location_provider=FakeLocationProvider(settings.position),
            display=display,
            settings=settings,
            runway_repository=runway_repository,
            clock=lambda: 0.0,
        ).run()

        self.assertEqual(display.rendered[0][1][0].aircraft, aircraft[0])

    def test_prints_poll_error_and_keeps_rendering(self) -> None:
        flight_data = FakeSnapshotPoller(
            [PollResult(received_at=0.0, error_message="offline")]
        )
        display = FakeDisplay(frames=1)
        settings = TrackerSettings()
        runway_repository = FakeRunwayRepository()

        output = io.StringIO()
        with redirect_stdout(output):
            TrackerApplication(
                flight_data_poller=flight_data,
                location_provider=FakeLocationProvider(settings.position),
                display=display,
                settings=settings,
                runway_repository=runway_repository,
                clock=lambda: 0.0,
            ).run()

        self.assertEqual(len(display.rendered), 1)
        self.assertIn("flight-data refresh failed: offline", output.getvalue())
        self.assertTrue(display.closed)
        self.assertTrue(flight_data.stopped)

    def test_queries_runways_once_and_reuses_tuple_for_each_frame(self) -> None:
        runways = (RunwaySegment(Position(40, -70), Position(40.1, -70)),)
        runway_repository = FakeRunwayRepository(runways)
        display = FakeDisplay(frames=2)
        settings = TrackerSettings()

        TrackerApplication(
            flight_data_poller=FakeSnapshotPoller(),
            location_provider=FakeLocationProvider(settings.position),
            display=display,
            settings=settings,
            runway_repository=runway_repository,
            clock=lambda: 0.0,
        ).run()

        self.assertEqual(len(runway_repository.calls), 1)
        self.assertEqual(display.rendered[0][2], runways)
        self.assertIs(display.rendered[0][2], display.rendered[1][2])


if __name__ == "__main__":
    unittest.main()
