"""Location providers and their shared interface."""

from .configured import ConfiguredLocationProvider
from .exceptions import (
    LocationError,
    LocationPermissionError,
    LocationTimeoutError,
    LocationUnavailableError,
)
from .macos import MacOSLocationProvider
from .providers import LocationProvider

__all__ = [
    "ConfiguredLocationProvider",
    "LocationError",
    "LocationPermissionError",
    "LocationProvider",
    "LocationTimeoutError",
    "LocationUnavailableError",
    "MacOSLocationProvider",
]
