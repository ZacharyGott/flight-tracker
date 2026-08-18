# Aircraft Statistics Display Plan

Date: 2026-08-18

## Instruction for GPT-5.6 Luna xHigh

Implement this plan in order. Keep the implementation small. Do not add features
that this plan excludes.

Read `AGENTS.md` before you edit code. Use ASD-STE Simplified Technical English
in documentation, comments, error messages, and user-interface text.

## Goal

Show basic aircraft statistics in the top-right corner of the display. Keep the
statistics outside the radar circle.

Highlight the fastest visible aircraft in cherry red. Highlight the highest
visible aircraft in blue.

## Display Content

Show these statistics:

- The number of visible aircraft.
- The number of visible aircraft in each display classification.
- The fastest visible aircraft.
- The highest visible aircraft.

Use the existing `AircraftClassification` values for the breakdown:

- Commercial.
- Private.
- General aviation.
- Military.
- Unknown.

Do not group aircraft by provider type codes such as `B738`. The number of type
codes has no fixed limit.

Use compact text in this form:

```text
Aircraft 12
Commercial 4 · Private 2 · GA 3
Military 1 · Unknown 2
Fastest AAL2741 · 483 mph
Highest N123AA · 35,000 ft
```

Use `Unknown` when no visible aircraft has a reported speed or altitude.

Use the existing display-name fallback order:

1. Callsign.
2. Registration.
3. Uppercase ICAO address.
4. `Unknown`.

## Aircraft Selection Rules

Build the statistics from the aircraft that have visible markers inside the
radar circle. Include current and stale aircraft.

Use `ground_speed_knots` to select the fastest aircraft. Exclude an aircraft
from this selection when its speed is `None`.

Use `altitude_feet` to select the highest aircraft. Exclude an aircraft from
this selection when its altitude is `None`.

Select the first visible aircraft when two aircraft have the same maximum
value. Do not add another tie rule.

Do not add validation for negative or unusually large speed and altitude
values. The flight-data conversion layer owns provider-data handling.

## Colors

Use these display colors:

```python
CHERRY_RED = (210, 4, 45)
BLUE = (0, 128, 255)
```

Apply these rules:

- Draw the fastest aircraft marker in cherry red.
- Draw the highest aircraft marker in blue.
- Draw a cherry-red marker with a thin blue ring when one aircraft is both.
- Draw the `Fastest` statistics line in cherry red.
- Draw the `Highest` statistics line in blue.
- Keep normal aircraft markers green or grey.
- Keep predicted paths and potential areas green or grey.
- Keep the selected-aircraft card behavior unchanged.

Apply the highlight color to aircraft sprites and dot fallbacks.

## Layout

Draw five compact lines. Align each line to the right. Place the lines in the
unused top-right area of the square window.

Keep the current radar size and center. Do not add a rectangular side panel.
Do not change the window configuration.

At the default 800-by-800 size, verify that each text rectangle stays outside
the radar circle. Adjust only the statistics font size, line gap, and compact
text spacing when necessary.

The target screen resolution is not selected. Do not add general responsive
layout logic in this change.

## Target File Structure

```text
flight_tracker/
└── display/
    ├── aircraft_card.py
    ├── aircraft_stats.py       # New pure summary and formatting logic
    ├── pygame_display.py       # Statistics layout and marker colors
    └── ...

tests/
├── test_aircraft_stats.py      # New summary and formatting tests
├── test_display.py             # Marker-color and boundary tests
└── ...

README.md                       # Document the statistics and colors
```

Do not change the application interface, flight-data provider, motion tracker,
configuration, or domain models.

## Statistics Module

Create `flight_tracker/display/aircraft_stats.py`.

Add a frozen and slotted `AircraftStats` data class. Store these values:

- Total visible aircraft.
- Counts for the five display classifications.
- The fastest `Aircraft`, or `None`.
- The highest `Aircraft`, or `None`.

Add one pure function that accepts a sequence of `Aircraft` values and returns
`AircraftStats`.

Add one pure function that returns the five compact display lines. Reuse the
existing aircraft display-name behavior. Do not create a second display-name
rule.

Keep Pygame types and colors out of this module.

## Pygame Display Changes

Update `flight_tracker/display/pygame_display.py`.

Build the visible-aircraft list before the display calculates statistics. Pass
only those aircraft to the statistics function.

Load sprite masks in green, grey, cherry red, and blue. Keep sprite selection
and rotation unchanged.

Add one small helper that selects the marker color. Use the current green or
grey rule when the aircraft is not an extreme.

Draw a thin blue ring before the cherry-red marker when the same aircraft is
both fastest and highest. Keep the existing selection ring visible.

Draw the statistics after the clipped aircraft layer. Draw the selected card
after the statistics so the card stays visible if the elements meet.

## Tests

Create `tests/test_aircraft_stats.py`.

Test these cases:

- An empty sequence has zero aircraft and no extremes.
- Each display classification has the correct count.
- Missing speed does not win the fastest selection.
- A speed of zero remains a valid reported speed.
- Missing altitude does not win the highest selection.
- An altitude of zero remains a valid reported altitude.
- The fastest and highest aircraft can be different.
- One aircraft can be both fastest and highest.
- A tie selects the first visible aircraft.
- The five formatted lines use the required labels and units.
- The aircraft name uses the agreed fallback order.

Update `tests/test_display.py`.

Test these cases:

- A normal current marker is green.
- A normal stale marker is grey.
- A fastest marker is cherry red.
- A highest marker is blue.
- A marker that is both uses cherry red and requests the blue ring.
- The statistics text rectangles stay outside the circle at 800 by 800 pixels.

Use generated aircraft data. Keep all tests offline and deterministic.

## Implementation Order

1. Add the statistics data class and summary function.
2. Add statistics-line formatting.
3. Add unit tests for summary and formatting behavior.
4. Calculate statistics from visible aircraft in the Pygame display.
5. Add the marker colors and dual-highlight ring.
6. Add the top-right statistics text.
7. Add display color and boundary tests.
8. Update `README.md`.
9. Run all available verification commands.
10. Inspect the display at 800 by 800 pixels.

## Verification

Run these available checks:

```bash
python -m unittest
pyright
```

The project does not define a formatter command. The project does not define a
build command. State these facts in the implementation report.

## Work Not Included

Do not add these features:

- Raw aircraft-type statistics.
- Airframe-kind statistics.
- Historical maximum values.
- Average speed or altitude.
- Alert behavior.
- New configuration options.
- New runtime dependencies.
- General responsive layout logic.
- Changes to flight-data classification.
- Changes to predicted paths or potential-area colors.
