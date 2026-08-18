(08/14/2026)

# Location Layer

The location layer returns the tracker position through one provider interface.

`LocationProvider` returns a shared `Position` value. The flight-data module does not know how the provider gets the position.

The configured provider returns a fixed position. Tests use this provider.

The macOS provider uses Core Location. It requests one position and returns it to the application.

## macOS setup

Install the macOS dependencies:

```text
pip install -e ".[macos]"
```

Build the small macOS runner with `py2app`:

```text
(cd macos && ../.venv/bin/python setup.py py2app)
```

Allow location access when macOS asks for permission.
