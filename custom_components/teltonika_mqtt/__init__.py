"""Teltonika MQTT integration."""

from __future__ import annotations

import json
from typing import Any, Callable

from homeassistant.components import mqtt
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback

from .const import (
    CONF_SERIAL,
    DOMAIN,
    PLATFORMS,
    TOPIC_MODBUS_RESPONSE,
    TOPIC_TELEMETRY,
)


class TeltonikaRouter:
    """Runtime representation of one Teltonika router."""

    def __init__(self, hass: HomeAssistant, serial: str) -> None:
        self.hass = hass
        self.serial = serial
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
    def handle_telemetry(self, msg: mqtt.ReceiveMessage) -> None:
        """Process telemetry JSON."""
        try:
            payload = json.loads(msg.payload)
        except (TypeError, ValueError):
            return
        if isinstance(payload, dict):
            self.data = payload
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
    router = TeltonikaRouter(hass, serial)

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
