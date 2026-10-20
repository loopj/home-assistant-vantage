"""Tests for the Vantage InFusion actions."""

from typing import Any
from unittest.mock import patch

from aiovantage import Vantage
from aiovantage.errors import ClientConnectionError
import pytest

from custom_components.vantage.const import (
    DOMAIN,
    SERVICE_START_TASK,
    SERVICE_STOP_TASK,
)
from homeassistant.const import ATTR_ID, ATTR_NAME
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError

pytestmark = pytest.mark.usefixtures("init_integration")


@pytest.mark.parametrize(
    ("service", "method"),
    [(SERVICE_START_TASK, "start"), (SERVICE_STOP_TASK, "stop")],
)
@pytest.mark.parametrize("service_data", [{ATTR_ID: 60}, {ATTR_NAME: "Goodnight"}])
async def test_task_actions(
    hass: HomeAssistant,
    mock_vantage: Vantage,
    service: str,
    method: str,
    service_data: dict[str, Any],
) -> None:
    """Test starting and stopping a task by id or by name."""
    with patch.object(mock_vantage.tasks[60], method) as mock_method:
        await hass.services.async_call(DOMAIN, service, service_data, blocking=True)

    mock_method.assert_awaited_once_with()


async def test_task_not_found(
    hass: HomeAssistant,
    mock_vantage: Vantage,
) -> None:
    """Test starting a task the controller does not have."""
    with pytest.raises(
        ServiceValidationError,
        match='Task "Good Morning" not found in any Vantage controller',
    ):
        await hass.services.async_call(
            DOMAIN, SERVICE_START_TASK, {ATTR_NAME: "Good Morning"}, blocking=True
        )


@pytest.mark.parametrize(
    ("service", "method", "error_match"),
    [
        (SERVICE_START_TASK, "start", 'Failed to start task "Goodnight"'),
        (SERVICE_STOP_TASK, "stop", 'Failed to stop task "Goodnight"'),
    ],
)
async def test_task_action_error(
    hass: HomeAssistant,
    mock_vantage: Vantage,
    service: str,
    method: str,
    error_match: str,
) -> None:
    """Test a task action when the controller request fails."""
    with (
        patch.object(mock_vantage.tasks[60], method, side_effect=ClientConnectionError),
        pytest.raises(HomeAssistantError, match=error_match),
    ):
        await hass.services.async_call(DOMAIN, service, {ATTR_ID: 60}, blocking=True)
