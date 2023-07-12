"""Support for Vantage number entities."""

import functools

from aiovantage import Vantage
from aiovantage.models import GMem

from homeassistant.components.number import NumberDeviceClass, NumberEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfTemperature, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .entity import VantageEntity, async_register_vantage_objects


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up Vantage number entities from config entry."""
    vantage: Vantage = hass.data[DOMAIN][entry.entry_id]
    register_items = functools.partial(
        async_register_vantage_objects, hass, entry, async_add_entities
    )

    # Register all number entities
    register_items(vantage.gmem, VantageNumberVariable, lambda obj: obj.is_int)


class VantageNumberVariable(VantageEntity[GMem], NumberEntity):
    """Vantage numeric variable number entity."""

    _attr_entity_registry_visible_default = False

    def __post_init__(self) -> None:
        """Initialize a Vantage number variable."""
        self._attr_name = self.obj.name
        self._device_id = f"{self.obj.master_id}:variables"

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

        if self.obj.is_fixed:
            self._attr_native_step = 0.001

    @property
    def native_value(self) -> float | None:
        """Return the value reported by the number."""
        if isinstance(self.obj.value, int):
            if self.obj.is_fixed:
                return self.obj.value / 1000

            return self.obj.value

        return None

    async def async_set_native_value(self, value: float) -> None:
        """Set new value."""
        if self.obj.is_fixed:
            value = int(value * 1000)
        else:
            value = int(value)

        await self.client.gmem.set_value(self.obj.id, value)
