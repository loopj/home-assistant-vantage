"""Support for Vantage sensor entities."""

import contextlib
from datetime import date, datetime
from decimal import Decimal
import functools
import socket

from aiovantage import Vantage
from aiovantage.models import Master, OmniSensor, Temperature

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    EntityCategory,
    UnitOfElectricCurrent,
    UnitOfPower,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType

from .const import DOMAIN
from .entity import VantageEntity, async_register_vantage_objects


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up Vantage sensor entities from config entry."""
    vantage: Vantage = hass.data[DOMAIN][entry.entry_id]
    register_items = functools.partial(
        async_register_vantage_objects, hass, entry, async_add_entities
    )

    # Register all sensor entities
    register_items(vantage.temperature_sensors, VantageTemperatureSensor)
    register_items(vantage.omni_sensors, VantageOmniSensor)
    register_items(vantage.masters, VantageMasterSerial)
    register_items(vantage.masters, VantageMasterIP)


class VantageTemperatureSensor(VantageEntity[Temperature], SensorEntity):
    """Vantage temperature sensory entity."""

    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_state_class = "measurement"

    def __post_init__(self) -> None:
        """Initialize a Vantage temperature sensor."""
        # If this is a thermostat temperature sensor, attach it to the thermostat device
        if parent := self.client.thermostats.get(self.obj.parent.id):
            self.parent_obj = parent

    @property
    def native_value(self) -> StateType | date | datetime | Decimal:
        """Return the value reported by the sensor."""
        return self.obj.value


class VantageOmniSensor(VantageEntity[OmniSensor], SensorEntity):
    """Vantage 'OmniSensor' sensory entity."""

    _attr_should_poll = True
    _attr_state_class = "measurement"

    def __post_init__(self) -> None:
        """Initialize a Vantage omnisensor."""
        # If this is a module omnisensor, attach it to the module device
        if parent := self.client.modules.get(self.obj.parent.id):
            self.parent_obj = parent

            # Disable module sensors by default, since they are noisy
            self._attr_entity_registry_enabled_default = False

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
    def native_value(self) -> StateType | date | datetime | Decimal:
        """Return the value reported by the sensor."""
        return self.obj.level

    async def async_update(self) -> None:
        """Update the state of the sensor."""
        await self.client.omni_sensors.get_level(self.obj.id)


class VantageMasterSerial(VantageEntity[Master], SensorEntity):
    """Vantage controller serial number sensor entity."""

    _attr_icon = "mdi:barcode"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def name(self) -> str | None:
        """Return the name of the entity."""
        return "Serial Number"

    def __post_init__(self) -> None:
        """Initialize a Vantage master serial number."""
        self._attr_unique_id = f"{self.obj.id}:serial_number"
        self._attr_native_value = str(self.obj.serial_number)


class VantageMasterIP(VantageEntity[Master], SensorEntity):
    """Vantage controller IP address sensor entity."""

    _attr_icon = "mdi:ip"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def name(self) -> str | None:
        """Return the name of the entity."""
        return "IP Address"

    def __post_init__(self) -> None:
        """Initialize a Vantage master IP address."""
        self._attr_unique_id = f"{self.obj.id}:ip_address"

        with contextlib.suppress(socket.gaierror):
            self._attr_native_value = socket.gethostbyname(self.client.host)
