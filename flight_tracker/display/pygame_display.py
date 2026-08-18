"""Pygame implementation of the radar display."""

from collections.abc import Sequence

import pygame

from flight_tracker.models import Aircraft, Position

from .projection import project_position


BLACK = (0, 0, 0)
GREEN = (0, 255, 0)
LIGHT_GREY = (180, 180, 180)
EDGE_MARGIN = 20
AIRCRAFT_RADIUS = 5


def calculate_radar_radius(
    window_size: tuple[int, int], edge_margin: int = EDGE_MARGIN
) -> int:
    """Return the pixel radius that fits inside the display."""

    return min(window_size) // 2 - edge_margin


class PygameRadarDisplay:
    """Draw the radar on a Pygame window."""

    def __init__(self, window_size: int = 800) -> None:
        pygame.init()
        self._screen = pygame.display.set_mode((window_size, window_size))
        pygame.display.set_caption("Flight Tracker Radar")
        self._clock = pygame.time.Clock()
        self._window_size = (window_size, window_size)

    def process_events(self) -> bool:
        """Process close and Escape events."""

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                return False
        return True

    def render(
        self,
        center: Position,
        aircraft: Sequence[Aircraft],
        search_radius_nm: int,
    ) -> None:
        """Draw one radar frame."""

        self._screen.fill(BLACK)
        pixel_center = (self._window_size[0] // 2, self._window_size[1] // 2)
        radar_radius = calculate_radar_radius(self._window_size)

        pygame.draw.circle(self._screen, GREEN, pixel_center, radar_radius, width=2)
        for ring_fraction in (1 / 3, 2 / 3):
            pygame.draw.circle(
                self._screen,
                GREEN,
                pixel_center,
                round(radar_radius * ring_fraction),
                width=1,
            )
        pygame.draw.line(
            self._screen,
            GREEN,
            (pixel_center[0] - radar_radius, pixel_center[1]),
            (pixel_center[0] + radar_radius, pixel_center[1]),
            width=1,
        )
        pygame.draw.line(
            self._screen,
            GREEN,
            (pixel_center[0], pixel_center[1] - radar_radius),
            (pixel_center[0], pixel_center[1] + radar_radius),
            width=1,
        )
        pygame.draw.circle(self._screen, GREEN, pixel_center, AIRCRAFT_RADIUS)

        for item in aircraft:
            if item.position is None:
                continue
            point = project_position(center, item.position, search_radius_nm)
            if point is None:
                continue
            pixel_position = (
                pixel_center[0] + round(point.east * radar_radius),
                pixel_center[1] - round(point.north * radar_radius),
            )
            color = LIGHT_GREY if item.is_stale else GREEN
            pygame.draw.circle(self._screen, color, pixel_position, AIRCRAFT_RADIUS)

        pygame.display.flip()

    def limit_frame_rate(self, frame_rate: int) -> None:
        """Limit the display frame rate."""

        self._clock.tick(frame_rate)

    def close(self) -> None:
        """Close the Pygame display."""

        pygame.quit()
