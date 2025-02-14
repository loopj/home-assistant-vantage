"""Handle forwarding Vantage events to the  Home Assistant event bus."""

from aiovantage.events import ObjectUpdated
from aiovantage.objects import Button, Task

from homeassistant.core import HomeAssistant

from .config_entry import VantageConfigEntry
from .const import (
    EVENT_BUTTON_PRESSED,
    EVENT_BUTTON_RELEASED,
    EVENT_TASK_STARTED,
    EVENT_TASK_STATE_CHANGED,
    EVENT_TASK_STOPPED,
)


def async_setup_events(hass: HomeAssistant, entry: VantageConfigEntry) -> None:
    """Set up Vantage events from a config entry."""
    vantage = entry.runtime_data.client

    def on_button_updated(event: ObjectUpdated[Button]) -> None:
        """Handle button press/release events."""
        if "state" not in event.attrs_changed:
            return

        payload = {
            "button_id": event.obj.vid,
            "button_name": event.obj.name,
            "button_position": event.obj.parent.position,
            "button_text1": event.obj.text1,
            "button_text2": event.obj.text2,
        }

        if station := vantage.stations.get(event.obj.parent.vid):
            payload["station_id"] = station.vid
            payload["station_name"] = station.name

        hass.bus.async_fire(
            EVENT_BUTTON_PRESSED if event.obj.is_down else EVENT_BUTTON_RELEASED,
            payload,
        )

    def on_task_updated(event: ObjectUpdated[Task]) -> None:
        """Handle task events."""
        if "running" in event.attrs_changed:
            # Fire task started/stopped event
            payload = {
                "task_id": event.obj.vid,
                "task_name": event.obj.name,
            }

            hass.bus.async_fire(
                EVENT_TASK_STARTED if event.obj.running else EVENT_TASK_STOPPED,
                payload,
            )

        if "state" in event.attrs_changed:
            # Fire task state changed event
            payload = {
                "task_id": event.obj.vid,
                "task_name": event.obj.name,
                "task_state": event.obj.state,
            }

            hass.bus.async_fire(EVENT_TASK_STATE_CHANGED, payload)

    # Subscribe to button and task events
    entry.async_on_unload(vantage.buttons.subscribe(ObjectUpdated, on_button_updated))
    entry.async_on_unload(vantage.tasks.subscribe(ObjectUpdated, on_task_updated))
