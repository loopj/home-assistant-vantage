"""Migration functions for the Vantage integration."""

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr

from .const import LOGGER


async def async_migrate_data(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Run all Vantage data migrations."""

    async_delete_back_boxes(hass, entry)


def async_delete_back_boxes(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Delete back boxes from the device registry."""
    dev_reg = dr.async_get(hass)

    back_box_devices = [
        device
        for device in dr.async_entries_for_config_entry(dev_reg, entry.entry_id)
        if device.model == "BackBox"
    ]

    if back_box_devices:
        LOGGER.debug(f"Deleting {len(back_box_devices)} back boxes from the registry.")

        for device in back_box_devices:
            dev_reg.async_remove_device(device.id)
