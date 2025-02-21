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
from .const import LOGGER, FAN_MAX
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
    FanInterface.FanSpeed.Max: FAN_MAX,
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

    if vantage.thermostats.status_type == StatusType.OBJECT:
        # If we are using "object" status updates, add every thermostat as a climate
        # entity. This is the default behavior for newer firmware versions (3.x+).
        add_entities_from_controller(
            entry, async_add_entities, VantageClimateEntity, vantage.thermostats
        )
    else:
        # If we are using "category" status updates, add only "Thermostat" objects
        # as legacy climate entities. This is for compatibility with older firmware
        # versions (2.x) where status updates for temperatures are only provided by
        # the "child" Temperature objects.
        add_entities_from_controller(
            entry,
            async_add_entities,
            VantageLegacyClimateEntity,
            vantage.thermostats,
            filter=lambda obj: isinstance(obj, Thermostat),
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
        | ClimateEntityFeature.TURN_OFF
        | ClimateEntityFeature.TURN_ON
    )

    _fan_modes: list[ThermostatInterface.FanMode] | None = None
    _fan_speeds: list[FanInterface.FanSpeed] | None = None
    _operation_modes: list[ThermostatInterface.OperationMode] | None = None

    @override
    async def async_added_to_hass(self):
        await super().async_added_to_hass()

        # Fetch supported fan modes/speeds
        if isinstance(self.obj, FanInterface):
            self._fan_speeds = await self.obj.get_supported_enum_values(
                FanInterface, FanInterface.FanSpeed
            )
        else:
            self._fan_modes = await self.obj.get_supported_enum_values(
                ThermostatInterface, ThermostatInterface.FanMode
            )

        # Fetch supported operation modes
        self._operation_modes = await self.obj.get_supported_enum_values(
            ThermostatInterface, ThermostatInterface.OperationMode
        )

    @property
    @override
    def current_temperature(self) -> float | None:
        if self.obj.indoor_temperature is not None:
            return float(self.obj.indoor_temperature)

        return None

    @property
    @override
    def fan_mode(self) -> str | None:
        if isinstance(self.obj, FanInterface):
            if self.obj.speed is not None:
                return VANTAGE_FAN_SPEED_TO_HA_FAN_MODE.get(self.obj.speed)
        else:
            if self.obj.fan_mode is not None:
                return VANTAGE_FAN_MODE_TO_HA_FAN_MODE.get(self.obj.fan_mode)

        return None

    @property
    @override
    def fan_modes(self) -> list[str] | None:
        if isinstance(self.obj, FanInterface):
            if self._fan_speeds:
                return [
                    fan_speed
                    for speed in self._fan_speeds
                    if (fan_speed := VANTAGE_FAN_SPEED_TO_HA_FAN_MODE.get(speed))
                    is not None
                ]
        else:
            if self._fan_modes:
                return [
                    fan_mode
                    for mode in self._fan_modes
                    if (fan_mode := VANTAGE_FAN_MODE_TO_HA_FAN_MODE.get(mode))
                    is not None
                ]

        return None

    @property
    @override
    def hvac_action(self) -> HVACAction | None:
        if self.obj.status is None:
            return None

        return VANTAGE_STATUS_TO_HA_HVAC_ACTION.get(self.obj.status)

    @property
    @override
    def hvac_mode(self) -> HVACMode | None:
        if self.obj.operation_mode is None:
            return None

        return VANTAGE_OPERATION_MODE_TO_HA_HVAC_MODE.get(self.obj.operation_mode)

    @property
    @override
    def hvac_modes(self) -> list[HVACMode] | None:
        if self._operation_modes is None:
            return None

        return [
            hvac_mode
            for mode in self._operation_modes
            if (hvac_mode := VANTAGE_OPERATION_MODE_TO_HA_HVAC_MODE.get(mode))
            is not None
        ]

    @property
    @override
    def target_temperature(self) -> float | None:
        if self.hvac_mode == HVACMode.HEAT:
            if self.obj.heat_set_point is not None:
                return float(self.obj.heat_set_point)

        if self.hvac_mode == HVACMode.COOL:
            if self.obj.cool_set_point is not None:
                return float(self.obj.cool_set_point)

        return None

    @property
    @override
    def target_temperature_high(self) -> float | None:
        if self.hvac_mode != HVACMode.HEAT_COOL:
            return None

        if self.obj.cool_set_point is not None:
            return float(self.obj.cool_set_point)

        return None

    @property
    @override
    def target_temperature_low(self) -> float | None:
        if self.hvac_mode != HVACMode.HEAT_COOL:
            return None

        if self.obj.heat_set_point is not None:
            return float(self.obj.heat_set_point)

        return None

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


class VantageLegacyClimateEntity(VantageClimateEntity):
    """Climate sensor entity provided by a legacy Vantage thermostat.

    This is a compatibility layer for older firmware versions (2.x) where status
    updates for temperatures (indoor, heat setpoint, cool setpoint) are provided by
    separate "child" Temperature objects.
    """

    @override
    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()

        # Lookup child sensors
        sensors = self.client.temperatures.filter(
            lambda obj: obj.parent.vid == self.obj.vid
        )

        # NOTE: The "position" lookup here is specific to "Thermostat" objects
        indoor_temperature = sensors.get(lambda obj: obj.parent.position == 1)
        cool_setpoint = sensors.get(lambda obj: obj.parent.position == 3)
        heat_setpoint = sensors.get(lambda obj: obj.parent.position == 4)

        # Subscribe to updates for child sensors
        def on_temperature_updated(event: ObjectUpdated[Temperature]) -> None:
            if indoor_temperature and event.obj.vid == indoor_temperature.vid:
                self.obj.indoor_temperature = event.obj.value
                self.async_write_ha_state()

            if cool_setpoint and event.obj.vid == cool_setpoint.vid:
                self.obj.cool_set_point = event.obj.value
                self.async_write_ha_state()

            if heat_setpoint and event.obj.vid == heat_setpoint.vid:
                self.obj.heat_set_point = event.obj.value
                self.async_write_ha_state()

        self.async_on_remove(
            self.client.temperatures.subscribe(ObjectUpdated, on_temperature_updated)
        )
