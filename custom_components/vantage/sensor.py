"""Support for Vantage sensor entities."""

import contextlib
from decimal import Decimal
import socket
from typing import override

from aiovantage.controllers import Controller
from aiovantage.objects import AnemoSensor, LightSensor, Master, OmniSensor, Temperature

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.const import (
    LIGHT_LUX,
    EntityCategory,
    UnitOfElectricCurrent,
    UnitOfPower,
    UnitOfSpeed,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .config_entry import VantageConfigEntry
from .entity import VantageEntity, add_entities_from_controller

FOOT_CANDLES_TO_LUX = 10.7639

OMNISENSOR_ENTITY_DESCRIPTIONS = {
    "Current": SensorEntityDescription(
        key="Current",
        device_class=SensorDeviceClass.CURRENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
    ),
    "Power": SensorEntityDescription(
        key="Power",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
    ),
    "Temperature": SensorEntityDescription(
        key="Temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
    ),
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: VantageConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Vantage sensor entities from a config entry."""
    vantage = entry.runtime_data.client

    # Add all temperature objects as sensor entities
    add_entities_from_controller(
        entry, async_add_entities, VantageTempSensorEntity, vantage.temperatures
    )

    # Add all anemo sensor objects as sensor entities
    add_entities_from_controller(
        entry, async_add_entities, VantageAnemoSensorEntity, vantage.anemo_sensors
    )

    # Add all light sensor objects as sensor entities
    add_entities_from_controller(
        entry, async_add_entities, VantageLightSensorEntity, vantage.light_sensors
    )

    # Add all omni sensor objects as sensor entities
    add_entities_from_controller(
        entry, async_add_entities, VantageOmniSensorEntity, vantage.omni_sensors
    )

    # Add all master IP addresses as sensor entities
    add_entities_from_controller(
        entry, async_add_entities, VantageMasterIPSensorEntity, vantage.masters
    )


class VantageTempSensorEntity(VantageEntity[Temperature], SensorEntity):
    """Vantage temperature sensor entity."""

    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_state_class = "measurement"
    _attr_suggested_display_precision = 1

    def __init__(
        self,
        entry: VantageConfigEntry,
        controller: Controller[Temperature],
        obj: Temperature,
    ):
        """Initialize a Vantage temperature sensor."""
        super().__init__(entry, controller, obj)

        # If this is a thermostat temperature sensor, attach it to the thermostat device
        if parent := self.client.thermostats.get(self.obj.parent.vid):
            self.parent_obj = parent

    @property
    @override
    def native_value(self) -> Decimal | None:
        return self.obj.value


class VantageAnemoSensorEntity(VantageEntity[AnemoSensor], SensorEntity):
    """Vantage wind sensor entity."""

    _attr_device_class = SensorDeviceClass.WIND_SPEED
    _attr_native_unit_of_measurement = UnitOfSpeed.MILES_PER_HOUR
    _attr_should_poll = True
    _attr_state_class = "measurement"

    @property
    def native_value(self) -> Decimal | None:
        """Return the value reported by the sensor."""
        return self.obj.speed


class VantageLightSensorEntity(VantageEntity[LightSensor], SensorEntity):
    """Vantage light sensor entity."""

    _attr_device_class = SensorDeviceClass.ILLUMINANCE
    _attr_native_unit_of_measurement = LIGHT_LUX
    _attr_should_poll = True
    _attr_state_class = "measurement"

    @property
    def native_value(self) -> float | None:
        """Return the value reported by the sensor."""
        if self.obj.level is None:
            return None

        return float(self.obj.level) * FOOT_CANDLES_TO_LUX


class VantageOmniSensorEntity(VantageEntity[OmniSensor], SensorEntity):
    """Vantage omni sensor entity."""

    _attr_should_poll = True
    _attr_state_class = "measurement"

    def __init__(
        self,
        entry: VantageConfigEntry,
        controller: Controller[OmniSensor],
        obj: OmniSensor,
    ):
        """Initialize a Vantage omnisensor."""
        super().__init__(entry, controller, obj)

        # Set the entity description based on the OmniSensor model
        if obj.model in OMNISENSOR_ENTITY_DESCRIPTIONS:
            self.entity_description = OMNISENSOR_ENTITY_DESCRIPTIONS[obj.model]

        # If this is a module omnisensor, attach it to the module device and disable by default
        if parent := self.client.modules.get(self.obj.parent.vid):
            self.parent_obj = parent
            self._attr_entity_registry_enabled_default = False

    @property
    @override
    def native_value(self) -> int | Decimal | None:
        return self.obj.level


class VantageMasterIPSensorEntity(VantageEntity[Master], SensorEntity):
    """Vantage controller IP address sensor entity."""

    _attr_icon = "mdi:ip"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    @override
    def unique_id(self) -> str:
        return f"{self.obj.vid}:ip_address"

    @property
    @override
    def native_value(self) -> str | None:
        with contextlib.suppress(socket.gaierror):
            return socket.gethostbyname(self.client.host)

        return None
