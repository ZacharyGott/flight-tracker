# Flight Tracker Project Guide

## Product Goal

Build a flight tracker for a Raspberry Pi and a circular screen.

The first milestone must:

- Get nearby aircraft from a free public API.
- Use a configured GPS position and search radius.
- Show aircraft paths on a radar-style circular display.

Future work can include:

- Different icons for different aircraft classes.
- Alerts for special aircraft.
- Direction guidance for a selected aircraft.
- Gyroscope support.
- Compass support.

Do not let future work increase the complexity of the first milestone.

## Technical Direction

Do not select a language, framework, flight API, or hardware library without a project decision.

Design for the limited resources of a Raspberry Pi. Design the interface for a circular screen. Do not assume a specific Raspberry Pi model or screen resolution until the project defines them.

Keep these areas separate:

- Flight-data retrieval.
- Flight domain data.
- Display logic.
- Configuration.
- Hardware access.

Put API and hardware integrations behind small interfaces. Tests must be able to replace these integrations with recorded or generated data. Unit tests must not require a network connection or a physical sensor.

Make the GPS position, search radius, refresh rate, and API settings configurable. Do not hard-code deployment values.

## Communication

Use ASD-STE100 Simplified Technical English for:

- Agent replies.
- Documentation.
- Code comments.
- Error messages.
- User-interface text.

Use short sentences. Use active voice. Use one instruction in each sentence. Use the same term for the same item.

Do not apply Simplified Technical English to code identifiers when it makes the identifiers less natural or less clear.

## Code Quality

Prefer readable and direct code. Use simple control flow. Use descriptive names.

Write small functions that have one clear purpose. Add a function when it makes the code easier to understand or removes useful repetition.

Write documentation for public behavior and important design decisions. Add comments to explain reasons and constraints. Do not add comments that only repeat the code.

Avoid premature abstractions. Avoid speculative features. Avoid unnecessary dependencies.

Add only necessary validation and error handling. State which checks or guards you intentionally did not add.

Do not add compatibility layers, defensive guards, a deployment workflow, or a formal accessibility standard before the project needs them.

## Verification

Add tests for these features when the features exist:

- Coordinate and radius handling.
- API-data conversion.
- Aircraft classification.
- Path plotting.
- Display-boundary calculations.

Use recorded or generated flight data for deterministic tests. Keep network calls and physical sensors out of unit tests.

Before work is complete, run the available formatter, tests, and build. They must pass. If the project does not yet provide one of these checks, state that fact.

Check important display changes at the target circular aspect ratio. If the project has not defined the target resolution, state that fact.

## Current Assumptions

- The first milestone contains only nearby-flight retrieval and the radar-style path display.
- The exact Raspberry Pi model is not selected.
- The screen resolution is not selected.
- The API provider is not selected.
- The software stack is not selected.
