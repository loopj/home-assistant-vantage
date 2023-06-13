from aiovantage import Vantage
from aiovantage.config_client.objects import Area, Load
from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .entity import VantageEntity


async def async_setup_entry(
    hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities
):
    # Get the client from the hass data store
    vantage: Vantage = hass.data[DOMAIN][config_entry.entry_id]

    # Fetch loads from the Vantage controller
    await vantage.loads.initialize()

    # Relay Load objects are switches
    async for load in vantage.loads.relays:
        area = await vantage.areas.aget(load.area_id)
        entity = VantageRelay(vantage, load, area)

        async_add_entities([entity])


class VantageRelay(VantageEntity[Load], SwitchEntity):
    def __init__(self, client: Vantage, obj: Load, area: Area):
        VantageEntity.__init__(self, client, client.loads, obj, area)

    @property
    def is_on(self) -> bool | None:
        """Return True if entity is on."""
        return self.obj.level

    async def async_turn_on(self, **kwargs) -> None:
        """Turn the switch on."""
        await self.client.loads.turn_on(self.obj.id)

    async def async_turn_off(self, **kwargs) -> None:
        """Turn the switch off."""
        await self.client.loads.turn_off(self.obj.id)
