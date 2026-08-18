"""Offline tests for aircraft classification filtering."""

import unittest

from flight_tracker.display.aircraft_filter import (
    AIRCRAFT_FILTER_CATEGORIES,
    filter_aircraft,
)
from flight_tracker.models import Aircraft, AircraftClassification
from flight_tracker.motion import TrackedAircraft


def tracked(icao_hex: str, classification: AircraftClassification) -> TrackedAircraft:
    """Build one tracked aircraft for a filter test."""

    return TrackedAircraft(
        aircraft=Aircraft(icao_hex=icao_hex, classification=classification),
        estimated_position=None,
        potential_radius_nm=None,
        is_stale=False,
    )


class AircraftFilterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.aircraft = tuple(
            tracked(str(index), classification)
            for index, classification in enumerate(AIRCRAFT_FILTER_CATEGORIES)
        )

    def test_all_classifications_can_pass_through(self) -> None:
        self.assertEqual(
            filter_aircraft(self.aircraft, AIRCRAFT_FILTER_CATEGORIES), self.aircraft
        )

    def test_each_disabled_classification_hides_only_its_aircraft(self) -> None:
        for index, category in enumerate(AIRCRAFT_FILTER_CATEGORIES):
            with self.subTest(category=category):
                visible = filter_aircraft(
                    self.aircraft,
                    set(AIRCRAFT_FILTER_CATEGORIES) - {category},
                )
                self.assertEqual(visible, self.aircraft[:index] + self.aircraft[index + 1 :])

    def test_unknown_aircraft_can_be_hidden(self) -> None:
        visible = filter_aircraft(
            self.aircraft,
            set(AIRCRAFT_FILTER_CATEGORIES) - {AircraftClassification.UNKNOWN},
        )

        self.assertNotIn(self.aircraft[-1], visible)

    def test_filter_preserves_aircraft_order(self) -> None:
        enabled = {
            AircraftClassification.MILITARY,
            AircraftClassification.COMMERCIAL,
        }

        self.assertEqual(
            filter_aircraft(self.aircraft, enabled), (self.aircraft[0], self.aircraft[3])
        )

    def test_no_enabled_classifications_return_empty_tuple(self) -> None:
        self.assertEqual(filter_aircraft(self.aircraft, set()), ())


if __name__ == "__main__":
    unittest.main()
