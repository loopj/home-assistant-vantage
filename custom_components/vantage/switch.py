from aiovantage import Vantage
from aiovantage.config_client.objects import Load, GMem
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

    # Relay Load objects are switches
    async for load in vantage.loads.relays:
        entity = VantageRelay(vantage, load)
        await entity.fetch_relations()
        async_add_entities([entity])

    # Boolean GMem objects are switches
    async for gmem in vantage.gmem.filter(lambda gmem: gmem.is_bool):
        entity = VantageBooleanVariable(vantage, gmem)
        await entity.fetch_relations()
        async_add_entities([entity])


class VantageRelay(VantageEntity[Load], SwitchEntity):
    """Representation of a Vantage relay."""

    def __init__(self, client: Vantage, obj: Load):
        """Initialize a Vantage relay."""
        super().__init__(client, client.loads, obj)

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


class VantageBooleanVariable(VantageEntity[GMem], SwitchEntity):
    """Representation of a Vantage boolean GMem variable."""

    def __init__(self, client: Vantage, obj: GMem):
        """Initialize a Vantage boolean variable."""
        super().__init__(client, client.gmem, obj)

    @property
    def is_on(self) -> bool | None:
        """Return True if entity is on."""
        return self.obj.value

    async def async_turn_on(self, **kwargs) -> None:
        """Turn the switch on."""
        await self.client.gmem.set_value(self.obj.id, True)

    async def async_turn_off(self, **kwargs) -> None:
        """Turn the switch off."""
        await self.client.gmem.set_value(self.obj.id, False)
