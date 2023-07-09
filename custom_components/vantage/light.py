"""Support for Vantage light entities."""

from collections.abc import Callable
from typing import Any, TypeVar

from aiovantage import Vantage, VantageEvent
from aiovantage.config_client.objects import Load, LoadGroup, RGBLoad
from aiovantage.controllers.base import BaseController

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_COLOR_TEMP_KELVIN,
    ATTR_HS_COLOR,
    ATTR_RGB_COLOR,
    ATTR_RGBW_COLOR,
    ATTR_TRANSITION,
    ColorMode,
    LightEntity,
    LightEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .entity import VantageEntity
from .helpers import (
    brightness_to_level,
    level_to_brightness,
    scale_color_brightness,
)

T = TypeVar("T", bound=Load | LoadGroup | RGBLoad)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Vantage lights from Config Entry."""
    vantage: Vantage = hass.data[DOMAIN][config_entry.entry_id]

    @callback
    def register_items(
        controller: BaseController[T],
        entity_class: type[VantageEntity[T]],
        object_filter: Callable[[T], bool] | None = None,
    ) -> None:
        @callback
        def async_add_entity(_type: VantageEvent, obj: T, _data: Any) -> None:
            if object_filter is None or object_filter(obj):
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

    # Set up all light-type objects
    register_items(vantage.loads, VantageLight, lambda obj: obj.is_light)
    register_items(vantage.rgb_loads, VantageRGBLight)
    register_items(vantage.load_groups, VantageLightGroup)


class VantageLight(VantageEntity[Load], LightEntity):
    """Representation of a Vantage light."""

    def __post_init__(self) -> None:
        """Initialize the light."""
        self._attr_supported_color_modes: set[str] = set()
        if self.obj.is_dimmable:
            self._attr_supported_color_modes.add(ColorMode.BRIGHTNESS)
            self._attr_color_mode = ColorMode.BRIGHTNESS
            self._attr_supported_features |= LightEntityFeature.TRANSITION
        else:
            self._attr_supported_color_modes.add(ColorMode.ONOFF)
            self._attr_color_mode = ColorMode.ONOFF

    @property
    def model(self) -> str | None:
        """Return the model of the light."""
        return f"{self.obj.load_type} Load"

    @property
    def is_on(self) -> bool | None:
        """Return True if entity is on."""
        return self.obj.is_on

    @property
    def brightness(self) -> int | None:
        """Return the brightness of this light between 0..255."""
        if self.obj.level is None:
            return None

        return level_to_brightness(self.obj.level)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the light on."""
        await self.client.loads.turn_on(
            self.obj.id,
            kwargs.get(ATTR_TRANSITION, 0),
            brightness_to_level(kwargs.get(ATTR_BRIGHTNESS, 255)),
        )

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the light off."""
        await self.client.loads.turn_off(self.obj.id, kwargs.get(ATTR_TRANSITION, 0))


class VantageRGBLight(VantageEntity[RGBLoad], LightEntity):
    """Representation of a Vantage RGB light."""

    def __post_init__(self) -> None:
        """Initialize the light."""
        self._attr_supported_color_modes: set[str] = set()
        match self.obj.color_type:
            case RGBLoad.ColorType.HSL:
                self._attr_supported_color_modes.add(ColorMode.HS)
                self._attr_color_mode = ColorMode.HS
            case RGBLoad.ColorType.RGB:
                self._attr_supported_color_modes.add(ColorMode.RGB)
                self._attr_color_mode = ColorMode.RGB
            case RGBLoad.ColorType.RGBW:
                self._attr_supported_color_modes.add(ColorMode.RGBW)
                self._attr_color_mode = ColorMode.RGBW
            case RGBLoad.ColorType.CCT:
                self._attr_supported_color_modes.add(ColorMode.COLOR_TEMP)
                self._attr_color_mode = ColorMode.COLOR_TEMP
                self._attr_min_color_temp_kelvin = self.obj.min_temp
                self._attr_max_color_temp_kelvin = self.obj.max_temp
            case _:
                self._attr_supported_color_modes.add(ColorMode.BRIGHTNESS)
                self._attr_color_mode = ColorMode.BRIGHTNESS

        # All RGB lights support transition
        self._attr_supported_features |= LightEntityFeature.TRANSITION

    @property
    def model(self) -> str | None:
        """Return the model of the light."""
        return "RGB Load"

    @property
    def is_on(self) -> bool | None:
        """Return True if entity is on."""
        return self.obj.is_on

    @property
    def brightness(self) -> int | None:
        """Return the brightness of this light between 0..255."""
        if self.obj.level is None:
            return None

        return level_to_brightness(self.obj.level)

    @property
    def hs_color(self) -> tuple[float, float] | None:
        """Return the hue and saturation color value [float, float]."""
        if self.obj.hsl is None:
            return None

        return self.obj.hsl[:2]

    @property
    def rgb_color(self) -> tuple[int, int, int] | None:
        """Return the rgb color value [int, int, int]."""
        return self.obj.rgb

    @property
    def rgbw_color(self) -> tuple[int, int, int, int] | None:
        """Return the rgbw color value [int, int, int, int]."""
        return self.obj.rgbw

    @property
    def color_temp_kelvin(self) -> int | None:
        """Return the CT color value in Kelvin."""
        return self.obj.color_temp

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the light on."""

        if ATTR_RGBW_COLOR in kwargs:
            # Turn on the light with the provided RGBW color, scaling brightness if provided
            red, green, blue, white = scale_color_brightness(
                kwargs[ATTR_RGBW_COLOR], kwargs.get(ATTR_BRIGHTNESS)
            )

            await self.client.rgb_loads.set_rgbw(self.obj.id, red, green, blue, white)

        elif ATTR_RGB_COLOR in kwargs:
            # Turn on the light with the provided RGB color, scaling brightness if provided
            red, green, blue = scale_color_brightness(
                kwargs[ATTR_RGB_COLOR], kwargs.get(ATTR_BRIGHTNESS)
            )

            await self.client.rgb_loads.dissolve_rgb(
                self.obj.id, red, green, blue, kwargs.get(ATTR_TRANSITION, 0)
            )

        elif ATTR_HS_COLOR in kwargs:
            # Turn on the light with the provided HS color and brightness
            hs_color: tuple[float, float] = kwargs[ATTR_HS_COLOR]

            await self.client.rgb_loads.dissolve_hsl(
                self.obj.id,
                hs_color[0],
                hs_color[1],
                brightness_to_level(kwargs.get(ATTR_BRIGHTNESS, 255)),
                kwargs.get(ATTR_TRANSITION, 0),
            )

        else:
            # Set the color temperature, if provided
            if ATTR_COLOR_TEMP_KELVIN in kwargs:
                color_temp = kwargs[ATTR_COLOR_TEMP_KELVIN]
                await self.client.rgb_loads.set_color_temp(self.obj.id, color_temp)

            # Turn on light with previous settings if no color is specified
            else:
                await self.client.rgb_loads.turn_on(
                    self.obj.id,
                    kwargs.get(ATTR_TRANSITION, 0),
                    brightness_to_level(kwargs.get(ATTR_BRIGHTNESS, 255)),
                )

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the light off."""
        await self.client.rgb_loads.turn_off(
            self.obj.id, kwargs.get(ATTR_TRANSITION, 0)
        )


class VantageLightGroup(VantageEntity[LoadGroup], LightEntity):
    """Representation of a Vantage light group."""

    def __post_init__(self) -> None:
        """Initialize a Vantage light group."""
        self._attr_supported_color_modes = {ColorMode.BRIGHTNESS}
        self._attr_color_mode = ColorMode.BRIGHTNESS
        self._attr_supported_features |= LightEntityFeature.TRANSITION

    @property
    def is_on(self) -> bool | None:
        """Return True if entity is on."""
        return self.obj.is_on

    @property
    def brightness(self) -> int | None:
        """Return the brightness of this light between 0..255."""
        if self.obj.level is None:
            return None

        return level_to_brightness(self.obj.level)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the light on."""
        await self.client.loads.turn_on(
            self.obj.id,
            kwargs.get(ATTR_TRANSITION, 0),
            brightness_to_level(kwargs.get(ATTR_BRIGHTNESS, 255)),
        )

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the light off."""
        await self.client.rgb_loads.turn_off(
            self.obj.id, kwargs.get(ATTR_TRANSITION, 0)
        )
