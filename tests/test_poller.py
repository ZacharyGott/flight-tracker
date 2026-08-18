"""Offline tests for the snapshot poller."""

import threading
import unittest
from datetime import datetime, timezone

from flight_tracker.flight_data import (
    FlightDataError,
    NearbyQuery,
    NearbySnapshot,
    PollResult,
    SnapshotPoller,
)


QUERY = NearbyQuery(40.0, -70.0, 50)
SNAPSHOT = NearbySnapshot(
    query=QUERY,
    aircraft=(),
    observed_at=datetime.fromtimestamp(1_725_000_000, tz=timezone.utc),
)


class TestFlightDataError(FlightDataError):
    """A test provider error."""


class FakeProvider:
    def __init__(self, responses: list[NearbySnapshot | Exception]) -> None:
        self.responses = responses
        self.called = threading.Event()
        self.queries: list[NearbyQuery] = []

    def nearby(self, query: NearbyQuery) -> NearbySnapshot:
        self.queries.append(query)
        self.called.set()
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def wait_for_result(poller: SnapshotPoller, event: threading.Event) -> PollResult:
    event.wait(1)
    for _ in range(100):
        results = poller.drain()
        if results:
            return results[0]
        event.wait(0.01)
    raise AssertionError("poll result was not queued")


class SnapshotPollerTests(unittest.TestCase):
    def test_worker_fetches_immediately_after_start(self) -> None:
        provider = FakeProvider([SNAPSHOT])
        poller = SnapshotPoller(provider, refresh_seconds=60)

        poller.start(QUERY)
        try:
            self.assertTrue(provider.called.wait(1))
            self.assertEqual(provider.queries, [QUERY])
        finally:
            poller.stop()

    def test_successful_request_produces_snapshot_result(self) -> None:
        provider = FakeProvider([SNAPSHOT])
        poller = SnapshotPoller(provider, refresh_seconds=60, clock=lambda: 12.5)

        poller.start(QUERY)
        try:
            result = wait_for_result(poller, provider.called)
        finally:
            poller.stop()

        self.assertEqual(result, PollResult(received_at=12.5, snapshot=SNAPSHOT))

    def test_flight_data_error_produces_error_result(self) -> None:
        provider = FakeProvider([TestFlightDataError("offline")])
        poller = SnapshotPoller(provider, refresh_seconds=60, clock=lambda: 12.5)

        poller.start(QUERY)
        try:
            result = wait_for_result(poller, provider.called)
        finally:
            poller.stop()

        self.assertEqual(
            result,
            PollResult(received_at=12.5, error_message="offline"),
        )

    def test_drain_preserves_result_order(self) -> None:
        provider = FakeProvider([SNAPSHOT])
        poller = SnapshotPoller(provider, refresh_seconds=60)
        first = PollResult(received_at=1, snapshot=SNAPSHOT)
        second = PollResult(received_at=2, error_message="offline")

        poller._results.put(first)  # type: ignore[reportPrivateUsage]
        poller._results.put(second)  # type: ignore[reportPrivateUsage]

        self.assertEqual(poller.drain(), (first, second))

    def test_stop_interrupts_refresh_wait_and_joins_worker(self) -> None:
        provider = FakeProvider([SNAPSHOT])
        poller = SnapshotPoller(provider, refresh_seconds=60)

        poller.start(QUERY)
        self.assertTrue(provider.called.wait(1))

        poller.stop()

        self.assertFalse(poller._thread.is_alive())  # type: ignore[reportPrivateUsage]


if __name__ == "__main__":
    unittest.main()
