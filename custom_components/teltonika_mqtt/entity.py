"""Base entities for Teltonika MQTT."""

from __future__ import annotations

from typing import Any

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import Entity

from . import TeltonikaRouter
from .const import DOMAIN, MANUFACTURER, MODEL


def nested(data: dict[str, Any], *path: str) -> Any:
    """Read a nested value."""
    value: Any = data
    for key in path:
        if not isinstance(value, dict):
            return None
        value = value.get(key)
    return value


class TeltonikaEntity(Entity):
    """Base entity backed by router telemetry."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, router: TeltonikaRouter, key: str) -> None:
        self.router = router
        self._attr_unique_id = f"{router.serial}_{key}"

    @property
    def device_info(self) -> DeviceInfo:
        """Return router device information."""
        firmware = nested(self.router.data, "base", "fw")
        if isinstance(firmware, str):
            firmware = firmware.strip()
        return DeviceInfo(
            identifiers={(DOMAIN, self.router.serial)},
            manufacturer=MANUFACTURER,
            model=MODEL,
            serial_number=self.router.serial,
            sw_version=firmware,
            name=f"Teltonika RUT956 {self.router.serial}",
        )

    async def async_added_to_hass(self) -> None:
        """Subscribe to router updates."""
        self.async_on_remove(
            self.router.add_listener(self._handle_router_update)
        )

    def _handle_router_update(self) -> None:
        self.async_write_ha_state()
