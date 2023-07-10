"""Support for Vantage binary sensor entities."""

import functools

from aiovantage import Vantage
from aiovantage.config_client.objects import DryContact

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .entity import VantageEntity, async_setup_vantage_entities


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Vantage binary sensors from Config Entry."""
    vantage: Vantage = hass.data[DOMAIN][config_entry.entry_id]
    register_items = functools.partial(
        async_setup_vantage_entities, vantage, config_entry, async_add_entities
    )

    # Set up all cover entities
    register_items(vantage.dry_contacts, VantageDryContact)


class VantageDryContact(VantageEntity[DryContact], BinarySensorEntity):
    """Representation of a Vantage dry contact."""

    @property
    def is_on(self) -> bool | None:
        """Return True if entity is on."""
        return self.obj.triggered
