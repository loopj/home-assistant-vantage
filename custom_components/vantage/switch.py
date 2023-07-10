"""Support for Vantage switch entities."""

import functools
from typing import Any

from aiovantage import Vantage
from aiovantage.config_client.objects import GMem, Load

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .entity import VantageEntity, async_setup_vantage_entities


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Vantage switches from Config Entry."""
    vantage: Vantage = hass.data[DOMAIN][config_entry.entry_id]
    register_items = functools.partial(
        async_setup_vantage_entities, vantage, config_entry, async_add_entities
    )

    # Register all switch entities
    register_items(vantage.loads, VantageLoadSwitch, lambda obj: obj.is_relay)
    register_items(vantage.gmem, VantageVariableSwitch, lambda obj: obj.is_bool)


class VantageLoadSwitch(VantageEntity[Load], SwitchEntity):
    """Representation of a Vantage relay."""

    def __post_init__(self) -> None:
        """Initialize the switch."""
        self._model = f"{self.obj.load_type} Load"

    @property
    def is_on(self) -> bool | None:
        """Return True if entity is on."""
        return self.obj.is_on

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        await self.client.loads.turn_on(self.obj.id)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        await self.client.loads.turn_off(self.obj.id)


class VantageVariableSwitch(VantageEntity[GMem], SwitchEntity):
    """Representation of a Vantage boolean GMem variable."""

    _attr_entity_registry_visible_default = False

    def __post_init__(self) -> None:
        """Initialize the switch."""
        self._attr_name = self.obj.name
        self._device_id = f"variables_{self.obj.master_id}"

    @property
    def is_on(self) -> bool | None:
        """Return True if entity is on."""
        if isinstance(self.obj.value, bool):
            return self.obj.value

        return None

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        await self.client.gmem.set_value(self.obj.id, True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        await self.client.gmem.set_value(self.obj.id, False)
