"""Read nearby runway segments from the packaged SQLite database."""

import math
import sqlite3
from pathlib import Path
from urllib.parse import quote

from flight_tracker.models import Position

from . import RunwaySegment


def search_bounds(
    center: Position, radius_nm: int | float
) -> tuple[float, float, float, float]:
    """Return the latitude and longitude bounds for a circular search area."""

    latitude_delta = radius_nm / 60
    longitude_delta = radius_nm / (60 * math.cos(math.radians(center.latitude)))
    return (
        center.latitude - latitude_delta,
        center.latitude + latitude_delta,
        center.longitude - longitude_delta,
        center.longitude + longitude_delta,
    )


class SqliteRunwayRepository:
    """Read runway segments from a SQLite database in read-only mode."""

    def __init__(self, database_path: Path | str) -> None:
        self._database_path = Path(database_path)

    def get_nearby_runways(
        self, center: Position, radius_nm: int | float
    ) -> tuple[RunwaySegment, ...]:
        """Return runway bounds that overlap the search bounding box."""

        min_latitude, max_latitude, min_longitude, max_longitude = search_bounds(
            center, radius_nm
        )
        database_uri = f"file:{quote(str(self._database_path.resolve()))}?mode=ro"
        with sqlite3.connect(database_uri, uri=True) as connection:
            rows = connection.execute(
                """
                SELECT runways.low_latitude,
                       runways.low_longitude,
                       runways.high_latitude,
                       runways.high_longitude
                FROM runway_bounds
                JOIN runways ON runways.id = runway_bounds.runway_id
                WHERE runway_bounds.max_latitude >= ?
                  AND runway_bounds.min_latitude <= ?
                  AND runway_bounds.max_longitude >= ?
                  AND runway_bounds.min_longitude <= ?
                ORDER BY runways.id
                """,
                (min_latitude, max_latitude, min_longitude, max_longitude),
            ).fetchall()
        return tuple(
            RunwaySegment(
                low=Position(row[0], row[1]),
                high=Position(row[2], row[3]),
            )
            for row in rows
        )


__all__ = ["SqliteRunwayRepository", "search_bounds"]
