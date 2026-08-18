# Smooth Display Implementation Plan

Date: 2026-08-18

## Instruction for GPT-5.6 Luna

Implement this plan in order. Keep the implementation small. Do not add features that this plan excludes.

Read `AGENTS.md` before you edit code. Use ASD-STE Simplified Technical English in documentation, comments, error messages, and user-interface text.

The working tree contains a user-owned deletion of `DISPLAY_PLAN.md`. Do not restore or edit that file.

## Goal

Move each aircraft marker between API updates. Use the last observed position, ground speed, ground track, and position time.

Fetch flight data on one worker thread. Keep the Pygame event loop and all motion state on the main thread.

## Scope

This change must:

- Parse ground speed and position age from adsb.lol.
- Calculate the time of each aircraft position.
- Predict a current position during each display frame.
- Replace the prediction when a new observed position arrives.
- Stop predictions after a fixed time.
- Fetch API data without blocking the display loop.
- Pass immutable results from the worker thread to the main thread.
- Keep all unit tests offline and deterministic.

## Non-goals

Do not add these features:

- Acceleration prediction.
- An expected-observed filter.
- An alpha-beta filter.
- A Kalman filter.
- Turn prediction with `track_rate`.
- A visible flight-path trail.
- Historical storage.
- A database.
- API retries.
- Rate-limit handling.
- The provider `lastPosition` fallback.
- GPS hardware support.
- More than one worker thread.
- Async I/O.
- New runtime dependencies.

## Required architecture

Use this one-way data flow:

```text
Worker thread
  adsb.lol client
       |
       | immutable PollResult
       v
  thread-safe queue
       |
       v
Main thread
  aircraft motion tracker
       |
       v
  Pygame display
```

The worker thread owns the flight-data provider while it runs. The worker thread must not access the motion tracker or display.

The main thread owns the motion tracker and display. The main thread may mutate the motion tracker because no other thread can access it.

Use `queue.SimpleQueue` for results. Use `threading.Event` for shutdown. Do not add an application lock.

## Target file structure

```text
flight_tracker/
├── app.py
├── models.py
├── motion/
│   ├── __init__.py
│   ├── prediction.py
│   └── tracker.py
├── flight_data/
│   ├── __init__.py
│   ├── adsb_lol.py
│   ├── models.py
│   ├── poller.py
│   └── transport.py
└── display/
    ├── projection.py
    └── pygame_display.py

tests/
├── test_display.py
├── test_flight_data.py
├── test_motion.py
└── test_poller.py
```

Do not create more motion or threading files.

## Data model changes

Update `flight_tracker/models.py`.

Add these optional fields to `Aircraft`:

```python
ground_speed_knots: float | None = None
position_observed_at: datetime | None = None
```

Keep `track_degrees`. It is the true track over the ground. Do not add a heading field.

Import `datetime` from `datetime`.

Keep `Aircraft` frozen and slotted. Keep `Position` unchanged.

## adsb.lol conversion

Update `flight_tracker/flight_data/adsb_lol.py`.

Parse these fields:

- Map `gs` to `ground_speed_knots`.
- Keep mapping `track` to `track_degrees`.
- Read `seen_pos` as a float.

Pass the snapshot `observed_at` value into the aircraft parser.

Calculate `position_observed_at` with this rule:

```text
position_observed_at = snapshot observed_at - seen_pos seconds
```

Set `position_observed_at` to `None` when the aircraft has no current position or `seen_pos` is absent.

Do not use `lastPosition`.

Keep the current optional numeric conversion behavior. Do not add new range checks for speed, track, or position age.

## Position prediction

Create `flight_tracker/motion/prediction.py`.

Add one public function:

```python
def predict_position(
    position: Position,
    ground_speed_knots: float,
    track_degrees: float,
    elapsed_seconds: float,
) -> Position:
```

Use this distance calculation:

```text
distance in nautical miles = ground speed in knots * elapsed seconds / 3600
```

