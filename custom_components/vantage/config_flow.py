"""Config flow for Vantage InFusion Controller integration."""

from typing import Any

from aiovantage.discovery import (
    VantageControllerDetails,
    get_controller_details,
    get_serial_from_controller,
    get_serial_from_hostname,
    validate_credentials,
)
from aiovantage.errors import ClientConnectionError
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.components import zeroconf
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_SSL, CONF_USERNAME
from homeassistant.data_entry_flow import FlowResult

from .const import DOMAIN

USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
    }
)

AUTH_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
    }
)

DEFAULT_VANTAGE_USERNAME = "administrator"


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for Vantage InFusion integration."""

    VERSION = 1

    controller: VantageControllerDetails | None = None
    username: str | None = None
    password: str | None = None
    reauth_entry: ConfigEntry | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle a flow initiated by the user."""
        if user_input is None:
            return self.async_show_form(step_id="user", data_schema=USER_SCHEMA)

        # Abort if this exact host is already configured
        self._async_abort_entries_match({CONF_HOST: user_input[CONF_HOST]})

        # Get information about the controller, show an error if it cannot be reached
        self.controller = await get_controller_details(user_input[CONF_HOST])
        if self.controller is None:
            return self.async_show_form(
                step_id="user",
                data_schema=USER_SCHEMA,
                errors={"base": "cannot_connect"},
            )

        # Show either the auth form or the confirmation form
        if self.controller.requires_auth:
            return await self.async_step_auth()
        return await self.async_finish()

    async def async_step_zeroconf(
        self, discovery_info: zeroconf.ZeroconfServiceInfo
    ) -> FlowResult:
        """Handle a flow initiated by zeroconf discovery."""
        serial_number = get_serial_from_hostname(discovery_info.hostname)
        if serial_number is None:
            return self.async_abort(reason="unknown")

        # Abort if this controller is already configured, update the host if it changed
        await self.async_set_unique_id(serial_number)
        self._abort_if_unique_id_configured(updates={CONF_HOST: discovery_info.host})

        # Get information about the controller, abort if it cannot be reached
        self.controller = await get_controller_details(discovery_info.host)
        if self.controller is None:
            return self.async_abort(reason="cannot_connect")

        # Show either the auth form or the confirmation form
        if self.controller.requires_auth:
            return await self.async_step_auth()
        return await self.async_step_zeroconf_confirm()

    async def async_step_zeroconf_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle a user confirming the discovered Vantage controller."""
        assert self.controller is not None

        # Show the confirmation form
        if user_input is None:
            return self.async_show_form(
                step_id="zeroconf_confirm",
                description_placeholders={
                    "host": self.controller.host,
                },
            )

        # Move on to the final step
        return await self.async_finish()

    async def async_step_auth(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle collecting authentication information."""
        assert self.controller is not None

        errors: dict[str, str] | None = None
        suggestions: dict[str, str] = {CONF_USERNAME: DEFAULT_VANTAGE_USERNAME}

        if user_input is not None:
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

            # Pre-fill the username field with the previous input
            suggestions[CONF_USERNAME] = user_input[CONF_USERNAME]

        # Show the auth input form
        return self.async_show_form(
            step_id="auth",
            data_schema=self.add_suggested_values_to_schema(AUTH_SCHEMA, suggestions),
            errors=errors,
            description_placeholders={
                "host": self.controller.host,
            },
        )

    async def async_finish(self) -> FlowResult:
        """Create the config entry with the gathered information."""
        assert self.controller is not None

        # Look up the first controller's serial number
        serial_number = await get_serial_from_controller(
            self.controller.host,
            self.username,
            self.password,
            self.controller.supports_ssl,
        )

        if serial_number is None:
            return self.async_abort(reason="cannot_connect")

        # Set the unique ID to the serial number, abort if it is already configured
        await self.async_set_unique_id(str(serial_number), raise_on_progress=False)
        self._abort_if_unique_id_configured(updates={CONF_HOST: self.controller.host})

        # Create the config entry
        return self.async_create_entry(
            title="Vantage InFusion",
            data={
                CONF_HOST: self.controller.host,
                CONF_SSL: self.controller.supports_ssl,
                CONF_USERNAME: self.username,
                CONF_PASSWORD: self.password,
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
        assert self.reauth_entry is not None

        errors: dict[str, str] | None = None
        suggestions: dict[str, str] = {
            CONF_USERNAME: self.reauth_entry.data[CONF_USERNAME]
        }

        if user_input is not None:
            # Validate the credentials
            errors = await self._validate_credentials(
                self.reauth_entry.data[CONF_HOST],
                user_input[CONF_USERNAME],
                user_input[CONF_PASSWORD],
                self.reauth_entry.data.get(CONF_SSL, True),
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

            # Pre-fill the username field with the previous input
            suggestions[CONF_USERNAME] = user_input[CONF_USERNAME]

        # Show the re-authentication form
        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=self.add_suggested_values_to_schema(AUTH_SCHEMA, suggestions),
            errors=errors,
            description_placeholders={
                "host": self.reauth_entry.data[CONF_HOST],
            },
        )

    @staticmethod
    async def _validate_credentials(
        host: str, username: str, password: str, ssl: bool
    ) -> dict[str, str] | None:
        """Validate the credentials for a Vantage controller, returning errors if invalid."""
        try:
            if not await validate_credentials(host, username, password, ssl):
                return {"base": "invalid_auth"}
        except ClientConnectionError:
            return {"base": "cannot_connect"}

        return None
