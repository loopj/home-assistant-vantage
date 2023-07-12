"""Handle Vantage service calls."""

import logging

from aiovantage import Vantage
import voluptuous as vol

from homeassistant.const import ATTR_ID, ATTR_NAME
from homeassistant.core import HomeAssistant, ServiceCall
import homeassistant.helpers.config_validation as cv

from .const import DOMAIN, SERVICE_START_TASK

LOGGER = logging.getLogger(__name__)

START_TASK_SCHEMA = vol.All(
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
        """Start a Vantage task by id."""
        task_id = call.data.get(ATTR_ID)
        task_name = call.data.get(ATTR_NAME)
        task_found = False

        vantage: Vantage
        for vantage in hass.data[DOMAIN].values():
            if task_id and task_id in vantage.tasks:
                await vantage.tasks.start(task_id)
                task_found = True
            elif task_name and (task := vantage.tasks.get(name=task_name)):
                await vantage.tasks.start(task.id)
                task_found = True

        if not task_found:
            LOGGER.warning(
                "Task '%s' not found in any Vantage controller", task_id or task_name
            )

    if not hass.services.has_service(DOMAIN, SERVICE_START_TASK):
        hass.services.async_register(
            DOMAIN, SERVICE_START_TASK, start_task, START_TASK_SCHEMA
        )
