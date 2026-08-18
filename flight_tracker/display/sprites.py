"""Aircraft sprite choices for the radar display."""

from enum import Enum

from flight_tracker.models import AirframeKind, Aircraft, AircraftClassification


class AircraftSprite(Enum):
    """A sprite selected for an aircraft."""

    GENERIC_AIRPLANE = "aircraft.svg"
    COMMERCIAL_AIRPLANE = "aircraft.svg"
    GENERAL_AVIATION_AIRPLANE = "airplane-general-aviation.svg"
    PRIVATE_AIRPLANE = "airplane-private.svg"
    MILITARY_AIRPLANE = "airplane-military.svg"
    CIVILIAN_HELICOPTER = "helicopter-civilian.svg"
    MILITARY_HELICOPTER = "helicopter-military.svg"

    @property
    def filename(self) -> str:
        """Return the asset file name for this sprite."""

        return self.value


def select_aircraft_sprite(aircraft: Aircraft) -> AircraftSprite:
    """Select a sprite from the normalized aircraft facts."""

    if aircraft.airframe_kind is AirframeKind.HELICOPTER:
        if aircraft.classification is AircraftClassification.MILITARY:
            return AircraftSprite.MILITARY_HELICOPTER
        return AircraftSprite.CIVILIAN_HELICOPTER
    if aircraft.classification is AircraftClassification.MILITARY:
        return AircraftSprite.MILITARY_AIRPLANE
    if aircraft.airframe_kind is not AirframeKind.AIRPLANE:
        return AircraftSprite.GENERIC_AIRPLANE
    if aircraft.classification is AircraftClassification.PRIVATE:
        return AircraftSprite.PRIVATE_AIRPLANE
    if aircraft.classification is AircraftClassification.GENERAL_AVIATION:
        return AircraftSprite.GENERAL_AVIATION_AIRPLANE
    if aircraft.classification is AircraftClassification.COMMERCIAL:
        return AircraftSprite.COMMERCIAL_AIRPLANE
    return AircraftSprite.GENERIC_AIRPLANE

