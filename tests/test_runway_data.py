"""Deterministic tests for runway import, search, and projection."""

import csv
import tempfile
import unittest
from pathlib import Path

from flight_tracker.display.projection import (
    project_runway_segment,
)
from flight_tracker.models import Position
from flight_tracker.runway_data import RunwaySegment
from flight_tracker.runway_data.sqlite_repository import (
    SqliteRunwayRepository,
    search_bounds,
)
from scripts.build_runway_database import build_database, read_runway


CSV_COLUMNS = [
    "le_latitude_deg",
    "le_longitude_deg",
    "he_latitude_deg",
    "he_longitude_deg",
]


def csv_row(
    low_latitude: str = "40",
    low_longitude: str = "-70",
    high_latitude: str = "40.1",
    high_longitude: str = "-70",
) -> dict[str, str]:
    """Return one small runway CSV row."""

    return {
        "le_latitude_deg": low_latitude,
        "le_longitude_deg": low_longitude,
        "he_latitude_deg": high_latitude,
        "he_longitude_deg": high_longitude,
    }


class RunwayImportTests(unittest.TestCase):
    def test_accepts_two_valid_runway_ends(self) -> None:
        segment = read_runway(csv_row())

        self.assertEqual(
            segment,
            RunwaySegment(Position(40, -70), Position(40.1, -70)),
        )

    def test_rejects_missing_coordinate(self) -> None:
        self.assertIsNone(read_runway(csv_row(low_latitude="")))

    def test_rejects_non_numeric_coordinate(self) -> None:
        self.assertIsNone(read_runway(csv_row(high_longitude="not-a-number")))

    def test_rejects_non_finite_coordinate(self) -> None:
        self.assertIsNone(read_runway(csv_row(high_latitude="nan")))
        self.assertIsNone(read_runway(csv_row(high_latitude="inf")))

    def test_rejects_coordinate_outside_range(self) -> None:
        self.assertIsNone(read_runway(csv_row(low_latitude="90.1")))
        self.assertIsNone(read_runway(csv_row(low_longitude="-180.1")))

    def test_rejects_identical_runway_ends(self) -> None:
        self.assertIsNone(
            read_runway(csv_row(high_latitude="40", high_longitude="-70"))
        )

    def test_rejects_runway_longer_than_ten_nautical_miles(self) -> None:
        self.assertIsNone(read_runway(csv_row(high_latitude="40.2")))

    def test_builds_database_and_reports_counts(self) -> None:
        rows = [
            csv_row(),
            csv_row(low_latitude=""),
            csv_row(high_longitude="not-a-number"),
            csv_row(high_latitude="nan"),
            csv_row(low_latitude="90.1"),
            csv_row(high_latitude="40", high_longitude="-70"),
            csv_row(high_latitude="40.2"),
        ]
        with tempfile.TemporaryDirectory() as temporary_directory:
            temporary_path = Path(temporary_directory)
            source_path = temporary_path / "runways.csv"
            database_path = temporary_path / "runways.sqlite3"
            with source_path.open("w", newline="", encoding="utf-8") as source_file:
                writer = csv.DictWriter(source_file, fieldnames=CSV_COLUMNS)
                writer.writeheader()
                writer.writerows(rows)

            report = build_database(source_path, database_path)

            self.assertEqual(report.source_row_count, 7)
            self.assertEqual(report.accepted_row_count, 1)
            self.assertEqual(report.rejected_row_count, 6)
            self.assertEqual(
                SqliteRunwayRepository(database_path).get_nearby_runways(
                    Position(40, -70), 10
                ),
                (RunwaySegment(Position(40, -70), Position(40.1, -70)),),
            )


class RunwayRepositoryTests(unittest.TestCase):
    def test_search_bounds_use_the_configured_position_and_radius(self) -> None:
        bounds = search_bounds(Position(40, -70), 60)

        self.assertAlmostEqual(bounds[0], 39)
        self.assertAlmostEqual(bounds[1], 41)
        self.assertAlmostEqual(bounds[2], -71.30540728933228)
        self.assertAlmostEqual(bounds[3], -68.69459271066772)

    def test_rtree_excludes_a_distant_runway(self) -> None:
        rows = [
            csv_row(),
            csv_row(low_latitude="41", high_latitude="41.1"),
        ]
        with tempfile.TemporaryDirectory() as temporary_directory:
            temporary_path = Path(temporary_directory)
            source_path = temporary_path / "runways.csv"
            database_path = temporary_path / "runways.sqlite3"
            with source_path.open("w", newline="", encoding="utf-8") as source_file:
                writer = csv.DictWriter(source_file, fieldnames=CSV_COLUMNS)
                writer.writeheader()
                writer.writerows(rows)
            build_database(source_path, database_path)

            runways = SqliteRunwayRepository(database_path).get_nearby_runways(
                Position(40, -70), 10
            )

        self.assertEqual(len(runways), 1)
        self.assertEqual(runways[0].low, Position(40, -70))


class RunwayProjectionTests(unittest.TestCase):
    def test_runway_inside_circle_is_visible(self) -> None:
        segment = project_runway_segment(
            Position(40, -70),
            RunwaySegment(Position(40, -70), Position(40.1, -70)),
            60,
        )

        self.assertIsNotNone(segment)
        assert segment is not None
        self.assertAlmostEqual(segment[0].east, 0)
        self.assertAlmostEqual(segment[0].north, 0)
        self.assertAlmostEqual(segment[1].east, 0)
        self.assertAlmostEqual(segment[1].north, 0.1)

    def test_runway_crossing_edge_is_clipped(self) -> None:
        segment = project_runway_segment(
            Position(40, -70),
            RunwaySegment(Position(39, -70), Position(42, -70)),
            60,
        )

        self.assertIsNotNone(segment)
        assert segment is not None
        self.assertAlmostEqual(segment[0].east, 0)
        self.assertAlmostEqual(segment[0].north, -1)
        self.assertAlmostEqual(segment[1].east, 0)
        self.assertAlmostEqual(segment[1].north, 1)

    def test_runway_outside_circle_is_not_visible(self) -> None:
        segment = project_runway_segment(
            Position(40, -70),
            RunwaySegment(Position(42, -70), Position(43, -70)),
            60,
        )

        self.assertIsNone(segment)


if __name__ == "__main__":
    unittest.main()
