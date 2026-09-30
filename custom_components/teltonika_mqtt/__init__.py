"""Teltonika MQTT integration."""

from __future__ import annotations

import json
from typing import Any, Callable

from homeassistant.components import mqtt
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr

from .const import (
    CONF_SERIAL,
    DOMAIN,
    PLATFORMS,
    TOPIC_MODBUS_RESPONSE,
    TOPIC_TELEMETRY,
)


def _nested(data: dict[str, Any], *path: str) -> Any:
    """Read a nested value without importing the entity module."""
    value: Any = data
    for key in path:
        if not isinstance(value, dict):
            return None
        value = value.get(key)
    return value


def _device_name(data: dict[str, Any]) -> str | None:
    """Return the configured router device name."""
    value = _nested(data, "device_info", "device_name")
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


class TeltonikaRouter:
    """Runtime representation of one Teltonika router."""

    def __init__(
        self,
        hass: HomeAssistant,
        serial: str,
        entry_id: str | None = None,
    ) -> None:
        self.hass = hass
        self.serial = serial
        self.entry_id = entry_id
        self.data: dict[str, Any] = {}
        self.last_response: dict[str, Any] | None = None
        self._listeners: set[Callable[[], None]] = set()

    @callback
    def add_listener(self, listener: Callable[[], None]) -> Callable[[], None]:
        """Register a state listener."""
        self._listeners.add(listener)

        @callback
        def remove_listener() -> None:
            self._listeners.discard(listener)

        return remove_listener

    @callback
    def _notify(self) -> None:
        for listener in tuple(self._listeners):
            listener()

    @callback
    def _update_device_name(self) -> None:
        """Update the HA device registry from the configured router name."""
        if not self.entry_id:
            return

        name = _device_name(self.data)
        if not name:
            return

        registry = dr.async_get(self.hass)
        device = registry.async_get_device(
            identifiers={(DOMAIN, self.serial)}
        )
        if device is not None and device.name != name:
            registry.async_update_device(device.id, name=name)

    @callback
    def handle_telemetry(self, msg: mqtt.ReceiveMessage) -> None:
        """Process telemetry JSON."""
        try:
            payload = json.loads(msg.payload)
        except (TypeError, ValueError):
            return
        if isinstance(payload, dict):
            self.data = payload
            self._update_device_name()
            self._notify()

    @callback
    def handle_response(self, msg: mqtt.ReceiveMessage) -> None:
        """Process a Modbus gateway response."""
        try:
            payload = json.loads(msg.payload)
        except (TypeError, ValueError):
            return
        if isinstance(payload, dict):
            self.last_response = payload
            self._notify()


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up a discovered Teltonika router."""
    serial = entry.data[CONF_SERIAL]
    router = TeltonikaRouter(hass, serial, entry.entry_id)

    if not await mqtt.async_wait_for_mqtt_client(hass):
        return False

    unsub_telemetry = await mqtt.async_subscribe(
        hass,
        TOPIC_TELEMETRY.format(serial=serial),
        router.handle_telemetry,
        qos=0,
    )
    unsub_response = await mqtt.async_subscribe(
        hass,
        TOPIC_MODBUS_RESPONSE.format(serial=serial),
        router.handle_response,
        qos=0,
    )

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "router": router,
        "unsubs": [unsub_telemetry, unsub_response],
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a Teltonika router."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        runtime = hass.data[DOMAIN].pop(entry.entry_id)
        for unsub in runtime["unsubs"]:
            unsub()
    return unloaded
