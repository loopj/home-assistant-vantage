"""Config flow for Vantage InFusion Controller integration."""
from __future__ import annotations

import re
from typing import Any

import voluptuous as vol
from aiovantage.discovery import (
    DiscoveredVantageController,
    discover_controller,
    valid_credentials,
)
from aiovantage.errors import ClientConnectionError
from homeassistant import config_entries
from homeassistant.components import zeroconf
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_SSL, CONF_USERNAME
from homeassistant.data_entry_flow import FlowResult

from .const import DOMAIN

AUTH_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
    }
)


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for Vantage InFusion Controller."""

    VERSION = 1

    controller: DiscoveredVantageController | None = None
    username: str | None = None
    password: str | None = None
    reauth_entry: ConfigEntry | None = None

    async def async_finish(self) -> FlowResult:
        """Create the config entry with the gathered information."""
        assert self.controller is not None
        return self.async_create_entry(
            title="Vantage InFusion",
            data={
                CONF_HOST: self.controller.host,
                CONF_SSL: self.controller.supports_ssl,
                CONF_USERNAME: self.username,
                CONF_PASSWORD: self.password,
            },
        )

    async def async_step_auth(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle collecting authentication information."""
        errors: dict[str, str] | None = None
        if user_input is not None:
            assert self.controller is not None

            # Validate the credentials
            errors = await self._validate_credentials(
                self.controller.host,
                user_input[CONF_USERNAME],
                user_input[CONF_PASSWORD],
                self.controller.supports_ssl,
            )

            # If valid, store the credentials and move on
            if not errors:
                self.username = user_input[CONF_USERNAME]
                self.password = user_input[CONF_PASSWORD]

                return await self.async_finish()

        # Show the auth input form
        return self.async_show_form(
            step_id="auth",
            data_schema=AUTH_SCHEMA,
            errors=errors,
        )

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle a flow initialized by the user."""
        errors: dict[str, str] = {}
        if user_input is not None:
            # Abort if this controller is already configured
            self._async_abort_entries_match({CONF_HOST: user_input[CONF_HOST]})

            # Get information about the controller
            try:
                self.controller = await discover_controller(user_input[CONF_HOST])
            except ClientConnectionError:
                errors["base"] = "cannot_connect"

            # Show either the auth form or finish the config flow
            if self.controller:
                if self.controller.requires_auth:
                    return await self.async_step_auth()
                return await self.async_finish()

        # Show the host input form
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HOST): str,
                }
            ),
            errors=errors,
        )

    async def async_step_zeroconf(
        self, discovery_info: zeroconf.ZeroconfServiceInfo
    ) -> FlowResult:
        """Handle a discovered Vantage controller."""
        serial_number = self._serial_number_from_hostname(discovery_info.hostname)
        if serial_number is None:
            return self.async_abort(reason="invalid_host")

        # Abort if this controller is already configured, update the host if it changed
        await self.async_set_unique_id(serial_number)
        self._abort_if_unique_id_configured(updates={CONF_HOST: discovery_info.host})

        # Get information about the controller
        try:
            self.controller = await discover_controller(discovery_info.host)
        except ClientConnectionError:
            return self.async_abort(reason="cannot_connect")

        # Show either the auth form or the confirmation form
        if self.controller.requires_auth:
            return await self.async_step_auth()
        return await self.async_step_zeroconf_confirm()

    async def async_step_zeroconf_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle a user confirming the discovered Vantage controller."""
        if user_input is not None:
            return await self.async_finish()

        # Show the confirmation form
        assert self.controller is not None
        return self.async_show_form(
            step_id="zeroconf_confirm",
            description_placeholders={
                "host": self.controller.host,
            },
        )

    async def async_step_reauth(
        self, _entry_data: dict[str, Any] | None = None
    ) -> FlowResult:
        """Perform reauth after controller authentication error."""
        self.reauth_entry = self.hass.config_entries.async_get_entry(
            self.context["entry_id"]
        )
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Dialog that informs the user that reauth is required."""
        errors: dict[str, str] | None = None
        if user_input is not None:
            # Get the config entry
            assert self.reauth_entry is not None

            # Validate the credentials
            errors = await self._validate_credentials(
                self.reauth_entry.data[CONF_HOST],
                user_input[CONF_USERNAME],
                user_input[CONF_PASSWORD],
                self.reauth_entry.data[CONF_SSL],
            )

            if not errors:
                # Update the config entry with the new credentials
                self.hass.config_entries.async_update_entry(
                    self.reauth_entry,
                    data={
                        **self.reauth_entry.data,
                        CONF_USERNAME: user_input[CONF_USERNAME],
                        CONF_PASSWORD: user_input[CONF_PASSWORD],
                    },
                )

                # Reload the integration and finish the config flow
                await self.hass.config_entries.async_reload(self.reauth_entry.entry_id)
                return self.async_abort(reason="reauth_successful")

        # Show the re-authentication form
        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=AUTH_SCHEMA,
            errors=errors,
        )

    @staticmethod
    async def _validate_credentials(
        host: str, username: str, password: str, ssl: bool
    ) -> dict[str, str] | None:
        """Validate the credentials for a Vantage controller."""
        try:
            if not await valid_credentials(host, username, password, ssl):
                return {"base": "invalid_auth"}
        except ClientConnectionError:
            return {"base": "cannot_connect"}

        return None

    @staticmethod
    def _serial_number_from_hostname(hostname: str) -> str | None:
        """Get the serial number from a Vantage hostname."""
        match = re.match(r"ic-ii-(?P<serial_number>\d+)", hostname)
        if not match:
            return None
        return match.group("serial_number")
