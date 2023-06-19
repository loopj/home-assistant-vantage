"""Support for Vantage cover entities.

The following Vantage objects are considered cover entities:
- "Blind" objects
- "BlindGroup" objects
"""

from typing import Any
from aiovantage import Vantage
from aiovantage.config_client.objects import Blind, BlindGroup
from homeassistant.components.cover import CoverDeviceClass, CoverEntity
from homeassistant.components.group.cover import CoverGroup
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity_registry import async_get as async_get_entity_registry

from .const import DOMAIN
from .entity import VantageEntity


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Vantage covers from Config Entry."""
    vantage: Vantage = hass.data[DOMAIN][config_entry.entry_id]
    registry = async_get_entity_registry(hass)

    async for blind in vantage.blinds:
        blind_entity = VantageCover(vantage, blind)
        await blind_entity.fetch_relations()
        async_add_entities([blind_entity])

    async for blind_group in vantage.blind_groups:
        # Get the blind ids for the group, and look up their HA entity ids
        entity_ids = []
        async for blind in vantage.blind_groups.blinds(blind_group.id):
            entity_id = registry.async_get_entity_id(
                Platform.COVER, DOMAIN, str(blind.id)
            )
            if entity_id is not None:
                entity_ids.append(entity_id)

        # Create the group entity and add it to HA
        blind_group_entity = VantageCoverGroup(vantage, blind_group, entity_ids)
        await blind_group_entity.fetch_relations()
        async_add_entities([blind_group_entity])


class VantageCover(VantageEntity[Blind], CoverEntity):
    """Representation of a Vantage Cover."""

    def __init__(self, client: Vantage, obj: Blind):
        """Initialize a Vantage Cover."""
        if obj.type == "Drapery":
            self._attr_device_class = CoverDeviceClass.CURTAIN
        else:
            self._attr_device_class = CoverDeviceClass.SHADE

        super().__init__(client, client.blinds, obj)

    @property
    def is_closed(self) -> bool | None:
        """Return if the cover is closed or not."""
        return None

    async def async_open_cover(self, **kwargs: Any) -> None:
        """Open the cover."""
        await self.client.blinds.open(self.obj.id)

    async def async_close_cover(self, **kwargs: Any) -> None:
        """Close cover."""
        await self.client.blinds.close(self.obj.id)

    async def async_stop_cover(self, **kwargs: Any) -> None:
        """Stop the cover."""
        await self.client.blinds.stop(self.obj.id)


class VantageCoverGroup(VantageEntity[BlindGroup], CoverGroup):
    """Representation of a Vantage cover group."""

    def __init__(self, client: Vantage, obj: BlindGroup, entities: list[str]):
        """Initialize a cover group."""
        VantageEntity.__init__(self, client, client.blind_groups, obj)
        CoverGroup.__init__(self, str(obj.id), obj.name, entities)

    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added to hass."""
        await CoverGroup.async_added_to_hass(self)
