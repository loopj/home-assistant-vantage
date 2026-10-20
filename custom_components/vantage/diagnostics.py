"""Support for Vantage diagnostics."""

from collections import Counter
import contextlib
from typing import Any

from aiovantage.errors import ClientError

from homeassistant.const import CONF_SSL
from homeassistant.core import HomeAssistant

from .config_entry import VantageConfigEntry


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: VantageConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    vantage = entry.runtime_data.client

    # Describe each controller
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
                "firmware": firmware,
            }
        )

    # Report whether state updates come from the Enhanced Log or category status
    status_type = vantage.loads.status_type

    return {
        "ssl": entry.data[CONF_SSL],
        "connected": entry.runtime_data.connected,
        "master_number": vantage.master_number,
        "peers": vantage.peers,
        "masters": masters,
        "status_type": status_type.name if status_type else None,
        "objects": dict(sorted(Counter(type(obj).__name__ for obj in vantage).items())),
    }
