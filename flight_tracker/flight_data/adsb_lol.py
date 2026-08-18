"""adsb.lol provider adapter."""

import json
from datetime import datetime, timedelta, timezone
from typing import TypeGuard, cast

from flight_tracker.classification import (
    airframe_kind_from_emitter_category,
    classify_aircraft,
)
from flight_tracker.models import Aircraft, Position

from .exceptions import ProviderHttpError, ProviderResponseError
from .models import NearbyQuery, NearbySnapshot
from .transport import HttpTransport, RequestsTransport


DEFAULT_BASE_URL = "https://api.adsb.lol"
JsonObject = dict[str, object]


class AdsbLolClient:
    """Retrieve nearby aircraft from adsb.lol."""

    def __init__(
        self,
        transport: HttpTransport | None = None,
        base_url: str = DEFAULT_BASE_URL,
    ) -> None:
        self._transport = transport or RequestsTransport()
        self._base_url = base_url.rstrip("/")

    def nearby(self, query: NearbyQuery) -> NearbySnapshot:
        """Return aircraft in the query radius."""

        url = self._nearby_url(query)
        response = self._transport.get(url)
        if not 200 <= response.status_code < 300:
            raise ProviderHttpError(response.status_code, url)
        return self._parse_response(query, response.body)

    def _nearby_url(self, query: NearbyQuery) -> str:
        return (
            f"{self._base_url}/v2/lat/{query.latitude}"
            f"/lon/{query.longitude}/dist/{query.radius_nm}"
        )

    def _parse_response(self, query: NearbyQuery, body: str) -> NearbySnapshot:
        try:
            payload: object = json.loads(body)
        except json.JSONDecodeError as error:
            raise ProviderResponseError("provider response is not valid JSON") from error

        if not isinstance(payload, dict):
            raise ProviderResponseError("provider response must be a JSON object")
        response = cast(JsonObject, payload)

        raw_aircraft = response.get("ac")
        raw_now = response.get("now")
        if not isinstance(raw_aircraft, list):
            raise ProviderResponseError("provider response must contain an aircraft list")
        if isinstance(raw_now, bool) or not isinstance(raw_now, int):
            raise ProviderResponseError("provider response must contain an integer timestamp")

        timestamp_seconds = raw_now / 1000 if raw_now >= 10_000_000_000 else raw_now
        try:
            observed_at = datetime.fromtimestamp(timestamp_seconds, tz=timezone.utc)
        except (OverflowError, OSError, ValueError) as error:
            raise ProviderResponseError("provider timestamp is invalid") from error

        aircraft_records = cast(list[object], raw_aircraft)
        aircraft = tuple(
            self._parse_aircraft(item, observed_at) for item in aircraft_records
        )
        return NearbySnapshot(query=query, aircraft=aircraft, observed_at=observed_at)

    def _parse_aircraft(self, value: object, observed_at: datetime) -> Aircraft:
        if not isinstance(value, dict):
            raise ProviderResponseError("each aircraft record must be a JSON object")
        record = cast(JsonObject, value)

        raw_hex = record.get("hex")
        if not isinstance(raw_hex, str) or not raw_hex.strip():
            raise ProviderResponseError("each aircraft record must contain a hex identifier")

        position = self._parse_position(record)
        seen_position_seconds = _optional_float(record.get("seen_pos"))
        position_observed_at = (
            observed_at - timedelta(seconds=seen_position_seconds)
            if position is not None and seen_position_seconds is not None
            else None
        )
        callsign = _optional_text(record.get("flight"))
        registration = _optional_text(record.get("r"))
        aircraft_type = _optional_text(record.get("t"))
        category = record.get("category")
        try:
            return Aircraft(
                icao_hex=raw_hex.strip(),
                position=position,
                callsign=callsign,
                registration=registration,
                aircraft_type=aircraft_type,
                airframe_kind=airframe_kind_from_emitter_category(category),
                classification=classify_aircraft(
                    category=category,
                    callsign=callsign,
                    registration=registration,
                    military=_has_military_flag(record.get("dbFlags")),
                ),
                altitude_feet=_optional_int(record.get("alt_baro")),
                track_degrees=_optional_float(record.get("track")),
                ground_speed_knots=_optional_float(record.get("gs")),
                position_observed_at=position_observed_at,
            )
        except ValueError as error:
            raise ProviderResponseError("aircraft record contains invalid data") from error

    def _parse_position(self, value: JsonObject) -> Position | None:
        latitude = value.get("lat")
        longitude = value.get("lon")
        if latitude is None or longitude is None:
            return None
        if not _is_real(latitude) or not _is_real(longitude):
            raise ProviderResponseError("aircraft position must contain numeric coordinates")
        try:
            return Position(latitude=float(latitude), longitude=float(longitude))
        except ValueError as error:
            raise ProviderResponseError("aircraft position is outside valid bounds") from error


def _optional_text(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    return text or None


def _optional_int(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return None
    return None


def _optional_float(value: object) -> float | None:
    if not _is_real(value):
        return None
    return float(value)


def _is_real(value: object) -> TypeGuard[int | float]:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _has_military_flag(value: object) -> bool:
    """Return whether the provider's military bit is set."""

    return isinstance(value, int) and not isinstance(value, bool) and bool(value & 1)
