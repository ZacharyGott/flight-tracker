"""Typed HTTP transport boundaries for flight-data providers."""

from dataclasses import dataclass
from typing import Protocol

import requests

from .exceptions import TransportError


@dataclass(frozen=True, slots=True)
class HttpResponse:
    """The HTTP response data needed by a provider adapter."""

    status_code: int
    body: str


class HttpTransport(Protocol):
    """The transport contract used by provider clients."""

    def get(self, url: str) -> HttpResponse:
        """Return a GET response or raise ``TransportError``."""
        ...


class RequestsTransport:
    """An HTTP transport backed by the ``requests`` package."""

    def __init__(self, timeout_seconds: float = 10.0) -> None:
        self._timeout_seconds = timeout_seconds

    def get(self, url: str) -> HttpResponse:
        try:
            response = requests.get(url, timeout=self._timeout_seconds)
        except requests.RequestException as error:
            raise TransportError(f"flight-data request failed: {url}") from error

        return HttpResponse(status_code=response.status_code, body=response.text)
