"""Tests for the Vantage InFusion events."""

from typing import Any

from aiovantage import Vantage
from aiovantage.events import ObjectUpdated
from aiovantage.objects import Button
import pytest
from pytest_homeassistant_custom_component.common import async_capture_events

from homeassistant.core import HomeAssistant

from custom_components.vantage.const import (
    EVENT_BUTTON_PRESSED,
    EVENT_BUTTON_RELEASED,
    EVENT_TASK_STARTED,
    EVENT_TASK_STATE_CHANGED,
    EVENT_TASK_STOPPED,
)

pytestmark = pytest.mark.usefixtures("init_integration")


@pytest.mark.parametrize(
    ("state", "event_type"),
    [
        (Button.State.Down, EVENT_BUTTON_PRESSED),
        (Button.State.Up, EVENT_BUTTON_RELEASED),
    ],
)
async def test_button_events(
    hass: HomeAssistant,
    mock_vantage: Vantage,
    state: Button.State,
    event_type: str,
) -> None:
    """Test that button presses and releases fire events."""
    events = async_capture_events(hass, event_type)

    button = mock_vantage.buttons[61]
    button.state = state
    mock_vantage.buttons.emit(ObjectUpdated(button, ["state"]))
    await hass.async_block_till_done()

    assert len(events) == 1
    assert events[0].data == {
        "button_id": 61,
        "button_name": "Kitchen Button",
        "button_position": 1,
        "button_text1": "All",
        "button_text2": "On",
        "station_id": 4,
        "station_name": "Kitchen Keypad",
    }


@pytest.mark.parametrize(
    ("attrs", "event_type", "data"),
    [
        (
            {"running": True},
            EVENT_TASK_STARTED,
            {"task_id": 60, "task_name": "Goodnight"},
        ),
        (
            {"running": False},
            EVENT_TASK_STOPPED,
            {"task_id": 60, "task_name": "Goodnight"},
        ),
        (
            {"state": 2},
            EVENT_TASK_STATE_CHANGED,
            {"task_id": 60, "task_name": "Goodnight", "task_state": 2},
        ),
    ],
)
async def test_task_events(
    hass: HomeAssistant,
    mock_vantage: Vantage,
    attrs: dict[str, Any],
    event_type: str,
    data: dict[str, Any],
) -> None:
    """Test that task changes fire events."""
    events = async_capture_events(hass, event_type)

    task = mock_vantage.tasks[60]
    for attr, value in attrs.items():
        setattr(task, attr, value)
    mock_vantage.tasks.emit(ObjectUpdated(task, list(attrs)))
    await hass.async_block_till_done()

    assert len(events) == 1
    assert events[0].data == data
