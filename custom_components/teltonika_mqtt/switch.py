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
from .entity import TeltonikaEntity, nested

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

    async def async_turn_on(self, **kwargs) -> None:
        await self._async_set_output(1)

    async def async_turn_off(self, **kwargs) -> None:
        await self._async_set_output(0)

    async def _async_set_output(self, value: int) -> None:
        payload = {
            "cookie": time.time_ns(),
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


class TeltonikaIsolatedOutputSwitch(TeltonikaModbusSwitch):
    """RUT956 galvanically isolated open collector output."""

    _attr_name = "Isolated output"
    register_number = ISOLATED_OUTPUT_REGISTER

    def __init__(self, router) -> None:
        super().__init__(router, "isolated_output_control")

    @property
    def is_on(self) -> bool | None:
        state = nested(self.router.data, "isolated_output", "state")
        if state is None:
            return None
        return str(state).lower() == "high level"


class TeltonikaRelaySwitch(TeltonikaModbusSwitch):
    """RUT956 relay."""

    _attr_name = "Relay"
    register_number = RELAY_REGISTER

    def __init__(self, router) -> None:
        super().__init__(router, "relay")

    @property
    def is_on(self) -> bool | None:
        state = nested(self.router.data, "relay", "state")
        if state is None:
            return None
        return str(state).lower() == "closed"
