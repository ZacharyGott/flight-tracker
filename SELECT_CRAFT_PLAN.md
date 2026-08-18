# Aircraft Selection Filter Plan

Date: 2026-08-18

## Instruction for GPT-5.6 Luna xHigh

Implement this plan in order. Keep the implementation small. Do not add features
that this plan excludes.

Read `AGENTS.md` before you edit code. Use ASD-STE Simplified Technical English
in documentation, comments, error messages, and user-interface text.

## Goal

Add five checkboxes that control which aircraft classifications appear on the
radar display.

Use the existing `AircraftClassification` values:

- Commercial.
- Private.
- General aviation.
- Military.
- Unknown.

Do not use provider aircraft type codes such as `B738`. These codes do not form
a small fixed list. Keep `AirframeKind` for sprite selection only.

## Behavior

Enable all five checkboxes when the application starts.

Click a checkbox to disable or enable its aircraft classification. Apply the
change on the next rendered frame.

Hide all of these items for a disabled classification:

- Aircraft marker.
- Predicted path.
- Predicted-position endpoint.
- Potential travel area.
- Selection ring.
- Aircraft information card.
- Aircraft statistics.

Clear the selected aircraft when its classification becomes hidden.

Keep hidden aircraft in the motion tracker. Show them again from the current
tracker state when the user enables the classification.

Keep the radar, runways, and center marker unchanged.

When all checkboxes are disabled, show no aircraft. Show zero aircraft in the
statistics.

Do not save checkbox state between application launches.

## Target File Structure

```text
flight_tracker/
└── display/
    ├── __init__.py
    ├── aircraft_card.py
    ├── aircraft_filter.py       # New pure filter rules
    ├── aircraft_stats.py
    ├── projection.py
    ├── pygame_display.py        # Checkbox state, events, and drawing
    └── sprites.py

tests/
├── test_aircraft_filter.py      # New filter tests
└── test_display.py              # Checkbox layout and interaction tests

README.md                        # Document the aircraft filters
SELECT_CRAFT_PLAN.md             # This implementation plan
```

Do not change `TrackerApplication`, the `RadarDisplay` protocol, configuration,
flight-data retrieval, motion tracking, or domain models.

## Aircraft Filter Module

Create `flight_tracker/display/aircraft_filter.py`.

Define the display order with one constant:

```python
AIRCRAFT_FILTER_CATEGORIES = (
    AircraftClassification.COMMERCIAL,
    AircraftClassification.PRIVATE,
    AircraftClassification.GENERAL_AVIATION,
    AircraftClassification.MILITARY,
    AircraftClassification.UNKNOWN,
)
```

Add one pure filter function:

```python
def filter_aircraft(
    aircraft: Sequence[TrackedAircraft],
    enabled: Collection[AircraftClassification],
) -> tuple[TrackedAircraft, ...]:
    ...
```

Preserve the input order. Return an empty tuple when no classifications are
enabled.

Keep Pygame types and display geometry out of this module.

## Pygame Display State

Store the enabled classifications in `PygameRadarDisplay`. Initialize the set
from `AIRCRAFT_FILTER_CATEGORIES`.

Keep the state local to the display. Do not add command-line options or settings.

Use these checkbox labels:

```text
Commercial
Private
General aviation
Military
Unknown
```

## Event Handling

Handle a checkbox click before an aircraft-marker click.

Toggle only the classification for the clicked row. Do not clear the state of
the other checkboxes.

Do not treat the same click as an aircraft selection click.

Use the complete checkbox row as the click target. Include the box and its label.

## Filtering Flow

Filter the tracked-aircraft sequence once at the start of `render`.

Use the filtered sequence for potential areas and position projection. Build
the visible-aircraft collection from this sequence.

Continue to use the visible-aircraft collection for paths, endpoints, markers,
selection, cards, and statistics. This keeps all existing visibility rules in
one flow.

Do not filter the poll result or the motion tracker.

## Checkbox Layout

Draw five compact checkbox rows in the unused upper-left area of the square
window. Keep the current statistics in the upper-right area.

Use the existing green display color for checkbox outlines, check marks, and
labels. Use the existing black background.

Use a compact font that matches the statistics text. Use a simple square outline
and a simple check mark. Do not add a panel background or border.

Keep every checkbox row outside the radar circle at the default 800-by-800
window size. Do not change the radar center, radar radius, or window settings.

The target screen resolution is not selected. Do not add general responsive
layout logic in this change.

## Tests

Create `tests/test_aircraft_filter.py`.

Test these cases:

- All classifications can pass through the filter.
- Each disabled classification hides only its aircraft.
- Unknown aircraft can be hidden.
- The filter preserves aircraft order.
- No enabled classifications return an empty tuple.

Update `tests/test_display.py`.

Test these cases:

- All five classifications are enabled at startup.
- Clicking a checkbox changes only its state.
- A checkbox click does not select an aircraft.
- A hidden selected aircraft is cleared.
- Hidden aircraft do not contribute to visible statistics.
- All checkbox row rectangles stay outside the 800-by-800 radar circle.

Use generated aircraft data. Do not require a network connection or physical
hardware.

## Documentation

Update `README.md`.

Document the five checkbox labels. State that all classifications are visible
at startup. State that filtering changes the radar markers and visible-aircraft
statistics.

## Implementation Steps for Luna xHigh

1. Add the pure aircraft filter module.
2. Add filter unit tests.
3. Add enabled-classification state to `PygameRadarDisplay`.
4. Add checkbox geometry and drawing.
5. Add checkbox click handling before marker selection.
6. Filter aircraft once at the start of each rendered frame.
7. Clear a selection when the selected aircraft becomes hidden.
8. Add display layout and interaction tests.
9. Update `README.md`.
10. Run all verification commands.
11. Inspect the display at 800 by 800 pixels.

## Verification

Run these available checks:

```bash
python -m unittest
pyright
```

All existing tests must continue to pass.

Inspect the display at 800 by 800 pixels. Confirm that the checkbox rows stay
outside the radar circle. Confirm that each checkbox hides and shows only its
aircraft classification.

The project does not define a formatter command. The project does not define a
build command. State these facts in the implementation report.

## Work Not Included

Do not add these features in this change:

- Saved filter preferences.
- Command-line filter settings.
- Configuration-file filter settings.
- Select-all or clear-all controls.
- Keyboard shortcuts.
- Touch gesture handling beyond the existing mouse event path.
- Filtering by provider aircraft type code.
- Filtering by broad airframe kind.
- Changes to aircraft classification rules.
- A new user-interface library.
- General responsive layout logic.

Do not add validation or defensive guards for internal checkbox state. The
display owns the fixed classification list and its state.
