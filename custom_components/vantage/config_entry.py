"""Vantage config entry."""

from dataclasses import dataclass

from homeassistant.config_entries import ConfigEntry

from aiovantage import Vantage

type VantageConfigEntry = ConfigEntry[VantageData]


@dataclass
class VantageData:
    """Data for a Vantage config entry."""

    client: Vantage
