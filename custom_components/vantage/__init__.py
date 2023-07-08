"""The Vantage InFusion Controller integration."""
from typing import Any, TypeVar

from aiovantage import Vantage, VantageEvent
from aiovantage.config_client.objects import LocationObject, Master, SystemObject
from aiovantage.controllers.base import BaseController
from aiovantage.errors import (
    ClientConnectionError,
    LoginFailedError,
    LoginRequiredError,
)

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigEntryAuthFailed,
    ConfigEntryNotReady,
)
from homeassistant.const import (
    CONF_HOST,
    CONF_PASSWORD,
    CONF_SSL,
    CONF_USERNAME,
    Platform,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr

from .const import DOMAIN

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.COVER,
    Platform.LIGHT,
    Platform.NUMBER,
    Platform.SENSOR,
    Platform.SWITCH,
    Platform.TEXT,
]

T = TypeVar("T", bound=SystemObject)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Vantage integration from a config entry."""

    # Create a Vantage client
    vantage = Vantage(
        entry.data[CONF_HOST],
        entry.data.get(CONF_USERNAME),
        entry.data.get(CONF_PASSWORD),
        use_ssl=entry.data.get(CONF_SSL, True),
    )

    # Store the client in the hass data store
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = vantage

    try:
        # Eager load all data from Vantage
        await vantage.initialize()

        # Add Vantage devices (controllers, modules, stations) to the device registry
        await async_setup_devices(hass, entry)

        # Monitor controller programming events, and re-initialize if necessary
        def reinitialize(_type: VantageEvent, _obj: Master, _data: Any) -> None:
            hass.async_create_task(vantage.initialize())

        if first_master := vantage.masters.first():
            entry.async_on_unload(
                vantage.masters.subscribe(
                    reinitialize,
                    first_master.id,
                    VantageEvent.OBJECT_UPDATED,
                )
            )

        # Set up each platform
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    except (LoginRequiredError, LoginFailedError) as err:
        raise ConfigEntryAuthFailed from err
    except ClientConnectionError as err:
        raise ConfigEntryNotReady from err

    return True


async def async_setup_devices(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Set up Vantage lights from Config Entry."""
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
            params = {
                "identifiers": {(DOMAIN, str(obj.id))},
                "config_entry_id": entry.entry_id,
                "name": obj.name,
                "manufacturer": "Vantage",
                "model": obj.model,
            }

            if isinstance(obj, LocationObject):
                if area := vantage.areas.get(obj.area_id):
                    params["suggested_area"] = area.name

            if isinstance(obj, Master):
                params["sw_version"] = obj.firmware_version
            else:
                params["via_device"] = (DOMAIN, str(obj.master_id))

            return dev_reg.async_get_or_create(**params)

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

        # TODO: Remove any devices that are no longer present

        # Register a callback for new members
        entry.async_on_unload(controller.subscribe(handle_device_event))

    # Register all devices
    register_items(vantage.masters)
    register_items(vantage.modules)
    register_items(vantage.stations)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    vantage: Vantage = hass.data[DOMAIN].pop(entry.entry_id, None)
    if vantage:
        vantage.close()

    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
