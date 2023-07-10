"""Support for Vantage cover entities."""

import functools
from typing import Any, TypeVar

from aiovantage import Vantage
from aiovantage.config_client.objects import Blind, BlindGroup

from homeassistant.components.cover import CoverDeviceClass, CoverEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .entity import VantageEntity, async_setup_vantage_entities

T = TypeVar("T", bound=Blind | BlindGroup)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Vantage covers from Config Entry."""
    vantage: Vantage = hass.data[DOMAIN][config_entry.entry_id]
    register_items = functools.partial(
        async_setup_vantage_entities, vantage, config_entry, async_add_entities
    )

    # Set up all cover entities
    register_items(vantage.blinds, VantageCover)
    register_items(vantage.blind_groups, VantageCoverGroup)


class VantageCover(VantageEntity[Blind], CoverEntity):
    """Representation of a Vantage Cover."""

    def __post_init__(self) -> None:
        """Initialize a Vantage Cover."""
        match self.obj.type:
            case "Drapery":
                self._attr_device_class = CoverDeviceClass.CURTAIN
            case _:
                self._attr_device_class = CoverDeviceClass.SHADE

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


class VantageCoverGroup(VantageEntity[BlindGroup], CoverEntity):
    """Representation of a Vantage Cover group."""

    @property
    def is_closed(self) -> bool | None:
        """Return if the cover is closed or not."""
        return None

    async def async_open_cover(self, **kwargs: Any) -> None:
        """Open the cover."""
        await self.client.blind_groups.open(self.obj.id)

    async def async_close_cover(self, **kwargs: Any) -> None:
        """Close cover."""
        await self.client.blind_groups.close(self.obj.id)

    async def async_stop_cover(self, **kwargs: Any) -> None:
        """Stop the cover."""
        await self.client.blind_groups.stop(self.obj.id)
