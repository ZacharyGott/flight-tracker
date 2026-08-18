# Runway data

The packaged `runways.sqlite3` file contains drawable runway segments from the
runway CSV export. The build script keeps rows with two valid runway
ends. It removes identical ends and segments longer than 10 nautical miles.

The application opens this database in read-only mode. It queries the nearby
runways once when it starts. It keeps the returned tuple in memory while it
runs. The application does not read a CSV file at runtime.

To rebuild the database, run:

```bash
python scripts/build_runway_database.py \
  /path/to/runways.csv \
  flight_tracker/runway_data/runways.sqlite3
```

The script reports the source row count, accepted row count, and rejected row
count.
