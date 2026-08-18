"""Poll flight data on one worker thread."""

import time
from collections.abc import Callable
from dataclasses import dataclass
from queue import Empty, SimpleQueue
from threading import Event, Thread
from typing import Protocol

from .exceptions import FlightDataError
from .models import NearbyQuery, NearbySnapshot


@dataclass(frozen=True, slots=True)
class PollResult:
    """The result of one nearby-aircraft poll."""

    received_at: float
    snapshot: NearbySnapshot | None = None
    error_message: str | None = None


class FlightDataProvider(Protocol):
    """Retrieve nearby flight data."""

    def nearby(self, query: NearbyQuery) -> NearbySnapshot:
        """Return the aircraft near the query position."""
        ...


class SnapshotPoller:
    """Fetch snapshots on one worker and queue immutable poll results."""

    def __init__(
        self,
        flight_data_provider: FlightDataProvider,
        refresh_seconds: float,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._flight_data_provider = flight_data_provider
        self._refresh_seconds = refresh_seconds
        self._clock = clock
        self._results: SimpleQueue[PollResult] = SimpleQueue()
        self._stop_event = Event()
        self._thread: Thread

    def start(self, query: NearbyQuery) -> None:
        """Start polling immediately on one non-daemon worker thread."""

        self._thread = Thread(target=self._run, args=(query,), daemon=False)
        self._thread.start()

    def drain(self) -> tuple[PollResult, ...]:
        """Return all results currently waiting in the queue."""

        results: list[PollResult] = []
        while True:
            try:
                results.append(self._results.get_nowait())
            except Empty:
                return tuple(results)

    def stop(self) -> None:
        """Stop the worker and wait for its current request to finish."""

        self._stop_event.set()
        self._thread.join()

    def _run(self, query: NearbyQuery) -> None:
        while True:
            try:
                snapshot = self._flight_data_provider.nearby(query)
            except FlightDataError as error:
                self._results.put(
                    PollResult(
                        received_at=self._clock(),
                        error_message=str(error),
                    )
                )
            else:
                self._results.put(
                    PollResult(
                        received_at=self._clock(),
                        snapshot=snapshot,
                    )
                )
            if self._stop_event.wait(self._refresh_seconds):
                return
