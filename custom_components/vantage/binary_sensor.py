"""Support for Vantage binary sensor entities."""

from typing import override

from aiovantage.controllers import Controller
from aiovantage.objects import DryContact

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .config_entry import VantageConfigEntry
from .entity import VantageEntity, add_entities_from_controller


async def async_setup_entry(
    hass: HomeAssistant,
    entry: VantageConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Vantage binary sensor entities from a config entry."""
    vantage = entry.runtime_data.client

    # Add every dry contact as a binary sensor entity
    add_entities_from_controller(
        entry, async_add_entities, VantageBinarySensorEntity, vantage.dry_contacts
    )


class VantageBinarySensorEntity(VantageEntity[DryContact], BinarySensorEntity):
    """Binary sensor entity provided by a Vantage DryContact object."""

    def __init__(
        self,
        entry: VantageConfigEntry,
        controller: Controller[DryContact],
        obj: DryContact,
    ):
        """Initialize a Vantage binary sensor entity."""
        super().__init__(entry, controller, obj)

        # If this is a thermostat contact, attach it to the thermostat device
        if parent := self.client.thermostats.get(self.obj.parent.vid):
            self.parent_obj = parent

    @property
    @override
    def is_on(self) -> bool | None:
        return self.obj.is_down
