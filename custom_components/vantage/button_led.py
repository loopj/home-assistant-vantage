"""Support for Vantage button LED entities."""

from typing import Any, override

from aiovantage.controllers import Controller
from aiovantage.object_interfaces import ButtonInterface
from aiovantage.objects import Button

from homeassistant.components.light import (
    ATTR_EFFECT,
    ATTR_RGB_COLOR,
    ColorMode,
    LightEntity,
    LightEntityFeature,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .config_entry import VantageConfigEntry
from .const import CONF_BLUE_BUTTON_LED
from .entity import VantageEntity, add_entities_from_controller
from .naming import hierarchical_button_name

# Default green for first turn-on; safe on all RG and RGB hardware
_DEFAULT_ACTIVE_COLOR: tuple[int, int, int] = (0, 255, 0)

# Blink rate effect names exposed to HA (excludes Off, which maps to no effect)
_BLINK_EFFECTS: list[str] = [
    ButtonInterface.BlinkRate.Fast,
    ButtonInterface.BlinkRate.Medium,
    ButtonInterface.BlinkRate.Slow,
    ButtonInterface.BlinkRate.VerySlow,
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: VantageConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Vantage button LED light entities from a config entry."""
    vantage = entry.runtime_data.client

    add_entities_from_controller(
        entry,
        async_add_entities,
        VantageButtonLEDEntity,
        vantage.buttons,
    )


class VantageButtonLEDEntity(VantageEntity[Button], LightEntity):
    """Light entity that controls the LED on a Vantage keypad button.

    Active color  → what the LED shows when the button is in the On/active state.
    Inactive color → what the LED shows when the button is in the Off/inactive state
                     (always kept at black/off by this entity).

    Blink rate is exposed as a light effect.  Blue channel can be disabled via
    the integration option ``blue_button_led`` for keypads that only support
    Red/Green LEDs.
    """

    _attr_has_entity_name = False
    _attr_icon = "mdi:led-on"
    # CONFIG keeps this entity out of area-targeted service calls so that
    # "turn off all lights in Living Room" never touches keypad LEDs.
    # TODO: migrate to a proper IndicatorLight type once that lands in HA core.
    _attr_entity_category = EntityCategory.CONFIG
    _attr_supported_color_modes = {ColorMode.RGB}
    _attr_color_mode = ColorMode.RGB
    _attr_supported_features = LightEntityFeature.EFFECT
    _attr_effect_list = _BLINK_EFFECTS

    def __init__(
        self,
        entry: VantageConfigEntry,
        controller: Controller[Button],
        obj: Button,
    ) -> None:
        """Initialize the button LED entity."""
        super().__init__(entry, controller, obj)
        # Attach to the parent station device so the LED appears alongside the
        # button sensor in the station's device page.
        if station := self.client.stations.get(obj.parent.vid):
            self.parent_obj = station

    @property
    @override
    def unique_id(self) -> str:
        return f"vantagevid-{self.obj.vid}:led"

    @property
    @override
    def name(self) -> str:
        return hierarchical_button_name(self.client, self.obj) + " LED"

    @property
    def _blue_enabled(self) -> bool:
        """Return True if the keypad hardware supports the blue LED channel."""
        return self.entry.options.get(CONF_BLUE_BUTTON_LED, False)

    @property
    @override
    def is_on(self) -> bool | None:
        color = self.obj.led_active_color
        if color is None:
            return None
        return any(c > 0 for c in color)

    @property
    @override
    def rgb_color(self) -> tuple[int, int, int] | None:
        return self.obj.led_active_color

    @property
    @override
    def effect(self) -> str | None:
        blink = self.obj.led_blink_rate
        if blink is None or blink == ButtonInterface.BlinkRate.Off:
            return None
        return blink

    @override
    async def async_turn_on(self, **kwargs: Any) -> None:
        rgb: tuple[int, int, int] = kwargs.get(
            ATTR_RGB_COLOR, self.obj.led_active_color or _DEFAULT_ACTIVE_COLOR
        )

        # Strip blue channel when hardware is RG-only
        if not self._blue_enabled:
            rgb = (rgb[0], rgb[1], 0)

        effect: str | None = kwargs.get(ATTR_EFFECT)
        if effect is not None:
            try:
                blink_rate = ButtonInterface.BlinkRate(effect)
            except ValueError:
                blink_rate = ButtonInterface.BlinkRate.Off
        else:
            blink_rate = self.obj.led_blink_rate or ButtonInterface.BlinkRate.Off

        inactive = self.obj.led_inactive_color or (0, 0, 0)
        await self.async_request_call(self.obj.set_led(rgb, inactive, blink_rate))

    @override
    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.async_request_call(self.obj.clear_led())
