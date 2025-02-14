"""Support for Vantage text entities."""

from typing import override

from homeassistant.components.text import TextEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .config_entry import VantageConfigEntry
from .entity import VantageGMemEntity, add_entities_from_controller


async def async_setup_entry(
    hass: HomeAssistant,
    entry: VantageConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Vantage text entities from a config entry."""
    vantage = entry.runtime_data.client

    # Add every GMem object with a text data type as a text entity
    await add_entities_from_controller(
        hass,
        entry,
        async_add_entities,
        VantageGMemTextEntity,
        vantage.gmem,
        lambda obj: obj.is_str,
    )


class VantageGMemTextEntity(VantageGMemEntity, TextEntity):
    """Text entity provided by a Vantage GMem object."""

    @property
    @override
    def native_value(self) -> str | None:
        if isinstance(self.obj.value, str):
            return self.obj.value

        return None

    @override
    async def async_set_value(self, value: str) -> None:
        await self.async_request_call(self.obj.set_value(value))
