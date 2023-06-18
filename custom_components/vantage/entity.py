"""Support for generic Vantage entities."""

from typing import Any, Generic, TypeVar

from aiovantage import Vantage, VantageEvent
from aiovantage.config_client.objects import Area, LocationObject, Master, SystemObject
from aiovantage.controllers.base import BaseController
from homeassistant.components.group import Entity
from homeassistant.core import callback
from homeassistant.helpers.device_registry import DeviceEntryType
from homeassistant.helpers.entity import DeviceInfo

from .const import DOMAIN

T = TypeVar("T", bound=SystemObject)


class VantageEntity(Generic[T], Entity):
    """Base class for Vantage entities."""

    # The Vantage client
    client: "Vantage"

    # The Vantage object this entity represents
    obj: T

    # Entity Properties
    _attr_should_poll = False

    # Entity Relations
    area: Area | None = None
    master: Master | None = None

    def __init__(self, client: Vantage, controller: BaseController, obj: T):
        """Initialize a generic Vantage entity."""
        self.client = client
        self.controller = controller
        self.obj = obj

        self._attr_name = obj.name
        self._attr_unique_id = str(obj.id)

    @property
    def device_info(self) -> DeviceInfo | None:
        """Device specific attributes."""
        # TODO: Argument of type "set[tuple[Literal['vantage'], str | None]]" cannot be assigned to parameter "identifiers" of type "set[tuple[str, str]]" in function "__init__"
        #   Type "str | None" cannot be assigned to type "str"
        #     Type "None" cannot be assigned to type "str"
        info = DeviceInfo(
            identifiers={(DOMAIN, self.unique_id)},
            entry_type=DeviceEntryType.SERVICE,
            name=self.name,
            suggested_area=self.suggested_area,
        )

        if self.master:
            # TODO: Could not assign item in TypedDict
            #   "int" is incompatible with "str"
            info["via_device"] = (DOMAIN, self.master.serial_number)

        return info

    @property
    def suggested_area(self) -> str | None:
        """Return device suggested area based on the Vantage Area."""
        return self.area.name if self.area else None

    async def fetch_relations(self) -> None:
        """Fetch related objects from the Vantage controller."""
        self.master = await self.client.masters.aget(self.obj.master_id)
        if isinstance(self.obj, LocationObject) and self.obj.area_id:
            self.area = await self.client.areas.aget(self.obj.area_id)

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
        self, _event: VantageEvent, _obj: T, _data: dict[str, Any]
    ) -> None:
        # Handle callback from Vantage for this object.

        # Object state is kept up to date by the Vantage client by an internal
        # subscription.  We just need to tell HA the state has 1changed.
        self.async_write_ha_state()
