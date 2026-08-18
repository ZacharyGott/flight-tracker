"""Typed flight-data retrieval interfaces."""

from .adsb_lol import AdsbLolClient
from .exceptions import (
    FlightDataError,
    ProviderHttpError,
    ProviderResponseError,
    TransportError,
)
from .models import NearbyQuery, NearbySnapshot
from .transport import HttpResponse, HttpTransport, RequestsTransport
from flight_tracker.models import Aircraft, Position

__all__ = [
    "AdsbLolClient",
    "Aircraft",
    "FlightDataError",
    "HttpResponse",
    "HttpTransport",
    "NearbyQuery",
    "NearbySnapshot",
    "Position",
    "ProviderHttpError",
    "ProviderResponseError",
    "RequestsTransport",
    "TransportError",
]
