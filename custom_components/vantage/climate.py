"""Support for Vantage climate entities."""

from typing import Any, override

from aiovantage.controllers import ThermostatTypes, StatusType
from aiovantage.events import ObjectUpdated
from aiovantage.object_interfaces import FanInterface, ThermostatInterface
from aiovantage.objects import Temperature, Thermostat

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
from .entity import VantageEntity, add_entities_from_controller

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
    await add_entities_from_controller(
        hass, entry, async_add_entities, VantageClimateEntity, vantage.thermostats
    )


class VantageClimateEntity(VantageEntity[ThermostatTypes], ClimateEntity):
    """Climate sensor entity provided by a Vantage thermostat."""

    _attr_max_temp = VANTAGE_MAX_TEMP
    _attr_min_temp = VANTAGE_MIN_TEMP
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_supported_features = (
        ClimateEntityFeature.FAN_MODE
        | ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.TARGET_TEMPERATURE_RANGE
    )

    _legacy_status_handling: bool = False

    @override
    async def async_init(self):
        self._attr_fan_modes = []
        self._attr_hvac_modes = []

        # Populate supported fan modes
        if isinstance(self.obj, FanInterface):
            for speed in await self.obj.get_supported_enum_values(
                FanInterface, FanInterface.FanSpeed
            ):
                if speed in VANTAGE_FAN_SPEED_TO_HA_FAN_MODE:
                    self._attr_fan_modes.append(VANTAGE_FAN_SPEED_TO_HA_FAN_MODE[speed])
        else:
            for mode in await self.obj.get_supported_enum_values(
                ThermostatInterface, ThermostatInterface.FanMode
            ):
                if mode in VANTAGE_FAN_MODE_TO_HA_FAN_MODE:
                    self._attr_fan_modes.append(VANTAGE_FAN_MODE_TO_HA_FAN_MODE[mode])

        # Populate supported HVAC modes
        for mode in await self.obj.get_supported_enum_values(
            ThermostatInterface, ThermostatInterface.OperationMode
        ):
            if mode in VANTAGE_OPERATION_MODE_TO_HA_HVAC_MODE:
                self._attr_hvac_modes.append(
                    VANTAGE_OPERATION_MODE_TO_HA_HVAC_MODE[mode]
                )

        # Setup legacy status sensors
        # This is only required for 2.x firmware versions, where status updates for
        # thermostats are provided by separate temperature sensors.
        if self.client.thermostats.status_type == StatusType.CATEGORY and isinstance(
            self.obj, Thermostat
        ):
            self._legacy_status_handling = True

            # Look up the sensors attached to this thermostat
            self._indoor_temperature_sensor = self.client.temperatures.get(
                lambda obj: obj.parent.vid == self.obj.vid and obj.parent.position == 1
            )

            self._cool_setpoint_sensor = self.client.temperatures.get(
                lambda obj: obj.parent.vid == self.obj.vid and obj.parent.position == 3
            )

            self._heat_setpoint_sensor = self.client.temperatures.get(
                lambda obj: obj.parent.vid == self.obj.vid and obj.parent.position == 4
            )

    @override
    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()

        # Setup legacy status callbacks
        if self._legacy_status_handling:
            sensor_ids = [
                obj.vid
                for obj in [
                    self._indoor_temperature_sensor,
                    self._cool_setpoint_sensor,
                    self._heat_setpoint_sensor,
                ]
                if obj is not None
            ]

            def on_temperature_updated(event: ObjectUpdated[Temperature]) -> None:
                if event.obj.vid in sensor_ids:
                    self.async_write_ha_state()

            self.async_on_remove(
                self.client.temperatures.subscribe(
                    ObjectUpdated, on_temperature_updated
                )
            )

    @property
    @override
    def current_temperature(self) -> float | None:
        return self._get_indoor_temperature()

    @property
    @override
    def target_temperature(self) -> float | None:
        if self.hvac_mode == HVACMode.HEAT:
            return self._get_heat_set_point()

        if self.hvac_mode == HVACMode.COOL:
            return self._get_cool_set_point()

        return None

    @property
    @override
    def target_temperature_high(self) -> float | None:
        if self.hvac_mode != HVACMode.HEAT_COOL:
            return None

        return self._get_cool_set_point()

    @property
    @override
    def target_temperature_low(self) -> float | None:
        if self.hvac_mode != HVACMode.HEAT_COOL:
            return None

        return self._get_heat_set_point()

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

    def _get_indoor_temperature(self) -> float | None:
        if self.obj.indoor_temperature is not None:
            return float(self.obj.indoor_temperature)

        # Legacy status handling for older firmware versions
        if (
            self._indoor_temperature_sensor is not None
            and self._indoor_temperature_sensor.value is not None
        ):
            return float(self._indoor_temperature_sensor.value)

        return

    def _get_cool_set_point(self) -> float | None:
        if self.obj.cool_set_point is not None:
            return float(self.obj.cool_set_point)

        # Legacy status handling for older firmware versions
        if (
            self._cool_setpoint_sensor is not None
            and self._cool_setpoint_sensor.value is not None
        ):
            return float(self._cool_setpoint_sensor.value)

        return None

    def _get_heat_set_point(self) -> float | None:
        if self.obj.heat_set_point is not None:
            return float(self.obj.heat_set_point)

        # Legacy status handling for older firmware versions
        if (
            self._heat_setpoint_sensor is not None
            and self._heat_setpoint_sensor.value is not None
        ):
            return float(self._heat_setpoint_sensor.value)

        return None
