"""The Vantage InFusion Controller integration."""

import asyncio
from typing import Any

from aiovantage import Vantage, VantageEvent
from aiovantage.errors import (
    ClientConnectionError,
    LoginFailedError,
    LoginRequiredError,
)
from aiovantage.models import Master

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigEntryAuthFailed,
    ConfigEntryNotReady,
)
from homeassistant.const import (
    CONF_HOST,
    CONF_PASSWORD,
    CONF_SSL,
    CONF_USERNAME,
    Platform,
)
from homeassistant.core import HomeAssistant
from homeassistant.util.ssl import get_default_no_verify_context

from .const import DOMAIN
from .device import async_setup_devices
from .entity import async_cleanup_entities
from .events import async_setup_events
from .migrate import async_migrate_data
from .services import async_register_services

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.CLIMATE,
    Platform.COVER,
    Platform.LIGHT,
    Platform.NUMBER,
    Platform.SENSOR,
    Platform.SWITCH,
    Platform.TEXT,
]

# How long to wait after receiving a system programming event before refreshing
SYSTEM_PROGRAMMING_DELAY = 30


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Vantage integration from a config entry."""
    # Create a Vantage client
    vantage = Vantage(
        entry.data[CONF_HOST],
        entry.data.get(CONF_USERNAME),
        entry.data.get(CONF_PASSWORD),
        ssl=(
            get_default_no_verify_context() if entry.data.get(CONF_SSL, True) else False
        ),
    )

    # Store the client in the hass data store
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = vantage

    try:
        # Initialize and fetch all objects
        await vantage.initialize()

        # Register vantage domain services
        async_register_services(hass)

        # Add Vantage devices (controllers, modules, stations) to the device registry
        async_setup_devices(hass, entry)

        # Generate events for button presses
        async_setup_events(hass, entry)

        # Set up each platform (lights, covers, etc.)
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

        # Clean up any orphaned entities
        async_cleanup_entities(hass, entry)

        # Subscribe to system programming events
        async def handle_system_program_event(
            event: VantageEvent, obj: Master, data: dict[str, Any]
        ) -> None:
            # Return early if the last_updated attribute did not change
            if "last_updated" not in data.get("attrs_changed", []):
                return

            # The last_updated attribute changes at the start of system programming.
            # Unfortunately, the Vantage controller does not send an event when
            # programming ends, so we must wait for a short time before refreshing
            # controllers to avoid fetching incomplete data.
            await asyncio.sleep(SYSTEM_PROGRAMMING_DELAY)
            await vantage.initialize()

        vantage.masters.subscribe(
            handle_system_program_event, event_filter=VantageEvent.OBJECT_UPDATED
        )

    except (LoginFailedError, LoginRequiredError) as err:
        # Handle expired or invalid credentials. This will prompt the user to
        # reconfigure the integration.
        raise ConfigEntryAuthFailed from err

    except ClientConnectionError as err:
        # Handle connection errors. Home Assistant will automatically take care of
        # retrying set up later.
        raise ConfigEntryNotReady from err

    # Run any migrations
    await async_migrate_data(hass, entry)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    vantage: Vantage = hass.data[DOMAIN].pop(entry.entry_id, None)
    if vantage:
        vantage.close()

    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
