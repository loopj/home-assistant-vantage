"""Support for Vantage cover entities."""

import functools
from typing import Any

from aiovantage.controllers.blinds import BlindTypes

from homeassistant.components.cover import (
    CoverDeviceClass,
    CoverEntity,
    CoverEntityFeature,
    ATTR_POSITION,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .config_entry import VantageConfigEntry
from .entity import VantageEntity, async_register_vantage_objects


async def async_setup_entry(
    hass: HomeAssistant,
    entry: VantageConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Vantage cover entities from config entry."""
    vantage = entry.runtime_data.client
    register_items = functools.partial(
        async_register_vantage_objects, hass, entry, async_add_entities
    )

    # Set up all cover entities
    register_items(vantage.blinds, VantageCover)


class VantageCover(VantageEntity[BlindTypes], CoverEntity):
    """Vantage blind cover entity."""

    def __post_init__(self) -> None:
        """Initialize a Vantage Cover."""
        self._attr_supported_features = (
            CoverEntityFeature.OPEN
            | CoverEntityFeature.CLOSE
            | CoverEntityFeature.STOP
            | CoverEntityFeature.SET_POSITION
        )
        match self.obj.shade_type:
            case "Drapery":
                self._attr_device_class = CoverDeviceClass.CURTAIN
            case _:
                self._attr_device_class = CoverDeviceClass.SHADE

    @property
    def is_closed(self) -> bool | None:
        """Return if the cover is closed or not."""
        if self.obj.position is None:
            return None
        return self.obj.position < 1

    @property
    def current_cover_position(self) -> int | None:
        """Return the current position of cover."""
        if self.obj.position is None:
            return None
        return int(self.obj.position)

    async def async_open_cover(self, **kwargs: Any) -> None:
        """Open the cover."""
        await self.async_request_call(self.obj.open())

    async def async_close_cover(self, **kwargs: Any) -> None:
        """Close cover."""
        await self.async_request_call(self.obj.close())

    async def async_stop_cover(self, **kwargs: Any) -> None:
        """Stop the cover."""
        await self.async_request_call(self.obj.stop())

    async def async_set_cover_position(self, **kwargs: Any) -> None:
        """Move the cover to a specific position."""
        if ATTR_POSITION in kwargs:
            position = kwargs[ATTR_POSITION]
            await self.async_request_call(self.obj.set_position(position))
