"""Support for generic Vantage entities."""

from collections.abc import Callable
from typing import Any, Generic, TypeVar

from aiovantage import Vantage, VantageEvent
from aiovantage.controllers import BaseController
from aiovantage.models import SystemObject

from homeassistant.components.group import Entity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .helpers import get_object_area, get_object_parent_id

T = TypeVar("T", bound=SystemObject)


def async_register_vantage_objects(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
    controller: BaseController[T],
    entity_class: type["VantageEntity[T]"],
    object_filter: Callable[[T], bool] | None = None,
) -> None:
    """Add entities to HA from a Vantage controller, add a callback for new entities."""
    vantage: Vantage = hass.data[DOMAIN][entry.entry_id]

    # Add all current objects in the controller that match the filter
    objects = controller.filter(object_filter) if object_filter else controller
    entities = [entity_class(vantage, controller, obj) for obj in objects]
    async_add_entities(entities)

    # Register a callback for objects added to this controller that match the filter
    @callback
    def async_add_entity(_type: VantageEvent, obj: T, _data: Any) -> None:
        if object_filter is None or object_filter(obj):
            async_add_entities([entity_class(vantage, controller, obj)])

    entry.async_on_unload(
        controller.subscribe(async_add_entity, event_filter=VantageEvent.OBJECT_ADDED)
    )


def async_cleanup_entities(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Remove entities from HA that are no longer in the Vantage controller."""
    vantage: Vantage = hass.data[DOMAIN][entry.entry_id]
    ent_reg = er.async_get(hass)
    for entity in er.async_entries_for_config_entry(ent_reg, entry.entry_id):
        # Entity IDs always start with the object ID, followed by an optional suffix
        vantage_id = int(entity.unique_id.split(":")[0])
        if vantage_id not in vantage.known_ids:
            ent_reg.async_remove(entity.entity_id)


class VantageEntity(Generic[T], Entity):
    """Base class for Vantage entities."""

    _attr_should_poll = False
    _attr_name: str | None = None
    _attr_has_entity_name = True

    _device_id: str | None = None
    _device_model: str | None = None
    _device_manufacturer: str | None = None
    _device_is_service: bool = False

    def __init__(self, client: Vantage, controller: BaseController[T], obj: T):
        """Initialize a generic Vantage entity."""
        self.client = client
        self.controller = controller
        self.obj = obj

        self._attr_unique_id = str(obj.id)
        self._device_manufacturer = "Vantage"
        self._device_model = obj.model

        self.__post_init__()

    def __post_init__(self) -> None:
        """Run after entity is initialized."""

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info for the entity."""
        if self._device_id is not None:
            return DeviceInfo(identifiers={(DOMAIN, self._device_id)})

        info = DeviceInfo(
            identifiers={(DOMAIN, str(self.obj.id))},
            name=self.obj.display_name or self.obj.name,
            manufacturer=self._device_manufacturer,
            model=self._device_model,
        )

        if self._device_is_service:
            info["entry_type"] = dr.DeviceEntryType.SERVICE

        if area := get_object_area(self.client, self.obj):
            info["suggested_area"] = area.name

        if parent_id := get_object_parent_id(self.obj):
            info["via_device"] = (DOMAIN, str(parent_id))
        else:
            info["via_device"] = (DOMAIN, str(self.obj.master_id))

        return info

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
        if event_type == VantageEvent.OBJECT_DELETED:
            # Remove the entity from the entity registry.
            ent_reg = er.async_get(self.hass)
            if self.entity_id in ent_reg.entities:
                ent_reg.async_remove(self.entity_id)

            # If this entity owns a device, also remove it from the device registry.
            dev_reg = dr.async_get(self.hass)
            device = dev_reg.async_get_device({(DOMAIN, str(obj.id))})
            if device is not None:
                dev_reg.async_remove_device(device.id)

        elif event_type == VantageEvent.OBJECT_UPDATED:
            # If this entity owns a device, update it in the device registry.
            dev_reg = dr.async_get(self.hass)
            device = dev_reg.async_get_device({(DOMAIN, str(obj.id))})
            if (
                device is not None
                and self.registry_entry is not None
                and self.registry_entry.config_entry_id is not None
            ):
                dev_reg.async_get_or_create(
                    config_entry_id=self.registry_entry.config_entry_id,
                    **self.device_info,
                )

        # Object state is kept up to date by the Vantage client by an internal
        # subscription.  We just need to tell HA the state has changed.
        self.async_write_ha_state()
