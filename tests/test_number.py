"""Tests for the Vantage InFusion number platform."""

from unittest.mock import patch

from aiovantage import Vantage
import pytest
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    snapshot_platform,
)
from syrupy.assertion import SnapshotAssertion

from homeassistant.components.number import (
    ATTR_VALUE,
    DOMAIN as NUMBER_DOMAIN,
    SERVICE_SET_VALUE,
)
from homeassistant.const import ATTR_ENTITY_ID, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

pytestmark = [
    pytest.mark.parametrize("init_integration", [Platform.NUMBER], indirect=True),
    pytest.mark.usefixtures("init_integration"),
]


async def test_entities(
    hass: HomeAssistant,
    entity_registry: er.EntityRegistry,
    snapshot: SnapshotAssertion,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test the number entities."""
    await snapshot_platform(hass, entity_registry, snapshot, mock_config_entry.entry_id)


@pytest.mark.parametrize(
    ("entity_id", "vid", "value", "expected"),
    [
        ("number.variables_scene_number", 51, 5, 5),
        # Fixed point variables hold thousandths
        ("number.variables_setpoint_offset", 53, 2.5, 2500),
        ("number.variables_setpoint_offset", 53, 1.001, 1001),
    ],
)
async def test_number(
    hass: HomeAssistant,
    mock_vantage: Vantage,
    entity_id: str,
    vid: int,
    value: float,
    expected: int,
) -> None:
    """Test the Vantage numbers."""
    with patch.object(mock_vantage.gmem[vid], "set_value") as mock_set_value:
        await hass.services.async_call(
            NUMBER_DOMAIN,
            SERVICE_SET_VALUE,
            {ATTR_ENTITY_ID: entity_id, ATTR_VALUE: value},
            blocking=True,
        )

    mock_set_value.assert_awaited_once_with(expected)
