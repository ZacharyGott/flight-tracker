"""Pygame implementation of the radar display."""

from collections.abc import Sequence
from pathlib import Path

import pygame

from flight_tracker.models import AircraftClassification, Position
from flight_tracker.motion import TrackedAircraft
from flight_tracker.runway_data import RunwaySegment

from .projection import (
    RadarPoint,
    clip_segment_to_unit_circle,
    project_position,
    project_position_unclipped,
    project_runway_segment,
)
from .sprites import AircraftSprite, select_aircraft_sprite
from .aircraft_card import (
    aircraft_card_lines,
    card_rect_near_aircraft,
    nearest_marker,
)
from .aircraft_stats import AircraftStats, aircraft_stats_lines, summarize_aircraft
from .aircraft_filter import (
    AIRCRAFT_FILTER_CATEGORIES,
    filter_aircraft,
)


BLACK = (0, 0, 0)
GREEN = (0, 255, 0)
DARK_GREEN = (0, 128, 0)
RUNWAY_GREEN = DARK_GREEN
LIGHT_GREY = (180, 180, 180)
DARK_GREY = (90, 90, 90)
CHERRY_RED = (210, 4, 45)
BLUE = (0, 128, 255)
EDGE_MARGIN = 20
AIRCRAFT_RADIUS = 5
AIRCRAFT_SPRITE_SIZE = 20
ESTIMATE_RADIUS = 2
POTENTIAL_ALPHA = 40
CARD_PADDING = 8
CARD_LINE_GAP = 2
CARD_BORDER_WIDTH = 1
SELECTION_RING_RADIUS = AIRCRAFT_RADIUS + 7
DUAL_HIGHLIGHT_RING_RADIUS = AIRCRAFT_RADIUS + 8
STATS_FONT_SIZE = 14
STATS_TOP = 8
STATS_LINE_GAP = 1
AIRCRAFT_ASSET_DIRECTORY = Path(__file__).with_name("assets")
AIRCRAFT_FILTER_LABELS = (
    "Commercial",
    "Private",
    "General aviation",
    "Military",
    "Unknown",
)
FILTER_LEFT = 8
FILTER_TOP = 8
FILTER_ROW_WIDTH = 160
FILTER_ROW_HEIGHT = 18
FILTER_BOX_SIZE = 12
FILTER_TEXT_GAP = 6


def checkbox_row_rectangles() -> tuple[pygame.Rect, ...]:
    """Return the five checkbox row rectangles for the square display."""

    return tuple(
        pygame.Rect(
            FILTER_LEFT,
            FILTER_TOP + index * FILTER_ROW_HEIGHT,
            FILTER_ROW_WIDTH,
            FILTER_ROW_HEIGHT,
        )
        for index in range(len(AIRCRAFT_FILTER_CATEGORIES))
    )


def calculate_radar_radius(
    window_size: tuple[int, int], edge_margin: int = EDGE_MARGIN
) -> int:
    """Return the pixel radius that fits inside the display."""

    return min(window_size) // 2 - edge_margin


def prediction_color(is_stale: bool) -> tuple[int, int, int]:
    """Return the endpoint color for a predicted position."""

    return DARK_GREY if is_stale else DARK_GREEN


def marker_color(item: TrackedAircraft, stats: AircraftStats) -> tuple[int, int, int]:
    """Return the marker color for one visible aircraft."""

    if item.aircraft is stats.fastest and item.aircraft is stats.highest:
        return CHERRY_RED
    if item.aircraft is stats.fastest:
        return CHERRY_RED
    if item.aircraft is stats.highest:
        return BLUE
    return LIGHT_GREY if item.is_stale else GREEN


def has_dual_highlight_ring(item: TrackedAircraft, stats: AircraftStats) -> bool:
    """Return whether one aircraft is both visible extremes."""

    return item.aircraft is stats.fastest and item.aircraft is stats.highest


def marker_draw_priority(item: TrackedAircraft, stats: AircraftStats) -> int:
    """Return a draw priority that keeps highlighted markers in front."""

    if item.aircraft is stats.fastest:
        return 2
    if item.aircraft is stats.highest:
        return 1
    return 0


