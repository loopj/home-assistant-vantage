"""Support for generic Vantage entities."""

from collections.abc import Awaitable, Callable
from typing import override

from aiovantage import Vantage
from aiovantage.controllers import Controller
from aiovantage.errors import (
    ClientError,
    InvalidObjectError,
    LoginFailedError,
    LoginRequiredError,
)
from aiovantage.events import ObjectAdded, ObjectDeleted, ObjectUpdated
from aiovantage.objects import GMem, SystemObject

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.helpers.entity import DeviceInfo, Entity
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .config_entry import VantageConfigEntry
from .const import DOMAIN
from .device import vantage_device_info


def async_cleanup_entities(hass: HomeAssistant, entry: VantageConfigEntry) -> None:
    """Remove entities from HA that are no longer in the Vantage controller."""
    vantage = entry.runtime_data.client
    ent_reg = er.async_get(hass)
    for entity in er.async_entries_for_config_entry(ent_reg, entry.entry_id):
        # Entity IDs always start with the object ID, followed by an optional suffix
        vantage_id = int(entity.unique_id.split(":")[0])
        if vantage_id not in vantage:
            ent_reg.async_remove(entity.entity_id)


def add_entities_from_controller[T: SystemObject](
    entry: VantageConfigEntry,
    async_add_entities: AddEntitiesCallback,
    entity_cls: type["VantageEntity[T]"],
    controller: Controller[T],
    filter: Callable[[T], bool] | None = None,
) -> None:
    """Add entities to HA from a Vantage controller."""
    # Add all entities currently known by the controller that match the filter
    queryset = controller.filter(filter) if filter else controller
    async_add_entities(entity_cls(entry, controller, obj) for obj in queryset)

    # Add any new entities added to the controller that match the filter
    def on_object_added(event: ObjectAdded[T]) -> None:
        if filter is None or filter(event.obj):
            async_add_entities([entity_cls(entry, controller, event.obj)])

    entry.async_on_unload(controller.subscribe(ObjectAdded, on_object_added))


class VantageEntity[T: SystemObject](Entity):
    """Base class for Vantage entities."""

    _attr_should_poll = False
    _attr_has_entity_name = True
    _attr_translation_key = "vantage"

    parent_obj: SystemObject | None = None

    def __init__(self, entry: VantageConfigEntry, controller: Controller[T], obj: T):
        """Initialize a generic Vantage entity."""
        self.entry = entry
        self.controller = controller
        self.obj = obj

    @property
    def client(self) -> Vantage:
        """Return the Vantage client."""
        return self.entry.runtime_data.client

    @property
    @override
    def unique_id(self) -> str:
        return str(self.obj.vid)

    @property
    @override
    def name(self) -> str | None:
        if self.parent_obj:
            return self.obj.name

        return None

    @property
    @override
    def device_info(self) -> DeviceInfo:
        if self.parent_obj:
            return vantage_device_info(self.client, self.parent_obj)

        return vantage_device_info(self.client, self.obj)

    async def async_request_call[U](self, coro: Awaitable[U]) -> U:
        """Send a request to the Vantage controller."""
        try:
            return await coro
        except ClientError as err:
            if isinstance(err, LoginFailedError | LoginRequiredError):
                # If authentication fails, prompt the user to reconfigure the
                # integration. This can happen when authentication is enabled on the
                # controller after the integration is configured, when the user changes
                # the password, or when a firmware update resets the password.
                self.entry.async_start_reauth(self.hass)
            elif isinstance(err, InvalidObjectError):
                # If the object ID of a request is invalid, mark the entity as
                # unavailable. This can happen when the user deletes an object from the
                # Vantage project and we haven't refreshed the entity registry yet.
                self._attr_available = False

            raise HomeAssistantError(
                f"Request for {self.entity_id} ({self.obj.vid}) failed: {err}"
            ) from err

    @override
    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            self.controller.subscribe(ObjectUpdated, self._on_object_updated)
        )

        self.async_on_remove(
            self.controller.subscribe(ObjectDeleted, self._on_object_deleted)
        )

    async def async_update(self) -> None:
        """Update the entity state (only used for polling entities)."""
        await self.async_request_call(self.obj.fetch_state())

    def _on_object_updated(self, event: ObjectUpdated[T]) -> None:
        if event.obj != self.obj:
            return

        # If this object owns a device, update it in the device registry.
        dev_reg = dr.async_get(self.hass)
        if dev_reg.async_get_device({(DOMAIN, str(self.obj.vid))}):
            if self.registry_entry and self.registry_entry.config_entry_id:
                dev_reg.async_get_or_create(
                    config_entry_id=self.registry_entry.config_entry_id,
                    **vantage_device_info(self.client, self.obj),
                )

        # Tell HA the state has changed.
        self.async_write_ha_state()

    def _on_object_deleted(self, event: ObjectDeleted[T]) -> None:
        if event.obj != self.obj:
            return

        # Remove the entity from the entity registry.
        ent_reg = er.async_get(self.hass)
        if self.entity_id in ent_reg.entities:
            ent_reg.async_remove(self.entity_id)

        # If this object owns a device, remove it from the device registry.
        dev_reg = dr.async_get(self.hass)
        if device := dev_reg.async_get_device({(DOMAIN, str(self.obj.vid))}):
            dev_reg.async_remove_device(device.id)

        # Tell HA the state has changed.
        self.async_write_ha_state()


class VantageGMemEntity(VantageEntity[GMem]):
    """Base class for Vantage Variable entities."""

    # Hide variables by default
    _attr_entity_registry_visible_default = False

    @property
    @override
    def name(self) -> str:
        return self.obj.name

    @property
    @override
    def device_info(self) -> DeviceInfo:
        # Attach variable entities to a "variables" virtual device
        return DeviceInfo(
            identifiers={(DOMAIN, f"{self.obj.master}:variables")},
            name="Variables",
            manufacturer="Vantage",
            model="Variables",
            entry_type=dr.DeviceEntryType.SERVICE,
            via_device=(DOMAIN, str(self.obj.master)),
        )
