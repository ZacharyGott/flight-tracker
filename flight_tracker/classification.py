"""Pure aircraft classification rules.

The rules in this module support display choices. They do not prove aircraft
ownership, operator, or legal status.
"""

import re

from .models import AirframeKind, AircraftClassification


_EMITTER_CATEGORY = re.compile(r"[A-D][0-7]")
_LIGHT_CATEGORIES = frozenset({"A1", "B4"})
_PRIVATE_AIRPLANE_CATEGORIES = frozenset({"A2", "A3", "A4", "A5", "A6"})
_REGISTRATION_CALLSIGN = re.compile(r"N(?=[A-Z0-9]*\d)[A-Z0-9]{2,5}")
_OPERATOR_CALLSIGN = re.compile(r"[A-Z]{3}\d[A-Z0-9]*")


def normalize_callsign(value: str | None) -> str | None:
    """Return a callsign in a form suitable for comparison."""

    return _normalize_identifier(value)


def normalize_registration(value: str | None) -> str | None:
    """Return a registration in a form suitable for comparison."""

    return _normalize_identifier(value)


def airframe_kind_from_emitter_category(value: object) -> AirframeKind:
    """Map an ADS-B emitter category to a provider-independent kind."""

    if not isinstance(value, str):
        return AirframeKind.UNKNOWN
    category = value.strip().upper()
    if category in {"A1", "A2", "A3", "A4", "A5", "A6", "B4"}:
        return AirframeKind.AIRPLANE
    if category == "A7":
        return AirframeKind.HELICOPTER
    if category == "B1":
        return AirframeKind.GLIDER
    if category == "B2":
        return AirframeKind.LIGHTER_THAN_AIR
    if category == "B6":
        return AirframeKind.UNMANNED
    if _EMITTER_CATEGORY.fullmatch(category) is not None:
        return AirframeKind.OTHER
    return AirframeKind.UNKNOWN


def classify_aircraft(
    category: object = None,
    callsign: str | None = None,
    registration: str | None = None,
    military: bool = False,
) -> AircraftClassification:
    """Return a best-effort display classification.

    A military database flag has priority. A callsign that matches a
    registration identifies a private or general-aviation display case when
    the emitter category supports that choice. An operator-style callsign is
    commercial when it does not match the registration. Remaining light
    aircraft are general aviation. All other records are unknown.
    """

    if military:
        return AircraftClassification.MILITARY

    normalized_callsign = normalize_callsign(callsign)
    normalized_registration = normalize_registration(registration)
    category_text = _category_text(category)
    registration_callsign = _is_registration_callsign(
        normalized_callsign, normalized_registration
    )
    if registration_callsign and category_text in _LIGHT_CATEGORIES:
        return AircraftClassification.GENERAL_AVIATION
    if registration_callsign and category_text in _PRIVATE_AIRPLANE_CATEGORIES:
        return AircraftClassification.PRIVATE
    if (
        normalized_callsign is not None
        and _OPERATOR_CALLSIGN.fullmatch(normalized_callsign) is not None
        and normalized_callsign != normalized_registration
    ):
        return AircraftClassification.COMMERCIAL
    if category_text in _LIGHT_CATEGORIES:
        return AircraftClassification.GENERAL_AVIATION
    return AircraftClassification.UNKNOWN


def _category_text(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    category = value.strip().upper()
    if _EMITTER_CATEGORY.fullmatch(category) is None:
        return None
    return category


def _normalize_identifier(value: str | None) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = "".join(
        character for character in value.upper() if character.isalnum()
    )
    return normalized or None


def _is_registration_callsign(
    callsign: str | None, registration: str | None
) -> bool:
    if callsign is None:
        return False
    if registration is not None and callsign == registration:
        return True
    return _REGISTRATION_CALLSIGN.fullmatch(callsign) is not None
