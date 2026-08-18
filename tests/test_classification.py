"""Offline tests for aircraft classification and sprite selection."""

import unittest

from flight_tracker.classification import (
    airframe_kind_from_emitter_category,
    classify_aircraft,
    normalize_callsign,
    normalize_registration,
)
from flight_tracker.display.sprites import AircraftSprite, select_aircraft_sprite
from flight_tracker.models import AirframeKind, Aircraft, AircraftClassification


class AirframeCategoryTests(unittest.TestCase):
    def test_maps_supported_categories(self) -> None:
        for category in ("A1", "A2", "A3", "A4", "A5", "A6", "B4"):
            self.assertEqual(
                airframe_kind_from_emitter_category(category), AirframeKind.AIRPLANE
            )
        self.assertEqual(
            airframe_kind_from_emitter_category("A7"), AirframeKind.HELICOPTER
        )
        self.assertEqual(
            airframe_kind_from_emitter_category("B1"), AirframeKind.GLIDER
        )
        self.assertEqual(
            airframe_kind_from_emitter_category("B2"), AirframeKind.LIGHTER_THAN_AIR
        )
        self.assertEqual(
            airframe_kind_from_emitter_category("B6"), AirframeKind.UNMANNED
        )
        for category in ("C1", "C7", "D7"):
            self.assertEqual(
                airframe_kind_from_emitter_category(category), AirframeKind.OTHER
            )

    def test_unknown_or_missing_category_is_unknown(self) -> None:
        self.assertEqual(
            airframe_kind_from_emitter_category(None), AirframeKind.UNKNOWN
        )
        self.assertEqual(
            airframe_kind_from_emitter_category("bad"), AirframeKind.UNKNOWN
        )


class AircraftClassificationTests(unittest.TestCase):
    def test_normalizes_identifiers(self) -> None:
        self.assertEqual(normalize_callsign(" aal 2741 "), "AAL2741")
        self.assertEqual(normalize_registration(" n292sp "), "N292SP")
        self.assertEqual(normalize_registration(" D-EABC "), "DEABC")

    def test_military_flag_wins(self) -> None:
        self.assertEqual(
            classify_aircraft("A3", "AAL2741", "N123AA", military=True),
            AircraftClassification.MILITARY,
        )

    def test_operator_callsign_is_commercial(self) -> None:
        self.assertEqual(
            classify_aircraft("A3", "AAL2741", "N123AA"),
            AircraftClassification.COMMERCIAL,
        )

    def test_matching_light_registration_is_general_aviation(self) -> None:
        self.assertEqual(
            classify_aircraft("A1", "N292SP", "N292SP"),
            AircraftClassification.GENERAL_AVIATION,
        )

    def test_matching_large_registration_is_private(self) -> None:
        for category in ("A2", "A3", "A4", "A5", "A6"):
            with self.subTest(category=category):
                self.assertEqual(
                    classify_aircraft(category, "N5GL", "N5GL"),
                    AircraftClassification.PRIVATE,
                )

    def test_light_category_without_callsign_is_general_aviation(self) -> None:
        self.assertEqual(
            classify_aircraft("B4"), AircraftClassification.GENERAL_AVIATION
        )

    def test_other_cases_are_unknown(self) -> None:
        self.assertEqual(
            classify_aircraft("A7", "AAL2741", "N123AA"),
            AircraftClassification.COMMERCIAL,
        )
        self.assertEqual(
            classify_aircraft("B1", None, None), AircraftClassification.UNKNOWN
        )


class AircraftSpriteTests(unittest.TestCase):
    def test_selects_each_sprite_branch(self) -> None:
        cases = (
            (
                Aircraft(
                    "military-helicopter",
                    airframe_kind=AirframeKind.HELICOPTER,
                    classification=AircraftClassification.MILITARY,
                ),
                AircraftSprite.MILITARY_HELICOPTER,
            ),
            (
                Aircraft(
                    "military-airplane",
                    airframe_kind=AirframeKind.AIRPLANE,
                    classification=AircraftClassification.MILITARY,
                ),
                AircraftSprite.MILITARY_AIRPLANE,
            ),
            (
                Aircraft(
                    "civilian-helicopter", airframe_kind=AirframeKind.HELICOPTER
                ),
                AircraftSprite.CIVILIAN_HELICOPTER,
            ),
            (
                Aircraft(
                    "private",
                    airframe_kind=AirframeKind.AIRPLANE,
                    classification=AircraftClassification.PRIVATE,
                ),
                AircraftSprite.PRIVATE_AIRPLANE,
            ),
            (
                Aircraft(
                    "general-aviation",
                    airframe_kind=AirframeKind.AIRPLANE,
                    classification=AircraftClassification.GENERAL_AVIATION,
                ),
                AircraftSprite.GENERAL_AVIATION_AIRPLANE,
            ),
            (
                Aircraft(
                    "commercial",
                    airframe_kind=AirframeKind.AIRPLANE,
                    classification=AircraftClassification.COMMERCIAL,
                ),
                AircraftSprite.COMMERCIAL_AIRPLANE,
            ),
            (
                Aircraft("unknown"),
                AircraftSprite.GENERIC_AIRPLANE,
            ),
        )
        for aircraft, expected in cases:
            with self.subTest(aircraft=aircraft.icao_hex):
                self.assertEqual(select_aircraft_sprite(aircraft), expected)


if __name__ == "__main__":
    unittest.main()
