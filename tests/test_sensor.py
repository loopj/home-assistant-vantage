"""Tests for the Vantage InFusion sensor platform."""

from unittest.mock import patch

from aiovantage import Vantage
from aiovantage.errors import ClientConnectionError
import pytest
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    snapshot_platform,
)
from syrupy.assertion import SnapshotAssertion

from homeassistant.const import STATE_UNAVAILABLE, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_component import async_update_entity

pytestmark = pytest.mark.parametrize(
    "init_integration", [Platform.SENSOR], indirect=True
)


@pytest.mark.usefixtures("entity_registry_enabled_by_default", "init_integration")
async def test_entities(
    hass: HomeAssistant,
    entity_registry: er.EntityRegistry,
    snapshot: SnapshotAssertion,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test the sensor entities."""
    await snapshot_platform(hass, entity_registry, snapshot, mock_config_entry.entry_id)


@pytest.mark.usefixtures("init_integration")
async def test_sensor_poll_error(hass: HomeAssistant, mock_vantage: Vantage) -> None:
    """Test that a polled sensor is unavailable until a poll succeeds."""
    obj = mock_vantage.anemo_sensors[40]

    with patch.object(obj, "fetch_state", side_effect=ClientConnectionError):
        await async_update_entity(hass, "sensor.wind_sensor")
    assert (sensor := hass.states.get("sensor.wind_sensor"))
    assert sensor.state == STATE_UNAVAILABLE

    with patch.object(obj, "fetch_state"):
        await async_update_entity(hass, "sensor.wind_sensor")
    assert (sensor := hass.states.get("sensor.wind_sensor"))
    assert sensor.state != STATE_UNAVAILABLE
