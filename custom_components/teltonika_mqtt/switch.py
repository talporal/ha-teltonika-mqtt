"""Switch platform for Teltonika MQTT."""

from __future__ import annotations

import json
import time

from homeassistant.components import mqtt
from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import DOMAIN, TOPIC_MODBUS_REQUEST
from .entity import TeltonikaEntity
from .helpers import nested

ISOLATED_OUTPUT_REGISTER = 202
RELAY_REGISTER = 203


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Teltonika switches."""
    router = hass.data[DOMAIN][entry.entry_id]["router"]
    async_add_entities([
        TeltonikaIsolatedOutputSwitch(router),
        TeltonikaRelaySwitch(router),
    ])


class TeltonikaModbusSwitch(TeltonikaEntity, SwitchEntity):
    """Base switch controlled through the MQTT Modbus Gateway."""

    register_number: int
    _pending_timeout = 20.0

    def __init__(self, router, key: str) -> None:
        super().__init__(router, key)
        self._pending_state: bool | None = None
        self._pending_cookie: int | None = None
        self._pending_until = 0.0
        self._pending_acknowledged = False

    async def async_turn_on(self, **kwargs) -> None:
        await self._async_set_output(1)

    async def async_turn_off(self, **kwargs) -> None:
        await self._async_set_output(0)

    async def _async_set_output(self, value: int) -> None:
        cookie = time.time_ns()
        self._pending_state = bool(value)
        self._pending_cookie = cookie
        self._pending_until = time.monotonic() + self._pending_timeout
        self._pending_acknowledged = False
        self.async_write_ha_state()
        payload = {
            "cookie": cookie,
            "type": 0,
            "host": "127.0.0.1",
            "port": 502,
            "timeout": 5,
            "server_id": 1,
            "function": 6,
            "register_number": self.register_number,
            "value": value,
        }
        await mqtt.async_publish(
            self.hass,
            TOPIC_MODBUS_REQUEST.format(serial=self.router.serial),
            json.dumps(payload, separators=(",", ":")),
            qos=0,
            retain=False,
        )

    def _state_with_pending(self, actual_state: bool | None) -> bool | None:
        """Hold the requested state while stale telemetry catches up."""
        if self._pending_state is None:
            return actual_state

        response = self.router.last_response
        if isinstance(response, dict) and response.get("cookie") == self._pending_cookie:
            if response.get("success") is False:
                self._clear_pending()
                return actual_state
            if response.get("success") is True:
                self._pending_acknowledged = True

        if self._pending_acknowledged and actual_state == self._pending_state:
            self._clear_pending()
            return actual_state

        if time.monotonic() >= self._pending_until:
            self._clear_pending()
            return actual_state

        return self._pending_state

    def _clear_pending(self) -> None:
        self._pending_state = None
        self._pending_cookie = None
        self._pending_until = 0.0
        self._pending_acknowledged = False


class TeltonikaIsolatedOutputSwitch(TeltonikaModbusSwitch):
    """RUT956 galvanically isolated open collector output."""

    _attr_name = "System Fans"
    _attr_icon = "mdi:fan"
    register_number = ISOLATED_OUTPUT_REGISTER

    def __init__(self, router) -> None:
        super().__init__(router, "isolated_output_control")

    @property
    def is_on(self) -> bool | None:
        state = nested(self.router.data, "isolated_output", "state")
        if state is None:
            return None
        return self._state_with_pending(str(state).lower() == "high level")


class TeltonikaRelaySwitch(TeltonikaModbusSwitch):
    """RUT956 relay."""

    _attr_name = "GNSS Receiver"
    _attr_icon = "mdi:satellite-variant"
    register_number = RELAY_REGISTER

    def __init__(self, router) -> None:
        super().__init__(router, "relay")

    @property
    def is_on(self) -> bool | None:
        state = nested(self.router.data, "relay", "state")
        if state is None:
            return None
        return self._state_with_pending(str(state).lower() == "closed")
