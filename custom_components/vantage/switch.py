"""Support for Vantage switch entities."""

from typing import Any, override

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from aiovantage.objects import Load

from .config_entry import VantageConfigEntry
from .entity import VantageEntity, VantageGMemEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: VantageConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Vantage switch entities from a config entry."""
    vantage = entry.runtime_data.client

    # Add every "relay" or "motor" load as a switch entity
    VantageLoadSwitchEntity.add_entities(
        entry,
        async_add_entities,
        vantage.loads,
        lambda obj: obj.is_relay or obj.is_motor,
    )

    # Add every GMem object with a boolean data type as a switch entity
    VantageGMemSwitchEntity.add_entities(
        entry, async_add_entities, vantage.gmem, lambda obj: obj.is_bool
    )


class VantageLoadSwitchEntity(VantageEntity[Load], SwitchEntity):
    """Switch entity provided by a Vantage Load object."""

    @property
    @override
    def is_on(self) -> bool | None:
        return self.obj.is_on

    @override
    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.async_request_call(self.obj.turn_on())

    @override
    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.async_request_call(self.obj.turn_off())


class VantageGMemSwitchEntity(VantageGMemEntity, SwitchEntity):
    """Switch entity provided by a Vantage GMem object."""

    @property
    @override
    def is_on(self) -> bool | None:
        if isinstance(self.obj.value, int):
            return bool(self.obj.value)

        return None

    @override
    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.async_request_call(self.obj.set_value(True))

    @override
    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.async_request_call(self.obj.set_value(False))
