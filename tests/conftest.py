"""Fixtures for the Vantage InFusion integration tests."""

from collections.abc import Generator
from contextlib import nullcontext
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch

from aiovantage import Vantage
from aiovantage.controllers import StatusType
from aiovantage.discovery import VantageControllerDetails
from aiovantage.objects import (
    AnemoSensor,
    Area,
    BlindGroup,
    Button,
    DryContact,
    GMem,
    Keypad,
    LightSensor,
    Load,
    LoadGroup,
    Master,
    Module,
    OmniSensor,
    Parent,
    PowerProfile,
    QISBlind,
    Task,
    Temperature,
    Thermostat,
    VantageDGColorLoad,
    VantageGenericHVACRS485ZoneChild,
)
from aiovantage.object_interfaces import FanInterface, ThermostatInterface
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.syrupy import HomeAssistantSnapshotExtension
from syrupy.assertion import SnapshotAssertion

from custom_components.vantage.const import DOMAIN
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_SSL, CONF_USERNAME
from homeassistant.core import HomeAssistant

from . import setup_integration

HOST = "192.168.1.100"
SERIAL_NUMBER = 12345678
USERNAME = "administrator"
PASSWORD = "secret"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Let Home Assistant load the integration from custom_components."""


@pytest.fixture(autouse=True)
def auto_mock_zeroconf(mock_async_zeroconf: MagicMock) -> None:
    """Keep the zeroconf dependency off the network."""


@pytest.fixture
def snapshot(snapshot: SnapshotAssertion) -> SnapshotAssertion:
    """Serialize snapshots the way Home Assistant core does."""
    return snapshot.use_extension(HomeAssistantSnapshotExtension)


@pytest.fixture
def entity_registry_enabled_by_default() -> Generator[None]:
    """Enable every entity, including those disabled by default."""
    with patch(
        "homeassistant.helpers.entity.Entity.entity_registry_enabled_default",
        return_value=True,
        new_callable=PropertyMock,
    ):
        yield


@pytest.fixture
def mock_config_entry() -> MockConfigEntry:
    """Return a config entry for a controller that requires authentication."""
    return MockConfigEntry(
        title="Vantage InFusion",
        domain=DOMAIN,
        data={
            CONF_HOST: HOST,
            CONF_SSL: True,
            CONF_USERNAME: USERNAME,
            CONF_PASSWORD: PASSWORD,
        },
        unique_id=str(SERIAL_NUMBER),
    )


@pytest.fixture
def mock_setup_entry() -> Generator[AsyncMock]:
    """Skip setting up the config entry the flow creates."""
    with patch(
        "custom_components.vantage.async_setup_entry", return_value=True
    ) as setup_entry:
        yield setup_entry


@pytest.fixture
def mock_get_controller_details() -> Generator[AsyncMock]:
    """Report a reachable controller that supports SSL and requires authentication."""
    with patch(
        "custom_components.vantage.config_flow.get_controller_details",
        return_value=VantageControllerDetails(
            HOST, supports_ssl=True, requires_auth=True
        ),
    ) as get_controller_details:
        yield get_controller_details


@pytest.fixture
def mock_validate_credentials() -> Generator[AsyncMock]:
    """Accept any credentials."""
    with patch(
        "custom_components.vantage.config_flow.validate_credentials",
        return_value=True,
    ) as validate_credentials:
        yield validate_credentials


@pytest.fixture
def mock_get_serial_from_controller() -> Generator[AsyncMock]:
    """Report the controller's serial number."""
    with patch(
        "custom_components.vantage.config_flow.get_serial_from_controller",
        return_value=SERIAL_NUMBER,
    ) as get_serial_from_controller:
        yield get_serial_from_controller


