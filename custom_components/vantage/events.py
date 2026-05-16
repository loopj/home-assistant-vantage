"""Handle forwarding Vantage events to the Home Assistant event bus."""

from typing import Any

from aiovantage.events import ObjectUpdated, StatusReceived
from aiovantage.objects import Task

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

    def on_button_status(event: StatusReceived) -> None:
        """Forward S:BTN status messages to the HA event bus.

        aiovantage emits button presses as ``StatusReceived(category="BTN", ...)``
        from the event stream, not as ``ObjectUpdated`` on the buttons controller,
        so we subscribe to the raw status stream here.
        """
        is_press = bool(event.args) and event.args[0].upper() == "PRESS"

        button = vantage.buttons.get(event.vid)
        payload: dict[str, Any] = {"button_id": event.vid}
        if button is not None:
            payload["button_name"] = button.name
            payload["button_text1"] = getattr(button, "text1", None)
            payload["button_text2"] = getattr(button, "text2", None)
            parent = getattr(button, "parent", None)
            if parent is not None:
                payload["button_position"] = getattr(parent, "position", None)
                station = vantage.stations.get(parent.vid)
                if station is not None:
                    payload["station_id"] = station.vid
                    payload["station_name"] = station.name

        hass.bus.async_fire(
            EVENT_BUTTON_PRESSED if is_press else EVENT_BUTTON_RELEASED,
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

    # Button presses arrive as S:BTN status messages on the event stream.
    entry.async_on_unload(
        vantage.event_stream.subscribe_status(on_button_status, "BTN")
    )
    # Task events still come through the controller dispatcher.
    entry.async_on_unload(vantage.tasks.subscribe(ObjectUpdated, on_task_updated))
