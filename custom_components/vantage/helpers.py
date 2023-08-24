"""Helper functions for Vantage integration."""

from typing import Protocol, runtime_checkable

from aiovantage import Vantage
from aiovantage.models import Area, LocationObject, Parent, SystemObject


@runtime_checkable
class ChildObject(Protocol):
    """Child object protocol."""

    parent: Parent


def scale_color_brightness(
    color: tuple[int, ...], brightness: int | None
) -> tuple[int, ...]:
    """Scale the brightness of an RGB/RGBW color tuple."""
    if brightness is None:
        return color

    return tuple(int(round(c * brightness / 255)) for c in color)


def brightness_to_level(brightness: int) -> float:
    """Convert a HA brightness value [0..255] to a Vantage level value [0..100]."""
    return brightness / 255 * 100


def level_to_brightness(level: float) -> int:
    """Convert a Vantage level value [0..100] to a HA brightness value [0..255]."""
    return round(level / 100 * 255)


def get_object_area(vantage: Vantage, obj: SystemObject) -> Area | None:
    """Get the area for a Vantage object, if it has one."""
    if isinstance(obj, LocationObject) and obj.area_id is not None:
        return vantage.areas.get(obj.area_id)

    return None


def get_object_parent_id(obj: SystemObject) -> int | None:
    """Get the parent id for a Vantage object, if it has one."""
    if isinstance(obj, ChildObject):
        return obj.parent.id

    return None
