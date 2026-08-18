"""Offline tests for visible-aircraft statistics."""

import unittest

from flight_tracker.display.aircraft_stats import (
    aircraft_stats_lines,
    summarize_aircraft,
)
from flight_tracker.models import Aircraft, AircraftClassification


class AircraftStatsTests(unittest.TestCase):
    def test_empty_sequence_has_no_aircraft_or_extremes(self) -> None:
        stats = summarize_aircraft(())

        self.assertEqual(stats.total, 0)
        self.assertEqual(
            (
                stats.commercial,
                stats.private,
                stats.general_aviation,
                stats.military,
                stats.unknown,
            ),
            (0, 0, 0, 0, 0),
        )
        self.assertIsNone(stats.fastest)
        self.assertIsNone(stats.highest)

    def test_counts_each_display_classification(self) -> None:
        aircraft = tuple(
            Aircraft(icao_hex=str(index), classification=classification)
            for index, classification in enumerate(
                (
                    AircraftClassification.COMMERCIAL,
                    AircraftClassification.PRIVATE,
                    AircraftClassification.GENERAL_AVIATION,
                    AircraftClassification.MILITARY,
                    AircraftClassification.UNKNOWN,
                )
            )
        )

        stats = summarize_aircraft(aircraft)

        self.assertEqual(stats.total, 5)
        self.assertEqual(
            (
                stats.commercial,
                stats.private,
                stats.general_aviation,
                stats.military,
                stats.unknown,
            ),
            (1, 1, 1, 1, 1),
        )

    def test_missing_speed_does_not_win_fastest_selection(self) -> None:
        aircraft = (
            Aircraft(icao_hex="missing"),
            Aircraft(icao_hex="reported", ground_speed_knots=20),
        )

        self.assertEqual(summarize_aircraft(aircraft).fastest, aircraft[1])

    def test_zero_speed_remains_a_valid_reported_speed(self) -> None:
        aircraft = (Aircraft(icao_hex="zero", ground_speed_knots=0),)

        self.assertEqual(summarize_aircraft(aircraft).fastest, aircraft[0])

    def test_missing_altitude_does_not_win_highest_selection(self) -> None:
        aircraft = (
            Aircraft(icao_hex="missing"),
            Aircraft(icao_hex="reported", altitude_feet=20),
        )

        self.assertEqual(summarize_aircraft(aircraft).highest, aircraft[1])

    def test_zero_altitude_remains_a_valid_reported_altitude(self) -> None:
        aircraft = (Aircraft(icao_hex="zero", altitude_feet=0),)

        self.assertEqual(summarize_aircraft(aircraft).highest, aircraft[0])

    def test_fastest_and_highest_can_be_different(self) -> None:
        fastest = Aircraft(icao_hex="fast", ground_speed_knots=400, altitude_feet=1)
        highest = Aircraft(icao_hex="high", ground_speed_knots=1, altitude_feet=40000)

        stats = summarize_aircraft((fastest, highest))

        self.assertEqual(stats.fastest, fastest)
        self.assertEqual(stats.highest, highest)

    def test_one_aircraft_can_be_both_fastest_and_highest(self) -> None:
        aircraft = Aircraft(
            icao_hex="both",
            ground_speed_knots=400,
            altitude_feet=40000,
        )

        stats = summarize_aircraft((aircraft,))

        self.assertIs(stats.fastest, aircraft)
        self.assertIs(stats.highest, aircraft)

    def test_tie_selects_the_first_visible_aircraft(self) -> None:
        first = Aircraft(icao_hex="first", ground_speed_knots=100, altitude_feet=1000)
        second = Aircraft(icao_hex="second", ground_speed_knots=100, altitude_feet=1000)

        stats = summarize_aircraft((first, second))

        self.assertIs(stats.fastest, first)
        self.assertIs(stats.highest, first)

    def test_formats_the_five_required_lines(self) -> None:
        aircraft = (
            Aircraft(
                icao_hex="abc123",
                callsign="AAL2741",
                classification=AircraftClassification.COMMERCIAL,
                ground_speed_knots=420,
                altitude_feet=35000,
            ),
            Aircraft(
                icao_hex="def456",
                classification=AircraftClassification.GENERAL_AVIATION,
                ground_speed_knots=200,
                altitude_feet=10000,
            ),
        )

        self.assertEqual(
            aircraft_stats_lines(summarize_aircraft(aircraft)),
            (
                "Aircraft 2",
                "Commercial 1 · Private 0 · GA 1",
                "Military 0 · Unknown 0",
                "Fastest AAL2741 · 483 mph",
                "Highest AAL2741 · 35,000 ft",
            ),
        )

    def test_aircraft_name_uses_the_required_fallback_order(self) -> None:
        with_callsign = Aircraft(
            icao_hex="abc123", callsign=" CALL ", registration="N123AA", ground_speed_knots=1
        )
        with_registration = Aircraft(
            icao_hex="def456", registration=" N456BB ", ground_speed_knots=2
        )
        with_icao = Aircraft(icao_hex="abc123", ground_speed_knots=3)
        with_unknown = Aircraft(icao_hex="", ground_speed_knots=4)

        lines = aircraft_stats_lines(
            summarize_aircraft(
                (with_callsign, with_registration, with_icao, with_unknown)
            )
        )

        self.assertEqual(lines[3], "Fastest Unknown · 5 mph")
        self.assertEqual(
            aircraft_stats_lines(summarize_aircraft((with_callsign,)))[3],
            "Fastest CALL · 1 mph",
        )
        self.assertEqual(
            aircraft_stats_lines(summarize_aircraft((with_registration,)))[3],
            "Fastest N456BB · 2 mph",
        )
        self.assertEqual(
            aircraft_stats_lines(summarize_aircraft((with_icao,)))[3],
            "Fastest ABC123 · 3 mph",
        )


if __name__ == "__main__":
    unittest.main()
