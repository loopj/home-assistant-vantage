"""Helper functions for Vantage integration."""

from typing import Protocol, runtime_checkable

from aiovantage import Vantage
from aiovantage.models import LocationObject, Master, Parent, SystemObject

from homeassistant.helpers.entity import DeviceInfo

from .const import DOMAIN


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


def vantage_device_info(client: Vantage, obj: SystemObject) -> DeviceInfo:
    """Build the device info for a Vantage object."""
    device_info = DeviceInfo(
        identifiers={(DOMAIN, str(obj.id))},
        name=obj.display_name or obj.name,
        manufacturer="Vantage",
        model=obj.model,
    )

    # Suggest an area for LocationObject devices
    if (
        isinstance(obj, LocationObject)
        and obj.area_id
        and (area := client.areas.get(obj.area_id))
    ):
        device_info["suggested_area"] = area.name

    # Set up device relationships
    if not isinstance(obj, Master):
        if isinstance(obj, ChildObject) and obj.parent.id in client:
            device_info["via_device"] = (DOMAIN, str(obj.parent.id))
        else:
            device_info["via_device"] = (DOMAIN, str(obj.master_id))

    # Attach the firmware version for Master devices
    if isinstance(obj, Master):
        device_info["sw_version"] = obj.firmware_version

    return device_info
