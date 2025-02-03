"""Handle Vantage service calls."""

from typing import Any
from aiovantage import Vantage
from aiovantage.objects import Task
import voluptuous as vol

from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import ATTR_ID, ATTR_NAME
from homeassistant.core import HomeAssistant, ServiceCall
import homeassistant.helpers.config_validation as cv

from .const import DOMAIN, LOGGER, SERVICE_START_TASK, SERVICE_STOP_TASK

TASK_SCHEMA = vol.All(
    cv.has_at_most_one_key(ATTR_ID, ATTR_NAME),  # type: ignore
    cv.has_at_least_one_key(ATTR_ID, ATTR_NAME),  # type: ignore
    vol.Schema(
        {
            ATTR_ID: cv.positive_int,
            ATTR_NAME: str,
        }
    ),
)


def async_register_services(hass: HomeAssistant) -> None:
    """Register services for Vantage integration."""

    def find_task(id_or_name: Any) -> Task | None:
        # Build a query for the task
        if isinstance(id_or_name, int):
            query = {"vid": id_or_name}
        elif isinstance(id_or_name, str):
            query = {"name": id_or_name}
        else:
            return None

        # Search for the task in all loaded config entries
        for entry in hass.config_entries.async_entries(DOMAIN):
            if entry.state is not ConfigEntryState.LOADED:
                continue

            vantage: Vantage = entry.runtime_data.client
            if task := vantage.tasks.get(**query):
                return task

        return None

    async def start_task(call: ServiceCall) -> None:
        """Start a Vantage task by id or name."""
        task_id_or_name = call.data.get(ATTR_ID) or call.data.get(ATTR_NAME)

        if task := find_task(task_id_or_name):
            await task.start()
            return

        LOGGER.warning("Task '%s' not found in any Vantage controller", task_id_or_name)

    async def stop_task(call: ServiceCall) -> None:
        """Stop a Vantage task by id or name."""
        task_id_or_name = call.data.get(ATTR_ID) or call.data.get(ATTR_NAME)

        if task := find_task(task_id_or_name):
            await task.stop()
            return

        LOGGER.warning("Task '%s' not found in any Vantage controller", task_id_or_name)

    # Register services
    if not hass.services.has_service(DOMAIN, SERVICE_START_TASK):
        hass.services.async_register(
            DOMAIN, SERVICE_START_TASK, start_task, schema=TASK_SCHEMA
        )

    if not hass.services.has_service(DOMAIN, SERVICE_STOP_TASK):
        hass.services.async_register(
            DOMAIN, SERVICE_STOP_TASK, stop_task, schema=TASK_SCHEMA
        )
