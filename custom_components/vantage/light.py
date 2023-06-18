"""Support for Vantage light entities.

The following Vantage objects are considered light entities:
- "Load" objects that are not relays or motors
- "RGBLoad" objects
"""

from aiovantage import Vantage
from aiovantage.config_client.objects import Load, LoadGroup, RGBLoad
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
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity_registry import async_get as async_get_entity_registry
from homeassistant.util.color import color_hsv_to_RGB as hsv_to_rgb

from .const import DOMAIN
from .entity import VantageEntity


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Vantage lights from Config Entry."""
    vantage: Vantage = hass.data[DOMAIN][config_entry.entry_id]
    registry = async_get_entity_registry(hass)

    # Non-motor, and non-relay Load object are lights
    async for load in vantage.loads.lights:
        load_entity = VantageLight(vantage, load)
        await load_entity.fetch_relations()
        async_add_entities([load_entity])

    # All RGBLoad objects are lights
    async for rgb_load in vantage.rgb_loads:
        rgb_load_entity = VantageRGBLight(vantage, rgb_load)
        await rgb_load_entity.fetch_relations()
        async_add_entities([rgb_load_entity])

    # Setup LoadGroups as LightGroups
    async for load_group in vantage.load_groups:
        # Get the load ids for the group, and look up their HA entity ids
        entity_ids = []
        for load_id in load_group.load_ids:
            entity_id = registry.async_get_entity_id(
                Platform.LIGHT, DOMAIN, str(load_id)
            )
            if entity_id is not None:
                entity_ids.append(entity_id)

        # Create the group entity and add it to HA
        light_group_entity = VantageLightGroup(vantage, load_group, entity_ids)
        await light_group_entity.fetch_relations()
        async_add_entities([light_group_entity])


class VantageLight(VantageEntity[Load], LightEntity):
    """Representation of a Vantage Light."""

    def __init__(self, client: Vantage, obj: Load):
        """Initialize the light."""
        super().__init__(client, client.loads, obj)

        self._attr_supported_color_modes: set[str] = set()
        if self.obj.is_dimmable:
            self._attr_supported_color_modes.add(ColorMode.BRIGHTNESS)
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
    """Representation of a Vantage RGB Light."""

    def __init__(self, client: Vantage, obj: RGBLoad):
        """Initialize the light."""
        super().__init__(client, client.rgb_loads, obj)

        self._attr_supported_color_modes: set[str] = set()
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
        """Return the hue and saturation color value [float, float]."""
        if self.obj.hsl is None:
            return None

        return self.obj.hsl[:2]

    @property
    def rgb_color(self) -> tuple[int, int, int] | None:
        """Return the rgb color value [int, int, int]."""
        if self.obj.rgb is None:
            return None

        return self.obj.rgb

    @property
    def rgbw_color(self) -> tuple[int, int, int, int] | None:
        """Return the rgbw color value [int, int, int, int]."""
        if self.obj.rgbw is None:
            return None

        return self.obj.rgbw

    @property
    def color_temp_kelvin(self) -> int | None:
        """Return the CT color value in Kelvin."""
        if self.obj.color_temp is None:
            return None

        return self.obj.color_temp

    async def async_turn_on(self, **kwargs) -> None:
        """Turn the light on."""
        if ATTR_BRIGHTNESS in kwargs:
            level = (kwargs[ATTR_BRIGHTNESS] * 100) / 255
        else:
            level = 100

        if self.color_mode == ColorMode.HS:
            hs_color = kwargs.get(ATTR_HS_COLOR, self.obj.hsl[:2])

            await self.client.rgb_loads.set_hsl(self.obj.id, *hs_color, level)

        elif self.color_mode == ColorMode.RGB:
            rgb_color = kwargs.get(ATTR_RGB_COLOR)
            if rgb_color is None:
                # Use last known color, converting from HSL since RGB is lossy
                rgb_color = hsv_to_rgb(*self.obj.hsl[:2], level)

            await self.client.rgb_loads.set_rgb(self.obj.id, *rgb_color)

        elif self.color_mode == ColorMode.RGBW:
            rgbw_color = kwargs.get(ATTR_RGBW_COLOR)
            if rgbw_color is None:
                # Use last known color, converting from HSL since RGBW is lossy
                rgbw_color = hsv_to_rgb(*self.obj.hsl[:2], level) + (level / 100 * 255,)

            await self.client.rgb_loads.set_rgbw(self.obj.id, *rgbw_color)

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


class VantageLightGroup(VantageEntity[LoadGroup], LightGroup):
    """Representation of a Vantage light group."""

    def __init__(self, client: Vantage, obj: LoadGroup, entities: list[str]):
        """Initialize a light group."""
        VantageEntity.__init__(self, client, client.load_groups, obj)
        LightGroup.__init__(self, str(obj.id), obj.name, entities, None)

    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added to hass."""
        await LightGroup.async_added_to_hass(self)
