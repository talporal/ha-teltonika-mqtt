"""Teltonika MQTT integration."""

from __future__ import annotations

import json
import time
from typing import Any, Callable

from homeassistant.components import mqtt
from homeassistant.components.binary_sensor import DOMAIN as BINARY_SENSOR_DOMAIN
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.event import async_call_later

from .helpers import device_model, device_name, firmware_version, hardware_version

from .const import (
    CONF_SERIAL,
    DOMAIN,
    MANUFACTURER,
    PLATFORMS,
    TOPIC_MODBUS_RESPONSE,
    TOPIC_TELEMETRY,
)



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
        self.last_telemetry_monotonic: float | None = None
        self.connection_state = "offline"
        self.reboot_pending = False
        self._listeners: set[Callable[[], None]] = set()
        self._offline_timer: Callable[[], None] | None = None

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

        name = device_name(self.data)
        if not name:
            return

        registry = dr.async_get(self.hass)
        device = registry.async_get_device(
            identifiers={(DOMAIN, self.serial)}
        )
        if device is not None:
            registry.async_update_device(
                device.id,
                name=name,
                manufacturer=MANUFACTURER,
                model=device_model(self.data),
                serial_number=self.serial,
                hw_version=hardware_version(self.data),
                sw_version=firmware_version(self.data),
            )

    @callback
    def handle_telemetry(self, msg: mqtt.ReceiveMessage) -> None:
        """Process telemetry JSON."""
        try:
            payload = json.loads(msg.payload)
        except (TypeError, ValueError):
            return
        if isinstance(payload, dict):
            self.data = payload
            self.last_telemetry_monotonic = time.monotonic()
            if self._offline_timer is not None:
                self._offline_timer()
            if self.connection_state == "offline":
                self.connection_state = "online"
                self.reboot_pending = False
            elif self.reboot_pending:
                self.connection_state = "rebooting"
            else:
                self.connection_state = "online"
            timeout = 180.0 if self.reboot_pending else 30.0
            self._offline_timer = async_call_later(
                self.hass, timeout, self._mark_offline
            )
            self._update_device_name()
            self._notify()

    @callback
    def _mark_offline(self, _now=None) -> None:
        """Mark the router offline when its telemetry watchdog expires."""
        self._offline_timer = None
        self.connection_state = "offline"
        self._notify()

    @callback
    def mark_rebooting(self) -> None:
        """Enter reboot-aware monitoring after a reboot command is sent."""
        self.reboot_pending = True
        self.connection_state = "rebooting"
        if self._offline_timer is not None:
            self._offline_timer()
        self._offline_timer = async_call_later(
            self.hass, 180.0, self._mark_offline
        )
        self._notify()

    def telemetry_available(self) -> bool:
        """Return whether the router currently has live telemetry."""
        return self.connection_state != "offline"

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


@callback
def _cleanup_retired_entities(hass: HomeAssistant, serial: str) -> None:
    """Remove entities retired by newer integration versions."""
    entity_registry = er.async_get(hass)
    retired_entities = (
        (BINARY_SENSOR_DOMAIN, f"{serial}_isolated_output"),
    )
    for platform, unique_id in retired_entities:
        if entity_id := entity_registry.async_get_entity_id(
            platform, DOMAIN, unique_id
        ):
            entity_registry.async_remove(entity_id)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up a discovered Teltonika router."""
    serial = entry.data[CONF_SERIAL]
    _cleanup_retired_entities(hass, serial)
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
        router = runtime["router"]
        if router._offline_timer is not None:
            router._offline_timer()
            router._offline_timer = None
        for unsub in runtime["unsubs"]:
            unsub()
    return unloaded
