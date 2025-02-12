"""Support for Vantage light entities."""

from typing import Any, cast, override

from aiovantage import Vantage
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
from .const import LOGGER
from .entity import VantageEntity

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
    VantageLoadLightEntity.add_entities(
        entry, async_add_entities, vantage.loads, lambda load: load.is_light
    )

    # Add every load group as a light entity
    VantageLoadGroupLightEntity.add_entities(
        entry, async_add_entities, vantage.load_groups
    )

    # Add every rgb load as a light entity
    VantageRGBLoadLightEntity.add_entities(entry, async_add_entities, vantage.rgb_loads)


class VantageLoadLightEntity(VantageEntity[Load], LightEntity):
    """Vantage load light entity."""

    @override
    def __post_init__(self) -> None:
        # Set up the light based on the power profile
        self._attr_supported_color_modes: set[ColorMode] = set()
        if _is_dimmable_load(self.client, self.obj):
            self._attr_supported_color_modes.add(ColorMode.BRIGHTNESS)
            self._attr_color_mode = ColorMode.BRIGHTNESS
            self._attr_supported_features |= LightEntityFeature.TRANSITION
        else:
            self._attr_supported_color_modes.add(ColorMode.ONOFF)
            self._attr_color_mode = ColorMode.ONOFF

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

    @override
    def __post_init__(self) -> None:
        self._attr_icon = "mdi:lightbulb-group"
        self._attr_supported_color_modes: set[str] = {ColorMode.BRIGHTNESS}
        self._attr_color_mode = ColorMode.BRIGHTNESS
        self._attr_supported_features |= LightEntityFeature.TRANSITION

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

    def __post_init__(self) -> None:
        """Initialize the light."""
        # Set up the light based on the color type
        self._attr_supported_color_modes: set[str] = set()

        match self.obj.color_type:
            case self.obj.ColorType.HSL:
                self._attr_supported_color_modes.add(ColorMode.HS)
                self._attr_color_mode = ColorMode.HS
                self._attr_supported_features |= LightEntityFeature.TRANSITION
            case self.obj.ColorType.RGB:
                self._attr_supported_color_modes.add(ColorMode.RGB)
                self._attr_color_mode = ColorMode.RGB
                self._attr_supported_features |= LightEntityFeature.TRANSITION
            case self.obj.ColorType.RGBW:
                self._attr_supported_color_modes.add(ColorMode.RGBW)
                self._attr_color_mode = ColorMode.RGBW
            case self.obj.ColorType.CCT:
                self._attr_supported_color_modes.add(ColorMode.COLOR_TEMP)
                self._attr_color_mode = ColorMode.COLOR_TEMP
                self._attr_min_color_temp_kelvin = self.obj.min_temp
                self._attr_max_color_temp_kelvin = self.obj.max_temp
                self._attr_supported_features |= LightEntityFeature.TRANSITION
            case _:
                # Treat all other color types as dimmable non-color lights
                self._attr_supported_color_modes.add(ColorMode.BRIGHTNESS)
                self._attr_color_mode = ColorMode.BRIGHTNESS
                self._attr_supported_features |= LightEntityFeature.TRANSITION

                LOGGER.warning(
                    "Unsupported color type %s for RGB light %s",
                    self.obj.color_type,
                    self.obj.name,
                )

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
        if ATTR_RGBW_COLOR in kwargs:
            # Turn on the light with the provided RGBW color
            rgbw: tuple[int, int, int, int] = kwargs[ATTR_RGBW_COLOR]

            # Scale the brightness of the color if provided
            if brightness := kwargs.get(ATTR_BRIGHTNESS) is not None:
                rgbw = _scale_color_brightness(rgbw, brightness)

            await self.async_request_call(self.obj.set_rgbw(*rgbw))

        elif ATTR_RGB_COLOR in kwargs:
            # Turn on the light with the provided RGB color
            rgb: tuple[int, int, int] = kwargs[ATTR_RGB_COLOR]
            transition = kwargs.get(ATTR_TRANSITION, 0)

            # Scale the brightness of the color if provided
            if brightness := kwargs.get(ATTR_BRIGHTNESS) is not None:
                rgb = _scale_color_brightness(rgb, brightness)

            await self.async_request_call(self.obj.dissolve_rgb(*rgb, transition))

        elif ATTR_HS_COLOR in kwargs:
            # Turn on the light with the provided HS color and brightness, default to
            # 100% brightness if not provided
            hue, saturation = kwargs[ATTR_HS_COLOR]
            level = brightness_to_value(LEVEL_RANGE, kwargs.get(ATTR_BRIGHTNESS, 255))
            transition = kwargs.get(ATTR_TRANSITION, 0)

            await self.async_request_call(
                self.obj.dissolve_hsl(hue, saturation, level, transition)
            )

        else:
            # Set the color temperature, if provided
            if ATTR_COLOR_TEMP_KELVIN in kwargs:
                color_temp: int = kwargs[ATTR_COLOR_TEMP_KELVIN]

                await self.async_request_call(self.obj.set_color_temp(color_temp))

            # Turn on the light with the provided brightness, default to 100%
            transition = kwargs.get(ATTR_TRANSITION, 0)
            level = brightness_to_value(LEVEL_RANGE, kwargs.get(ATTR_BRIGHTNESS, 255))

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


def _is_dimmable_load(client: Vantage, obj: Load) -> bool:
    # Determine if a load is dimmable based on its power profile
    power_profile = client.power_profiles.get(obj.power_profile)
    return power_profile is not None and power_profile.is_dimmable
