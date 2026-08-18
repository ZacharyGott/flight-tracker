"""Typed flight-data retrieval interfaces."""

from .adsb_lol import AdsbLolClient
from .exceptions import (
    FlightDataError,
    ProviderHttpError,
    ProviderResponseError,
    TransportError,
)
from .models import NearbyQuery, NearbySnapshot
from .poller import PollResult, SnapshotPoller
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
    "PollResult",
    "ProviderHttpError",
    "ProviderResponseError",
    "RequestsTransport",
    "SnapshotPoller",
    "TransportError",
]
