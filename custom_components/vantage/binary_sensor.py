"""Support for Vantage binary sensor entities."""

import functools

from aiovantage import Vantage
from aiovantage.models import DryContact

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .entity import VantageEntity, async_register_vantage_objects


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up Vantage binary sensor entities from a config entry."""
    vantage: Vantage = hass.data[DOMAIN][entry.entry_id]
    register_items = functools.partial(
        async_register_vantage_objects, hass, entry, async_add_entities
    )

    # Set up all cover entities
    register_items(vantage.dry_contacts, VantageDryContact)


class VantageDryContact(VantageEntity[DryContact], BinarySensorEntity):
    """Vantage dry contact binary sensor entity."""

    @property
    def is_on(self) -> bool | None:
        """Return True if entity is on."""
        return self.obj.triggered
