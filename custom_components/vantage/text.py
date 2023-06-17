"""Support for Vantage text entities.

The following Vantage objects are considered switch entities:
- "GMem" objects that are strings
"""

from aiovantage import Vantage
from aiovantage.config_client.objects import GMem
from homeassistant.components.text import TextEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .entity import VantageEntity


async def async_setup_entry(
    hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities
):
    """Set up Vantage texts from Config Entry."""
    vantage: Vantage = hass.data[DOMAIN][config_entry.entry_id]

    # "Text" GMem objects are text entities
    async for gmem in vantage.gmem.filter(lambda gmem: gmem.is_str):
        entity = VantageTextVariable(vantage, gmem)
        await entity.fetch_relations()
        async_add_entities([entity])


class VantageTextVariable(VantageEntity[GMem], TextEntity):
    """Representation of a Vantage text GMem variable."""

    def __init__(self, client: Vantage, obj: GMem):
        """Initialize a Vantage text variable."""
        super().__init__(client, client.gmem, obj)

    @property
    def native_value(self) -> str | None:
        """Return the value reported by the text."""
        return self.obj.value

    async def async_set_value(self, value: str) -> None:
        """Change the value."""
        await self.client.gmem.set_value(self.obj.id, value)
