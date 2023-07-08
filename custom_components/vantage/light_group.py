"""Support for Vantage light groups."""

from typing import Any

from aiovantage import Vantage, VantageEvent
from aiovantage.config_client.objects import LoadGroup

from homeassistant.components.light import ATTR_BRIGHTNESS, ATTR_TRANSITION, LightEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .entity import VantageEntity
from .helpers import brightness_to_level, level_to_brightness


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Vantage light groups from Config Entry."""
    vantage: Vantage = hass.data[DOMAIN][config_entry.entry_id]
    controller = vantage.load_groups

    @callback
    def async_add_entity(_type: VantageEvent, obj: LoadGroup, _data: Any) -> None:
        async_add_entities([VantageLightGroup(vantage, controller, obj)])

    # Add all current members of this controller
    for obj in controller:
        async_add_entity(VantageEvent.OBJECT_ADDED, obj, {})

    # Register a callback for new members
    config_entry.async_on_unload(
        controller.subscribe(async_add_entity, event_filter=VantageEvent.OBJECT_ADDED)
    )


class VantageLightGroup(VantageEntity[LoadGroup], LightEntity):
    """Representation of a Vantage light group."""

    @property
    def is_on(self) -> bool | None:
        """Return True if entity is on."""
        return self.obj.is_on

    @property
    def brightness(self) -> int | None:
        """Return the brightness of this light between 0..255."""
        if self.obj.level is None:
            return None

        return level_to_brightness(self.obj.level)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the light on."""
        await self.client.loads.turn_on(
            self.obj.id,
            kwargs.get(ATTR_TRANSITION, 0),
            brightness_to_level(kwargs.get(ATTR_BRIGHTNESS, 255)),
        )

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the light off."""
        await self.client.rgb_loads.turn_off(
            self.obj.id, kwargs.get(ATTR_TRANSITION, 0)
        )
