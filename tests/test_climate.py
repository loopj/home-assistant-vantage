"""Tests for the Vantage InFusion climate platform."""

from decimal import Decimal
from typing import Any
from unittest.mock import patch

from aiovantage import Vantage
from aiovantage.events import ObjectUpdated
from aiovantage.object_interfaces import FanInterface, ThermostatInterface
import pytest
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    snapshot_platform,
)
from syrupy.assertion import SnapshotAssertion

from homeassistant.components.climate import (
    ATTR_FAN_MODE,
    ATTR_HVAC_MODE,
    ATTR_TARGET_TEMP_HIGH,
    ATTR_TARGET_TEMP_LOW,
    DOMAIN as CLIMATE_DOMAIN,
    FAN_HIGH,
    FAN_ON,
    SERVICE_SET_FAN_MODE,
    SERVICE_SET_HVAC_MODE,
    SERVICE_SET_TEMPERATURE,
    HVACMode,
)
from homeassistant.const import ATTR_ENTITY_ID, ATTR_TEMPERATURE, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import entity_registry as er

from . import setup_integration


@pytest.mark.parametrize("init_integration", [Platform.CLIMATE], indirect=True)
@pytest.mark.usefixtures("init_integration")
async def test_entities(
    hass: HomeAssistant,
    entity_registry: er.EntityRegistry,
    snapshot: SnapshotAssertion,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test the climate entities."""
    await snapshot_platform(hass, entity_registry, snapshot, mock_config_entry.entry_id)


@pytest.mark.parametrize(
    ("entity_id", "vid", "service", "service_data", "method", "args"),
    [
        (
            "climate.thermostat",
            30,
            SERVICE_SET_HVAC_MODE,
            {ATTR_HVAC_MODE: HVACMode.COOL},
            "set_operation_mode",
            (ThermostatInterface.OperationMode.Cool,),
        ),
        (
            "climate.thermostat",
            30,
            SERVICE_SET_FAN_MODE,
            {ATTR_FAN_MODE: FAN_ON},
            "set_fan_mode",
            (ThermostatInterface.FanMode.On,),
        ),
        (
            "climate.hvac_zone",
            31,
            SERVICE_SET_FAN_MODE,
            {ATTR_FAN_MODE: FAN_HIGH},
            "set_speed",
            (FanInterface.FanSpeed.High,),
        ),
    ],
)
@pytest.mark.parametrize("init_integration", [Platform.CLIMATE], indirect=True)
@pytest.mark.usefixtures("init_integration")
async def test_climate(
    hass: HomeAssistant,
    mock_vantage: Vantage,
    entity_id: str,
    vid: int,
    service: str,
    service_data: dict[str, Any],
    method: str,
    args: tuple[Any, ...],
) -> None:
    """Test the Vantage thermostats."""
    with patch.object(mock_vantage[vid], method) as mock_method:
        await hass.services.async_call(
            CLIMATE_DOMAIN,
            service,
            {ATTR_ENTITY_ID: entity_id, **service_data},
            blocking=True,
        )

    mock_method.assert_awaited_once_with(*args)


@pytest.mark.parametrize(
    ("operation_mode", "service_data", "heat_set_point", "cool_set_point"),
    [
        (ThermostatInterface.OperationMode.Heat, {ATTR_TEMPERATURE: 22}, 22, None),
        (ThermostatInterface.OperationMode.Cool, {ATTR_TEMPERATURE: 23}, None, 23),
        (
            ThermostatInterface.OperationMode.Auto,
            {ATTR_TARGET_TEMP_LOW: 19, ATTR_TARGET_TEMP_HIGH: 25},
            19,
            25,
        ),
    ],
)
async def test_set_temperature(
    hass: HomeAssistant,
    mock_vantage: Vantage,
    mock_config_entry: MockConfigEntry,
    operation_mode: ThermostatInterface.OperationMode,
    service_data: dict[str, Any],
    heat_set_point: float | None,
    cool_set_point: float | None,
) -> None:
    """Test setting the set points that match the HVAC mode."""
    obj = mock_vantage.thermostats[30]
    obj.operation_mode = operation_mode
    await setup_integration(hass, mock_config_entry)

    with (
        patch.object(obj, "set_heat_set_point") as mock_set_heat_set_point,
        patch.object(obj, "set_cool_set_point") as mock_set_cool_set_point,
    ):
        await hass.services.async_call(
            CLIMATE_DOMAIN,
            SERVICE_SET_TEMPERATURE,
            {ATTR_ENTITY_ID: "climate.thermostat", **service_data},
            blocking=True,
        )

    if heat_set_point is None:
        mock_set_heat_set_point.assert_not_awaited()
    else:
        mock_set_heat_set_point.assert_awaited_once_with(heat_set_point)

    if cool_set_point is None:
        mock_set_cool_set_point.assert_not_awaited()
    else:
        mock_set_cool_set_point.assert_awaited_once_with(cool_set_point)


async def test_set_temperature_in_off_mode(
    hass: HomeAssistant,
    mock_vantage: Vantage,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test that a temperature cannot be set while the thermostat is off."""
    mock_vantage.thermostats[30].operation_mode = ThermostatInterface.OperationMode.Off
    await setup_integration(hass, mock_config_entry)

    with pytest.raises(ServiceValidationError, match="Cannot set temperature"):
        await hass.services.async_call(
            CLIMATE_DOMAIN,
            SERVICE_SET_TEMPERATURE,
            {ATTR_ENTITY_ID: "climate.thermostat", ATTR_TEMPERATURE: 22},
            blocking=True,
        )


async def test_legacy_thermostat(
    hass: HomeAssistant,
    mock_vantage: Vantage,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test that 2.x firmware thermostats follow their temperature sensors."""
    mock_vantage.thermostats._status_type = None  # type: ignore
    await setup_integration(hass, mock_config_entry)

    # Only Thermostat objects are supported on 2.x firmware
    assert not hass.states.get("climate.hvac_zone")

    for vid, value in [(33, 18), (34, 26), (35, 17)]:
        temperature = mock_vantage.temperatures[vid]
        temperature.value = Decimal(value)
        mock_vantage.temperatures.emit(ObjectUpdated(temperature, ["value"]))
    await hass.async_block_till_done()

    assert (state := hass.states.get("climate.thermostat"))
    assert state.attributes["current_temperature"] == 18
    assert state.attributes["temperature"] == 17
    assert mock_vantage.thermostats[30].cool_set_point == 26


@pytest.mark.parametrize("init_integration", [Platform.CLIMATE], indirect=True)
@pytest.mark.usefixtures("init_integration")
async def test_set_temperature_with_hvac_mode(
    hass: HomeAssistant, mock_vantage: Vantage
) -> None:
    """Test setting a temperature and switching HVAC mode in one action."""
    obj = mock_vantage.thermostats[30]

    with (
        patch.object(obj, "set_operation_mode") as mock_set_operation_mode,
        patch.object(obj, "set_heat_set_point") as mock_set_heat_set_point,
        patch.object(obj, "set_cool_set_point") as mock_set_cool_set_point,
    ):
        await hass.services.async_call(
            CLIMATE_DOMAIN,
            SERVICE_SET_TEMPERATURE,
            {
                ATTR_ENTITY_ID: "climate.thermostat",
                ATTR_HVAC_MODE: HVACMode.COOL,
                ATTR_TEMPERATURE: 23,
            },
            blocking=True,
        )

    mock_set_operation_mode.assert_awaited_once_with(
        ThermostatInterface.OperationMode.Cool
    )
    mock_set_cool_set_point.assert_awaited_once_with(23)
    mock_set_heat_set_point.assert_not_awaited()
