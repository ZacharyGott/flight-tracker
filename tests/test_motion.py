"""Offline tests for aircraft position prediction and tracking."""

import unittest
from datetime import datetime, timedelta, timezone

from flight_tracker.flight_data import NearbyQuery, NearbySnapshot
from flight_tracker.models import Aircraft, Position
from flight_tracker.motion.prediction import predict_position
from flight_tracker.motion.tracker import AircraftMotionTracker


OBSERVED_AT = datetime.fromtimestamp(1_725_000_000, tz=timezone.utc)
QUERY = NearbyQuery(0.0, 0.0, 100)


def snapshot(*aircraft: Aircraft) -> NearbySnapshot:
    return NearbySnapshot(QUERY, tuple(aircraft), OBSERVED_AT)


class PredictionTests(unittest.TestCase):
    def test_zero_elapsed_time_returns_input_position(self) -> None:
        position = Position(40.0, -70.0)

        self.assertIs(predict_position(position, 400, 90, 0), position)

    def test_north_movement_increases_latitude(self) -> None:
        predicted = predict_position(Position(0, 0), 60, 0, 3600)

        self.assertAlmostEqual(predicted.latitude, 1.0, delta=0.001)
        self.assertAlmostEqual(predicted.longitude, 0.0, places=5)

    def test_east_movement_increases_longitude(self) -> None:
        predicted = predict_position(Position(0, 0), 60, 90, 3600)

        self.assertAlmostEqual(predicted.latitude, 0.0, places=5)
        self.assertAlmostEqual(predicted.longitude, 1.0, delta=0.001)

    def test_south_and_west_movement_use_correct_signs(self) -> None:
        south = predict_position(Position(0, 0), 60, 180, 3600)
        west = predict_position(Position(0, 0), 60, 270, 3600)

        self.assertAlmostEqual(south.latitude, -1.0, delta=0.001)
        self.assertAlmostEqual(west.longitude, -1.0, delta=0.001)

    def test_longitude_wraps_at_date_line(self) -> None:
        predicted = predict_position(Position(0, 179.9), 60, 90, 3600)

        self.assertLess(predicted.longitude, 180)
        self.assertAlmostEqual(predicted.longitude, -179.1, delta=0.001)


class AircraftMotionTrackerTests(unittest.TestCase):
    def test_provider_position_age_is_included_in_elapsed_time(self) -> None:
        aircraft = Aircraft(
            icao_hex="abc123",
            position=Position(0, 0),
            ground_speed_knots=60,
            track_degrees=0,
            position_observed_at=OBSERVED_AT - timedelta(seconds=5),
        )
        tracker = AircraftMotionTracker(max_prediction_seconds=20)
        tracker.update(snapshot(aircraft), received_at=100)

        current = tracker.current_aircraft(105)[0]

        self.assertAlmostEqual(current.position.latitude, 1 / 360, places=5)  # type: ignore[union-attr]

    def test_predicts_a_new_position_on_later_frames(self) -> None:
        aircraft = Aircraft(
            icao_hex="abc123",
            position=Position(0, 0),
            ground_speed_knots=60,
            track_degrees=90,
            position_observed_at=OBSERVED_AT,
        )
        tracker = AircraftMotionTracker(max_prediction_seconds=20)
        tracker.update(snapshot(aircraft), received_at=100)

        current = tracker.current_aircraft(101)[0]

        self.assertAlmostEqual(current.position.longitude, 1 / 3600, places=5)  # type: ignore[union-attr]

    def test_new_observation_replaces_previous_prediction(self) -> None:
        first = Aircraft(
            icao_hex="abc123",
            position=Position(0, 0),
            ground_speed_knots=60,
            track_degrees=90,
            position_observed_at=OBSERVED_AT,
        )
        second = Aircraft(
            icao_hex="abc123",
            position=Position(10, 10),
            ground_speed_knots=60,
            track_degrees=0,
            position_observed_at=OBSERVED_AT,
        )
        tracker = AircraftMotionTracker(max_prediction_seconds=20)
        tracker.update(snapshot(first), received_at=100)
        tracker.update(snapshot(second), received_at=110)

        current = tracker.current_aircraft(110)[0]

        self.assertEqual(current.position, Position(10, 10))

    def test_missing_motion_fields_keep_observed_position_fixed(self) -> None:
        for aircraft in (
            Aircraft(
                icao_hex="missing-speed",
                position=Position(1, 1),
                track_degrees=90,
                position_observed_at=OBSERVED_AT,
            ),
            Aircraft(
                icao_hex="missing-track",
                position=Position(2, 2),
                ground_speed_knots=60,
                position_observed_at=OBSERVED_AT,
            ),
            Aircraft(
                icao_hex="missing-time",
                position=Position(3, 3),
                ground_speed_knots=60,
                track_degrees=90,
            ),
        ):
            tracker = AircraftMotionTracker(max_prediction_seconds=20)
            tracker.update(snapshot(aircraft), received_at=100)

            self.assertEqual(tracker.current_aircraft(110)[0].position, aircraft.position)

    def test_aircraft_missing_from_one_snapshot_becomes_stale(self) -> None:
        aircraft = Aircraft(
            icao_hex="abc123",
            position=Position(0, 0),
            position_observed_at=OBSERVED_AT,
        )
        tracker = AircraftMotionTracker(max_prediction_seconds=20)
        tracker.update(snapshot(aircraft), received_at=100)
        tracker.update(snapshot(), received_at=110)

        self.assertEqual(len(tracker.current_aircraft(119)), 1)
        current = tracker.current_aircraft(121)[0]
        self.assertTrue(current.is_stale)
        self.assertEqual(current.position, aircraft.position)

    def test_stale_aircraft_keeps_predicting(self) -> None:
        aircraft = Aircraft(
            icao_hex="abc123",
            position=Position(0, 0),
            ground_speed_knots=60,
            track_degrees=90,
            position_observed_at=OBSERVED_AT,
        )
        tracker = AircraftMotionTracker(max_prediction_seconds=20)
        tracker.update(snapshot(aircraft), received_at=100)

        current = tracker.current_aircraft(121)[0]

        self.assertTrue(current.is_stale)
        self.assertGreater(current.position.longitude, aircraft.position.longitude)  # type: ignore[union-attr]

    def test_two_aircraft_keep_independent_state(self) -> None:
        north = Aircraft(
            icao_hex="north",
            position=Position(0, 0),
            ground_speed_knots=60,
            track_degrees=0,
            position_observed_at=OBSERVED_AT,
        )
        east = Aircraft(
            icao_hex="east",
            position=Position(0, 0),
            ground_speed_knots=60,
            track_degrees=90,
            position_observed_at=OBSERVED_AT,
        )
        tracker = AircraftMotionTracker(max_prediction_seconds=20)
        tracker.update(snapshot(north, east), received_at=100)

        current = tracker.current_aircraft(101)

        self.assertAlmostEqual(current[0].position.latitude, 1 / 3600, places=5)  # type: ignore[union-attr]
        self.assertAlmostEqual(current[1].position.longitude, 1 / 3600, places=5)  # type: ignore[union-attr]


if __name__ == "__main__":
    unittest.main()
