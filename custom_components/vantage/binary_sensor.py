"""Support for Vantage binary sensor entities."""

from typing import override

from aiovantage.controllers import Controller
from aiovantage.events import Connected, Disconnected, Reconnected
from aiovantage.objects import DryContact, Master

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.const import EntityCategory
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

    # Add a connectivity binary sensor for each controller
    add_entities_from_controller(
        entry, async_add_entities, VantageControllerConnectivityEntity, vantage.masters
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


class VantageControllerConnectivityEntity(VantageEntity[Master], BinarySensorEntity):
    """Binary sensor reflecting the live connection to a Vantage controller.

    Unlike the per-object entities, this sensor stays available and reports `off`
    while the controller is unreachable, giving a single reliable signal that does
    not depend on individual object polls failing one by one.
    """

    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    # Override the base "vantage" translation key so the name comes from the
    # connectivity device class ("Connectivity").
    _attr_translation_key = None

    # Setup only completes after a successful initialize(), so the event stream is
    # connected at this point. Connection events keep this in sync afterwards.
    _attr_is_on = True

    @property
    @override
    def unique_id(self) -> str:
        return f"{self.obj.vid}:connectivity"

    @property
    @override
    def is_on(self) -> bool | None:
        return self._attr_is_on

    @override
    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()

        event_stream = self.client.event_stream

        def set_connected(_event: Connected | Reconnected) -> None:
            self._attr_is_on = True
            self.async_write_ha_state()

        def set_disconnected(_event: Disconnected) -> None:
            self._attr_is_on = False
            self.async_write_ha_state()

        self.async_on_remove(event_stream.subscribe(Connected, set_connected))
        self.async_on_remove(event_stream.subscribe(Reconnected, set_connected))
        self.async_on_remove(event_stream.subscribe(Disconnected, set_disconnected))
