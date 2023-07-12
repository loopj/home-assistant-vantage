"""Handle Vantage service calls."""

from aiovantage import Vantage
import voluptuous as vol

from homeassistant.const import ATTR_ID, ATTR_NAME
from homeassistant.core import HomeAssistant, ServiceCall
import homeassistant.helpers.config_validation as cv

from .const import DOMAIN, SERVICE_START_TASK_BY_ID, SERVICE_START_TASK_BY_NAME


def async_register_services(hass: HomeAssistant) -> None:
    """Register services for Vantage integration."""

    async def start_task_by_id(call: ServiceCall) -> None:
        """Start a Vantage task by id."""
        vantage: Vantage
        for vantage in hass.data[DOMAIN].values():
            task_id: int = call.data[ATTR_ID]
            if task_id in vantage.tasks:
                await vantage.tasks.start(task_id)

    async def start_task_by_name(call: ServiceCall) -> None:
        """Start a Vantage task by name."""
        vantage: Vantage
        for vantage in hass.data[DOMAIN].values():
            task_name: str = call.data[ATTR_NAME]
            task = vantage.tasks.get(name=task_name)
            if task is not None:
                await vantage.tasks.start(task.id)

    if not hass.services.has_service(DOMAIN, SERVICE_START_TASK_BY_ID):
        hass.services.async_register(
            DOMAIN,
            SERVICE_START_TASK_BY_ID,
            start_task_by_id,
            schema=vol.Schema({vol.Required(ATTR_ID): cv.positive_int}),
        )

    if not hass.services.has_service(DOMAIN, SERVICE_START_TASK_BY_NAME):
        hass.services.async_register(
            DOMAIN,
            SERVICE_START_TASK_BY_NAME,
            start_task_by_name,
            schema=vol.Schema({vol.Required(ATTR_NAME): str}),
        )
