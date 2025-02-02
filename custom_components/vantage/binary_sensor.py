"""Support for Vantage binary sensor entities."""

from functools import partial

from aiovantage.objects import DryContact

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .config_entry import VantageConfigEntry
from .entity import VantageEntity, async_register_vantage_objects


async def async_setup_entry(
    hass: HomeAssistant,
    entry: VantageConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Vantage binary sensor entities from a config entry."""
    vantage = entry.runtime_data.client
    register_items = partial(
        async_register_vantage_objects, hass, entry, async_add_entities
    )

    # Set up all cover entities
    register_items(vantage.dry_contacts, VantageDryContact)


class VantageDryContact(VantageEntity[DryContact], BinarySensorEntity):
    """Vantage dry contact binary sensor entity."""

    def __post_init__(self) -> None:
        """Initialize a Vantage dry contact."""
        # If this is a thermostat contact, attach it to the thermostat device
        if parent := self.client.thermostats.get(self.obj.parent.id):
            self.parent_obj = parent

    @property
    def is_on(self) -> bool | None:
        """Return True if entity is on."""
        return self.obj.triggered
