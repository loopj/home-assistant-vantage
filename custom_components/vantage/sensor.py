"""Support for Vantage sensor entities."""

import contextlib
from datetime import date, datetime
from decimal import Decimal
import functools
import socket

from aiovantage import Vantage
from aiovantage.config_client.objects import Master, OmniSensor

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
from .entity import VantageEntity, async_setup_vantage_entities


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Vantage sensors from Config Entry."""
    vantage: Vantage = hass.data[DOMAIN][config_entry.entry_id]
    register_items = functools.partial(
        async_setup_vantage_entities, vantage, config_entry, async_add_entities
    )

    # Register all sensor entities
    register_items(vantage.omni_sensors, VantageOmniSensor)
    register_items(vantage.masters, VantageMasterSerial)
    register_items(vantage.masters, VantageMasterIP)


class VantageOmniSensor(VantageEntity[OmniSensor], SensorEntity):
    """Representation of a Vantage OmniSensor."""

    _attr_should_poll = True
    _attr_state_class = "measurement"

    def __post_init__(self) -> None:
        """Initialize a Vantage omnisensor."""
        # If this is a module omnisensor, attach it to the module device
        if self.client.modules.get(self.obj.parent_id) is not None:
            self._attr_name = self.obj.name
            self._device_id = str(self.obj.parent_id)
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
    """Representation of a Vantage master serial number."""

    _attr_icon = "mdi:barcode"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_name = "Serial Number"

    def __post_init__(self) -> None:
        """Initialize a Vantage master serial number."""
        self._device_id = str(self.obj.id)
        self._attr_unique_id = f"{self.obj.id}_serial_number"
        self._attr_native_value = str(self.obj.serial_number)


class VantageMasterIP(VantageEntity[Master], SensorEntity):
    """Representation of a Vantage master IP address."""

    _attr_icon = "mdi:ip"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_name = "IP Address"

    def __post_init__(self) -> None:
        """Initialize a Vantage master IP address."""
        self._device_id = str(self.obj.id)
        self._attr_unique_id = f"{self.obj.id}_ip_address"

        with contextlib.suppress(socket.gaierror):
            self._attr_native_value = socket.gethostbyname(self.client.host)
