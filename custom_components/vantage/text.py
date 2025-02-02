"""Support for Vantage text entities."""

from collections.abc import Callable
import functools

from aiovantage.objects import GMem

from homeassistant.components.text import TextEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .config_entry import VantageConfigEntry
from .entity import VantageVariableEntity, async_register_vantage_objects


async def async_setup_entry(
    hass: HomeAssistant,
    entry: VantageConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Vantage text entities from config entry."""
    vantage = entry.runtime_data.client
    register_items = functools.partial(
        async_register_vantage_objects, hass, entry, async_add_entities
    )

    # Register all text entities
    gmem_filter: Callable[[GMem], bool] = lambda obj: obj.is_str
    register_items(vantage.gmem, VantageTextVariable, gmem_filter)


class VantageTextVariable(VantageVariableEntity, TextEntity):
    """Vantage text variable text entity."""

    @property
    def native_value(self) -> str | None:
        """Return the value reported by the text."""
        if isinstance(self.obj.value, str):
            return self.obj.value

        return None

    async def async_set_value(self, value: str) -> None:
        """Change the value."""
        await self.async_request_call(self.client.gmem.set_value(self.obj.id, value))
