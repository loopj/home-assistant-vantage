"""Fixtures for the Vantage InFusion integration tests."""

from collections.abc import Generator
from unittest.mock import AsyncMock, MagicMock, patch

from aiovantage.discovery import VantageControllerDetails
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.vantage.const import DOMAIN
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_SSL, CONF_USERNAME

HOST = "192.168.1.100"
SERIAL_NUMBER = 12345678
USERNAME = "administrator"
PASSWORD = "secret"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Let Home Assistant load the integration from custom_components."""


@pytest.fixture(autouse=True)
def auto_mock_zeroconf(mock_async_zeroconf: MagicMock) -> None:
    """Keep the zeroconf dependency off the network."""


@pytest.fixture
def mock_config_entry() -> MockConfigEntry:
    """Return a config entry for a controller that requires authentication."""
    return MockConfigEntry(
        title="Vantage InFusion",
        domain=DOMAIN,
        data={
            CONF_HOST: HOST,
            CONF_SSL: True,
            CONF_USERNAME: USERNAME,
            CONF_PASSWORD: PASSWORD,
        },
        unique_id=str(SERIAL_NUMBER),
    )


@pytest.fixture
def mock_setup_entry() -> Generator[AsyncMock]:
    """Skip setting up the config entry the flow creates."""
    with patch(
        "custom_components.vantage.async_setup_entry", return_value=True
    ) as setup_entry:
        yield setup_entry


@pytest.fixture
def mock_get_controller_details() -> Generator[AsyncMock]:
    """Report a reachable controller that supports SSL and requires authentication."""
    with patch(
        "custom_components.vantage.config_flow.get_controller_details",
        return_value=VantageControllerDetails(
            HOST, supports_ssl=True, requires_auth=True
        ),
    ) as get_controller_details:
        yield get_controller_details


@pytest.fixture
def mock_validate_credentials() -> Generator[AsyncMock]:
    """Accept any credentials."""
    with patch(
        "custom_components.vantage.config_flow.validate_credentials",
        return_value=True,
    ) as validate_credentials:
        yield validate_credentials


@pytest.fixture
def mock_get_serial_from_controller() -> Generator[AsyncMock]:
    """Report the controller's serial number."""
    with patch(
        "custom_components.vantage.config_flow.get_serial_from_controller",
        return_value=SERIAL_NUMBER,
    ) as get_serial_from_controller:
        yield get_serial_from_controller
