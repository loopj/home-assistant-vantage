"""Migration functions for the Vantage integration."""

from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er

from .config_entry import VantageConfigEntry
from .const import LOGGER


async def async_migrate_data(hass: HomeAssistant, entry: VantageConfigEntry) -> None:
    """Run all Vantage data migrations."""

    async_delete_back_boxes(hass, entry)
    async_delete_serial_number_entities(hass, entry)


def async_delete_back_boxes(hass: HomeAssistant, entry: VantageConfigEntry) -> None:
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


def async_delete_serial_number_entities(
    hass: HomeAssistant, entry: VantageConfigEntry
) -> None:
    """Delete serial number entities from the entity registry."""
    ent_reg = er.async_get(hass)

    serial_number_entities = [
        entity
        for entity in er.async_entries_for_config_entry(ent_reg, entry.entry_id)
        if entity.unique_id.endswith(":serial_number")
    ]

    if serial_number_entities:
        LOGGER.debug(
            f"Deleting {len(serial_number_entities)} serial number entities from the registry."
        )

        for entity in serial_number_entities:
            ent_reg.async_remove(entity.entity_id)
