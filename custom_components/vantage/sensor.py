"""Support for Vantage sensor entities."""

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from aiovantage import Vantage, VantageEvent
from aiovantage.config_client.objects import OmniSensor

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    UnitOfElectricCurrent,
    UnitOfPower,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType

from .const import DOMAIN
from .entity import VantageEntity


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Vantage sensors from Config Entry."""
    vantage: Vantage = hass.data[DOMAIN][config_entry.entry_id]
    controller = vantage.omni_sensors

    @callback
    def async_add_entity(_type: VantageEvent, obj: OmniSensor, _data: Any) -> None:
        async_add_entities([VantageOmniSensor(vantage, controller, obj)])

    # Add all current sensors
    for obj in controller:
        async_add_entity(VantageEvent.OBJECT_ADDED, obj, {})

    # Register a callback for new sensors
    config_entry.async_on_unload(
        controller.subscribe(async_add_entity, event_filter=VantageEvent.OBJECT_ADDED)
    )


class VantageOmniSensor(VantageEntity[OmniSensor], SensorEntity):
    """Representation of a Vantage OmniSensor."""

    def __post_init__(self) -> None:
        """Initialize a Vantage omnisensor."""
        self._attr_should_poll = True
        self._attr_state_class = "measurement"

        # Set the device class and unit of measurement based on the sensor type
        match self.obj.model:
            case "Current":
                self._attr_device_class = SensorDeviceClass.CURRENT
                self._attr_native_unit_of_measurement = UnitOfElectricCurrent.AMPERE
                self._attr_suggested_display_precision = 3
            case "Power":
                self._attr_device_class = SensorDeviceClass.POWER
                self._attr_native_unit_of_measurement = UnitOfPower.WATT
            case "Temperature":
                self._attr_device_class = SensorDeviceClass.TEMPERATURE
                self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS

    @property
    def attach_to_device_id(self) -> int | None:
        """The id of the device this entity should be attached to, if any."""
        if self.client.modules.get(self.obj.parent_id) is not None:
            return self.obj.parent_id

        return None

    @property
    def native_value(self) -> StateType | date | datetime | Decimal:
        """Return the value reported by the sensor."""
        return self.obj.level

    async def async_update(self) -> None:
        """Update the state of the sensor."""
        await self.client.omni_sensors.get_level(self.obj.id)
