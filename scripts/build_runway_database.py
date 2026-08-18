"""Build the packaged runway SQLite database from a runway CSV file."""

import argparse
import csv
import math
import sqlite3
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from flight_tracker.models import Position
from flight_tracker.runway_data import RunwaySegment


MAX_RUNWAY_LENGTH_NM = 10.0
EARTH_RADIUS_NM = 3440.065


@dataclass(frozen=True, slots=True)
class ImportReport:
    """Counts reported after importing a runway CSV file."""

    source_row_count: int
    accepted_row_count: int
    rejected_row_count: int


def parse_coordinate(
    value: str | None, minimum: float, maximum: float
) -> float | None:
    """Return a finite coordinate in range, or None for an invalid value."""

    if value is None or value.strip() == "":
        return None
    try:
        coordinate = float(value)
    except ValueError:
        return None
    if not math.isfinite(coordinate) or not minimum <= coordinate <= maximum:
        return None
    return coordinate


def read_runway(row: Mapping[str, str | None]) -> RunwaySegment | None:
    """Convert one CSV row to a drawable runway segment when it is valid."""

    low_latitude = parse_coordinate(row.get("le_latitude_deg"), -90, 90)
    low_longitude = parse_coordinate(row.get("le_longitude_deg"), -180, 180)
    high_latitude = parse_coordinate(row.get("he_latitude_deg"), -90, 90)
    high_longitude = parse_coordinate(row.get("he_longitude_deg"), -180, 180)
    if (
        low_latitude is None
        or low_longitude is None
        or high_latitude is None
        or high_longitude is None
    ):
        return None
    if low_latitude == high_latitude and low_longitude == high_longitude:
        return None
    segment = RunwaySegment(
        low=Position(low_latitude, low_longitude),
        high=Position(high_latitude, high_longitude),
    )
    if runway_length_nm(segment) > MAX_RUNWAY_LENGTH_NM:
        return None
    return segment


def runway_length_nm(segment: RunwaySegment) -> float:
    """Return the great-circle distance between runway endpoints."""

    latitude_delta = math.radians(segment.high.latitude - segment.low.latitude)
    longitude_delta = math.radians(segment.high.longitude - segment.low.longitude)
    low_latitude = math.radians(segment.low.latitude)
    high_latitude = math.radians(segment.high.latitude)
    haversine = (
        math.sin(latitude_delta / 2) ** 2
        + math.cos(low_latitude)
        * math.cos(high_latitude)
        * math.sin(longitude_delta / 2) ** 2
    )
    return 2 * EARTH_RADIUS_NM * math.atan2(
        math.sqrt(haversine), math.sqrt(1 - haversine)
    )


def build_database(source_path: Path, database_path: Path) -> ImportReport:
    """Import accepted runway segments and return the import counts."""

    database_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(database_path) as connection:
        connection.executescript(
            """
            DROP TABLE IF EXISTS runway_bounds;
            DROP TABLE IF EXISTS runways;
            CREATE TABLE runways (
                id INTEGER PRIMARY KEY,
                low_latitude REAL NOT NULL,
                low_longitude REAL NOT NULL,
                high_latitude REAL NOT NULL,
                high_longitude REAL NOT NULL
            );
            CREATE VIRTUAL TABLE runway_bounds USING rtree(
                runway_id,
                min_latitude,
                max_latitude,
                min_longitude,
                max_longitude
            );
            """
        )
        source_row_count = 0
        accepted_row_count = 0
        with source_path.open(newline="", encoding="utf-8") as source_file:
            reader = csv.DictReader(source_file)
            for row in reader:
                source_row_count += 1
                segment = read_runway(row)
                if segment is None:
                    continue
                accepted_row_count += 1
                runway_id = accepted_row_count
                connection.execute(
                    """
                    INSERT INTO runways(
                        id, low_latitude, low_longitude,
                        high_latitude, high_longitude
                    ) VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        runway_id,
                        segment.low.latitude,
                        segment.low.longitude,
                        segment.high.latitude,
                        segment.high.longitude,
                    ),
                )
                connection.execute(
                    """
                    INSERT INTO runway_bounds(
                        runway_id, min_latitude, max_latitude,
                        min_longitude, max_longitude
                    ) VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        runway_id,
                        min(segment.low.latitude, segment.high.latitude),
                        max(segment.low.latitude, segment.high.latitude),
                        min(segment.low.longitude, segment.high.longitude),
                        max(segment.low.longitude, segment.high.longitude),
                    ),
                )
        connection.commit()
    return ImportReport(
        source_row_count=source_row_count,
        accepted_row_count=accepted_row_count,
        rejected_row_count=source_row_count - accepted_row_count,
    )


def main(arguments: list[str] | None = None) -> None:
    """Build a database from the source CSV and print import counts."""

    parser = argparse.ArgumentParser(description="Build the runway SQLite database.")
    parser.add_argument("source_csv", type=Path)
    parser.add_argument("database", type=Path)
    values = parser.parse_args(arguments)
    report = build_database(values.source_csv, values.database)
    print(f"Source rows: {report.source_row_count}")
    print(f"Accepted rows: {report.accepted_row_count}")
    print(f"Rejected rows: {report.rejected_row_count}")


if __name__ == "__main__":
    main()
