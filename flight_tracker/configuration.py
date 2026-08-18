"""Application settings."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TrackerSettings:
    """Settings that control the first flight-tracker milestone."""

    search_radius_nm: int
    refresh_seconds: float
    location_timeout_seconds: float
