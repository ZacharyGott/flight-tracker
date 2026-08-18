# Runway Display Plan

## Goal

Plot nearby runways in the circular radar display.

Prepare the runway data once. Keep the runtime work small for Raspberry Pi hardware.

## Project Decisions

Use SQLite with its RTree spatial index.

Use the Python standard-library `sqlite3` module. Do not add a database dependency.

Generate the database before runtime. Commit the generated database to the repository. Do not put the source CSV on the target device.

Query the database once when the application starts. Keep the query result in memory while the application runs.

## Source Data Review

The reviewed `runways.csv` file contains 48,178 rows.

- 15,530 rows have valid coordinates for both runway ends.
- 19 of those rows have identical runway ends.
- Two rows have runway ends more than 10 nautical miles apart.
- The final database will contain 15,509 drawable runway segments.
- A prototype database is approximately 1.7 MiB.

The city test queries returned 132 to 217 bounding-box candidates for a 100-nautical-mile radius. Cached queries took approximately 0.1 to 0.2 milliseconds on the development computer.

## Import Rules

Keep a row only when both runway ends contain a valid latitude and longitude.

A valid coordinate must meet these conditions:

- The value is present.
- The value is numeric.
- The value is finite.
- Latitude is from -90 through 90 degrees.
- Longitude is from -180 through 180 degrees.

A drawable runway segment must meet these conditions:

- The two runway ends are different.
- The distance between the runway ends is not more than 10 nautical miles.

Do not filter by closed state, surface, lighting, or reported runway length.

The import script must report the source row count, the accepted row count, and the rejected row count.

## Proposed File Structure

```text
scripts/build_runway_database.py
flight_tracker/runway_data/__init__.py
flight_tracker/runway_data/sqlite_repository.py
flight_tracker/runway_data/runways.sqlite3
flight_tracker/runway_data/README.md
tests/test_runway_data.py
```

Use a small runway domain model. Store only the data that the display needs.

Put the SQLite implementation behind a small repository interface. Tests must be able to replace the repository with generated data.

## Database Structure

Use one table for runway coordinates.

```sql
CREATE TABLE runways (
    id INTEGER PRIMARY KEY,
    low_latitude REAL NOT NULL,
    low_longitude REAL NOT NULL,
    high_latitude REAL NOT NULL,
    high_longitude REAL NOT NULL
);
```

Use one RTree virtual table for runway bounds.

```sql
CREATE VIRTUAL TABLE runway_bounds USING rtree(
    runway_id,
    min_latitude,
    max_latitude,
    min_longitude,
    max_longitude
);
```

The import script must write one row to each table for every accepted runway.

## Runtime Flow

1. Read the configured position and search radius.
2. Open the runway database in read-only mode.
3. Convert the circular search area to a latitude and longitude bounding box.
4. Use the RTree to find runway bounds that overlap the search bounds.
5. Read the matching runway coordinates.
6. Close the database.
7. Keep the returned runway tuple in memory.
8. Pass the runway tuple to the display for each frame.

The RTree query can return a small number of bounding-box false positives. The display projection must do the exact circular boundary check.

## Display Flow

Use the existing normalized radar projection.

1. Project both runway ends without clipping them first.
2. Clip the runway segment to the circular radar boundary.
3. Skip a segment that does not intersect the radar circle.
4. Convert each clipped end to a pixel position.
5. Draw a one-pixel muted green line.
6. Draw runway lines before aircraft paths and aircraft markers.

Do not add a runway label, selection action, information card, or surface style in this change.

Do not add a runway-layer cache in this change. The application will query the database only once. Profile the display on the selected Raspberry Pi before adding a cache.

## Configuration

Add a `--runway-database` command-line option.

Use the packaged `flight_tracker/runway_data/runways.sqlite3` file as the default value.

Do not scan the CSV at runtime. Do not add a CSV fallback.

## Implementation Steps for Luna-xHigh

1. Add the runway domain model and repository interface.
2. Add the SQLite repository implementation.
3. Add the one-time CSV import script.
4. Generate and commit the runway database.
5. Add the database path to `TrackerSettings` and the command-line parser.
6. Query nearby runways once in `TrackerApplication.run()`.
7. Pass the runway tuple through the radar display interface.
8. Add a runway-segment projection helper.
9. Draw clipped runway segments in `PygameRadarDisplay`.
10. Update the project documentation.
11. Add deterministic tests.
12. Run all available verification commands.

## Tests

Use a small generated CSV and a temporary SQLite database for unit tests.

Test these import cases:

- Both runway ends are valid.
- One coordinate is missing.
- One coordinate is not numeric.
- One coordinate is not finite.
- One coordinate is outside its valid range.
- Both runway ends are identical.
- The runway ends are more than 10 nautical miles apart.

Test these search and display cases:

- The RTree query returns a nearby runway.
- The RTree query excludes a distant runway.
- A runway inside the circle is visible.
- A runway that crosses the radar edge is clipped.
- A runway outside the circle is not visible.
- The application queries the repository once.
- The application supplies the same runway tuple to each display frame.

Unit tests must not use the downloaded CSV. Unit tests must not require a network connection.

## Verification

Run these available checks:

```bash
python -m unittest
pyright
```

Inspect the display at 800 by 800 pixels. The project has not selected the target screen resolution.

The project does not currently define a formatter command or a build command. State this fact in the implementation report.

## Work Not Included

Do not add these features in this change:

- Automatic runway-data downloads.
- Database migrations.
- A CSV runtime fallback.
- Runway labels or runway information cards.
- Styles for closed, lighted, or paved runways.
- A compatibility layer for SQLite builds without RTree.
- Polar-region support.
- Date-line crossing support.

The existing projection does not support polar regions or date-line crossing. Address those limits in a separate project decision.
