"""Exceptions raised by the flight-data module."""


class FlightDataError(Exception):
    """Base class for flight-data errors."""


class TransportError(FlightDataError):
    """The HTTP transport could not complete a request."""


class ProviderHttpError(FlightDataError):
    """The provider returned a non-success HTTP status."""

    def __init__(self, status_code: int, url: str) -> None:
        self.status_code = status_code
        self.url = url
        super().__init__(f"flight-data provider returned HTTP {status_code}: {url}")


class ProviderResponseError(FlightDataError):
    """The provider returned invalid or unsupported response data."""

