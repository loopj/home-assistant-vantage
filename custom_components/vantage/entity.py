"""Support for generic Vantage entities."""

from typing import Any, Generic, Protocol, TypeVar, runtime_checkable

from aiovantage import Vantage, VantageEvent
from aiovantage.config_client.objects import LocationObject, SystemObject
from aiovantage.controllers.base import BaseController

from homeassistant.components.group import Entity
from homeassistant.core import callback
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.helpers.entity import DeviceInfo

from .const import DOMAIN

T = TypeVar("T", bound=SystemObject)


@runtime_checkable
class ChildObject(Protocol):
    """A Vantage object that has a parent."""

    parent_id: int


class VantageEntity(Generic[T], Entity):
    """Base class for Vantage entities."""

    _attr_should_poll = False
    _attr_has_entity_name = True

    def __init__(self, client: Vantage, controller: BaseController[T], obj: T):
        """Initialize a generic Vantage entity."""
        self.client = client
        self.controller = controller
        self.obj = obj

        self.__post_init__()

    def __post_init__(self) -> None:
        """Run after entity is initialized.

        This is a separate method so that subclasses can override it without
        having to call super().
        """

    @property
    def unique_id(self) -> str | None:
        """Return the unique id of the entity."""
        return str(self.obj.id)

    @property
    def name(self) -> str | None:
        """Return the name of the entity."""
        if self.attach_to_device is not None:
            return self.obj.name

        return None

    @property
    def device_info(self) -> DeviceInfo | None:
        """Return the device info for the entity."""
        if self.attach_to_device is not None:
            return DeviceInfo(
                identifiers={(DOMAIN, str(self.attach_to_device))},
            )

        info = DeviceInfo(
            identifiers={(DOMAIN, str(self.obj.id))},
            name=self.obj.name,
            default_manufacturer="Vantage",
            default_model=self.obj.model,
            manufacturer=self.manufacturer,
            model=self.model,
        )

        if isinstance(self.obj, ChildObject):
            info["via_device"] = (DOMAIN, str(self.obj.parent_id))

        if isinstance(self.obj, LocationObject):
            if area := self.client.areas.get(self.obj.area_id):
                info["suggested_area"] = area.name

        return info

    @property
    def manufacturer(self) -> str | None:
        """Manufacturer of the entity."""
        return None

    @property
    def model(self) -> str | None:
        """Model of the entity."""
        return None

    @property
    def attach_to_device(self) -> int | None:
        """The id of the device this entity should be attached to, if any."""
        return None

    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added to hass."""
        self.async_on_remove(
            self.controller.subscribe(
                self._handle_event,
                self.obj.id,
                (VantageEvent.OBJECT_UPDATED, VantageEvent.OBJECT_DELETED),
            )
        )

    @callback
    def _handle_event(self, event_type: VantageEvent, obj: T, _data: Any) -> None:
        # Handle callback from Vantage for this object.
        dev_reg = dr.async_get(self.hass)
        if event_type == VantageEvent.OBJECT_DELETED:
            # If this object has a device, remove it from the device registry.
            if device := dev_reg.async_get_device({(DOMAIN, str(obj.id))}):
                dev_reg.async_remove_device(device.id)

            # Some objects don't have their own device, but are attached to
            # another device. If so, remove them from the entity registry.
            if self.attach_to_device is not None:
                ent_reg = er.async_get(self.hass)
                ent_reg.async_remove(self.entity_id)

        elif event_type == VantageEvent.OBJECT_UPDATED:
            if self.attach_to_device is None:
                # Objects that have their own device need to update name, etc
                # in the device registry.
                if device := dev_reg.async_get_device({(DOMAIN, str(obj.id))}):
                    ...  # TODO

        # Object state is kept up to date by the Vantage client by an internal
        # subscription.  We just need to tell HA the state has changed.
        self.async_schedule_update_ha_state()
