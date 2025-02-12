"""The Vantage InFusion Controller integration."""

import asyncio

from aiovantage import Vantage
from aiovantage.errors import (
    ClientConnectionError,
    LoginFailedError,
    LoginRequiredError,
)
from aiovantage.events import ObjectUpdated
from aiovantage.objects import Master

from homeassistant.config_entries import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.const import (
    CONF_HOST,
    CONF_PASSWORD,
    CONF_SSL,
    CONF_USERNAME,
    Platform,
)
from homeassistant.core import HomeAssistant
from homeassistant.util.ssl import get_default_no_verify_context

from .config_entry import VantageConfigEntry, VantageData
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


async def async_setup_entry(hass: HomeAssistant, entry: VantageConfigEntry) -> bool:
    """Set up Vantage integration from a config entry."""
    # Create a Vantage client
    vantage = Vantage(
        entry.data[CONF_HOST],
        entry.data.get(CONF_USERNAME),
        entry.data.get(CONF_PASSWORD),
        ssl=entry.data.get(CONF_SSL, True),
        ssl_context_factory=get_default_no_verify_context,
    )

    # Store the client in the config entry's runtime data
    entry.runtime_data = VantageData(client=vantage)

    try:
        # Initialize and fetch all objects
        await vantage.initialize()

        # Add Vantage devices (controllers, modules, stations) to the device registry
        await async_setup_devices(hass, entry)

        # Set up each platform (lights, covers, etc.)
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

        # Register services (start task, stop task, etc.)
        async_register_services(hass)

        # Generate events for button presses, etc.
        async_setup_events(hass, entry)

        # Clean up any orphaned entities
        async_cleanup_entities(hass, entry)

        # Run any migrations
        await async_migrate_data(hass, entry)

        # Subscribe to system programming events
        def on_master_updated(event: ObjectUpdated[Master]) -> None:
            # Return early if the m_time attribute did not change
            if "m_time" not in event.attrs_changed:
                return

            async def refresh_controllers() -> None:
                # The m_time attribute changes at the start of system programming.
                # Unfortunately, the Vantage controller does not send an event when
                # programming ends, so we must wait for a short time before refreshing
                # controllers to avoid fetching incomplete data.
                await asyncio.sleep(SYSTEM_PROGRAMMING_DELAY)
                await vantage.initialize()

            hass.async_create_task(refresh_controllers())

        entry.async_on_unload(
            vantage.masters.subscribe(ObjectUpdated, on_master_updated)
        )

    except (LoginFailedError, LoginRequiredError) as err:
        # Handle expired or invalid credentials. This will prompt the user to
        # reconfigure the integration.
        raise ConfigEntryAuthFailed from err

    except ClientConnectionError as err:
        # Handle connection errors. Home Assistant will automatically take care of
        # retrying set up later.
        raise ConfigEntryNotReady from err

    return True


async def async_unload_entry(hass: HomeAssistant, entry: VantageConfigEntry) -> bool:
    """Unload a config entry."""
    # Close the Vantage client connection
    entry.runtime_data.client.close()

    # Unload all platforms
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
