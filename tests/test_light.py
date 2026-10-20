"""Tests for the Vantage InFusion light platform."""

from decimal import Decimal
from typing import Any
from unittest.mock import patch

from aiovantage import Vantage
from aiovantage.errors import (
    ClientConnectionError,
    InvalidObjectError,
    LoginFailedError,
)
import pytest
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    snapshot_platform,
)
from syrupy.assertion import SnapshotAssertion

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_COLOR_TEMP_KELVIN,
    ATTR_HS_COLOR,
    ATTR_RGB_COLOR,
    ATTR_RGBW_COLOR,
    ATTR_TRANSITION,
    DOMAIN as LIGHT_DOMAIN,
)
from homeassistant.config_entries import SOURCE_REAUTH
from homeassistant.const import (
    ATTR_ENTITY_ID,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    STATE_ON,
    STATE_UNAVAILABLE,
    Platform,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er

from . import setup_integration


@pytest.mark.parametrize("init_integration", [Platform.LIGHT], indirect=True)
@pytest.mark.usefixtures("init_integration")
async def test_entities(
    hass: HomeAssistant,
    entity_registry: er.EntityRegistry,
    snapshot: SnapshotAssertion,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test the light entities."""
    await snapshot_platform(hass, entity_registry, snapshot, mock_config_entry.entry_id)


@pytest.mark.parametrize(
    ("entity_id", "vid", "service", "service_data", "method", "args"),
    [
        ("light.kitchen_pendant", 10, SERVICE_TURN_ON, {}, "turn_on", (0, 100)),
        (
            "light.kitchen_pendant",
            10,
            SERVICE_TURN_ON,
            {ATTR_BRIGHTNESS: 255, ATTR_TRANSITION: 2},
            "turn_on",
            (2, 100),
        ),
        ("light.kitchen_pendant", 10, SERVICE_TURN_OFF, {}, "turn_off", (0,)),
        ("light.all_lights", 12, SERVICE_TURN_ON, {}, "turn_on", (0, 100)),
        ("light.all_lights", 12, SERVICE_TURN_OFF, {}, "turn_off", (0,)),
        (
            "light.rgb_light",
            13,
            SERVICE_TURN_ON,
            {ATTR_RGB_COLOR: (255, 128, 0)},
            "set_rgb",
            (255, 128, 0),
        ),
        (
            "light.rgb_light",
            13,
            SERVICE_TURN_ON,
            {ATTR_RGB_COLOR: (255, 128, 0), ATTR_BRIGHTNESS: 128, ATTR_TRANSITION: 2},
            "dissolve_rgb",
            (128, 64, 0, 2),
        ),
        (
            "light.rgbw_light",
            14,
            SERVICE_TURN_ON,
            {ATTR_RGBW_COLOR: (255, 128, 0, 255)},
            "set_rgbw",
            (255, 128, 0, 255),
        ),
        (
            "light.rgbw_light",
            14,
            SERVICE_TURN_ON,
            {
                ATTR_RGBW_COLOR: (255, 128, 0, 255),
                ATTR_BRIGHTNESS: 128,
                ATTR_TRANSITION: 2,
            },
            "dissolve_rgbw",
            (128, 64, 0, 128, 2),
        ),
        (
            "light.hsl_light",
            15,
            SERVICE_TURN_ON,
            {ATTR_HS_COLOR: (120, 50)},
            "set_hsl",
            (120, 50, 100),
        ),
        (
            "light.hsl_light",
            15,
            SERVICE_TURN_ON,
            {ATTR_HS_COLOR: (120, 50), ATTR_BRIGHTNESS: 255, ATTR_TRANSITION: 2},
            "dissolve_hsl",
            (120, 50, 100, 2),
        ),
        ("light.cct_light", 16, SERVICE_TURN_ON, {}, "turn_on", (0, 100)),
        ("light.cct_light", 16, SERVICE_TURN_OFF, {}, "turn_off", (0,)),
    ],
)
@pytest.mark.parametrize("init_integration", [Platform.LIGHT], indirect=True)
@pytest.mark.usefixtures("init_integration")
async def test_light(
    hass: HomeAssistant,
    mock_vantage: Vantage,
    entity_id: str,
    vid: int,
    service: str,
    service_data: dict[str, Any],
    method: str,
    args: tuple[Any, ...],
) -> None:
    """Test the Vantage lights."""
    with patch.object(mock_vantage[vid], method) as mock_method:
        await hass.services.async_call(
            LIGHT_DOMAIN,
            service,
            {ATTR_ENTITY_ID: entity_id, **service_data},
            blocking=True,
        )

    mock_method.assert_awaited_once_with(*args)


async def test_set_color_temp_when_off(
    hass: HomeAssistant,
    mock_vantage: Vantage,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test that setting a color temperature turns an off light on."""
    obj = mock_vantage.rgb_loads[16]
    obj.level = Decimal(0)
    await setup_integration(hass, mock_config_entry)

    with (
        patch.object(obj, "set_color_temp") as mock_set_color_temp,
        patch.object(obj, "turn_on") as mock_turn_on,
    ):
        await hass.services.async_call(
            LIGHT_DOMAIN,
            SERVICE_TURN_ON,
            {ATTR_ENTITY_ID: "light.cct_light", ATTR_COLOR_TEMP_KELVIN: 4000},
            blocking=True,
        )

    mock_set_color_temp.assert_awaited_once_with(4000)
    mock_turn_on.assert_awaited_once_with(0, 100)


@pytest.mark.parametrize(
    ("error", "state"),
    [
        (ClientConnectionError("Connection lost"), STATE_ON),
        (InvalidObjectError("Invalid object"), STATE_UNAVAILABLE),
    ],
)
@pytest.mark.parametrize("init_integration", [Platform.LIGHT], indirect=True)
@pytest.mark.usefixtures("init_integration")
async def test_light_error(
    hass: HomeAssistant,
    mock_vantage: Vantage,
    error: Exception,
    state: str,
) -> None:
    """Test the Vantage lights when a request fails."""
    with (
        patch.object(mock_vantage.loads[10], "turn_off", side_effect=error),
        pytest.raises(
            HomeAssistantError,
            match=f"Request for light.kitchen_pendant failed: {error}",
        ),
    ):
        await hass.services.async_call(
            LIGHT_DOMAIN,
            SERVICE_TURN_OFF,
            {ATTR_ENTITY_ID: "light.kitchen_pendant"},
            blocking=True,
        )

    assert (light := hass.states.get("light.kitchen_pendant"))
    assert light.state == state


@pytest.mark.parametrize("init_integration", [Platform.LIGHT], indirect=True)
@pytest.mark.usefixtures("init_integration")
async def test_light_authentication_error(
    hass: HomeAssistant,
    mock_vantage: Vantage,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test the Vantage lights when the controller rejects the credentials."""
    with (
        patch.object(
            mock_vantage.loads[10],
            "turn_off",
            side_effect=LoginFailedError("Login failed"),
        ),
        pytest.raises(
            HomeAssistantError,
            match="Request for light.kitchen_pendant failed: Login failed",
        ),
    ):
        await hass.services.async_call(
            LIGHT_DOMAIN,
            SERVICE_TURN_OFF,
            {ATTR_ENTITY_ID: "light.kitchen_pendant"},
            blocking=True,
        )

    # A rejected login asks the user to reauthenticate
    await hass.async_block_till_done()
    assert any(mock_config_entry.async_get_active_flows(hass, {SOURCE_REAUTH}))
