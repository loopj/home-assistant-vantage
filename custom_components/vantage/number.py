"""Support for Vantage number entities.

The following Vantage objects are considered number entities:
- "GMem" objects that are numbers
"""

from aiovantage import Vantage
from aiovantage.config_client.objects import GMem
from homeassistant.components.number import NumberDeviceClass, NumberEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfTemperature, UnitOfTime
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .entity import VantageEntity


async def async_setup_entry(
    hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities
):
    """Set up Vantage numbers from Config Entry."""
    vantage: Vantage = hass.data[DOMAIN][config_entry.entry_id]

    # Integer GMem objects are Number entities
    async for gmem in vantage.gmem.filter(lambda gmem: gmem.is_int):
        entity = VantageNumberVariable(vantage, gmem)
        await entity.fetch_relations()
        async_add_entities([entity])


class VantageNumberVariable(VantageEntity[GMem], NumberEntity):
    """Representation of a Vantage number GMem variable."""

    def __init__(self, client: Vantage, obj: GMem):
        """Initialize a Vantage number variable."""
        super().__init__(client, client.gmem, obj)

        match obj.tag.type:
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

        if self.obj.is_fixed:
            self._attr_native_step = 0.001

    @property
    def native_value(self) -> float | None:
        """Return the value reported by the number."""

        if self.obj.is_fixed:
            return self.obj.value / 1000

        return self.obj.value

    async def async_set_native_value(self, value: float) -> None:
        """Set new value."""

        if self.obj.is_fixed:
            value = int(value * 1000)
        else:
            value = int(value)

        await self.client.gmem.set_value(self.obj.id, value)
