"""Support for Vantage cover entities."""

from typing import Any, override

from aiovantage.controllers import BlindGroupTypes, BlindTypes

from homeassistant.components.cover import (
    CoverDeviceClass,
    CoverEntity,
    CoverEntityFeature,
    ATTR_POSITION,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .config_entry import VantageConfigEntry
from .entity import VantageEntity, add_entities_from_controller


async def async_setup_entry(
    hass: HomeAssistant,
    entry: VantageConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Vantage cover entities from a config entry."""
    vantage = entry.runtime_data.client

    # Add every blind as a cover entity
    add_entities_from_controller(
        entry, async_add_entities, VantageCoverEntity, vantage.blinds
    )

    # Add every blind group as a cover entity
    add_entities_from_controller(
        entry, async_add_entities, VantageCoverEntity, vantage.blind_groups
    )


class VantageCoverEntity[T: BlindTypes | BlindGroupTypes](
    VantageEntity[T], CoverEntity
):
    """Vantage blind cover entity."""

    _attr_supported_features = (
        CoverEntityFeature.OPEN
        | CoverEntityFeature.CLOSE
        | CoverEntityFeature.STOP
        | CoverEntityFeature.SET_POSITION
    )

    @property
    @override
    def device_class(self) -> str | None:
        if self.obj.shade_type == "Drapery":
            return CoverDeviceClass.CURTAIN

        return CoverDeviceClass.SHADE

    @property
    @override
    def is_closed(self) -> bool | None:
        if self.obj.position is None:
            return None

        return self.obj.position < 1

    @property
    @override
    def current_cover_position(self) -> int | None:
        if self.obj.position is None:
            return None

        return int(self.obj.position)

    @override
    async def async_open_cover(self, **kwargs: Any) -> None:
        await self.async_request_call(self.obj.open())

    @override
    async def async_close_cover(self, **kwargs: Any) -> None:
        await self.async_request_call(self.obj.close())

    @override
    async def async_stop_cover(self, **kwargs: Any) -> None:
        await self.async_request_call(self.obj.stop())

    @override
    async def async_set_cover_position(self, **kwargs: Any) -> None:
        if ATTR_POSITION in kwargs:
            position = kwargs[ATTR_POSITION]
            await self.async_request_call(self.obj.set_position(position))
