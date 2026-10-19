"""Tests for the Vantage InFusion cover platform."""

from typing import Any
from unittest.mock import patch

from aiovantage import Vantage
import pytest
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    snapshot_platform,
)
from syrupy.assertion import SnapshotAssertion

from homeassistant.components.cover import (
    ATTR_POSITION,
    DOMAIN as COVER_DOMAIN,
    SERVICE_CLOSE_COVER,
    SERVICE_OPEN_COVER,
    SERVICE_SET_COVER_POSITION,
    SERVICE_STOP_COVER,
)
from homeassistant.const import ATTR_ENTITY_ID, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

pytestmark = [
    pytest.mark.parametrize("init_integration", [Platform.COVER], indirect=True),
    pytest.mark.usefixtures("init_integration"),
]


async def test_entities(
    hass: HomeAssistant,
    entity_registry: er.EntityRegistry,
    snapshot: SnapshotAssertion,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test the cover entities."""
    await snapshot_platform(hass, entity_registry, snapshot, mock_config_entry.entry_id)


@pytest.mark.parametrize(
    ("service", "service_data", "method", "args"),
    [
        (SERVICE_OPEN_COVER, {}, "open", ()),
        (SERVICE_CLOSE_COVER, {}, "close", ()),
        (SERVICE_STOP_COVER, {}, "stop", ()),
        (SERVICE_SET_COVER_POSITION, {ATTR_POSITION: 25}, "set_position", (25,)),
    ],
)
async def test_cover(
    hass: HomeAssistant,
    mock_vantage: Vantage,
    service: str,
    service_data: dict[str, Any],
    method: str,
    args: tuple[Any, ...],
) -> None:
    """Test the Vantage covers."""
    with patch.object(mock_vantage.blinds[20], method) as mock_method:
        await hass.services.async_call(
            COVER_DOMAIN,
            service,
            {ATTR_ENTITY_ID: "cover.kitchen_shade", **service_data},
            blocking=True,
        )

    mock_method.assert_awaited_once_with(*args)
