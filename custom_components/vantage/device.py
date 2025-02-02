"""Support for Vantage devices."""

from typing import Any, Protocol, TypeVar, runtime_checkable

from aiovantage import Vantage, VantageEvent
from aiovantage.controllers import BaseController
from aiovantage.objects import (
    LocationObject,
    Master,
    Parent,
    StationObject,
    SystemObject,
)

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.entity import DeviceInfo

from .config_entry import VantageConfigEntry
from .const import DOMAIN

T = TypeVar("T", bound=SystemObject)


def async_setup_devices(hass: HomeAssistant, entry: VantageConfigEntry) -> None:
    """Set up Vantage devices in the device registry."""
    vantage = entry.runtime_data.client
    dev_reg = dr.async_get(hass)

    @callback
    def remove_device(device_id: str) -> None:
        """Remove device from the registry."""
        if device := dev_reg.async_get_device({(DOMAIN, device_id)}):
            dev_reg.async_remove_device(device.id)

    @callback
    def register_items(controller: BaseController[T]) -> None:
        @callback
        def add_device(obj: T) -> dr.DeviceEntry:
            """Register a Vantage device in the device registry."""
            return dev_reg.async_get_or_create(
                config_entry_id=entry.entry_id, **vantage_device_info(vantage, obj)
            )

        @callback
        def handle_device_event(event_type: VantageEvent, obj: T, _data: Any) -> None:
            """Handle a Vantage event for a device."""
            if event_type == VantageEvent.OBJECT_DELETED:
                remove_device(str(obj.id))
            else:
                add_device(obj)

        # Add all current members of this controller
        for obj in controller:
            add_device(obj)

        # Register a callback for new members
        entry.async_on_unload(controller.subscribe(handle_device_event))

    # Register "parent" devices (controllers, modules, port devices, and stations)
    register_items(vantage.masters)
    register_items(vantage.modules)
    register_items(vantage.port_devices)
    register_items(vantage.stations)

    # Clean up any devices for objects that no longer exist on the Vantage controller
    for device in dr.async_entries_for_config_entry(dev_reg, entry.entry_id):
        # Device IDs always start with the object ID, followed by an optional suffix
        device_id = next(x[1] for x in device.identifiers if x[0] == DOMAIN)
        vantage_id = int(device_id.split(":")[0])
        if vantage_id not in vantage:
            dev_reg.async_remove_device(device.id)


@runtime_checkable
class ChildObject(Protocol):
    """Child object protocol."""

    parent: Parent


def vantage_device_info(client: Vantage, obj: SystemObject) -> DeviceInfo:
    """Build the device info for a Vantage object."""
    device_info = DeviceInfo(
        identifiers={(DOMAIN, str(obj.id))},
        name=obj.display_name,
    )

    # Suggest sensible model and manufacturer names
    parts = obj.vantage_type().split(".", 1)
    if len(parts) > 1:
        # Vantage CustomDevice objects take the form "manufacturer.model"
        device_info["manufacturer"] = parts[0]
        device_info["model"] = parts[1]
    else:
        # Otherwise, assume this is a built-in Vantage object
        device_info["manufacturer"] = "Vantage"
        device_info["model"] = parts[0]

    # Suggest an area for LocationObject devices
    if (
        isinstance(obj, LocationObject)
        and obj.area
        and (area := client.areas.get(obj.area))
    ):
        device_info["suggested_area"] = area.name

    # Attach serial number for devices that have one
    if isinstance(obj, Master) or isinstance(obj, StationObject):
        if obj.serial_number:
            device_info["serial_number"] = str(obj.serial_number)

    # Set up device relationships
    if not isinstance(obj, Master):
        if (
            isinstance(obj, ChildObject)
            and obj.parent.id in client
            and not client.back_boxes.get(obj.parent.id)
        ):
            # Attach the parent device for child objects (except for BackBoxes)
            device_info["via_device"] = (DOMAIN, str(obj.parent.id))
        else:
            # Attach the master device for all other objects
            device_info["via_device"] = (DOMAIN, str(obj.master))

    # Attach the firmware version for Master devices
    if isinstance(obj, Master):
        device_info["sw_version"] = obj.firmware_version

    return device_info
