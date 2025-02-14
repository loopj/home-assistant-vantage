"""Support for Vantage climate entities."""

from typing import Any, override

from aiovantage.controllers import ThermostatTypes
from aiovantage.events import ObjectUpdated
from aiovantage.object_interfaces import FanInterface, ThermostatInterface
from aiovantage.objects import Temperature

from homeassistant.components.climate import (
    ATTR_TARGET_TEMP_HIGH,
    ATTR_TARGET_TEMP_LOW,
    FAN_AUTO,
    FAN_HIGH,
    FAN_LOW,
    FAN_MEDIUM,
    FAN_OFF,
    FAN_ON,
    ClimateEntity,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .config_entry import VantageConfigEntry
from .const import LOGGER
from .entity import VantageEntity

# Set up the min/max temperature range for the thermostat
VANTAGE_MIN_TEMP = 5
VANTAGE_MAX_TEMP = 40

# Mappings for ThermostatInterface.OperationMode <-> HA HVAC modes
VANTAGE_OPERATION_MODE_TO_HA_HVAC_MODE = {
    ThermostatInterface.OperationMode.Heat: HVACMode.HEAT,
    ThermostatInterface.OperationMode.Cool: HVACMode.COOL,
    ThermostatInterface.OperationMode.Auto: HVACMode.HEAT_COOL,
    ThermostatInterface.OperationMode.Off: HVACMode.OFF,
}

HA_HVAC_MODE_TO_VANTAGE_OPERATION_MODE = {
    v: k for k, v in VANTAGE_OPERATION_MODE_TO_HA_HVAC_MODE.items()
}

# Mappings for ThermostatInterface.Status <-> HA HVAC actions
VANTAGE_STATUS_TO_HA_HVAC_ACTION = {
    ThermostatInterface.Status.Heating: HVACAction.HEATING,
    ThermostatInterface.Status.Cooling: HVACAction.COOLING,
    ThermostatInterface.Status.Off: HVACAction.OFF,
}

HA_HVAC_ACTION_TO_VANTAGE_STATUS = {
    v: k for k, v in VANTAGE_STATUS_TO_HA_HVAC_ACTION.items()
}

# Mappings for ThermostatInterface.FanMode <-> HA fan modes
VANTAGE_FAN_MODE_TO_HA_FAN_MODE = {
    ThermostatInterface.FanMode.Off: FAN_AUTO,
    ThermostatInterface.FanMode.On: FAN_ON,
}

HA_FAN_MODE_TO_VANTAGE_FAN_MODE = {
    v: k for k, v in VANTAGE_FAN_MODE_TO_HA_FAN_MODE.items()
}

# Mappings for FanInterface.FanSpeed <-> HA fan modes
VANTAGE_FAN_SPEED_TO_HA_FAN_MODE = {
    FanInterface.FanSpeed.Off: FAN_OFF,
    FanInterface.FanSpeed.Low: FAN_LOW,
    FanInterface.FanSpeed.Medium: FAN_MEDIUM,
    FanInterface.FanSpeed.High: FAN_HIGH,
    FanInterface.FanSpeed.Max: "max",
    FanInterface.FanSpeed.Auto: FAN_AUTO,
}

HA_FAN_MODE_TO_VANTAGE_FAN_SPEED = {
    v: k for k, v in VANTAGE_FAN_SPEED_TO_HA_FAN_MODE.items()
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: VantageConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Vantage climate entities from a config entry."""
    vantage = entry.runtime_data.client

    # Add every thermostat as a climate entity
    VantageClimateEntity.add_entities(entry, async_add_entities, vantage.thermostats)


class VantageClimateEntity(VantageEntity[ThermostatTypes], ClimateEntity):
    """Climate sensor entity provided by a Vantage thermostat."""

    _attr_max_temp = VANTAGE_MAX_TEMP
    _attr_min_temp = VANTAGE_MIN_TEMP
    _attr_temperature_unit = UnitOfTemperature.CELSIUS

    @override
    def __post_init__(self) -> None:
        # Look up the sensors attached to this thermostat
        sensors = self.client.temperatures.filter(
            lambda obj: obj.parent.vid == self.obj.vid
        )

        self.indoor_temperature = sensors.get(lambda obj: obj.parent.position == 1)
        self.cool_setpoint = sensors.get(lambda obj: obj.parent.position == 3)
        self.heat_setpoint = sensors.get(lambda obj: obj.parent.position == 4)

        # Set up the entity attributes
        self._attr_supported_features = (
            ClimateEntityFeature.FAN_MODE
            | ClimateEntityFeature.TARGET_TEMPERATURE
            | ClimateEntityFeature.TARGET_TEMPERATURE_RANGE
        )

        self._attr_fan_modes = [
            FAN_AUTO,
            FAN_ON,
        ]

        self._attr_hvac_modes = [
            HVACMode.HEAT_COOL,
            HVACMode.COOL,
            HVACMode.HEAT,
            HVACMode.OFF,
        ]

    @override
    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()

        # Register a callback for when thermostat temperature sensors are updated
        sensor_ids = [
            obj.vid
            for obj in [self.indoor_temperature, self.cool_setpoint, self.heat_setpoint]
            if obj is not None
        ]

        def on_temperature_updated(event: ObjectUpdated[Temperature]) -> None:
            if event.obj.vid in sensor_ids:
                self.async_write_ha_state()

        self.async_on_remove(
            self.client.temperatures.subscribe(ObjectUpdated, on_temperature_updated)
        )

    @property
    @override
    def current_temperature(self) -> float | None:
        if self.indoor_temperature is None or self.indoor_temperature.value is None:
            return None

        return float(self.indoor_temperature.value)

    @property
    @override
    def target_temperature(self) -> float | None:
        if self.hvac_mode == HVACMode.HEAT:
            if self.heat_setpoint is not None and self.heat_setpoint.value is not None:
                return float(self.heat_setpoint.value)

        if self.hvac_mode == HVACMode.COOL:
            if self.cool_setpoint is not None and self.cool_setpoint.value is not None:
                return float(self.cool_setpoint.value)

        return None

    @property
    @override
    def target_temperature_high(self) -> float | None:
        if self.hvac_mode != HVACMode.HEAT_COOL:
            return None

        if self.cool_setpoint is None or self.cool_setpoint.value is None:
            return None

        return float(self.cool_setpoint.value)

    @property
    @override
    def target_temperature_low(self) -> float | None:
        if self.hvac_mode != HVACMode.HEAT_COOL:
            return None

        if self.heat_setpoint is None or self.heat_setpoint.value is None:
            return None

        return float(self.heat_setpoint.value)

    @property
    @override
    def hvac_mode(self) -> HVACMode | None:
        if self.obj.operation_mode is None:
            return None

        return VANTAGE_OPERATION_MODE_TO_HA_HVAC_MODE.get(self.obj.operation_mode)

    @property
    @override
    def fan_mode(self) -> str | None:
        if self.obj.fan_mode is None:
            return None

        return VANTAGE_FAN_MODE_TO_HA_FAN_MODE.get(self.obj.fan_mode)

    @override
    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        vantage_hvac_mode = HA_HVAC_MODE_TO_VANTAGE_OPERATION_MODE.get(hvac_mode)
        if vantage_hvac_mode is None:
            LOGGER.error("Invalid mode for async_set_hvac_mode: %s", hvac_mode)
            return

        await self.async_request_call(self.obj.set_operation_mode(vantage_hvac_mode))

    @override
    async def async_set_fan_mode(self, fan_mode: str) -> None:
        vantage_fan_mode = HA_FAN_MODE_TO_VANTAGE_FAN_MODE.get(fan_mode)
        if vantage_fan_mode is None:
            LOGGER.error("Invalid mode for async_set_fan_mode: %s", fan_mode)
            return

        await self.async_request_call(self.obj.set_fan_mode(vantage_fan_mode))

    @override
    async def async_set_temperature(self, **kwargs: Any) -> None:
        low_temp = kwargs.get(ATTR_TARGET_TEMP_LOW)
        high_temp = kwargs.get(ATTR_TARGET_TEMP_HIGH)
        temp = kwargs.get(ATTR_TEMPERATURE)

        if self.hvac_mode == HVACMode.HEAT_COOL and low_temp and high_temp:
            await self.async_request_call(self.obj.set_cool_set_point(high_temp))
            await self.async_request_call(self.obj.set_heat_set_point(low_temp))
        elif self.hvac_mode == HVACMode.HEAT and temp:
            await self.async_request_call(self.obj.set_heat_set_point(temp))
        elif self.hvac_mode == HVACMode.COOL and temp:
            await self.async_request_call(self.obj.set_cool_set_point(temp))
        else:
            LOGGER.error("Invalid arguments for async_set_temperature in %s", kwargs)
