"""The Vantage InFusion Controller integration."""
from __future__ import annotations

from aiovantage import Vantage
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant
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


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up controller from a config entry."""

    # Create a Vantage client
    vantage = Vantage(
        entry.data[CONF_HOST],
        entry.data.get(CONF_USERNAME),
        entry.data.get(CONF_PASSWORD),
    )

    # Store the client in the hass data store
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = vantage

    # Add each Vantage Controller to the device registry
    device_registry = dr.async_get(hass)
    async for master in vantage.masters:
        # Get the firmware version of the controller
        version = await vantage.masters.get_firmware_version(
            master.id, vantage.masters.Firmware.APPLICATION
        )

        # Add the controller to the device registry
        device_registry.async_get_or_create(
            identifiers={(DOMAIN, str(master.serial_number))},
            config_entry_id=entry.entry_id,
            manufacturer="Vantage",
            name=master.name,
            model=master.model,
            sw_version=version,
        )

    # Set up each platform
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""

    vantage = hass.data[DOMAIN][entry.entry_id]
    await vantage.close()

    if len(hass.data[DOMAIN]) == 0:
        hass.data.pop(DOMAIN)

    return True
