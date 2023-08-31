"""Support for Vantage devices."""

from typing import Any, TypeVar

from aiovantage import Vantage, VantageEvent
from aiovantage.controllers import BaseController
from aiovantage.models import SystemObject

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr

from .const import DOMAIN
from .helpers import vantage_device_info

T = TypeVar("T", bound=SystemObject)


def async_setup_devices(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Set up Vantage devices in the device registry."""
    vantage: Vantage = hass.data[DOMAIN][entry.entry_id]
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
