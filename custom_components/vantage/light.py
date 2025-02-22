"""Support for Vantage light entities."""

from typing import Any, cast, override

from aiovantage.controllers import RGBLoadTypes
from aiovantage.objects import Load, LoadGroup

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
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util.color import brightness_to_value, value_to_brightness

from .config_entry import VantageConfigEntry
from .entity import VantageEntity, add_entities_from_controller

# Vantage level range for converting between HA brightness and Vantage levels
LEVEL_RANGE = (1, 100)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: VantageConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Vantage light entities from a config entry."""
    vantage = entry.runtime_data.client

    # Add every "light" load as a light entity
    add_entities_from_controller(
        entry,
        async_add_entities,
        VantageLoadLightEntity,
        vantage.loads,
        lambda load: load.is_light,
    )

    # Add every load group as a light entity
    add_entities_from_controller(
        entry, async_add_entities, VantageLoadGroupLightEntity, vantage.load_groups
    )

    # Add every rgb load as a light entity
    add_entities_from_controller(
        entry, async_add_entities, VantageRGBLoadLightEntity, vantage.rgb_loads
    )


class VantageLoadLightEntity(VantageEntity[Load], LightEntity):
    """Vantage load light entity."""

    @property
    def is_dimmable(self) -> bool:
        """Determine if a load is dimmable based on its power profile."""
        if hasattr(self.obj, "power_profile"):
            if power_profile := self.client.power_profiles.get(self.obj.power_profile):
                return power_profile.is_dimmable

        return False

    @property
    @override
    def supported_features(self) -> int:
        if self.is_dimmable:
            return LightEntityFeature.TRANSITION

        return LightEntityFeature(0)

    @property
    @override
    def supported_color_modes(self) -> set[ColorMode]:
        if self.is_dimmable:
            return {ColorMode.BRIGHTNESS}

        return {ColorMode.ONOFF}

    @property
    @override
    def color_mode(self) -> ColorMode:
        if self.is_dimmable:
            return ColorMode.BRIGHTNESS

        return ColorMode.ONOFF

    @property
    @override
    def is_on(self) -> bool | None:
        return self.obj.is_on

    @property
    @override
    def brightness(self) -> int | None:
        if self.obj.level is None:
            return None

        return value_to_brightness(LEVEL_RANGE, float(self.obj.level))

    @override
    async def async_turn_on(self, **kwargs: Any) -> None:
        transition = kwargs.get(ATTR_TRANSITION, 0)
        level = brightness_to_value(LEVEL_RANGE, kwargs.get(ATTR_BRIGHTNESS, 255))

        await self.async_request_call(self.obj.turn_on(transition, level))

    @override
    async def async_turn_off(self, **kwargs: Any) -> None:
        transition = kwargs.get(ATTR_TRANSITION, 0)

        await self.async_request_call(self.obj.turn_off(transition))


class VantageLoadGroupLightEntity(VantageEntity[LoadGroup], LightEntity):
    """Vantage load group light entity."""

    _attr_icon = "mdi:lightbulb-group"
    _attr_supported_color_modes = {ColorMode.BRIGHTNESS}
    _attr_color_mode = ColorMode.BRIGHTNESS
    _attr_supported_features = LightEntityFeature.TRANSITION

    @property
    @override
    def is_on(self) -> bool | None:
        return self.obj.is_on

    @property
    @override
    def brightness(self) -> int | None:
        if self.obj.level is None:
            return None

        return value_to_brightness(LEVEL_RANGE, float(self.obj.level))

    @override
    async def async_turn_on(self, **kwargs: Any) -> None:
        transition = kwargs.get(ATTR_TRANSITION, 0)
        level = brightness_to_value(LEVEL_RANGE, kwargs.get(ATTR_BRIGHTNESS, 255))

        await self.async_request_call(self.obj.turn_on(transition, level))

    @override
    async def async_turn_off(self, **kwargs: Any) -> None:
        transition = kwargs.get(ATTR_TRANSITION, 0)

        await self.async_request_call(self.obj.turn_off(transition))


class VantageRGBLoadLightEntity(VantageEntity[RGBLoadTypes], LightEntity):
    """Vantage RGB load light entity."""

    _attr_supported_features = LightEntityFeature.TRANSITION

    @property
    @override
    def supported_color_modes(self) -> set[ColorMode]:
        if hasattr(self.obj, "color_type"):
            if self.obj.color_type.value == "HSL":
                return {ColorMode.HS}

            if self.obj.color_type.value == "RGB":
                return {ColorMode.RGB}

            if self.obj.color_type.value == "RGBW":
                return {ColorMode.RGBW}

            if self.obj.color_type.value == "CCT":
                return {ColorMode.COLOR_TEMP}

        return {ColorMode.BRIGHTNESS}

    @property
    @override
    def color_mode(self) -> ColorMode:
        if hasattr(self.obj, "color_type"):
            if self.obj.color_type.value == "HSL":
                return ColorMode.HS

            if self.obj.color_type.value == "RGB":
                return ColorMode.RGB

            if self.obj.color_type.value == "RGBW":
                return ColorMode.RGBW

            if self.obj.color_type.value == "CCT":
                return ColorMode.COLOR_TEMP

        return ColorMode.BRIGHTNESS

    @property
    @override
    def min_color_temp_kelvin(self) -> int:
        if hasattr(self.obj, "min_temp"):
            return self.obj.min_temp

        return super().min_color_temp_kelvin

    @property
    @override
    def max_color_temp_kelvin(self) -> int:
        if hasattr(self.obj, "max_temp"):
            return self.obj.max_temp

        return super().max_color_temp_kelvin

    @property
    @override
    def is_on(self) -> bool | None:
        return self.obj.is_on

    @property
    @override
    def brightness(self) -> int | None:
        if self.obj.level is None:
            return None

        return value_to_brightness(LEVEL_RANGE, float(self.obj.level))

    @property
    @override
    def hs_color(self) -> tuple[float, float] | None:
        if self.obj.hsl is None:
            return None

        return self.obj.hsl[:2]

    @property
    @override
    def rgb_color(self) -> tuple[int, int, int] | None:
        return self.obj.rgb

    @property
    @override
    def rgbw_color(self) -> tuple[int, int, int, int] | None:
        return self.obj.rgbw

    @property
    @override
    def color_temp_kelvin(self) -> int | None:
        return self.obj.color_temp

    @override
    async def async_turn_on(self, **kwargs: Any) -> None:
        transition = kwargs.get(ATTR_TRANSITION, 0)
        brightness = kwargs.get(ATTR_BRIGHTNESS)

        if ATTR_RGBW_COLOR in kwargs:
            rgbw: tuple[int, int, int, int] = kwargs[ATTR_RGBW_COLOR]

            # Scale the brightness of the color if provided
            if brightness is not None:
                rgbw = _scale_color_brightness(rgbw, brightness)

            # Turn on the light with the provided RGBW color, with optional transition
            if transition:
                await self.async_request_call(self.obj.dissolve_rgbw(*rgbw, transition))
            else:
                await self.async_request_call(self.obj.set_rgbw(*rgbw))

        elif ATTR_RGB_COLOR in kwargs:
            rgb: tuple[int, int, int] = kwargs[ATTR_RGB_COLOR]

            # Scale the brightness of the color if provided
            if brightness is not None:
                rgb = _scale_color_brightness(rgb, brightness)

            # Turn on the light with the provided RGB color, with optional transition
            if transition:
                await self.async_request_call(self.obj.dissolve_rgb(*rgb, transition))
            else:
                await self.async_request_call(self.obj.set_rgb(*rgb))

        elif ATTR_HS_COLOR in kwargs:
            hue, saturation = kwargs[ATTR_HS_COLOR]

            # Scale the brightness, default to 100%
            level = brightness_to_value(LEVEL_RANGE, brightness) if brightness else 100

            # Turn on the light with the provided HS color, with optional transition
            if transition:
                await self.async_request_call(
                    self.obj.dissolve_hsl(hue, saturation, level, transition)
                )
            else:
                await self.async_request_call(self.obj.set_hsl(hue, saturation, level))

        else:
            if ATTR_COLOR_TEMP_KELVIN in kwargs:
                color_temp: int = kwargs[ATTR_COLOR_TEMP_KELVIN]

                # Set the color temperature, if provided
                await self.async_request_call(self.obj.set_color_temp(color_temp))

            # Turn on the light with the provided brightness, default to 100%
            level = brightness_to_value(LEVEL_RANGE, brightness) if brightness else 100

            await self.async_request_call(self.obj.turn_on(transition, level))

    @override
    async def async_turn_off(self, **kwargs: Any) -> None:
        transition = kwargs.get(ATTR_TRANSITION, 0)

        await self.async_request_call(self.obj.turn_off(transition))


def _scale_color_brightness[T: tuple[int, ...]](color: T, brightness: int | None) -> T:
    # Scale the brightness of an RGB/RGBW color tuple.
    if brightness is None:
        return color

    return cast(T, tuple(int(round(c * brightness / 255)) for c in color))
