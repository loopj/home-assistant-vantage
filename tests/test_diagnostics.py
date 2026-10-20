"""Tests for the Vantage InFusion diagnostics."""

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.components.diagnostics import (
    get_diagnostics_for_config_entry,
)
from pytest_homeassistant_custom_component.typing import ClientSessionGenerator
from syrupy.assertion import SnapshotAssertion
from syrupy.filters import props

from homeassistant.core import HomeAssistant


@pytest.mark.usefixtures("init_integration")
async def test_entry_diagnostics(
    hass: HomeAssistant,
    hass_client: ClientSessionGenerator,
    mock_config_entry: MockConfigEntry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test config entry diagnostics."""
    result = await get_diagnostics_for_config_entry(
        hass, hass_client, mock_config_entry
    )
    assert result == snapshot(exclude=props("created_at", "modified_at", "entry_id"))
