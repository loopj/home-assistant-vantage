"""Support for Vantage switch entities."""

import functools
from typing import Any

from aiovantage import Vantage
from aiovantage.errors import ClientError
from aiovantage.models import Load

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .entity import VantageEntity, VantageVariableEntity, async_register_vantage_objects


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up Vantage switch entities from config entry."""
    vantage: Vantage = hass.data[DOMAIN][entry.entry_id]
    register_items = functools.partial(
        async_register_vantage_objects, hass, entry, async_add_entities
    )

    # Register all switch entities
    register_items(
        vantage.loads, VantageLoadSwitch, lambda obj: obj.is_relay or obj.is_motor
    )
    register_items(vantage.gmem, VantageVariableSwitch, lambda obj: obj.is_bool)


class VantageLoadSwitch(VantageEntity[Load], SwitchEntity):
    """Vantage relay load switch entity."""

    @property
    def is_on(self) -> bool | None:
        """Return True if entity is on."""
        return self.obj.is_on

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        try:
            await self.client.loads.turn_on(self.obj.id)
        except ClientError as err:
            raise HomeAssistantError(
                f"Turning {self.obj.name} on failed with error: {err}"
            ) from err

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        try:
            await self.client.loads.turn_off(self.obj.id)
        except ClientError as err:
            raise HomeAssistantError(
                f"Turning {self.obj.name} off failed with error: {err}"
            ) from err


class VantageVariableSwitch(VantageVariableEntity, SwitchEntity):
    """Vantage boolean variable switch entity."""

    @property
    def is_on(self) -> bool | None:
        """Return True if entity is on."""
        if isinstance(self.obj.value, bool):
            return self.obj.value

        return None

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        try:
            await self.client.gmem.set_value(self.obj.id, True)
        except ClientError as err:
            raise HomeAssistantError(
                f"Setting variable {self.obj.name} value failed with error: {err}"
            ) from err

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        try:
            await self.client.gmem.set_value(self.obj.id, False)
        except ClientError as err:
            raise HomeAssistantError(
                f"Setting variable {self.obj.name} value failed with error: {err}"
            ) from err
