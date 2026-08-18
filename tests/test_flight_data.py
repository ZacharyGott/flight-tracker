"""Tests for typed nearby flight-data retrieval."""

import json
import unittest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import requests

from flight_tracker.geo import Position
from flight_tracker.flight_data import (
    AdsbLolClient,
    HttpResponse,
    NearbyQuery,
    ProviderHttpError,
    ProviderResponseError,
    RequestsTransport,
    TransportError,
)


class FakeTransport:
    def __init__(self, response: HttpResponse) -> None:
        self.response = response
        self.requested_url: str | None = None

    def get(self, url: str) -> HttpResponse:
        self.requested_url = url
        return self.response


class FailingTransport:
    def get(self, url: str) -> HttpResponse:
        raise TransportError("test transport failure")


class NearbyQueryTests(unittest.TestCase):
    def test_accepts_provider_limits(self) -> None:
        self.assertEqual(NearbyQuery(Position(-90, 180), 250).radius_nm, 250)

    def test_rejects_invalid_coordinates(self) -> None:
        with self.assertRaises(ValueError):
            Position(-90.1, 0)
        with self.assertRaises(ValueError):
            Position(0, 180.1)

    def test_rejects_invalid_radius(self) -> None:
        with self.assertRaises(ValueError):
            NearbyQuery(Position(0, 0), -1)
        with self.assertRaises(ValueError):
            NearbyQuery(Position(0, 0), 251)
        with self.assertRaises(ValueError):
            NearbyQuery(Position(0, 0), 10.5)  # type: ignore[arg-type]


class AdsbLolClientTests(unittest.TestCase):
    def test_builds_url_and_converts_aircraft(self) -> None:
        query = NearbyQuery(Position(40, -74), 20)
        response = HttpResponse(
            status_code=200,
            body=json.dumps(
                {
                    "now": 1_725_000_000,
                    "ac": [
                        {
                            "hex": "abc123",
                            "flight": " TEST123 ",
                            "r": " N123AB ",
                            "t": " B738 ",
                            "lat": 40.25,
                            "lon": -73.75,
                            "alt_baro": "35000",
                            "track": 270.5,
                            "type": "adsb_icao",
                        }
                    ],
                }
            ),
        )
        transport = FakeTransport(response)

        snapshot = AdsbLolClient(transport=transport).nearby(query)

        self.assertEqual(
            transport.requested_url,
            "https://api.adsb.lol/v2/lat/40/lon/-74/dist/20",
        )
        self.assertEqual(snapshot.query, query)
        self.assertEqual(
            snapshot.observed_at,
            datetime.fromtimestamp(1_725_000_000, tz=timezone.utc),
        )
        self.assertEqual(snapshot.aircraft[0].icao_hex, "abc123")
        self.assertEqual(snapshot.aircraft[0].callsign, "TEST123")
        self.assertEqual(snapshot.aircraft[0].registration, "N123AB")
        self.assertEqual(snapshot.aircraft[0].aircraft_type, "B738")
        self.assertEqual(snapshot.aircraft[0].position, Position(40.25, -73.75))
        self.assertEqual(snapshot.aircraft[0].altitude_feet, 35000)
        self.assertEqual(snapshot.aircraft[0].track_degrees, 270.5)

    def test_preserves_aircraft_without_current_position(self) -> None:
        response = HttpResponse(
            status_code=200,
            body=json.dumps(
                {
                    "now": 1_725_000_000,
                    "ac": [
                        {
                            "hex": "abc123",
                            "flight": " ",
                            "r": None,
                            "t": None,
                            "lat": None,
                            "lon": None,
                            "lastPosition": {"lat": 40, "lon": -74},
                            "alt_baro": "ground",
                            "track": None,
                        }
                    ],
                }
            ),
        )

        snapshot = AdsbLolClient(FakeTransport(response)).nearby(
            NearbyQuery(Position(40, -74), 20)
        )

        aircraft = snapshot.aircraft[0]
        self.assertIsNone(aircraft.position)
        self.assertIsNone(aircraft.callsign)
        self.assertIsNone(aircraft.registration)
        self.assertIsNone(aircraft.aircraft_type)
        self.assertIsNone(aircraft.altitude_feet)
        self.assertIsNone(aircraft.track_degrees)

    def test_handles_empty_response(self) -> None:
        response = HttpResponse(status_code=200, body=json.dumps({"now": 1_725_000_000, "ac": []}))

        snapshot = AdsbLolClient(FakeTransport(response)).nearby(
            NearbyQuery(Position(0, 0), 0)
        )

        self.assertEqual(snapshot.aircraft, ())

    def test_rejects_malformed_json(self) -> None:
        response = HttpResponse(status_code=200, body="not-json")

        with self.assertRaises(ProviderResponseError):
            AdsbLolClient(FakeTransport(response)).nearby(
                NearbyQuery(Position(0, 0), 10)
            )

    def test_rejects_malformed_response_envelope(self) -> None:
        response = HttpResponse(status_code=200, body=json.dumps({"now": 1_725_000_000}))

        with self.assertRaises(ProviderResponseError):
            AdsbLolClient(FakeTransport(response)).nearby(
                NearbyQuery(Position(0, 0), 10)
            )

    def test_rejects_malformed_aircraft_record(self) -> None:
        response = HttpResponse(
            status_code=200,
            body=json.dumps({"now": 1_725_000_000, "ac": [{"lat": 0, "lon": 0}]}),
        )

        with self.assertRaises(ProviderResponseError):
            AdsbLolClient(FakeTransport(response)).nearby(
                NearbyQuery(Position(0, 0), 10)
            )

    def test_raises_for_provider_http_error(self) -> None:
        transport = FakeTransport(HttpResponse(status_code=429, body="{}"))

        with self.assertRaises(ProviderHttpError) as context:
            AdsbLolClient(transport).nearby(NearbyQuery(Position(0, 0), 10))

        self.assertEqual(context.exception.status_code, 429)

    def test_propagates_transport_error(self) -> None:
        with self.assertRaises(TransportError):
            AdsbLolClient(FailingTransport()).nearby(
                NearbyQuery(Position(0, 0), 10)
            )


class RequestsTransportTests(unittest.TestCase):
    @patch("flight_tracker.flight_data.transport.requests.get")
    def test_converts_requests_response(self, get: MagicMock) -> None:
        response = MagicMock(status_code=200, text="{}")
        get.return_value = response

        result = RequestsTransport(timeout_seconds=3).get("https://example.test")

        self.assertEqual(result, HttpResponse(status_code=200, body="{}"))

    @patch("flight_tracker.flight_data.transport.requests.get")
    def test_converts_requests_failure(self, get: MagicMock) -> None:
        get.side_effect = requests.RequestException("offline")

        with self.assertRaises(TransportError):
            RequestsTransport().get("https://example.test")


if __name__ == "__main__":
    unittest.main()
