"""Tests for the Vantage InFusion text platform."""

from unittest.mock import patch

from aiovantage import Vantage
from aiovantage.events import ObjectUpdated
import pytest
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    snapshot_platform,
)
from syrupy.assertion import SnapshotAssertion

from homeassistant.components.text import (
    ATTR_VALUE,
    DOMAIN as TEXT_DOMAIN,
    SERVICE_SET_VALUE,
)
from homeassistant.const import ATTR_ENTITY_ID, STATE_UNKNOWN, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

pytestmark = [
    pytest.mark.parametrize("init_integration", [Platform.TEXT], indirect=True),
    pytest.mark.usefixtures("init_integration"),
]


async def test_entities(
    hass: HomeAssistant,
    entity_registry: er.EntityRegistry,
    snapshot: SnapshotAssertion,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test the text entities."""
    await snapshot_platform(hass, entity_registry, snapshot, mock_config_entry.entry_id)


async def test_text(hass: HomeAssistant, mock_vantage: Vantage) -> None:
    """Test the Vantage text variables."""
    with patch.object(mock_vantage.gmem[52], "set_value") as mock_set_value:
        await hass.services.async_call(
            TEXT_DOMAIN,
            SERVICE_SET_VALUE,
            {ATTR_ENTITY_ID: "text.variables_message", ATTR_VALUE: "Goodbye"},
            blocking=True,
        )

    mock_set_value.assert_awaited_once_with("Goodbye")


async def test_text_without_value(hass: HomeAssistant, mock_vantage: Vantage) -> None:
    """Test a text variable that has no value."""
    obj = mock_vantage.gmem[52]
    obj.value = None
    mock_vantage.gmem.emit(ObjectUpdated(obj, ["value"]))
    await hass.async_block_till_done()

    assert (state := hass.states.get("text.variables_message"))
    assert state.state == STATE_UNKNOWN
