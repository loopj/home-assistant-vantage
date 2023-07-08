"""Support for Vantage binary sensor entities."""

from typing import Any

from aiovantage import Vantage, VantageEvent
from aiovantage.config_client.objects import DryContact

from homeassistant.components.binary_sensor import BinarySensorEntity
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
    """Set up Vantage binary sensors from Config Entry."""
    vantage: Vantage = hass.data[DOMAIN][config_entry.entry_id]
    controller = vantage.dry_contacts

    @callback
    def async_add_entity(_type: VantageEvent, obj: DryContact, _data: Any) -> None:
        async_add_entities([VantageDryContact(vantage, controller, obj)])

    # Add all current members of this controller
    for obj in controller:
        async_add_entity(VantageEvent.OBJECT_ADDED, obj, {})

    # Register a callback to add new members
    config_entry.async_on_unload(
        controller.subscribe(async_add_entity, event_filter=VantageEvent.OBJECT_ADDED)
    )


class VantageDryContact(VantageEntity[DryContact], BinarySensorEntity):
    """Representation of a Vantage dry contact."""

    @property
    def is_on(self) -> bool | None:
        """Return True if entity is on."""
        return self.obj.triggered
