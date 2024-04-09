"""Handle Vantage service calls."""

from aiovantage import Vantage
from aiovantage.models import Task
import voluptuous as vol

from homeassistant.const import ATTR_ID, ATTR_NAME
from homeassistant.core import HomeAssistant, ServiceCall
import homeassistant.helpers.config_validation as cv

from .const import DOMAIN, LOGGER, SERVICE_START_TASK, SERVICE_STOP_TASK

TASK_SCHEMA = vol.All(
    cv.has_at_most_one_key(ATTR_ID, ATTR_NAME),
    cv.has_at_least_one_key(ATTR_ID, ATTR_NAME),
    vol.Schema(
        {
            ATTR_ID: cv.positive_int,
            ATTR_NAME: str,
        }
    ),
)


def async_register_services(hass: HomeAssistant) -> None:
    """Register services for Vantage integration."""

    async def start_task(call: ServiceCall) -> None:
        """Start a Vantage task by id or name."""
        task_id_or_name = call.data.get(ATTR_ID) or call.data.get(ATTR_NAME)
        task_found = False

        vantage: Vantage
        for vantage in hass.data[DOMAIN].values():
            if task := _get_task(vantage, task_id_or_name):
                await vantage.tasks.start(task.id)
                task_found = True

        if not task_found:
            LOGGER.warning(
                "Task '%s' not found in any Vantage controller", task_id_or_name
            )

    async def stop_task(call: ServiceCall) -> None:
        """Stop a Vantage task by id or name."""
        task_id_or_name = call.data.get(ATTR_ID) or call.data.get(ATTR_NAME)
        task_found = False

        vantage: Vantage
        for vantage in hass.data[DOMAIN].values():
            if task := _get_task(vantage, task_id_or_name):
                await vantage.tasks.stop(task.id)
                task_found = True

        if not task_found:
            LOGGER.warning(
                "Task '%s' not found in any Vantage controller", task_id_or_name
            )

    # Register services
    if not hass.services.has_service(DOMAIN, SERVICE_START_TASK):
        hass.services.async_register(
            DOMAIN, SERVICE_START_TASK, start_task, schema=TASK_SCHEMA
        )

    if not hass.services.has_service(DOMAIN, SERVICE_STOP_TASK):
        hass.services.async_register(
            DOMAIN, SERVICE_STOP_TASK, stop_task, schema=TASK_SCHEMA
        )


def _get_task(vantage: Vantage, id_or_name: int | str) -> Task | None:
    """Get the task from the service call."""
    if isinstance(id_or_name, int):
        return vantage.tasks.get(id_or_name)

    if isinstance(id_or_name, str):
        return vantage.tasks.get(name=id_or_name)

    return None
