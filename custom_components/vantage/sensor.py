"""Support for Vantage sensor entities.

The following Vantage objects are considered sensor entities:
- "OmniSensor" objects
"""

from datetime import date, datetime
from decimal import Decimal

from aiovantage import Vantage
from aiovantage.config_client.objects import OmniSensor
from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfElectricCurrent, UnitOfPower, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import StateType

from .const import DOMAIN
from .entity import VantageEntity


async def async_setup_entry(
    hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities
):
    """Set up Vantage sensors from Config Entry."""
    vantage: Vantage = hass.data[DOMAIN][config_entry.entry_id]

    # Expose all omnisensors
    async for omni_sensor in vantage.omni_sensors:
        entity = VantageOmniSensor(vantage, omni_sensor)
        await entity.fetch_relations()
        async_add_entities([entity])


class VantageOmniSensor(VantageEntity[OmniSensor], SensorEntity):
    """Representation of a Vantage omnisensor."""

    _attr_should_poll = True

    def __init__(self, client: Vantage, obj: OmniSensor):
        """Initialize a Vantage omnisensor."""
        super().__init__(client, client.omni_sensors, obj)

        # Set the device class and unit of measurement based on the sensor type
        if obj.is_current_sensor:
            self._attr_device_class = SensorDeviceClass.CURRENT
            self._attr_native_unit_of_measurement = UnitOfElectricCurrent.AMPERE
            self._attr_suggested_display_precision = 3
        elif obj.is_power_sensor:
            self._attr_device_class = SensorDeviceClass.POWER
            self._attr_native_unit_of_measurement = UnitOfPower.WATT
        elif obj.is_temperature_sensor:
            self._attr_device_class = SensorDeviceClass.TEMPERATURE
            self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS

    @property
    def native_value(self) -> StateType | date | datetime | Decimal:
        """Return the value reported by the sensor."""
        return self.obj.level

    async def async_update(self):
        """Update the state of the sensor."""
        await self.client.omni_sensors.get_level(self.obj.id)
