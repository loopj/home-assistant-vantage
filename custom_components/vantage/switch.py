"""Support for Vantage switch entities."""

from collections.abc import Callable
from typing import Any, TypeVar

from aiovantage import Vantage, VantageEvent
from aiovantage.config_client.objects import GMem, Load
from aiovantage.controllers.base import BaseController

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .entity import VantageEntity

T = TypeVar("T", bound=Load | GMem)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Vantage switches from Config Entry."""
    vantage: Vantage = hass.data[DOMAIN][config_entry.entry_id]

    @callback
    def register_items(
        controller: BaseController[T],
        entity_class: type[VantageEntity[T]],
        filter_fn: Callable[[T], bool] = lambda _: True,
    ) -> None:
        @callback
        def async_add_entity(_type: VantageEvent, obj: T, _data: Any) -> None:
            if filter_fn(obj):
                async_add_entities([entity_class(vantage, controller, obj)])

        # Add all current members of this controller
        for obj in controller:
            async_add_entity(VantageEvent.OBJECT_ADDED, obj, {})

        # Register a callback for new members
        config_entry.async_on_unload(
            controller.subscribe(
                async_add_entity, event_filter=VantageEvent.OBJECT_ADDED
            )
        )

    # Set up all switch-type objects
    register_items(vantage.loads, VantageLoadSwitch, lambda obj: obj.is_relay)
    register_items(vantage.gmem, VantageVariableSwitch, lambda obj: obj.is_bool)


class VantageLoadSwitch(VantageEntity[Load], SwitchEntity):
    """Representation of a Vantage relay."""

    @property
    def model(self) -> str:
        """Model of the relay."""
        return f"{self.obj.load_type} Load"

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

    def __post_init__(self) -> None:
        """Initialize the switch."""
        self._attr_name = self.obj.name

    @property
    def attach_to_device_id(self) -> int | None:
        """The id of the device this entity should be attached to, if any."""
        return self.obj.master_id

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
