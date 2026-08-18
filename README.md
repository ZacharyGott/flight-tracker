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

Aircraft markers move between API updates. The movement uses ground speed and
ground track. The display does not show a retained trail.

The default display is 800 by 800 pixels. The default center is latitude
40.0 and longitude -70.0. The default search radius is 100 nautical miles.

You can set the center and radius with command-line options:

```bash
python3 radar.py --latitude 40 --longitude -70 --radius 50
```

## Current limits

- The application uses a configured location.
- The application does not access GPS hardware.
- The target screen resolution is not selected.
- adsb.lol can return no aircraft for a valid request.
