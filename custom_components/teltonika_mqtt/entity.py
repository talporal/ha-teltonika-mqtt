"""Base entities for Teltonika MQTT."""

from __future__ import annotations

import re
from typing import Any

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import Entity

from . import TeltonikaRouter
from .const import DEFAULT_MODEL, DOMAIN, MANUFACTURER


def nested(data: dict[str, Any], *path: str) -> Any:
    """Read a nested value."""
    value: Any = data
    for key in path:
        if not isinstance(value, dict):
            return None
        value = value.get(key)
    return value


def device_name(data: dict[str, Any]) -> str | None:
    """Return the configured router device name."""
    value = nested(data, "device_info", "device_name")
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def product_code(data: dict[str, Any]) -> str | None:
    """Return the manufacturing product code."""
    value = nested(data, "mnf_info", "name")
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def device_model(data: dict[str, Any]) -> str:
    """Derive the router model from the manufacturing product code."""
    code = product_code(data)
    if code:
        match = re.match(r"^(RUT\d{3})", code, re.IGNORECASE)
        if match:
            return match.group(1).upper()
    return DEFAULT_MODEL


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

        hardware = nested(self.router.data, "mnf_info", "hwver")
        if isinstance(hardware, str):
            hardware = hardware.strip() or None

        name = device_name(self.router.data)
        model = device_model(self.router.data)

        return DeviceInfo(
            identifiers={(DOMAIN, self.router.serial)},
            manufacturer=MANUFACTURER,
            model=model,
            serial_number=self.router.serial,
            hw_version=hardware,
            sw_version=firmware,
            name=name or f"Teltonika {model} {self.router.serial}",
        )

    async def async_added_to_hass(self) -> None:
        """Subscribe to router updates."""
        self.async_on_remove(
            self.router.add_listener(self._handle_router_update)
        )

    def _handle_router_update(self) -> None:
        self.async_write_ha_state()