Use the spherical destination formula. Use an Earth radius of `3440.065` nautical miles. Treat the track as a clockwise bearing from true north.

Normalize the result longitude to the range from `-180` degrees through less than `180` degrees.

Return the input position when the elapsed time is zero. Do not add a geographic library.

## Motion tracker

Create `flight_tracker/motion/tracker.py`.

Add a public `AircraftMotionTracker` class with this interface:

```python
class AircraftMotionTracker:
    def __init__(self, max_prediction_seconds: float) -> None: ...

    def update(self, snapshot: NearbySnapshot, received_at: float) -> None: ...

    def current_aircraft(self, now: float) -> tuple[Aircraft, ...]: ...
```

Key internal state by `icao_hex`.

Store only these values for each track:

- The latest `Aircraft` value.
- The position reference time on the monotonic clock.

Calculate the monotonic reference time during `update`:

```text
position age = snapshot observed_at - aircraft position_observed_at
reference time = poll result received_at - position age
```

Use `received_at` as the reference time when `position_observed_at` is absent.

Ignore an aircraft that has no current position. Keep an older track for that ICAO identifier until it expires.

Replace the stored track when a new snapshot contains a current position. This is the full correction step. Do not blend the expected position with the observed position.

During `current_aircraft`:

- Calculate the age from `now` and the reference time.
- Remove a track when its age is greater than `max_prediction_seconds`.
- Predict a position only when position time, ground speed, and ground track are present.
- Keep the observed position fixed when any required motion field is absent.
- Return new `Aircraft` values with predicted positions.
- Use `dataclasses.replace` to preserve aircraft metadata.

The tracker must continue to return an aircraft that is absent from one successful snapshot. The time limit must remove it later.

Export `AircraftMotionTracker` from `flight_tracker/motion/__init__.py`.

## Cross-thread result

Create `flight_tracker/flight_data/poller.py`.

Add this immutable result type:

```python
@dataclass(frozen=True, slots=True)
class PollResult:
    received_at: float
    snapshot: NearbySnapshot | None = None
    error_message: str | None = None
```

Do not add validation that enforces one result field. The poller controls construction.

Add a small provider protocol with the existing `nearby` method.

Add a `SnapshotPoller` class with this interface:

```python
class SnapshotPoller:
    def __init__(
        self,
        flight_data_provider: FlightDataProvider,
        refresh_seconds: float,
        clock: Callable[[], float] = time.monotonic,
    ) -> None: ...

    def start(self, query: NearbyQuery) -> None: ...

    def drain(self) -> tuple[PollResult, ...]: ...

    def stop(self) -> None: ...
```

`start` must create one non-daemon worker thread. The worker must fetch immediately. It must then wait for the refresh interval.

Use `Event.wait(refresh_seconds)` for the interval. This lets shutdown interrupt the wait.

After a successful request, capture the monotonic time and enqueue a `PollResult` with the snapshot.

Catch `FlightDataError`. Convert it to `error_message`. Enqueue the error result. Keep polling after the normal interval.

Do not catch unexpected exceptions.

`drain` must use non-blocking queue reads. It must return all current results in queue order.

`stop` must set the event and join the worker. The HTTP timeout already limits the maximum join delay.

Do not add guards for repeated `start` or `stop` calls. The application owns the lifecycle.

Export `PollResult` and `SnapshotPoller` from `flight_tracker/flight_data/__init__.py`.

## Application loop

Update `flight_tracker/app.py`.

Replace the synchronous flight-data provider dependency with a small poller protocol. The protocol must contain `start`, `drain`, and `stop`.

Keep the location provider, display, settings, and injected main-thread clock.

At application start:

1. Get the configured position once.
2. Create the `NearbyQuery`.
3. Start the poller with the query.
4. Create `AircraftMotionTracker` with `settings.refresh_seconds * 2` as the prediction limit.

During each display frame:

