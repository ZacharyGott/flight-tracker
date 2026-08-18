(08/18/2026)

# Flight Tracker

This project displays nearby aircraft on a radar-style circular display.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
python3 radar.py
```

Each aircraft shows a small top-view aircraft sprite at its last observed
position. The sprite points in the reported ground-track direction. If the
provider does not supply a ground track, the display uses a 5 pixel dot. When
the provider supplies position time, ground speed, and ground track, the
display draws a thin line to the estimated current position and a smaller
endpoint marker. A translucent circle shows the area reached at the last
reported speed since the observation. The circle is clipped to the radar
boundary.

If the provider does not supply ground speed, the display shows the sprite
without the estimated path or potential area. If it does not supply track, the
display uses the dot fallback and shows the potential area without the line or
endpoint. If it does not supply position time, the display shows the sprite or
dot without motion estimates.

Aircraft become grey when the observation age is greater than 20 seconds. The
tracker removes an aircraft when the age is greater than 60 seconds. Both
limits are configurable.

The default display is 800 by 800 pixels. The default center is latitude
40.0 and longitude -70.0. The default search radius is 100 nautical miles.

You can set the center and radius with command-line options:

```bash
python3 radar.py --latitude 40 --longitude -70 --radius 50
```

Set the age limits with these options:

```bash
python3 radar.py --stale-after-seconds 20 --remove-after-seconds 60
```

## Current limits

- The application uses a configured location.
- The application does not access GPS hardware.
- The target screen resolution is not selected.
- adsb.lol can return no aircraft for a valid request.
