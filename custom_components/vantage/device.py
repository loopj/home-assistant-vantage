"""Support for Vantage devices."""

from typing import Protocol, runtime_checkable
from collections.abc import Awaitable, Callable

from aiovantage import Vantage
from aiovantage.controllers import BaseController
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


async def async_setup_devices(hass: HomeAssistant, entry: VantageConfigEntry) -> None:
    """Set up Vantage devices in the device registry."""
    vantage = entry.runtime_data.client
    dev_reg = dr.async_get(hass)

    async def register_items[T: SystemObject](
        controller: BaseController[T],
        extra_info_fn: Callable[[T], Awaitable[DeviceInfo]] | None = None,
    ) -> None:
        # Register a device in the device registry
        async def add_or_update_device(obj: T) -> dr.DeviceEntry:
            device_info = vantage_device_info(vantage, obj)
            if extra_info_fn:
                device_info.update(await extra_info_fn(obj))

            return dev_reg.async_get_or_create(
                config_entry_id=entry.entry_id, **device_info
            )

        # Add all current members of this controller
        for obj in controller:
            await add_or_update_device(obj)

        # Monitor for changes to the controller
        def on_device_added(event: ObjectAdded[T]) -> None:
            hass.async_create_task(add_or_update_device(event.obj))

        def on_device_updated(event: ObjectUpdated[T]) -> None:
            hass.async_create_task(add_or_update_device(event.obj))

        def on_device_deleted(event: ObjectDeleted[T]) -> None:
            if device := dev_reg.async_get_device({(DOMAIN, str(event.obj.vid))}):
                dev_reg.async_remove_device(device.id)

        entry.async_on_unload(controller.subscribe(ObjectAdded, on_device_added))
        entry.async_on_unload(controller.subscribe(ObjectDeleted, on_device_deleted))
        entry.async_on_unload(controller.subscribe(ObjectUpdated, on_device_updated))

    # Register "master" devices, additionally fetching the firmware version
    async def extra_master_info(obj: Master) -> DeviceInfo:
        return DeviceInfo(sw_version=await obj.get_application_version())

    await register_items(vantage.masters, extra_master_info)

    # Register "parent" devices (controllers, modules, port devices, and stations)
    await register_items(vantage.modules)
    await register_items(vantage.port_devices)
    await register_items(vantage.stations)

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
