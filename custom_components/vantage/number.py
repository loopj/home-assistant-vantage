"""Support for Vantage number entities."""

from typing import override

from homeassistant.components.number import NumberDeviceClass, NumberEntity
from homeassistant.const import PERCENTAGE, LIGHT_LUX, UnitOfTemperature, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .config_entry import VantageConfigEntry
from .const import LOGGER
from .entity import VantageGMemEntity, add_entities_from_controller


async def async_setup_entry(
    hass: HomeAssistant,
    entry: VantageConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Vantage number entities from a config entry."""
    vantage = entry.runtime_data.client

    # Add every GMem object with a numeric data type as a number entity
    await add_entities_from_controller(
        hass,
        entry,
        async_add_entities,
        VantageGMemNumberEntity,
        vantage.gmem,
        filter=lambda obj: obj.is_int or obj.is_fixed,
    )


class VantageGMemNumberEntity(VantageGMemEntity, NumberEntity):
    """Number entity provided by a Vantage GMem object."""

    @override
    def __post_init__(self) -> None:
        match self.obj.tag.type:
            case "DeviceUnits":
                # Generic fixed-precision unsigned measurement unit
                self._attr_native_min_value = 0
                self._attr_native_max_value = 604800.0
            case "Level":
                # A percentage
                self._attr_native_min_value = 0
                self._attr_native_max_value = 100.0
                self._attr_native_unit_of_measurement = PERCENTAGE
            case "Load" | "Task":
                # Integer "pointer" to another object, via id
                self._attr_native_min_value = 1
                self._attr_native_max_value = 10000
            case "Number":
                # Generic 32-bit signed integer
                self._attr_native_min_value = -(2**31)
                self._attr_native_max_value = 2**31 - 1
            case "Delay":
                # Up to 24 hour delay, with millisecond precision
                self._attr_native_unit_of_measurement = UnitOfTime.MILLISECONDS
                self._attr_native_min_value = 0
                self._attr_native_max_value = 24 * 60 * 60 * 1000
            case "Seconds":
                # Number of seconds, up to 7 days, with millisecond precision
                self._attr_native_unit_of_measurement = UnitOfTime.SECONDS
                self._attr_native_min_value = 0.0
                self._attr_native_max_value = 7 * 24 * 60 * 60
            case "DegC":
                # Temperature in degrees Celsius
                self._attr_native_min_value = -40
                self._attr_native_max_value = 150
                self._attr_device_class = NumberDeviceClass.TEMPERATURE
                self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
            case "Footcandles":
                self._attr_native_min_value = 0
                self._attr_native_max_value = 2**31
                self._attr_native_step = (
                    0.001 * 10.7639104167
                )  # units: footcandles to lux
                self._attr_device_class = NumberDeviceClass.ILLUMINANCE
                self._attr_native_unit_of_measurement = LIGHT_LUX
            case "Decimal":
                # Generic signed decimal
                self._attr_native_min_value = -(2**31)
                self._attr_native_max_value = 2**31
                self._attr_native_step = 0.001
            case _:
                LOGGER.warning(
                    "Unknown number type %s: %s", self.obj.tag.type, self.obj
                )

    @property
    @override
    def native_value(self) -> float | None:
        if isinstance(self.obj.value, int):
            if self.obj.is_fixed:
                return self.obj.value / 1000

            return self.obj.value

        return None

    @override
    async def async_set_native_value(self, value: float) -> None:
        if self.obj.is_fixed:
            value = int(value * 1000)
        else:
            value = int(value)

        await self.async_request_call(self.obj.set_value(value))
