"""Support for Vantage climate entities."""

from typing import Any, override

from aiovantage.controllers import ThermostatTypes
from aiovantage.events import ObjectUpdated
from aiovantage.objects import Temperature, Thermostat

from homeassistant.components.climate import (
    ATTR_TARGET_TEMP_HIGH,
    ATTR_TARGET_TEMP_LOW,
    FAN_AUTO,
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

# Map Vantage enums to HA enums
VANTAGE_HVAC_MODE_MAP = {
    Thermostat.OperationMode.Heat: HVACMode.HEAT,
    Thermostat.OperationMode.Cool: HVACMode.COOL,
    Thermostat.OperationMode.Auto: HVACMode.HEAT_COOL,
    Thermostat.OperationMode.Off: HVACMode.OFF,
}

VANTAGE_HVAC_ACTION_MAP = {
    Thermostat.Status.Heating: HVACAction.HEATING,
    Thermostat.Status.Cooling: HVACAction.COOLING,
    Thermostat.Status.Off: HVACAction.OFF,
}

VANTAGE_FAN_MODE_MAP = {
    Thermostat.FanMode.Off: FAN_AUTO,
    Thermostat.FanMode.On: FAN_ON,
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

        return VANTAGE_HVAC_MODE_MAP.get(self.obj.operation_mode)

    @property
    @override
    def fan_mode(self) -> str | None:
        if self.obj.fan_mode is None:
            return None

        return VANTAGE_FAN_MODE_MAP.get(self.obj.fan_mode)

    @override
    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        vantage_hvac_mode = next(
            (key for key, val in VANTAGE_HVAC_MODE_MAP.items() if val == hvac_mode),
            None,
        )

        if vantage_hvac_mode is None:
            LOGGER.error("Invalid mode for async_set_hvac_mode: %s", hvac_mode)
            return

        await self.async_request_call(self.obj.set_operation_mode(vantage_hvac_mode))

    @override
    async def async_set_fan_mode(self, fan_mode: str) -> None:
        vantage_fan_mode = next(
            (key for key, val in VANTAGE_FAN_MODE_MAP.items() if val == fan_mode),
            None,
        )

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
