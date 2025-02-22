"""Support for Vantage number entities."""

from typing import override

from homeassistant.components.number import (
    NumberDeviceClass,
    NumberEntity,
    NumberEntityDescription,
)
from homeassistant.const import PERCENTAGE, LIGHT_LUX, UnitOfTemperature, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from aiovantage.controllers import Controller
from aiovantage.objects import GMem

from .config_entry import VantageConfigEntry
from .entity import VantageGMemEntity, add_entities_from_controller

NUMBER_ENTITY_DESCRIPTIONS: dict[str, NumberEntityDescription] = {
    # Generic fixed-precision unsigned measurement unit
    "DeviceUnits": NumberEntityDescription(
        key="DeviceUnits",
        native_min_value=0,
        native_max_value=604800.0,
    ),
    # A percentage
    "Level": NumberEntityDescription(
        key="Level",
        native_min_value=0,
        native_max_value=100.0,
        native_unit_of_measurement=PERCENTAGE,
    ),
    # Integer "pointer" to a Load object, via VID
    "Load": NumberEntityDescription(
        key="Load",
        native_min_value=1,
        native_max_value=10000,
    ),
    # Integer "pointer" to a Task object, via VID
    "Task": NumberEntityDescription(
        key="Task",
        native_min_value=1,
        native_max_value=10000,
    ),
    # Generic 32-bit signed integer
    "Number": NumberEntityDescription(
        key="Number",
        native_min_value=-(2**31),
        native_max_value=2**31 - 1,
    ),
    # Up to 24 hour delay, with millisecond precision
    "Delay": NumberEntityDescription(
        key="Delay",
        device_class=NumberDeviceClass.DURATION,
        native_min_value=0,
        native_max_value=24 * 60 * 60 * 1000,
        native_unit_of_measurement=UnitOfTime.MILLISECONDS,
    ),
    # Number of seconds, up to 7 days, with millisecond precision
    "Seconds": NumberEntityDescription(
        key="Seconds",
        device_class=NumberDeviceClass.DURATION,
        native_min_value=0,
        native_max_value=7 * 24 * 60 * 60,
        native_unit_of_measurement=UnitOfTime.SECONDS,
    ),
    # Temperature in degrees Celsius
    "DegC": NumberEntityDescription(
        key="DegC",
        device_class=NumberDeviceClass.TEMPERATURE,
        native_min_value=-40,
        native_max_value=150,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
    ),
    # Light level in footcandles
    "Footcandles": NumberEntityDescription(
        key="Footcandles",
        device_class=NumberDeviceClass.ILLUMINANCE,
        native_min_value=0,
        native_max_value=2**31,
        native_step=0.001 * 10.7639104167,
        native_unit_of_measurement=LIGHT_LUX,
    ),
    # Generic signed decimal
    "Decimal": NumberEntityDescription(
        key="Decimal",
        native_min_value=-(2**31),
        native_max_value=2**31 - 1,
        native_step=0.001,
    ),
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: VantageConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Vantage number entities from a config entry."""
    vantage = entry.runtime_data.client

    # Add every GMem object with a numeric data type as a number entity
    add_entities_from_controller(
        entry,
        async_add_entities,
        VantageGMemNumberEntity,
        vantage.gmem,
        filter=lambda obj: obj.is_int or obj.is_fixed,
    )


class VantageGMemNumberEntity(VantageGMemEntity, NumberEntity):
    """Number entity provided by a Vantage GMem object."""

    def __init__(
        self, entry: VantageConfigEntry, controller: Controller[GMem], obj: GMem
    ):
        """Initialize a Vantage number entity."""
        super().__init__(entry, controller, obj)

        # Set the entity description based on the GMem object's data type
        if obj.tag.type in NUMBER_ENTITY_DESCRIPTIONS:
            self.entity_description = NUMBER_ENTITY_DESCRIPTIONS[obj.tag.type]

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
