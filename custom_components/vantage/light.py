from aiovantage import Vantage
from aiovantage.config_client.objects import Area, Load, RGBLoad
from homeassistant.components.group.light import LightGroup
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
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util.color import color_hsv_to_RGB as hsv_to_rgb

from .const import DOMAIN
from .entity import VantageEntity


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Vantage Light from Config Entry."""
    vantage: Vantage = hass.data[DOMAIN][config_entry.entry_id]

    # Non-motor, and non-relay Load object are lights
    async for load in vantage.loads.lights:
        area = await vantage.areas.aget(load.area_id)
        entity = VantageLight(vantage, load, area)

        async_add_entities([entity])

    # All RGBLoad objects are lights
    async for rgb_load in vantage.rgb_loads:
        area = await vantage.areas.aget(rgb_load.area_id)
        entity = VantageRGBLight(vantage, rgb_load, area)

        async_add_entities([entity])

    # Setup LoadGroups as LightGroups
    registry = er.async_get(hass)
    async for load_group in vantage.load_groups:
        # Get the entity IDs of the loads in the group
        load_entities = [
            registry.async_get_entity_id(Platform.LIGHT, DOMAIN, str(load_id))
            for load_id in load_group.load_ids
        ]

        # Remove any entities that aren't lights
        load_entities = [e for e in load_entities if e is not None]

        async_add_entities(
            [LightGroup(load_group.id, load_group.name, load_entities, None)]
        )


class VantageLight(VantageEntity[Load], LightEntity):
    """Representation of a Vantage Light."""

    def __init__(self, client: Vantage, obj: Load, area: Area):
        """Initialize a Vantage Light."""
        super().__init__(client, client.loads, obj, area)

        self._attr_supported_color_modes = set()

        if self.obj.is_dimmable:
            self._attr_supported_color_modes.add(ColorMode.BRIGHTNESS)
            self._attr_supported_features |= LightEntityFeature.TRANSITION

    @property
    def is_on(self) -> bool | None:
        """Return True if entity is on."""
        return self.obj.level

    @property
    def brightness(self) -> int | None:
        """Return the brightness of this light between 0..255."""
        if self.obj.level is None:
            return None

        return round((self.obj.level / 100) * 255)

    async def async_turn_on(self, **kwargs) -> None:
        """Turn the light on."""
        if ATTR_BRIGHTNESS in kwargs:
            level = (kwargs[ATTR_BRIGHTNESS] * 100) / 255
        else:
            level = 100

        await self.client.loads.turn_on(
            self.obj.id, kwargs.get(ATTR_TRANSITION, 0), level
        )

    async def async_turn_off(self, **kwargs) -> None:
        """Turn the light off."""
        await self.client.loads.turn_off(self.obj.id, kwargs.get(ATTR_TRANSITION, 0))


class VantageRGBLight(VantageEntity[RGBLoad], LightEntity):
    def __init__(self, client: Vantage, obj: RGBLoad, area: Area):
        VantageEntity.__init__(self, client, client.rgb_loads, obj, area)

        self._attr_supported_color_modes = set()
        if obj.color_type == RGBLoad.ColorType.HSL:
            self._attr_supported_color_modes.add(ColorMode.HS)
            self._attr_color_mode = ColorMode.HS
        elif obj.color_type == RGBLoad.ColorType.RGB:
            self._attr_supported_color_modes.add(ColorMode.RGB)
            self._attr_color_mode = ColorMode.RGB
        elif obj.color_type == RGBLoad.ColorType.RGBW:
            self._attr_supported_color_modes.add(ColorMode.RGBW)
            self._attr_color_mode = ColorMode.RGBW
        elif obj.color_type == RGBLoad.ColorType.CCT:
            self._attr_supported_color_modes.add(ColorMode.COLOR_TEMP)
            self._attr_color_mode = ColorMode.COLOR_TEMP
            self._attr_min_color_temp_kelvin = self.obj.min_temp
            self._attr_max_color_temp_kelvin = self.obj.max_temp

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

        return round((self.obj.level / 100) * 255)

    @property
    def hs_color(self) -> tuple[float, float] | None:
        if self.obj.hsl is None:
            return None

        return self.obj.hsl[:2]

    @property
    def rgb_color(self) -> tuple[int, int, int] | None:
        if self.obj.rgb is None:
            return None

        return self.obj.rgb

    @property
    def rgbw_color(self) -> tuple[int, int, int, int] | None:
        if self.obj.rgbw is None:
            return None

        return self.obj.rgbw

    @property
    def color_temp_kelvin(self) -> int | None:
        if self.obj.color_temp is None:
            return None

        return self.obj.color_temp

    async def async_turn_on(self, **kwargs) -> None:
        if ATTR_BRIGHTNESS in kwargs:
            level = (kwargs[ATTR_BRIGHTNESS] * 100) / 255
        else:
            level = 100

        # TODO: Consider just checking for ATTR_*_COLOR, and calling the appropriate
        #       method on the controller. If no color is specified, just call
        #       load.turn_on()

        if self.color_mode == ColorMode.HS:
            hs = kwargs.get(ATTR_HS_COLOR, self.obj.hsl[:2])

            await self.client.rgb_loads.set_hsl(self.obj.id, *hs, level)

        elif self.color_mode == ColorMode.RGB:
            rgb = kwargs.get(ATTR_RGB_COLOR)
            if rgb is None:
                # Use last known color, converting from HSL since RGB is lossy
                rgb = hsv_to_rgb(*self.obj.hsl[:2], level)

            await self.client.rgb_loads.set_rgb(self.obj.id, *rgb)

        elif self.color_mode == ColorMode.RGBW:
            rgbw = kwargs.get(ATTR_RGBW_COLOR)
            if rgbw is None:
                # Use last known color, converting from HSL since RGBW is lossy
                rgbw = hsv_to_rgb(*self.obj.hsl[:2], level) + (level / 100 * 255,)

            await self.client.rgb_loads.set_rgbw(self.obj.id, *rgbw)

        elif self.color_mode == ColorMode.COLOR_TEMP:
            if ATTR_COLOR_TEMP_KELVIN in kwargs:
                color_temp = kwargs[ATTR_COLOR_TEMP_KELVIN]
                await self.client.rgb_loads.set_color_temp(self.obj.id, color_temp)

            await self.client.rgb_loads.set_level(self.obj.id, level)

    async def async_turn_off(self, **kwargs) -> None:
        """Turn the light off."""
        await self.client.rgb_loads.turn_off(
            self.obj.id, kwargs.get(ATTR_TRANSITION, 0)
        )
