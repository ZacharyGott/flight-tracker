"""Pygame implementation of the radar display."""

from collections.abc import Sequence

import pygame

from flight_tracker.models import Position
from flight_tracker.motion import TrackedAircraft

from .projection import (
    RadarPoint,
    clip_segment_to_unit_circle,
    project_position,
    project_position_unclipped,
)


BLACK = (0, 0, 0)
GREEN = (0, 255, 0)
LIGHT_GREY = (180, 180, 180)
EDGE_MARGIN = 20
AIRCRAFT_RADIUS = 5
ESTIMATE_RADIUS = 2
POTENTIAL_ALPHA = 40


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
        self._aircraft_layer = pygame.Surface(self._window_size, pygame.SRCALPHA)
        self._radar_mask = pygame.Surface(self._window_size, pygame.SRCALPHA)

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
        aircraft: Sequence[TrackedAircraft],
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

        self._draw_potential_areas(
            center, aircraft, search_radius_nm, pixel_center, radar_radius
        )
        visible_aircraft: list[tuple[TrackedAircraft, RadarPoint]] = []
        for item in aircraft:
            observed = item.position
            if observed is None:
                continue
            observed_point = project_position(center, observed, search_radius_nm)
            if observed_point is None:
                continue
            visible_aircraft.append((item, observed_point))

        for item, observed_point in visible_aircraft:
            estimated = item.estimated_position
            if estimated is None:
                continue
            color = LIGHT_GREY if item.is_stale else GREEN
            estimated_point = project_position_unclipped(
                center, estimated, search_radius_nm
            )
            segment = clip_segment_to_unit_circle(observed_point, estimated_point)
            if segment is not None:
                pygame.draw.line(
                    self._aircraft_layer,
                    color,
                    self._pixel_position(segment[0], pixel_center, radar_radius),
                    self._pixel_position(segment[1], pixel_center, radar_radius),
                    width=1,
                )

        for item, _ in visible_aircraft:
            estimated = item.estimated_position
            if estimated is None:
                continue
            estimated_point = project_position(center, estimated, search_radius_nm)
            if estimated_point is None:
                continue
            color = LIGHT_GREY if item.is_stale else GREEN
            pygame.draw.circle(
                self._aircraft_layer,
                color,
                self._pixel_position(estimated_point, pixel_center, radar_radius),
                ESTIMATE_RADIUS,
            )

        for item, observed_point in visible_aircraft:
            color = LIGHT_GREY if item.is_stale else GREEN
            pygame.draw.circle(
                self._aircraft_layer,
                color,
                self._pixel_position(observed_point, pixel_center, radar_radius),
                AIRCRAFT_RADIUS,
            )

        self._blit_clipped_aircraft_layer(pixel_center, radar_radius)

        pygame.display.flip()

    def _draw_potential_areas(
        self,
        center: Position,
        aircraft: Sequence[TrackedAircraft],
        search_radius_nm: int,
        pixel_center: tuple[int, int],
        radar_radius: int,
    ) -> None:
        """Draw clipped translucent travel areas below the aircraft markers."""

        self._aircraft_layer.fill((0, 0, 0, 0))
        for item in aircraft:
            if item.position is None or item.potential_radius_nm is None:
                continue
            point = project_position(center, item.position, search_radius_nm)
            if point is None:
                continue
            color = LIGHT_GREY if item.is_stale else GREEN
            area_color = (*color, POTENTIAL_ALPHA)
            radius = round(
                item.potential_radius_nm / search_radius_nm * radar_radius
            )
            pygame.draw.circle(
                self._aircraft_layer,
                area_color,
                self._pixel_position(point, pixel_center, radar_radius),
                radius,
            )

    def _blit_clipped_aircraft_layer(
        self, pixel_center: tuple[int, int], radar_radius: int
    ) -> None:
        """Clip the aircraft layer to the circular radar boundary."""

        self._radar_mask.fill((0, 0, 0, 0))
        pygame.draw.circle(
            self._radar_mask,
            (255, 255, 255, 255),
            pixel_center,
            radar_radius,
        )
        self._aircraft_layer.blit(
            self._radar_mask,
            (0, 0),
            special_flags=pygame.BLEND_RGBA_MULT,
        )
        self._screen.blit(self._aircraft_layer, (0, 0))

    @staticmethod
    def _pixel_position(
        point: RadarPoint,
        pixel_center: tuple[int, int],
        radar_radius: int,
    ) -> tuple[int, int]:
        """Convert a normalized radar point to screen pixels."""

        return (
            pixel_center[0] + round(point.east * radar_radius),
            pixel_center[1] - round(point.north * radar_radius),
        )

    def limit_frame_rate(self, frame_rate: int) -> None:
        """Limit the display frame rate."""

        self._clock.tick(frame_rate)

    def close(self) -> None:
        """Close the Pygame display."""

        pygame.quit()
