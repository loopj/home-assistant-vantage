"""Support for Vantage fan entities (Motor loads)."""

from typing import Any, override

from aiovantage.controllers import Controller
from aiovantage.objects import Load

from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util.percentage import percentage_to_ranged_value, ranged_value_to_percentage

from .config_entry import VantageConfigEntry
from .entity import VantageEntity, add_entities_from_controller
from .naming import hierarchical_load_name

# Vantage level range for percentage conversion
LEVEL_RANGE = (1, 100)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: VantageConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Vantage fan entities from a config entry."""
    vantage = entry.runtime_data.client

    # Add every motor load as a fan entity
    add_entities_from_controller(
        entry,
        async_add_entities,
        VantageLoadFanEntity,
        vantage.loads,
        lambda obj: obj.is_motor,
    )


class VantageLoadFanEntity(VantageEntity[Load], FanEntity):
    """Fan entity provided by a Vantage Motor Load.

    Ceiling fans and exhaust fans in Vantage are Load objects with
    load_type == "Motor". They use the same continuous LoadInterface.SetLevel(0-100)
    protocol as dimmable lights — not the FanInterface (which is for HVAC fans).
    """

    _attr_has_entity_name = False
    _attr_supported_features = (
        FanEntityFeature.SET_SPEED | FanEntityFeature.TURN_ON | FanEntityFeature.TURN_OFF
    )

    def __init__(
        self,
        entry: VantageConfigEntry,
        controller: Controller[Load],
        obj: Load,
    ) -> None:
        """Initialize the fan entity."""
        super().__init__(entry, controller, obj)
        # Remember the last non-zero level so turn_on can restore it
        self._last_level: int = 100

    @property
    @override
    def name(self) -> str:
        return hierarchical_load_name(self.client, self.obj)

    @property
    @override
    def is_on(self) -> bool | None:
        return self.obj.is_on

    @property
    @override
    def percentage(self) -> int | None:
        """Return the current speed as a percentage (0-100)."""
        if self.obj.level is None:
            return None
        level = float(self.obj.level)
        if level == 0:
            return 0
        return ranged_value_to_percentage(LEVEL_RANGE, level)

    @override
    async def async_turn_on(
        self,
        percentage: int | None = None,
        preset_mode: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Turn on the fan, optionally at a specific speed."""
        if percentage is not None:
            target = percentage
        else:
            # Restore previous non-zero speed, default to 100%
            target = self._last_level if self._last_level > 0 else 100

        self._last_level = target
        level = percentage_to_ranged_value(LEVEL_RANGE, target)
        await self.async_request_call(self.obj.set_level(level))

    @override
    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the fan, remembering the current speed for restore."""
        if self.obj.level and float(self.obj.level) > 0:
            self._last_level = int(float(self.obj.level))
        await self.async_request_call(self.obj.turn_off())

    @override
    async def async_set_percentage(self, percentage: int) -> None:
        """Set the fan speed as a percentage."""
        if percentage == 0:
            await self.async_turn_off()
            return

        self._last_level = percentage
        level = percentage_to_ranged_value(LEVEL_RANGE, percentage)
        await self.async_request_call(self.obj.set_level(level))
