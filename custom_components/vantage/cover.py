from aiovantage import Vantage
from aiovantage.config_client.objects import Area, Blind
from homeassistant.components.cover import CoverEntity, CoverDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .entity import VantageEntity


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Vantage Light from Config Entry."""
    vantage: Vantage = hass.data[DOMAIN][config_entry.entry_id]

    async for blind in vantage.blinds:
        area = await vantage.areas.aget(blind.area_id)
        entity = VantageCover(vantage, blind, area)

        async_add_entities([entity])


class VantageCover(VantageEntity[Blind], CoverEntity):
    def __init__(self, client: Vantage, obj: Blind, area: Area):
        """Initialize a Vantage Cover."""

        if obj.type == "Drapery":
            self._attr_device_class = CoverDeviceClass.CURTAIN
        else:
            self._attr_device_class = CoverDeviceClass.SHADE

        super().__init__(client, client.blinds, obj, area)

    @property
    def is_closed(self):
        """Return if the cover is closed or not."""

        return None

    async def async_open_cover(self, **kwargs):
        """Open the cover."""

        await self.client.blinds.open(self.obj.id)

    async def async_close_cover(self, **kwargs):
        """Close cover."""

        await self.client.blinds.close(self.obj.id)

    async def async_stop_cover(self, **kwargs):
        """Stop the cover."""

        await self.client.blinds.stop(self.obj.id)
