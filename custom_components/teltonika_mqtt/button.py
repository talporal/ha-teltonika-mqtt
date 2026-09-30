"""Button platform for Teltonika MQTT."""

from __future__ import annotations

import json
import time

from homeassistant.components import mqtt
from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import DOMAIN, TOPIC_MODBUS_REQUEST
from .entity import TeltonikaEntity

REBOOT_REGISTER = 207


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Teltonika buttons."""
    router = hass.data[DOMAIN][entry.entry_id]["router"]
    async_add_entities([TeltonikaRebootButton(router)])


class TeltonikaRebootButton(TeltonikaEntity, ButtonEntity):
    """Reboot the router through the MQTT Modbus Gateway."""

    _attr_name = "Reboot"
    _attr_icon = "mdi:restart"

    def __init__(self, router) -> None:
        super().__init__(router, "reboot")

    async def async_press(self) -> None:
        """Send the reboot command."""
        payload = {
            "cookie": time.time_ns(),
            "type": 0,
            "host": "127.0.0.1",
            "port": 502,
            "timeout": 5,
            "server_id": 1,
            "function": 6,
            "register_number": REBOOT_REGISTER,
            "value": 1,
        }
        await mqtt.async_publish(
            self.hass,
            TOPIC_MODBUS_REQUEST.format(serial=self.router.serial),
            json.dumps(payload, separators=(",", ":")),
            qos=0,
            retain=False,
        )
