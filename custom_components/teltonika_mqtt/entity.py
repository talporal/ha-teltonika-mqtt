"""Base entities for Teltonika MQTT."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import Entity

from . import TeltonikaRouter
from .const import DOMAIN, MANUFACTURER
from .helpers import device_model, device_name, firmware_version, hardware_version


class TeltonikaEntity(Entity):
    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, router: TeltonikaRouter, key: str) -> None:
        self.router = router
        self._attr_unique_id = f"{router.serial}_{key}"

    @property
    def device_info(self) -> DeviceInfo:
        model = device_model(self.router.data)
        name = device_name(self.router.data)
        return DeviceInfo(
            identifiers={(DOMAIN, self.router.serial)},
            manufacturer=MANUFACTURER,
            model=model,
            serial_number=self.router.serial,
            hw_version=hardware_version(self.router.data),
            sw_version=firmware_version(self.router.data),
            name=name or f"Teltonika {model} {self.router.serial}",
        )

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(self.router.add_listener(self._handle_router_update))

    def _handle_router_update(self) -> None:
        self.async_write_ha_state()