@pytest.fixture
def mock_vantage() -> Generator[Vantage]:
    """Return a Vantage client loaded with one object of each supported kind."""
    vantage = Vantage(HOST, USERNAME, PASSWORD)

    # The controller, with a module and a keypad in the kitchen
    master = Master(
        vid=1,
        master=1,
        name="Controller 1",
        model="",
        note="",
        number=1,
        serial_number=SERIAL_NUMBER,
    )
    master.get_application_version = AsyncMock(return_value="4.1.1.4")
    kitchen = Area(vid=2, master=1, name="Kitchen", model="", note="", area_type="Room")
    module = Module(
        vid=3,
        master=1,
        name="Module 1",
        model="",
        note="",
        parent=Parent(vid=1, position=1),
        join1=False,
        join2=False,
        join3=False,
        join4=False,
        quiet_mode=False,
    )
    keypad = Keypad(
        vid=4,
        master=1,
        name="Kitchen Keypad",
        model="",
        note="",
        area=2,
        serial_number="87654321",
        bus=1,
        parent=Parent(vid=1, position=1),
    )
    dimmer_profile = PowerProfile(
        vid=5, master=1, name="Dimmer", model="", note="", min=0, max=100
    )

    # Lights and relays
    kitchen_light = Load(
        vid=10,
        master=1,
        name="Pendant",
        model="",
        note="",
        area=2,
        parent=Parent(vid=3, position=1),
        contractor_number="",
        power_profile=5,
    )
    kitchen_light.level = Decimal(50)
    porch_light = Load(
        vid=17,
        master=1,
        name="Porch Light",
        model="",
        note="",
        parent=Parent(vid=3, position=3),
        contractor_number="",
        power_profile=0,
    )
    porch_light.level = Decimal(100)
    fan_relay = Load(
        vid=11,
        master=1,
        name="Fan",
        model="",
        note="",
        parent=Parent(vid=3, position=2),
        contractor_number="",
        load_type="High Voltage Relay",
        power_profile=0,
    )
    fan_relay.level = Decimal(0)
    all_lights = LoadGroup(vid=12, master=1, name="All Lights", model="", note="")
    all_lights.level = Decimal(100)
    color_loads = [
        VantageDGColorLoad(
            vid=vid,
            master=1,
            name=f"{color_type.value} Light",
            model="",
            note="",
            parent=Parent(vid=3, position=vid),
            color_type=color_type,
            min_temp=2700,
            max_temp=6500,
        )
        for vid, color_type in [
            (13, VantageDGColorLoad.ColorType.RGB),
            (14, VantageDGColorLoad.ColorType.RGBW),
            (15, VantageDGColorLoad.ColorType.HSL),
            (16, VantageDGColorLoad.ColorType.CCT),
        ]
    ]
    for color_load in color_loads:
        color_load.level = Decimal(100)
        color_load.rgb = (255, 0, 0)
        color_load.rgbw = (255, 0, 0, 0)
        color_load.hsl = (0, 100, 50)
        color_load.color_temp = 3000

    # Blinds
    kitchen_shade = QISBlind(
        vid=20,
        master=1,
        name="Kitchen Shade",
        model="",
        note="",
        serial_number="",
        bus=1,
        upper_limit=100,
        lower_limit=0,
        movement=QISBlind.Movement(),
    )
    kitchen_shade.position = Decimal(50)
    all_shades = BlindGroup(
        vid=21, master=1, name="All Shades", model="", note="", category=0
    )

    # Thermostats, one with fan speeds, and the thermostat's sensors
    thermostat = Thermostat(
        vid=30,
        master=1,
        name="Thermostat",
        model="",
        note="",
        serial_number="",
        bus=1,
        external_temperature=0,
    )
    hvac_zone = VantageGenericHVACRS485ZoneChild(
        vid=31,
        master=1,
        name="HVAC Zone",
        model="",
        note="",
        version=1.0,
        parent=Parent(vid=3, position=1),
        indoor_settings=VantageGenericHVACRS485ZoneChild.IndoorSettings(
            indoor_sensor=0
        ),
    )
    hvac_zone.speed = FanInterface.FanSpeed.Auto
    for climate in (thermostat, hvac_zone):
        climate.indoor_temperature = Decimal(21)
        climate.heat_set_point = Decimal(20)
        climate.cool_set_point = Decimal(24)
        climate.operation_mode = ThermostatInterface.OperationMode.Heat
        climate.fan_mode = ThermostatInterface.FanMode.Off
        climate.status = ThermostatInterface.Status.Heating
        climate.is_enumerator_supported = AsyncMock(return_value=True)
    thermostat_contact = DryContact(
        vid=32,
        master=1,
        name="Thermostat Contact",
        model="",
        note="",
        parent=Parent(vid=30, position=5),
        reverse_polarity=False,
    )
    thermostat_temperatures = [
        Temperature(
            vid=vid,
            master=1,
            name=name,
            model="",
            note="",
            parent=Parent(vid=30, position=position),
            range_high=50,
            range_low=0,
            hold_on_time=0,
        )
        for vid, name, position in [
            (33, "Indoor Temperature", 1),
            (34, "Cool Set Point", 3),
            (35, "Heat Set Point", 4),
        ]
    ]
    for temperature, value in zip(thermostat_temperatures, (21, 24, 20), strict=True):
        temperature.value = Decimal(value)

    # Polled sensors
    wind_sensor = AnemoSensor(
        vid=40,
        master=1,
        name="Wind Sensor",
        model="",
        note="",
        parent=Parent(vid=3, position=1),
        hold_on_time=0,
    )
    wind_sensor.speed = Decimal(5)
    light_sensor = LightSensor(
        vid=41,
        master=1,
        name="Light Sensor",
        model="",
        note="",
        parent=Parent(vid=3, position=1),
    )
    light_sensor.level = Decimal(10)
    module_power = OmniSensor(
        vid=42,
        master=1,
        name="Module Power",
        model="Power",
        note="",
        parent=Parent(vid=3, position=1),
        get=OmniSensor.Get(
            formula=OmniSensor.Get.Formula(formula=""),
            method="GetPower",
            method_hw="GetPowerHW",
        ),
        set=OmniSensor.Set(
            formula=OmniSensor.Set.Formula(formula=""),
            method="SetPower",
            method_sw="SetPowerSW",
        ),
    )
    module_power.level = Decimal(120)

    # Variables
    variables = [
        GMem(
            vid=vid,
            master=1,
            name=name,
            model="",
            note="",
            category=0,
            data=GMem.Data(fixed=fixed),
            tag=GMem.Tag(type=tag_type),
        )
        for vid, name, tag_type, fixed in [
            (50, "Away Mode", "bool", False),
            (51, "Scene Number", "Number", False),
            (52, "Message", "Text", False),
            (53, "Setpoint Offset", "Decimal", True),
        ]
    ]
    for variable, value in zip(variables, (1, 3, "Hello", 1500), strict=True):
        variable.value = value

    # A task, and a button on the kitchen keypad
    task = Task(vid=60, master=1, name="Goodnight", model="", note="")
    button = Button(
        vid=61,
        master=1,
        name="Kitchen Button",
        model="",
        note="",
        parent=Parent(vid=4, position=1),
        text1="All",
        text2="On",
        button_style=0,
        led_style=0,
    )

    # Load each controller as if the controller had been queried
    for controller, objects in [
        (vantage.masters, [master]),
        (vantage.areas, [kitchen]),
        (vantage.modules, [module]),
        (vantage.stations, [keypad]),
        (vantage.power_profiles, [dimmer_profile]),
        (vantage.loads, [kitchen_light, porch_light, fan_relay]),
        (vantage.load_groups, [all_lights]),
        (vantage.rgb_loads, color_loads),
        (vantage.blinds, [kitchen_shade]),
        (vantage.blind_groups, [all_shades]),
        (vantage.thermostats, [thermostat, hvac_zone]),
        (vantage.dry_contacts, [thermostat_contact]),
        (vantage.temperatures, thermostat_temperatures),
        (vantage.anemo_sensors, [wind_sensor]),
        (vantage.light_sensors, [light_sensor]),
        (vantage.omni_sensors, [module_power]),
        (vantage.gmem, variables),
        (vantage.tasks, [task]),
        (vantage.buttons, [button]),
    ]:
        controller._objects.update((obj.vid, obj) for obj in objects)  # type: ignore
    vantage.thermostats._status_type = StatusType.OBJECT  # type: ignore

    with (
        patch("custom_components.vantage.Vantage", return_value=vantage),
        patch.object(vantage, "initialize"),
    ):
        yield vantage


@pytest.fixture
async def init_integration(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_vantage: Vantage,
    request: pytest.FixtureRequest,
) -> MockConfigEntry:
    """Set up the integration, with only the platform given as a parameter."""
    context = nullcontext()
    if platform := getattr(request, "param", None):
        context = patch("custom_components.vantage.PLATFORMS", [platform])

    with context:
        await setup_integration(hass, mock_config_entry)

    return mock_config_entry
