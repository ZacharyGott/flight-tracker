"""Typed flight-data retrieval interfaces."""

from .adsb_lol import AdsbLolClient
from .exceptions import (
    FlightDataError,
    ProviderHttpError,
    ProviderResponseError,
    TransportError,
)
from .models import Aircraft, NearbyQuery, NearbySnapshot
from .transport import HttpResponse, HttpTransport, RequestsTransport

__all__ = [
    "AdsbLolClient",
    "Aircraft",
    "FlightDataError",
    "HttpResponse",
    "HttpTransport",
    "NearbyQuery",
    "NearbySnapshot",
    "ProviderHttpError",
    "ProviderResponseError",
    "RequestsTransport",
    "TransportError",
]
