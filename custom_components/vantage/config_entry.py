"""Vantage config entry."""

from dataclasses import dataclass

from homeassistant.config_entries import ConfigEntry

from aiovantage import Vantage

from .const import DOMAIN

type VantageConfigEntry = ConfigEntry[VantageData]


@dataclass
class VantageData:
    """Data for a Vantage config entry."""

    client: Vantage
    entry_id: str
    connected: bool = True

    @property
    def signal_connection_changed(self) -> str:
        """Dispatcher signal sent when the controller connection is lost or restored."""
        return f"{DOMAIN}_connection_changed_{self.entry_id}"
