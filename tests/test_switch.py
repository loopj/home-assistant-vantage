"""Tests for the Vantage InFusion switch platform."""

from typing import Any
from unittest.mock import patch

from aiovantage import Vantage
import pytest
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    snapshot_platform,
)
from syrupy.assertion import SnapshotAssertion

from homeassistant.components.switch import DOMAIN as SWITCH_DOMAIN
from homeassistant.const import (
    ATTR_ENTITY_ID,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    Platform,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

pytestmark = [
    pytest.mark.parametrize("init_integration", [Platform.SWITCH], indirect=True),
    pytest.mark.usefixtures("init_integration"),
]


async def test_entities(
    hass: HomeAssistant,
    entity_registry: er.EntityRegistry,
    snapshot: SnapshotAssertion,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test the switch entities."""
    await snapshot_platform(hass, entity_registry, snapshot, mock_config_entry.entry_id)


@pytest.mark.parametrize(
    ("entity_id", "vid", "service", "method", "args"),
    [
        ("switch.fan", 11, SERVICE_TURN_ON, "turn_on", ()),
        ("switch.fan", 11, SERVICE_TURN_OFF, "turn_off", ()),
        ("switch.variables_away_mode", 50, SERVICE_TURN_ON, "set_value", (True,)),
        ("switch.variables_away_mode", 50, SERVICE_TURN_OFF, "set_value", (False,)),
    ],
)
async def test_switch(
    hass: HomeAssistant,
    mock_vantage: Vantage,
    entity_id: str,
    vid: int,
    service: str,
    method: str,
    args: tuple[Any, ...],
) -> None:
    """Test the Vantage switches."""
    with patch.object(mock_vantage[vid], method) as mock_method:
        await hass.services.async_call(
            SWITCH_DOMAIN, service, {ATTR_ENTITY_ID: entity_id}, blocking=True
        )

    mock_method.assert_awaited_once_with(*args)
