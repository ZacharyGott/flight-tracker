"""Location-provider errors."""


class LocationError(Exception):
    """Base class for location-provider errors."""


class LocationPermissionError(LocationError):
    """The operating system denied location access."""


class LocationTimeoutError(LocationError):
    """The provider did not return a position before the timeout."""


class LocationUnavailableError(LocationError):
    """The location service is not available."""
