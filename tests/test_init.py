"""Tests for setting up the Vantage InFusion integration."""

from dataclasses import replace
from unittest.mock import patch

from aiovantage import Vantage
from aiovantage.errors import ClientConnectionError, LoginFailedError
from aiovantage.events import (
    Disconnected,
    ObjectAdded,
    ObjectDeleted,
    ObjectUpdated,
    Reconnected,
)
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.vantage.const import DOMAIN
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import STATE_OFF, STATE_ON, STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er

from . import setup_integration


async def test_load_unload_entry(
    hass: HomeAssistant,
    mock_vantage: Vantage,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test loading and unloading the config entry."""
    await setup_integration(hass, mock_config_entry)

    assert mock_config_entry.state is ConfigEntryState.LOADED

    with patch.object(mock_vantage, "close") as mock_close:
        await hass.config_entries.async_unload(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    assert mock_config_entry.state is ConfigEntryState.NOT_LOADED
    mock_close.assert_called_once()


@pytest.mark.parametrize(
    ("exception", "state"),
    [
        (LoginFailedError, ConfigEntryState.SETUP_ERROR),
        (ClientConnectionError, ConfigEntryState.SETUP_RETRY),
    ],
)
async def test_setup_entry_errors(
    hass: HomeAssistant,
    mock_vantage: Vantage,
    mock_config_entry: MockConfigEntry,
    exception: Exception,
    state: ConfigEntryState,
) -> None:
    """Test the config entry state when the controller cannot be reached."""
    mock_vantage.initialize.side_effect = exception  # type: ignore

    await setup_integration(hass, mock_config_entry)

    assert mock_config_entry.state is state


async def test_connection_lost(
    hass: HomeAssistant,
    mock_vantage: Vantage,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test that entities are unavailable while the connection is down."""
    await setup_integration(hass, mock_config_entry)

    mock_vantage.event_stream.emit(Disconnected())
    await hass.async_block_till_done()
    assert (state := hass.states.get("light.kitchen_pendant"))
    assert state.state == STATE_UNAVAILABLE

    mock_vantage.event_stream.emit(Reconnected())
    await hass.async_block_till_done()
    assert (state := hass.states.get("light.kitchen_pendant"))
    assert state.state == STATE_ON


async def test_system_programming(
    hass: HomeAssistant,
    mock_vantage: Vantage,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test that objects are fetched again after the project is reprogrammed."""
    await setup_integration(hass, mock_config_entry)
    mock_vantage.initialize.reset_mock()  # type: ignore

    with patch("custom_components.vantage.SYSTEM_PROGRAMMING_DELAY", 0):
        mock_vantage.masters.emit(ObjectUpdated(mock_vantage.masters[1], ["m_time"]))
        await hass.async_block_till_done()

    mock_vantage.initialize.assert_awaited_once()  # type: ignore


async def test_stale_registry_entries_removed(
    hass: HomeAssistant,
    device_registry: dr.DeviceRegistry,
    entity_registry: er.EntityRegistry,
    mock_vantage: Vantage,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test that setup removes devices and entities the controller no longer has."""
    mock_config_entry.add_to_hass(hass)
    stale_device = device_registry.async_get_or_create(
        config_entry_id=mock_config_entry.entry_id, identifiers={(DOMAIN, "999")}
    )
    back_box = device_registry.async_get_or_create(
        config_entry_id=mock_config_entry.entry_id,
        identifiers={(DOMAIN, "2")},
        model="BackBox",
    )
    stale_entity = entity_registry.async_get_or_create(
        "light", DOMAIN, "999", config_entry=mock_config_entry
    )
    serial_number = entity_registry.async_get_or_create(
        "sensor", DOMAIN, "1:serial_number", config_entry=mock_config_entry
    )
    ip_address = entity_registry.async_get_or_create(
        "sensor", DOMAIN, "1:ip_address", config_entry=mock_config_entry
    )

    await setup_integration(hass, mock_config_entry)

    assert device_registry.async_get(stale_device.id) is None
    assert device_registry.async_get(back_box.id) is None
    assert entity_registry.async_get(stale_entity.entity_id) is None
    assert entity_registry.async_get(serial_number.entity_id) is None
    assert entity_registry.async_get(ip_address.entity_id) is None


async def test_dynamic_objects(
    hass: HomeAssistant,
    device_registry: dr.DeviceRegistry,
    entity_registry: er.EntityRegistry,
    mock_vantage: Vantage,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test adding, updating and deleting objects after setup."""
    await setup_integration(hass, mock_config_entry)

    # Add a light
    sconce = replace(mock_vantage.loads[10], vid=18, name="Sconce")
    mock_vantage.loads.emit(ObjectAdded(sconce))
    await hass.async_block_till_done()
    assert (state := hass.states.get("light.kitchen_sconce"))
    assert state.state == STATE_OFF

    # Turn it on, and rename its device
    sconce.level = 100
    sconce.d_name = "Kitchen Sconce"
    mock_vantage.loads.emit(ObjectUpdated(sconce, ["level", "d_name"]))
    await hass.async_block_till_done()
    assert (state := hass.states.get("light.kitchen_sconce"))
    assert state.state == STATE_ON
    device = device_registry.async_get_device_by_identifier(
        (DOMAIN, "18"), mock_config_entry.entry_id
    )
    assert device
    assert device.name == "Kitchen Sconce"

    # Delete it
    mock_vantage.loads.emit(ObjectDeleted(sconce))
    await hass.async_block_till_done()
    assert entity_registry.async_get("light.kitchen_sconce") is None
    assert (
        device_registry.async_get_device_by_identifier(
            (DOMAIN, "18"), mock_config_entry.entry_id
        )
        is None
    )


async def test_dynamic_devices(
    hass: HomeAssistant,
    device_registry: dr.DeviceRegistry,
    mock_vantage: Vantage,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test adding, updating and deleting devices after setup."""
    await setup_integration(hass, mock_config_entry)

    # Add a module
    module = replace(mock_vantage.modules[3], vid=5, name="Module 2")
    mock_vantage.modules.emit(ObjectAdded(module))
    await hass.async_block_till_done()
    assert device_registry.async_get_device_by_identifier(
        (DOMAIN, "5"), mock_config_entry.entry_id
    )

    # Rename it
    module.name = "Basement Module"
    mock_vantage.modules.emit(ObjectUpdated(module, ["name"]))
    await hass.async_block_till_done()
    device = device_registry.async_get_device_by_identifier(
        (DOMAIN, "5"), mock_config_entry.entry_id
    )
    assert device
    assert device.name == "Basement Module"

    # Delete it
    mock_vantage.modules.emit(ObjectDeleted(module))
    await hass.async_block_till_done()
    assert (
        device_registry.async_get_device_by_identifier(
            (DOMAIN, "5"), mock_config_entry.entry_id
        )
        is None
    )
