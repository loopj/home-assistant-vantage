"""Support for Vantage diagnostics."""

from collections import Counter
import contextlib
from typing import Any

from aiovantage.errors import ClientError

from homeassistant.components.diagnostics import async_redact_data  # type: ignore
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant

from .config_entry import VantageConfigEntry

# A reset controller's password is its serial number, so redact it too
TO_REDACT = {CONF_HOST, CONF_PASSWORD, CONF_USERNAME, "serial_number", "unique_id"}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: VantageConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    vantage = entry.runtime_data.client

    # Describe each controller in the system, with its firmware version
    masters: list[dict[str, Any]] = []
    for master in vantage.masters:
        firmware = None
        with contextlib.suppress(ClientError):
            firmware = await master.get_application_version()

        masters.append(
            {
                "vid": master.vid,
                "name": master.name,
                "model": master.model,
                "number": master.number,
                "serial_number": master.serial_number,
                "firmware": firmware,
            }
        )

    # Report whether state updates come from the Enhanced Log or category status
    status_type = vantage.loads.status_type

    return async_redact_data(  # type: ignore
        {
            "config_entry": entry.as_dict(),
            "connected": entry.runtime_data.connected,
            "master_number": vantage.master_number,
            "peers": vantage.peers,
            "masters": masters,
            "status_type": status_type.name if status_type else None,
            "objects": dict(
                sorted(Counter(type(obj).__name__ for obj in vantage).items())
            ),
        },
        TO_REDACT,
    )