def statistics_text_rectangles(
    window_size: tuple[int, int],
    line_sizes: Sequence[tuple[int, int]],
    top: int = STATS_TOP,
    right_margin: int = EDGE_MARGIN,
    line_gap: int = STATS_LINE_GAP,
) -> tuple[tuple[int, int, int, int], ...]:
    """Return right-aligned statistics rectangles for the square display."""

    right = window_size[0] - right_margin
    rectangles: list[tuple[int, int, int, int]] = []
    y = top
    for width, height in line_sizes:
        rectangles.append((right - width, y, width, height))
        y += height + line_gap
    return tuple(rectangles)


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
        self._aircraft_sprites = self._load_aircraft_sprites()
        self._card_font = pygame.font.Font(None, 18)
        self._stats_font = pygame.font.Font(None, STATS_FONT_SIZE)
        self._enabled_classifications = set(AIRCRAFT_FILTER_CATEGORIES)
        self._visible_aircraft: dict[
            str, tuple[TrackedAircraft, tuple[int, int]]
        ] = {}
        self._selected_icao: str | None = None

    @property
    def enabled_classifications(self) -> frozenset[AircraftClassification]:
        """Return the classifications shown by the display."""

        return frozenset(self._enabled_classifications)

    def process_events(self) -> bool:
        """Process close, Escape, and aircraft selection events."""

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                return False
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                checkbox_index = self._checkbox_index_at(event.pos)
                if checkbox_index is not None:
                    classification = AIRCRAFT_FILTER_CATEGORIES[checkbox_index]
                    if classification in self._enabled_classifications:
                        self._enabled_classifications.remove(classification)
                    else:
                        self._enabled_classifications.add(classification)
                    continue
                markers = tuple(
                    (icao_hex, pixel_position)
                    for icao_hex, (_, pixel_position) in self._visible_aircraft.items()
                )
                self._selected_icao = nearest_marker(event.pos, markers)
        return True

    def render(
        self,
        center: Position,
        aircraft: Sequence[TrackedAircraft],
        runways: Sequence[RunwaySegment],
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
        filtered_aircraft = filter_aircraft(aircraft, self._enabled_classifications)
        self._draw_runways(
            center, runways, search_radius_nm, pixel_center, radar_radius
        )
        pygame.draw.circle(self._screen, GREEN, pixel_center, AIRCRAFT_RADIUS)

        self._draw_potential_areas(
            center,
            filtered_aircraft,
            search_radius_nm,
            pixel_center,
            radar_radius,
        )
        visible_aircraft: list[tuple[TrackedAircraft, RadarPoint]] = []
        for item in filtered_aircraft:
            observed = item.position
            if observed is None:
                continue
            observed_point = project_position(center, observed, search_radius_nm)
            if observed_point is None:
                continue
            visible_aircraft.append((item, observed_point))
        self._visible_aircraft = {
            item.aircraft.icao_hex.upper(): (
                item,
                self._pixel_position(observed_point, pixel_center, radar_radius),
            )
            for item, observed_point in visible_aircraft
        }
        stats = summarize_aircraft(tuple(item.aircraft for item, _ in visible_aircraft))
        selected = self._selected_aircraft()

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

        marker_draw_order = sorted(
            visible_aircraft,
            key=lambda visible: marker_draw_priority(visible[0], stats),
        )
        for item, observed_point in marker_draw_order:
            color = marker_color(item, stats)
            pixel_position = self._pixel_position(
                observed_point, pixel_center, radar_radius
            )
            if has_dual_highlight_ring(item, stats):
                pygame.draw.circle(
                    self._aircraft_layer,
                    BLUE,
                    pixel_position,
                    DUAL_HIGHLIGHT_RING_RADIUS,
                    width=1,
                )
            track_degrees = item.aircraft.track_degrees
            if track_degrees is None:
                pygame.draw.circle(
                    self._aircraft_layer,
                    color,
                    pixel_position,
                    AIRCRAFT_RADIUS,
                )
                continue
            # The source sprite points north. Pygame needs a negative screen angle.
            sprite_kind = select_aircraft_sprite(item.aircraft)
            sprite = pygame.transform.rotate(
                self._aircraft_sprites[(sprite_kind, color)], -track_degrees
            )
            self._aircraft_layer.blit(sprite, sprite.get_rect(center=pixel_position))

        # Draw the prediction endpoint last so it stays visible over the sprite.
        for item, _ in visible_aircraft:
            estimated = item.estimated_position
            if estimated is None:
                continue
            estimated_point = project_position(center, estimated, search_radius_nm)
            if estimated_point is None:
                continue
            pygame.draw.circle(
                self._aircraft_layer,
                prediction_color(item.is_stale),
                self._pixel_position(estimated_point, pixel_center, radar_radius),
                ESTIMATE_RADIUS,
            )

        if selected is not None:
            selected_item, selected_position = selected
            color = LIGHT_GREY if selected_item.is_stale else GREEN
            pygame.draw.circle(
                self._aircraft_layer,
                color,
                selected_position,
                SELECTION_RING_RADIUS,
                width=1,
            )

        self._blit_clipped_aircraft_layer(pixel_center, radar_radius)
        self._draw_aircraft_filters()
        self._draw_aircraft_stats(stats)
        if selected is not None:
            self._draw_aircraft_card(
                selected[0],
                selected[1],
                pixel_center,
                radar_radius,
            )

        pygame.display.flip()

    def _draw_aircraft_stats(self, stats: AircraftStats) -> None:
        """Draw the visible-aircraft statistics outside the radar circle."""

        lines = aircraft_stats_lines(stats)
        surfaces = tuple(
            self._stats_font.render(
                line,
                True,
                CHERRY_RED if index == 3 else BLUE if index == 4 else GREEN,
            )
            for index, line in enumerate(lines)
        )
        rectangles = statistics_text_rectangles(
            self._window_size,
            tuple(surface.get_size() for surface in surfaces),
        )
        for surface, rectangle in zip(surfaces, rectangles, strict=True):
            self._screen.blit(surface, rectangle[:2])

    def _draw_aircraft_filters(self) -> None:
        """Draw the aircraft classification checkboxes."""

        for category, label, row in zip(
            AIRCRAFT_FILTER_CATEGORIES,
            AIRCRAFT_FILTER_LABELS,
            checkbox_row_rectangles(),
            strict=True,
        ):
            box = pygame.Rect(
                row.left,
                row.top + (row.height - FILTER_BOX_SIZE) // 2,
                FILTER_BOX_SIZE,
                FILTER_BOX_SIZE,
            )
            pygame.draw.rect(self._screen, GREEN, box, width=1)
            if category in self._enabled_classifications:
                pygame.draw.line(
                    self._screen,
                    GREEN,
                    (box.left + 2, box.centery),
                    (box.left + 5, box.bottom - 3),
                    width=1,
                )
                pygame.draw.line(
                    self._screen,
                    GREEN,
                    (box.left + 5, box.bottom - 3),
                    (box.right - 2, box.top + 3),
                    width=1,
                )
            text = self._stats_font.render(label, True, GREEN)
            text_y = row.top + (row.height - text.get_height()) // 2
            self._screen.blit(text, (box.right + FILTER_TEXT_GAP, text_y))

    @staticmethod
    def _checkbox_index_at(position: tuple[int, int]) -> int | None:
        """Return the checkbox row at one screen position."""

        for index, row in enumerate(checkbox_row_rectangles()):
            if row.collidepoint(position):
                return index
        return None

    def _draw_runways(
        self,
        center: Position,
        runways: Sequence[RunwaySegment],
        search_radius_nm: int,
        pixel_center: tuple[int, int],
        radar_radius: int,
    ) -> None:
        """Draw runway segments clipped to the radar boundary."""

        for runway in runways:
            segment = project_runway_segment(center, runway, search_radius_nm)
            if segment is None:
                continue
            pygame.draw.line(
                self._screen,
                RUNWAY_GREEN,
                self._pixel_position(segment[0], pixel_center, radar_radius),
                self._pixel_position(segment[1], pixel_center, radar_radius),
                width=1,
            )

    def _draw_aircraft_card(
        self,
        item: TrackedAircraft,
        pixel_position: tuple[int, int],
        pixel_center: tuple[int, int],
        radar_radius: int,
    ) -> None:
        """Draw the selected aircraft information card."""

        lines = aircraft_card_lines(item.aircraft)
        line_height = self._card_font.get_linesize()
        card_width = max(
            self._card_font.size(line)[0] for line in lines
        ) + CARD_PADDING * 2
        card_height = (
            line_height * len(lines)
            + CARD_PADDING * 2
            + CARD_LINE_GAP * (len(lines) - 1)
        )
        card_rect = card_rect_near_aircraft(
            pixel_position,
            (card_width, card_height),
            pixel_center,
            radar_radius,
        )
        card_surface = pygame.Surface((card_width, card_height), pygame.SRCALPHA)
        card_surface.fill((*BLACK, 255))
        color = LIGHT_GREY if item.is_stale else GREEN
        pygame.draw.rect(
            card_surface,
            color,
            card_surface.get_rect(),
            width=CARD_BORDER_WIDTH,
        )
        y = CARD_PADDING
        for line in lines:
            text_surface = self._card_font.render(line, True, color)
            card_surface.blit(text_surface, (CARD_PADDING, y))
            y += line_height + CARD_LINE_GAP
        self._screen.blit(card_surface, card_rect[:2])

    def _selected_aircraft(
        self,
    ) -> tuple[TrackedAircraft, tuple[int, int]] | None:
        """Return the selected aircraft in the current visible frame."""

        if self._selected_icao is None:
            return None
        selected = self._visible_aircraft.get(self._selected_icao)
        if selected is None:
            self._selected_icao = None
        return selected

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

    @staticmethod
    def _load_aircraft_sprites() -> dict[
        tuple[AircraftSprite, tuple[int, int, int]], pygame.Surface
    ]:
        """Load each sprite mask and its four display colors once."""

        sprites: dict[
            tuple[AircraftSprite, tuple[int, int, int]], pygame.Surface
        ] = {}
        for sprite_kind in AircraftSprite:
            image = pygame.image.load(
                AIRCRAFT_ASSET_DIRECTORY / sprite_kind.filename
            ).convert_alpha()
            image = pygame.transform.smoothscale(
                image, (AIRCRAFT_SPRITE_SIZE, AIRCRAFT_SPRITE_SIZE)
            )
            mask = pygame.mask.from_surface(image)
            for color in (GREEN, LIGHT_GREY, CHERRY_RED, BLUE):
                sprites[(sprite_kind, color)] = mask.to_surface(
                    setcolor=(*color, 255), unsetcolor=(0, 0, 0, 0)
                ).convert_alpha()
        return sprites

    def close(self) -> None:
        """Close the Pygame display."""

        pygame.quit()
