"""Support for Vantage text entities."""

import functools

from aiovantage import Vantage
from aiovantage.config_client.objects import GMem

from homeassistant.components.text import TextEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .entity import VantageEntity, async_setup_vantage_entities


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Vantage text entities from Config Entry."""
    vantage: Vantage = hass.data[DOMAIN][config_entry.entry_id]
    register_items = functools.partial(
        async_setup_vantage_entities, vantage, config_entry, async_add_entities
    )

    # Register all text entities
    register_items(vantage.gmem, VantageTextVariable, lambda obj: obj.is_str)


class VantageTextVariable(VantageEntity[GMem], TextEntity):
    """Representation of a Vantage text GMem variable."""

    _attr_entity_registry_visible_default = False

    def __post_init__(self) -> None:
        """Initialize a Vantage text variable."""
        self._attr_name = self.obj.name
        self._device_id = f"variables_{self.obj.master_id}"

    @property
    def native_value(self) -> str | None:
        """Return the value reported by the text."""
        if isinstance(self.obj.value, str):
            return self.obj.value

        return None

    async def async_set_value(self, value: str) -> None:
        """Change the value."""
        await self.client.gmem.set_value(self.obj.id, value)
