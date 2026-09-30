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

RELAY_REGISTER = 203


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Teltonika switches."""
    router = hass.data[DOMAIN][entry.entry_id]["router"]
    async_add_entities([TeltonikaRelaySwitch(router)])


class TeltonikaRelaySwitch(TeltonikaEntity, SwitchEntity):
    """RUT956 relay controlled through the MQTT Modbus Gateway."""

    _attr_name = "Relay"

    def __init__(self, router) -> None:
        super().__init__(router, "relay")

    @property
    def is_on(self) -> bool | None:
        state = nested(self.router.data, "relay", "state")
        if state is None:
            return None
        return str(state).lower() == "closed"

    async def async_turn_on(self, **kwargs) -> None:
        await self._async_set_relay(1)

    async def async_turn_off(self, **kwargs) -> None:
        await self._async_set_relay(0)

    async def _async_set_relay(self, value: int) -> None:
        payload = {
            "cookie": time.time_ns(),
            "type": 0,
            "host": "127.0.0.1",
            "port": 502,
            "timeout": 5,
            "server_id": 1,
            "function": 6,
            "register_number": RELAY_REGISTER,
            "value": value,
        }
        await mqtt.async_publish(
            self.hass,
            TOPIC_MODBUS_REQUEST.format(serial=self.router.serial),
            json.dumps(payload, separators=(",", ":")),
            qos=0,
            retain=False,
        )
