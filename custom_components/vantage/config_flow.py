"""Config flow for Vantage InFusion Controller integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from aiovantage.command_client import CommandClient
from aiovantage.errors import (
    ClientConnectionError,
    LoginFailedError,
    LoginRequiredError,
)
from homeassistant import config_entries
from homeassistant.components import zeroconf
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""


HOST_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): cv.string,
    }
)

AUTH_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): cv.string,
        vol.Required(CONF_PASSWORD): cv.string,
    }
)


async def _validate_host(host: str) -> None:
    # Attempt to connect to a Vantage host
    try:
        async with CommandClient(host) as client:
            await client.command("ECHO")
    except ClientConnectionError as err:
        raise CannotConnect from err
    except LoginRequiredError:
        pass


async def _auth_required(host: str) -> bool:
    # Connect to the host without a username/password
    async with CommandClient(host) as client:
        try:
            await client.command("ECHO")
        except LoginRequiredError:
            return True

    return False


async def _validate_credentials(host: str, username: str, password: str) -> None:
    # Attempt to connect to the host with the username/password
    async with CommandClient(host) as client:
        try:
            await client.command("LOGIN", username, password)
        except LoginFailedError as err:
            raise InvalidAuth from err


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Vantage InFusion Controller."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the Vantage config flow."""
        self.data: dict[str, Any] = {}

    async def async_step_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Confirm we want to add this controller to Home Assistant."""

        if user_input is not None:
            return self.async_create_entry(title="Vantage InFusion", data=self.data)

        return self.async_show_form(step_id="confirm")

    async def async_step_auth(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle authenticating with the Vantage controller.

        If this controller requires authentication, show a form asking for credentials.
        Otherwise, move on to the confirmation step.
        """

        if user_input is None:
            # Check if we can connect without auth before asking for credentials
            if not await _auth_required(self.data["host"]):
                return await self.async_step_confirm()

        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                await _validate_credentials(
                    self.data["host"],
                    user_input[CONF_USERNAME],
                    user_input[CONF_PASSWORD],
                )
            except InvalidAuth:
                errors["base"] = "invalid_auth"

            if not errors:
                self.data.update(
                    {
                        "username": user_input[CONF_USERNAME],
                        "password": user_input[CONF_PASSWORD],
                    }
                )

                return await self.async_step_confirm()

        return self.async_show_form(
            step_id="auth", data_schema=AUTH_SCHEMA, errors=errors
        )

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle a flow initialized by the user."""

        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                await _validate_host(user_input[CONF_HOST])
            except CannotConnect:
                errors["base"] = "cannot_connect"

            if not errors:
                self.data.update(
                    {
                        "host": user_input[CONF_HOST],
                    }
                )

                return await self.async_step_auth()

        return self.async_show_form(
            step_id="user", data_schema=HOST_SCHEMA, errors=errors
        )

    async def async_step_zeroconf(
        self, discovery_info: zeroconf.ZeroconfServiceInfo
    ) -> FlowResult:
        """Handle a discovered Hue bridge.

        This flow is triggered by the Zeroconf component. It will check if the
        host is already configured and delegate to the auth step if not.
        """

        # Abort if we have already configured this controller
        await self.async_set_unique_id(discovery_info.hostname)
        self._abort_if_unique_id_configured()

        # Pass the host to the next step
        self.data = {
            "host": discovery_info.host,
            "zeroconf": True,
        }

        return await self.async_step_auth()
