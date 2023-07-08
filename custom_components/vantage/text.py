"""Support for Vantage text entities."""

from typing import Any

from aiovantage import Vantage, VantageEvent
from aiovantage.config_client.objects import GMem

from homeassistant.components.text import TextEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .entity import VantageEntity


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Vantage texts from Config Entry."""
    vantage: Vantage = hass.data[DOMAIN][config_entry.entry_id]
    controller = vantage.gmem

    @callback
    def async_add_entity(_type: VantageEvent, obj: GMem, _data: Any) -> None:
        if obj.is_str:
            async_add_entities([VantageTextVariable(vantage, controller, obj)])

    # Add all current members of this controller
    for obj in controller:
        async_add_entity(VantageEvent.OBJECT_ADDED, obj, {})

    # Register a callback for new members
    config_entry.async_on_unload(
        controller.subscribe(async_add_entity, event_filter=VantageEvent.OBJECT_ADDED)
    )


class VantageTextVariable(VantageEntity[GMem], TextEntity):
    """Representation of a Vantage text GMem variable."""

    def __post_init__(self) -> None:
        """Initialize a Vantage text variable."""
        self._attr_name = self.obj.name

    @property
    def attach_to_device(self) -> int | None:
        """The id of the device this entity should be attached to, if any."""
        return self.obj.master_id

    @property
    def native_value(self) -> str | None:
        """Return the value reported by the text."""
        if isinstance(self.obj.value, str):
            return self.obj.value

        return None

    async def async_set_value(self, value: str) -> None:
        """Change the value."""
        await self.client.gmem.set_value(self.obj.id, value)
