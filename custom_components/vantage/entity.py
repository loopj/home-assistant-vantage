from typing import Any, Dict, Generic, Optional, TypeVar

from aiovantage import Vantage, VantageEvent
from aiovantage.config_client.objects import Area, SystemObject
from aiovantage.controllers.base import BaseController
from homeassistant.components.group import Entity
from homeassistant.core import Event, callback
from homeassistant.helpers.device_registry import DeviceEntryType
from homeassistant.helpers.entity import DeviceInfo

from .const import DOMAIN

T = TypeVar("T", bound="SystemObject")


class VantageEntity(Generic[T], Entity):
    # The Vantage client
    client: "Vantage"

    # The Vantage object this entity represents
    obj: T

    # Entity Properties
    _attr_should_poll = False

    def __init__(
        self,
        client: Vantage,
        controller: BaseController,
        obj: T,
        area: Optional[Area] = None,
    ):
        """Initialize a generic Vantage entity."""
        self.client = client
        self.controller = controller
        self.obj = obj
        self.area = area

    @property
    def name(self) -> str:
        """Return the name of the entity."""
        return self.obj.name

    @property
    def unique_id(self) -> str:
        """Return a unique ID."""
        return str(self.obj.id)

    @property
    def device_info(self) -> DeviceInfo | None:
        """Device specific attributes."""
        return DeviceInfo(
            identifiers={(DOMAIN, self.unique_id)},
            entry_type=DeviceEntryType.SERVICE,
            name=self.name,
            suggested_area=self.area.name if self.area else None,
            via_device=(DOMAIN, self.client.masters[self.obj.master_id].serial_number),
        )

    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added to hass."""
        self.async_on_remove(
            self.controller.subscribe(
                self._handle_event,
                self.obj.id,
                VantageEvent.OBJECT_UPDATED,
            )
        )

    @callback
    def _handle_event(
        self, event: Event, obj: SystemObject, data: Dict[str, Any]
    ) -> None:
        # Handle callback from Vantage for this object.

        # Object state is kept up to date by the Vantage client by an internal
        # subscription.  We just need to tell HA the state has changed.
        self.async_write_ha_state()