1. Read the main-thread monotonic clock.
2. Drain all poll results.
3. Send each successful snapshot to the motion tracker.
4. Print `flight-data refresh failed: <message>` for each error result.
5. Get the current predicted aircraft from the motion tracker.
6. Render the predicted aircraft.
7. Limit the frame rate.

Do not wait for a snapshot in the display loop. The first frames can contain no aircraft.

In the existing `finally` block:

1. Stop the poller.
2. Close the display.

Pygame calls must remain on the main thread.

## Program assembly

Update `radar.py`.

Create the existing adsb.lol client and transport. Wrap the client in `SnapshotPoller`. Pass the poller to `TrackerApplication`.

Do not change command-line options. Do not add a prediction setting. Derive the prediction limit from the refresh interval.

## Tests

Keep all tests offline. Use generated data and fake providers.

### Flight-data tests

Update `tests/test_flight_data.py`.

Test these behaviors:

- `gs` maps to `ground_speed_knots`.
- `seen_pos` produces the correct `position_observed_at` value.
- Missing `gs` produces `None`.
- Missing `seen_pos` produces `None`.
- An aircraft without a current position has no position time.

### Prediction and tracker tests

Create `tests/test_motion.py`.

Test these behaviors:

- Zero elapsed time returns the input position.
- North movement produces the expected latitude change.
- East movement produces the expected longitude change.
- South and west movement use the correct signs.
- Longitude wraps at the date line.
- The tracker includes the provider position age in elapsed time.
- The tracker predicts a new position on later frames.
- A new observation fully replaces the previous prediction.
- Missing speed keeps the observed position fixed.
- Missing track keeps the observed position fixed.
- Missing position time keeps the observed position fixed.
- An aircraft missing from one snapshot continues until expiry.
- A track disappears after the prediction limit.
- Two aircraft keep independent state.

Use tolerances for floating-point coordinate assertions.

### Poller tests

Create `tests/test_poller.py`.

Test these behaviors:

- The worker fetches immediately after `start`.
- A successful request produces a snapshot result.
- A `FlightDataError` produces an error result.
- `drain` preserves result order.
- `stop` interrupts the refresh wait and joins the worker.

Use fake providers. Do not use `sleep` as the primary synchronization method. Use threading events where synchronization is necessary.

### Application tests

Update `tests/test_display.py`.

Replace the fake synchronous provider with a fake poller.

Test these behaviors:

- The application starts the poller with the configured query.
- The application renders when the poller has no result.
- The application applies a successful snapshot.
- The application prints a poll error and keeps rendering.
- The application stops the poller and closes the display.

Keep projection and display-boundary tests unchanged.

## Documentation

Update `README.md`.

State that aircraft markers move between API updates. State that the movement uses ground speed and ground track. State that the display does not show a retained trail.

Update `flight_tracker/flight_data/README.md`.

Document `ground_speed_knots` and `position_observed_at`. State that the poller uses one worker thread.

## Verification

Run these commands from the repository root:

```bash
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/pyright
```

Both commands must pass.

The project has no configured formatter. Do not add one.

The project has no separate build command. State this in the final report.

The target screen resolution is not defined. Use the current 800 by 800 display for any manual check. State this limit in the final report.

## Acceptance criteria

The work is complete when all these statements are true:

- The display loop never performs an HTTP request.
- One worker thread performs all HTTP requests.
- The worker sends immutable results through a thread-safe queue.
- Only the main thread mutates motion state.
- Only the main thread calls Pygame.
- Aircraft markers move during frames between API updates.
- New API positions fully correct previous predictions.
- Stale predictions expire after two refresh intervals.
- Missing motion data does not stop other aircraft predictions.
- No unit test uses the network.
- All tests pass.
- Pyright passes.

## Intentionally omitted checks and guards

Do not add checks for implausible speeds, sudden position jumps, negative provider ages, repeated poller lifecycle calls, or provider clock drift.

Do not correct for network latency. The `received_at` value and provider position age are sufficient for this milestone.

Do not add a bounded queue. The worker produces one result per refresh interval. The main thread drains the queue on every frame.
