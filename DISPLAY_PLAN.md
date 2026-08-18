# Display Implementation Plan

## Goal

Create a working radar display that starts with this command:

```bash
python3 radar.py
```

The command must open an 800-by-800 radar window. The default center must be
`40.0, -70.0`. The display must show current aircraft as circles.

## 1. Update the project settings

Modify `pyproject.toml`.

- Add `pygame-ce>=2.5.7,<3` to the runtime dependencies.
- Keep `requests`.
- Do not add a geographic library.
- Do not add a hardware library.

Modify `pyrightconfig.json`.

- Set `pythonVersion` to `3.11`.
- Add `radar.py` to the checked files.

## 2. Separate the domain data

Create `flight_tracker/models.py`.

Move these provider-independent types into it:

- `Position`
- `Aircraft`

Keep these retrieval types in `flight_tracker/flight_data/models.py`:

- `NearbyQuery`
- `NearbySnapshot`

Update imports throughout the package.

Continue to export `Position` and `Aircraft` from `flight_tracker.flight_data`.
This keeps the current public imports working.

Run the existing tests after this change. Do not continue until they pass.

## 3. Add configuration and location boundaries

Create `flight_tracker/configuration.py`.

Add an immutable `TrackerSettings` data class with these values:

```text
position:             Position(40.0, -70.0)
search_radius_nm:     100
refresh_seconds:      10.0
api_base_url:         https://api.adsb.lol
api_timeout_seconds:  5.0
window_size:          800
frame_rate:           30
```

Add command-line arguments for these values. `python3 radar.py` must work
without arguments.

Support these optional arguments:

```text
--latitude
--longitude
--radius
--refresh-seconds
--api-base-url
--api-timeout-seconds
--window-size
--frame-rate
```

Do not add environment-variable loading or a configuration file.

Create the `flight_tracker/location` package.

- Define a small `LocationProvider` protocol.
- Give it one `get_position()` method.
- Add `ConfiguredLocationProvider`.
- Make it return the configured position.

Do not copy the macOS location implementation from the other branch.

## 4. Add the radar projection

Create `flight_tracker/display/projection.py`.

Add a small immutable `RadarPoint` type.

Use normalized coordinates:

- `east` ranges from `-1.0` to `1.0`.
- `north` ranges from `-1.0` to `1.0`.
- The radar center is `0.0, 0.0`.

Add a function that accepts these values:

- The radar center.
- An aircraft position.
- The search radius.

Use a local latitude and longitude projection.

```text
north_nm = latitude difference x 60
east_nm = longitude difference x 60 x cos(center latitude)
```

Divide each offset by the search radius.

Return `None` when the projected point is outside the radar circle.

Do not add date-line handling or polar handling. The configured example does
not need these checks.

## 5. Add the Pygame display

Create the `flight_tracker/display` package.

Define a small display protocol. It must let the application perform these
actions:

- Process close events.
- Render one frame.
- Limit the frame rate.
- Close the display.

Create `flight_tracker/display/pygame_display.py`.

Draw these items:

- A black background.
- A green outer radar circle.
- Two green range rings.
- Horizontal and vertical crosshairs.
- A center point.
- One filled circle for each aircraft with a current position.

Use a small fixed aircraft-circle radius. Do not add aircraft icons or labels.

Calculate the radar radius from the smaller display dimension. Leave a small
edge margin. Reverse the north axis when you convert it to screen coordinates.
Pygame increases the screen Y coordinate downward.

Support these exit actions:

- Close the window.
- Press Escape.

Do not add a rotating sweep. Do not add animation classes. Do not use Pygame
sprite classes.

## 6. Add the application loop

Create `flight_tracker/app.py`.

Let the application receive these integrations:

- Flight-data provider.
- Location provider.
- Radar display.
- Tracker settings.

Use `time.monotonic()` to schedule refreshes.

At each data refresh, perform these actions:

1. Get the current tracker position.
2. Build a `NearbyQuery`.
3. Request a `NearbySnapshot`.
4. Store the latest successful aircraft data.
5. Schedule the next refresh.

Keep the previous aircraft data when a flight-data request fails. Print a short
error to the console. Let the next normal refresh try again.

Start with an empty aircraft collection. This lets the radar open when the
first request fails.

Keep the HTTP request synchronous. Do not add a worker thread. Do not add
asynchronous code, retries, or caching.

Call the location provider at each refresh. This lets a future live location
provider replace the configured provider without display changes.

Always close Pygame when the application exits.

## 7. Add the entry point

Create `radar.py` at the repository root.

The file must perform these actions:

1. Parse the settings.
2. Create `ConfiguredLocationProvider`.
3. Create `RequestsTransport` with the configured timeout.
4. Create `AdsbLolClient` with the configured base URL.
5. Create `PygameRadarDisplay`.
6. Call the application loop.

Add this entry-point guard:

```python
if __name__ == "__main__":
    main()
```

Keep all other application logic out of `radar.py`.

## 8. Add deterministic tests

Keep all unit tests offline.

Add tests for these behaviors:

- Default configuration values.
- Command-line configuration overrides.
- The configured location provider.
- North, south, east, and west projection.
- A point at the radar center.
- A point outside the radar circle.
- Radar pixel bounds for an 800-by-800 display.
- Aircraft without a current position.
- Application query coordinates and radius.
- A failed refresh that preserves the last successful data.

Use fake flight-data, location, and display integrations for application tests.

Do not create a real Pygame window in the unit tests.

## 9. Update the documentation

Update `README.md`.

Document this setup:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
python3 radar.py
```

Add one configuration example:

```bash
python3 radar.py --latitude 40 --longitude -70 --radius 50
```

State these limits:

- The display shows current positions only.
- The display does not show paths yet.
- The application uses a configured location.
- The application does not access GPS hardware.
- The target screen resolution is not selected.
- adsb.lol can return no aircraft for a valid request.

## 10. Verify the result

Run these checks:

```bash
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/pyright
```

Verify package installation:

```bash
.venv/bin/python -m pip install -e .
```

Launch the application in a graphical session:

```bash
python3 radar.py
```

Check the display at 800 by 800 pixels.

Confirm these results:

- The radar remains circular.
- The window closes correctly.
- Aircraft stay inside the outer circle.
- The center represents `40.0, -70.0`.
- An empty API response shows an empty radar.
- A failed refresh does not close the radar.

The project has no formatter. The project has no defined build command. State
these facts in the completion report.

## Explicit exclusions

Do not add these features:

- Live location.
- GPS hardware access.
- macOS Core Location.
- Aircraft paths or trails.
- Aircraft classification.
- Callsign labels.
- Compass or gyroscope support.
- Full-screen deployment logic.
- Threads or asynchronous code.
- Retries or caching.
- Extra validation beyond what the current milestone needs.
