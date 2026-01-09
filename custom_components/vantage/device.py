"""Support for Vantage devices."""

import contextlib
from typing import Protocol, runtime_checkable

from aiovantage import Vantage
from aiovantage.controllers import Controller
from aiovantage.errors import CommandError
from aiovantage.events import ObjectAdded, ObjectDeleted, ObjectUpdated
from aiovantage.objects import (
    LocationObject,
    Master,
    Parent,
    StationObject,
    SystemObject,
)

from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.entity import DeviceInfo

from .config_entry import VantageConfigEntry
from .const import DOMAIN


async def add_devices_from_controller[T: SystemObject](
    hass: HomeAssistant, entry: VantageConfigEntry, controller: Controller[T]
) -> None:
    """Add devices to the device registry from a Vantage controller."""
    vantage = entry.runtime_data.client
    dev_reg = dr.async_get(hass)

    # Register a device in the device registry
    async def add_or_update_device(obj: T) -> None:
        device_info = vantage_device_info(vantage, obj)
        if isinstance(obj, Master):
            with contextlib.suppress(CommandError):
                device_info["sw_version"] = await obj.get_application_version()

        dev_reg.async_get_or_create(config_entry_id=entry.entry_id, **device_info)

    # Add devices for all objects currently known by this controller
    for obj in controller:
        await add_or_update_device(obj)

    # Add entities for any new objects added to this controller
    def on_device_added(event: ObjectAdded[T]) -> None:
        hass.async_create_task(add_or_update_device(event.obj))

    entry.async_on_unload(controller.subscribe(ObjectAdded, on_device_added))

    # Update devices when objects are updated
    def on_device_updated(event: ObjectUpdated[T]) -> None:
        hass.async_create_task(add_or_update_device(event.obj))

    entry.async_on_unload(controller.subscribe(ObjectUpdated, on_device_updated))

    # Remove devices when objects are deleted
    def on_device_deleted(event: ObjectDeleted[T]) -> None:
        if device := dev_reg.async_get_device({(DOMAIN, str(event.obj.vid))}):
            dev_reg.async_remove_device(device.id)

    entry.async_on_unload(controller.subscribe(ObjectDeleted, on_device_deleted))


def async_cleanup_devices(hass: HomeAssistant, entry: VantageConfigEntry) -> None:
    """Remove devices from HA that are no longer in the Vantage controller."""
    vantage = entry.runtime_data.client
    dev_reg = dr.async_get(hass)

    for device in dr.async_entries_for_config_entry(dev_reg, entry.entry_id):
        # Device IDs always start with the object ID, followed by an optional suffix
        device_id = next(x[1] for x in device.identifiers if x[0] == DOMAIN)
        vantage_id = int(device_id.split(":")[0])
        if vantage_id not in vantage:
            dev_reg.async_remove_device(device.id)


async def async_setup_devices(hass: HomeAssistant, entry: VantageConfigEntry) -> None:
    """Set up Vantage devices in the device registry."""
    vantage = entry.runtime_data.client

    # Register "parent" devices (controllers, modules, port devices, and stations)
    await add_devices_from_controller(hass, entry, vantage.masters)
    await add_devices_from_controller(hass, entry, vantage.modules)
    await add_devices_from_controller(hass, entry, vantage.port_devices)
    await add_devices_from_controller(hass, entry, vantage.stations)


@runtime_checkable
class ChildObject(Protocol):
    """Child object protocol."""

    parent: Parent


def vantage_device_info(client: Vantage, obj: SystemObject) -> DeviceInfo:
    """Build the device info for a Vantage object."""
    device_info = DeviceInfo(
        identifiers={(DOMAIN, str(obj.vid))},
        name=obj.d_name or obj.name,
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
            and obj.parent.vid in client
            and not client.back_boxes.get(obj.parent.vid)
        ):
            # Attach the parent device for child objects (except for BackBoxes)
            device_info["via_device"] = (DOMAIN, str(obj.parent.vid))
        else:
            # Attach the master device for all other objects
            device_info["via_device"] = (DOMAIN, str(obj.master))

    return device_info
