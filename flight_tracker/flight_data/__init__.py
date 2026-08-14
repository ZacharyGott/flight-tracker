"""Typed flight-data retrieval interfaces."""

from .adsb_lol import AdsbLolClient
from .exceptions import (
    FlightDataError,
    ProviderHttpError,
    ProviderResponseError,
    TransportError,
)
from .models import Aircraft, NearbyQuery, NearbySnapshot, Position
from .transport import HttpResponse, HttpTransport, RequestsTransport

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

