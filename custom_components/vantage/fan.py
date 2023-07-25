"""Support for Vantage fan entities."""

import functools
from typing import Any

from aiovantage import Vantage
from aiovantage.models import Load

from homeassistant.components.fan import FanEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .entity import VantageEntity, async_register_vantage_objects


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up Vantage fan entities from config entry."""
    vantage: Vantage = hass.data[DOMAIN][entry.entry_id]
    register_items = functools.partial(
        async_register_vantage_objects, hass, entry, async_add_entities
    )

    # Register all fan entities
    register_items(vantage.loads, VantageFan, lambda obj: obj.is_motor)


class VantageFan(VantageEntity[Load], FanEntity):
    """Vantage motor load fan entity."""

    def __post_init__(self) -> None:
        """Initialize the switch."""
        self._device_model = f"{self.obj.load_type} Load"

    @property
    def is_on(self) -> bool | None:
        """Return True if entity is on."""
        return self.obj.is_on

    async def async_turn_on(
        self,
        percentage: int | None = None,
        preset_mode: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Turn on the fan."""
        await self.client.loads.turn_on(self.obj.id)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the entity off."""
        await self.client.loads.turn_off(self.obj.id)
