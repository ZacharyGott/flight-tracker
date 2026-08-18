"""Command-line settings for the flight tracker."""

import argparse
from dataclasses import dataclass, field
from typing import Sequence

from flight_tracker.models import Position


@dataclass(frozen=True, slots=True)
class TrackerSettings:
    """Settings used by the tracker application."""

    position: Position = field(default_factory=lambda: Position(40.0, -70.0))
    search_radius_nm: int = 100
    refresh_seconds: float = 10.0
    api_base_url: str = "https://api.adsb.lol"
    api_timeout_seconds: float = 5.0
    window_size: int = 800
    frame_rate: int = 30


def parse_settings(arguments: Sequence[str] | None = None) -> TrackerSettings:
    """Parse tracker settings from command-line arguments."""

    parser = argparse.ArgumentParser(description="Display nearby aircraft on a radar.")
    parser.add_argument("--latitude", type=float, default=40.0)
    parser.add_argument("--longitude", type=float, default=-70.0)
    parser.add_argument("--radius", type=int, default=100)
    parser.add_argument("--refresh-seconds", type=float, default=10.0)
    parser.add_argument("--api-base-url", default="https://api.adsb.lol")
    parser.add_argument("--api-timeout-seconds", type=float, default=5.0)
    parser.add_argument("--window-size", type=int, default=800)
    parser.add_argument("--frame-rate", type=int, default=30)
    values = parser.parse_args(arguments)
    return TrackerSettings(
        position=Position(values.latitude, values.longitude),
        search_radius_nm=values.radius,
        refresh_seconds=values.refresh_seconds,
        api_base_url=values.api_base_url,
        api_timeout_seconds=values.api_timeout_seconds,
        window_size=values.window_size,
        frame_rate=values.frame_rate,
    )
