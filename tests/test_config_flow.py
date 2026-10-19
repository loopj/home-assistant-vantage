"""Tests for the Vantage InFusion config flow."""

from dataclasses import replace
from ipaddress import ip_address
from unittest.mock import AsyncMock

from aiovantage.discovery import VantageControllerDetails
from aiovantage.errors import ClientConnectionError
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.vantage.const import DOMAIN
from homeassistant.config_entries import SOURCE_USER, SOURCE_ZEROCONF
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_SSL, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers.service_info.zeroconf import ZeroconfServiceInfo

from .conftest import HOST, PASSWORD, SERIAL_NUMBER, USERNAME

pytestmark = pytest.mark.usefixtures(
    "mock_setup_entry",
    "mock_get_controller_details",
    "mock_validate_credentials",
    "mock_get_serial_from_controller",
)

ZEROCONF_DISCOVERY = ZeroconfServiceInfo(
    ip_address=ip_address(HOST),
    ip_addresses=[ip_address(HOST)],
    port=443,
    hostname=f"ic-ii-{SERIAL_NUMBER}.local.",
    name=f"ic-ii-{SERIAL_NUMBER}._secure_aci._tcp.local.",
    properties={},
    type="_secure_aci._tcp.local.",
)


async def test_user_flow(hass: HomeAssistant) -> None:
    """Test setting up a controller that requires authentication."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={CONF_HOST: HOST}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "auth"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={CONF_USERNAME: USERNAME, CONF_PASSWORD: PASSWORD},
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Vantage InFusion"

    config_entry = result["result"]
    assert config_entry.unique_id == str(SERIAL_NUMBER)
    assert config_entry.data == {
        CONF_HOST: HOST,
        CONF_SSL: True,
        CONF_USERNAME: USERNAME,
        CONF_PASSWORD: PASSWORD,
    }


async def test_user_flow_without_auth(
    hass: HomeAssistant, mock_get_controller_details: AsyncMock
) -> None:
    """Test setting up a controller that does not require authentication."""
    mock_get_controller_details.return_value = VantageControllerDetails(
        HOST, supports_ssl=False, requires_auth=False
    )

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={CONF_HOST: HOST}
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["result"].data == {
        CONF_HOST: HOST,
        CONF_SSL: False,
        CONF_USERNAME: None,
        CONF_PASSWORD: None,
    }


async def test_user_flow_errors(
    hass: HomeAssistant, mock_get_controller_details: AsyncMock
) -> None:
    """Test the user step shows an error until the controller can be reached."""
    details = mock_get_controller_details.return_value
    mock_get_controller_details.return_value = None

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={CONF_HOST: HOST}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {"base": "cannot_connect"}

    mock_get_controller_details.return_value = details
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={CONF_HOST: HOST}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={CONF_USERNAME: USERNAME, CONF_PASSWORD: PASSWORD},
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY


@pytest.mark.parametrize(
    ("validate_result", "expected_error"),
    [
        ({"return_value": False}, "invalid_auth"),
        ({"side_effect": ClientConnectionError}, "cannot_connect"),
    ],
)
async def test_user_flow_auth_errors(
    hass: HomeAssistant,
    mock_validate_credentials: AsyncMock,
    validate_result: dict[str, object],
    expected_error: str,
) -> None:
    """Test the auth step shows an error until the credentials are accepted."""
    mock_validate_credentials.configure_mock(**validate_result)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={CONF_HOST: HOST}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={CONF_USERNAME: USERNAME, CONF_PASSWORD: "wrong"},
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "auth"
    assert result["errors"] == {"base": expected_error}

    mock_validate_credentials.configure_mock(return_value=True, side_effect=None)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={CONF_USERNAME: USERNAME, CONF_PASSWORD: PASSWORD},
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY


async def test_user_flow_already_configured(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Test the user step aborts when the host is already configured."""
    mock_config_entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={CONF_HOST: HOST}
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_user_flow_abort_no_serial(
    hass: HomeAssistant, mock_get_serial_from_controller: AsyncMock
) -> None:
    """Test the flow aborts when the controller does not report a serial number."""
    mock_get_serial_from_controller.return_value = None

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={CONF_HOST: HOST}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={CONF_USERNAME: USERNAME, CONF_PASSWORD: PASSWORD},
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "cannot_connect"


async def test_zeroconf_flow(hass: HomeAssistant) -> None:
    """Test setting up a discovered controller that requires authentication."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_ZEROCONF}, data=ZEROCONF_DISCOVERY
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "auth"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={CONF_USERNAME: USERNAME, CONF_PASSWORD: PASSWORD},
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["result"].unique_id == str(SERIAL_NUMBER)


async def test_zeroconf_flow_without_auth(
    hass: HomeAssistant, mock_get_controller_details: AsyncMock
) -> None:
    """Test confirming a discovered controller that does not require authentication."""
    mock_get_controller_details.return_value = VantageControllerDetails(
        HOST, supports_ssl=True, requires_auth=False
    )

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_ZEROCONF}, data=ZEROCONF_DISCOVERY
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "zeroconf_confirm"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={}
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY


async def test_zeroconf_flow_abort_no_serial(hass: HomeAssistant) -> None:
    """Test discovery aborts when the hostname has no serial number."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_ZEROCONF},
        data=replace(ZEROCONF_DISCOVERY, hostname="infusion.local."),
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "unknown"


async def test_zeroconf_flow_not_discovered_again(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Test discovery does not offer a controller that is already configured."""
    mock_config_entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_ZEROCONF}, data=ZEROCONF_DISCOVERY
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_zeroconf_flow_abort_system_configured(hass: HomeAssistant) -> None:
    """Test discovering another master aborts once a system is configured."""
    MockConfigEntry(domain=DOMAIN, unique_id="87654321").add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_ZEROCONF}, data=ZEROCONF_DISCOVERY
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_zeroconf_flow_abort_cannot_connect(
    hass: HomeAssistant, mock_get_controller_details: AsyncMock
) -> None:
    """Test discovery aborts when the controller cannot be reached."""
    mock_get_controller_details.return_value = None

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_ZEROCONF}, data=ZEROCONF_DISCOVERY
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "cannot_connect"


async def test_reauth_flow(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_validate_credentials: AsyncMock,
) -> None:
    """Test reauthentication shows an error until new credentials are accepted."""
    mock_config_entry.add_to_hass(hass)
    mock_validate_credentials.return_value = False

    result = await mock_config_entry.start_reauth_flow(hass)

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reauth_confirm"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={CONF_USERNAME: USERNAME, CONF_PASSWORD: "wrong"},
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_auth"}

    mock_validate_credentials.return_value = True
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={CONF_USERNAME: "installer", CONF_PASSWORD: "new-secret"},
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert mock_config_entry.data == {
        CONF_HOST: HOST,
        CONF_SSL: True,
        CONF_USERNAME: "installer",
        CONF_PASSWORD: "new-secret",
    }
