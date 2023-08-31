"""Support for Vantage climate entities."""
# Ignore type errors until homeassistant.components.climate is typed
# See home-assistant/core#99301
# mypy: ignore-errors

import functools
from typing import Any

from aiovantage import Vantage, VantageEvent
from aiovantage.models import Temperature, Thermostat

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
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, LOGGER
from .entity import VantageEntity, async_register_vantage_objects

# Set up the min/max temperature range for the thermostat
VANTAGE_MIN_TEMP = 5
VANTAGE_MAX_TEMP = 40

# Map Vantage enums to HA enums
VANTAGE_HVAC_MODE_MAP = {
    Thermostat.OperationMode.HEAT: HVACMode.HEAT,
    Thermostat.OperationMode.COOL: HVACMode.COOL,
    Thermostat.OperationMode.AUTO: HVACMode.HEAT_COOL,
    Thermostat.OperationMode.OFF: HVACMode.OFF,
}

VANTAGE_HVAC_ACTION_MAP = {
    Thermostat.Status.HEATING: HVACAction.HEATING,
    Thermostat.Status.COOLING: HVACAction.COOLING,
    Thermostat.Status.OFF: HVACAction.OFF,
}

VANTAGE_FAN_MODE_MAP = {
    Thermostat.FanMode.OFF: FAN_AUTO,
    Thermostat.FanMode.ON: FAN_ON,
}


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up Vantage cover entities from config entry."""
    vantage: Vantage = hass.data[DOMAIN][entry.entry_id]
    register_items = functools.partial(
        async_register_vantage_objects, hass, entry, async_add_entities
    )

    # Set up all climate entities
    register_items(vantage.thermostats, VantageClimate)


class VantageClimate(VantageEntity[Thermostat], ClimateEntity):
    """Vantage blind cover entity."""

    _attr_max_temp = VANTAGE_MAX_TEMP
    _attr_min_temp = VANTAGE_MIN_TEMP
    _attr_temperature_unit = UnitOfTemperature.CELSIUS

    def __post_init__(self) -> None:
        """Initialize a Vantage Cover."""

        # Look up the sensors attached to this thermostat
        self.sensors = self.client.thermostats.sensors(self.obj.id)
        self.temperature = self.sensors.get(setpoint=None)
        self.cool_setpoint = self.sensors.get(setpoint=Temperature.Setpoint.COOL)
        self.heat_setpoint = self.sensors.get(setpoint=Temperature.Setpoint.HEAT)

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

    async def async_added_to_hass(self) -> None:
        """Register callbacks."""
        await super().async_added_to_hass()

        # Register a callback for when the temperature sensors are updated
        self.async_on_remove(
            self.client.temperature_sensors.subscribe(
                lambda e, o, d: self.async_write_ha_state(),
                (obj.id for obj in self.sensors),
                VantageEvent.OBJECT_UPDATED,
            )
        )

    @property
    def current_temperature(self) -> float | None:
        """Return the current temperature."""
        if self.temperature is None or self.temperature.value is None:
            return None

        return float(self.temperature.value)

    @property
    def target_temperature(self) -> float | None:
        """Return the temperature we try to reach."""
        if self.hvac_mode == HVACMode.HEAT:
            return self._heat_setpoint_value
        if self.hvac_mode == HVACMode.COOL:
            return self._cool_setpoint_value

        return None

    @property
    def target_temperature_high(self) -> float | None:
        """Return the highbound target temperature we try to reach."""
        if self.hvac_mode != HVACMode.HEAT_COOL:
            return None

        return self._cool_setpoint_value

    @property
    def target_temperature_low(self) -> float | None:
        """Return the lowbound target temperature we try to reach."""
        if self.hvac_mode != HVACMode.HEAT_COOL:
            return None

        return self._heat_setpoint_value

    @property
    def hvac_mode(self) -> HVACMode | None:
        """Return current HVAC mode."""
        if self.obj.operation_mode is None:
            return None

        return VANTAGE_HVAC_MODE_MAP.get(self.obj.operation_mode)

    @property
    def fan_mode(self) -> str | None:
        """Return the fan setting."""
        if self.obj.fan_mode is None:
            return None

        return VANTAGE_FAN_MODE_MAP.get(self.obj.fan_mode)

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set new target hvac mode."""
        vantage_hvac_mode = next(
            (key for key, val in VANTAGE_HVAC_MODE_MAP.items() if val == hvac_mode),
            None,
        )

        if vantage_hvac_mode is None:
            LOGGER.error("Invalid mode for async_set_hvac_mode: %s", hvac_mode)
            return

        await self.client.thermostats.set_operation_mode(self.obj.id, vantage_hvac_mode)

    async def async_set_fan_mode(self, fan_mode: str) -> None:
        """Set new target fan mode."""
        vantage_fan_mode = next(
            (key for key, val in VANTAGE_FAN_MODE_MAP.items() if val == fan_mode),
            None,
        )

        if vantage_fan_mode is None:
            LOGGER.error("Invalid mode for async_set_fan_mode: %s", fan_mode)
            return

        await self.client.thermostats.set_fan_mode(self.obj.id, vantage_fan_mode)

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set new target temperature."""
        low_temp = kwargs.get(ATTR_TARGET_TEMP_LOW)
        high_temp = kwargs.get(ATTR_TARGET_TEMP_HIGH)
        temp = kwargs.get(ATTR_TEMPERATURE)

        if self.hvac_mode == HVACMode.HEAT_COOL and low_temp and high_temp:
            await self.client.thermostats.set_cool_set_point(self.obj.id, high_temp)
            await self.client.thermostats.set_heat_set_point(self.obj.id, low_temp)
        elif self.hvac_mode == HVACMode.HEAT and temp:
            await self.client.thermostats.set_heat_set_point(self.obj.id, temp)
        elif self.hvac_mode == HVACMode.COOL and temp:
            await self.client.thermostats.set_cool_set_point(self.obj.id, temp)
        else:
            LOGGER.error("Invalid arguments for async_set_temperature in %s", kwargs)

    @property
    def _cool_setpoint_value(self) -> float | None:
        # Return the current cool setpoint value.
        if self.cool_setpoint is None or self.cool_setpoint.value is None:
            return None

        return float(self.cool_setpoint.value)

    @property
    def _heat_setpoint_value(self) -> float | None:
        # Return the current heat setpoint value.
        if self.heat_setpoint is None or self.heat_setpoint.value is None:
            return None

        return float(self.heat_setpoint.value)
