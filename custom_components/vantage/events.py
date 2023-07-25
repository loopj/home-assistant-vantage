"""Handle forwarding Vantage events to the  Home Assistant event bus."""

from typing import Any

from aiovantage import Vantage, VantageEvent
from aiovantage.models import Button, Task

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import (
    DOMAIN,
    EVENT_BUTTON_PRESSED,
    EVENT_BUTTON_RELEASED,
    EVENT_TASK_STARTED,
    EVENT_TASK_STATE_CHANGED,
    EVENT_TASK_STOPPED,
)


def async_setup_events(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Set up Vantage events from a config entry."""
    vantage: Vantage = hass.data[DOMAIN][entry.entry_id]

    def handle_button_event(_event: VantageEvent, obj: Button, data: Any) -> None:
        """Handle button press/release events."""
        if "pressed" not in data["attrs_changed"]:
            return

        payload = {
            "button_id": obj.id,
            "button_name": obj.name,
            "button_position": obj.parent_position,
            "button_text1": obj.text1,
            "button_text2": obj.text2,
        }

        if station := vantage.stations.get(obj.parent_id):
            payload["station_id"] = station.id
            payload["station_name"] = station.name

        hass.bus.async_fire(
            EVENT_BUTTON_PRESSED if obj.pressed else EVENT_BUTTON_RELEASED,
            payload,
        )

    def handle_task_event(_event: VantageEvent, obj: Task, data: Any) -> None:
        """Handle task events."""
        if "is_running" in data["attrs_changed"]:
            # Fire task started/stopped event
            payload = {
                "task_id": obj.id,
                "task_name": obj.name,
            }

            hass.bus.async_fire(
                EVENT_TASK_STARTED if obj.is_running else EVENT_TASK_STOPPED,
                payload,
            )

        elif "state" in data["attrs_changed"]:
            # Fire task state changed event
            payload = {
                "task_id": obj.id,
                "task_name": obj.name,
                "task_state": obj.state,
            }

            hass.bus.async_fire(EVENT_TASK_STATE_CHANGED, payload)

    # Subscribe to button events
    entry.async_on_unload(
        vantage.buttons.subscribe(
            handle_button_event, event_filter=VantageEvent.OBJECT_UPDATED
        )
    )

    # Subscribe to task events
    entry.async_on_unload(
        vantage.tasks.subscribe(
            handle_task_event, event_filter=VantageEvent.OBJECT_UPDATED
        )
    )
