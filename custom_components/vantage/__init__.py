"""The Vantage InFusion Controller integration."""
from typing import Any, TypeVar

from aiovantage import Vantage, VantageEvent
from aiovantage.config_client.objects import Master, SystemObject
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
from homeassistant.helpers.entity import DeviceInfo

from .const import DOMAIN
from .helpers import get_object_area

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

        # Set up each platform (lights, covers, etc.)
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    except (LoginRequiredError, LoginFailedError) as err:
        # Handle expired or invalid credentials. This will prompt the user to reconfigure
        # the integration.
        raise ConfigEntryAuthFailed from err

    except ClientConnectionError as err:
        # Handle offline or unavailable devices and services. Home Assistant will
        # automatically put the config entry in a failure state and start a reauth flow.
        raise ConfigEntryNotReady from err

    return True


async def async_setup_devices(hass: HomeAssistant, entry: ConfigEntry) -> None:
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
            device_info = DeviceInfo(
                identifiers={(DOMAIN, str(obj.id))},
                name=obj.name,
                manufacturer="Vantage",
                model=obj.model,
            )

            if area := get_object_area(vantage, obj):
                device_info["suggested_area"] = area.name

            if not isinstance(obj, Master):
                device_info["via_device"] = (DOMAIN, str(obj.master_id))

            if isinstance(obj, Master):
                device_info["sw_version"] = obj.firmware_version

            return dev_reg.async_get_or_create(
                config_entry_id=entry.entry_id, **device_info
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

    # Register controllers, modules, and stations
    register_items(vantage.masters)
    register_items(vantage.modules)
    register_items(vantage.stations)

    # Create virtual devices to hold variables
    for master in vantage.masters:
        dev_reg.async_get_or_create(
            config_entry_id=entry.entry_id,
            identifiers={(DOMAIN, f"variables_{master.id}")},
            name="Variables",
            manufacturer="Vantage",
            entry_type=dr.DeviceEntryType.SERVICE,
            via_device=(DOMAIN, str(master.id)),
        )


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    vantage: Vantage = hass.data[DOMAIN].pop(entry.entry_id, None)
    if vantage:
        vantage.close()

    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
