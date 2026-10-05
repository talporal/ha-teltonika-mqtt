"""Binary sensor platform for Teltonika MQTT."""

from __future__ import annotations

import json

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import DOMAIN
from .entity import TeltonikaEntity
from .helpers import nested


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Teltonika binary sensors."""
    router = hass.data[DOMAIN][entry.entry_id]["router"]
    async_add_entities([TeltonikaIsolatedInput(router), TeltonikaPowerAlarm(router)])


class TeltonikaIsolatedInput(TeltonikaEntity, BinarySensorEntity):
    """RUT956 isolated input."""

    _attr_name = "Isolated input"

    def __init__(self, router) -> None:
        super().__init__(router, "isolated_input")

    @property
    def is_on(self) -> bool | None:
        state = nested(self.router.data, "isolated_input", "state")
        if state is None:
            return None
        return str(state).lower() == "high level"


class TeltonikaIsolatedOutputState(TeltonikaEntity, BinarySensorEntity):
    """RUT956 isolated output state; control mapping is not yet verified."""

    _attr_name = "Isolated output"

    def __init__(self, router) -> None:
        super().__init__(router, "isolated_output")

    @property
    def is_on(self) -> bool | None:
        state = nested(self.router.data, "isolated_output", "state")
        if state is None:
            return None
        return str(state).lower() == "high level"

class TeltonikaPowerAlarm(TeltonikaEntity, BinarySensorEntity):
    """PZEM-014 alarm status."""

    _attr_name = "Power alarm"
    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_icon = "mdi:alert-circle-outline"

    def __init__(self, router) -> None:
        super().__init__(router, "power_alarm")

    @property
    def is_on(self) -> bool | None:
        records = self.router.data.get("Modbus")
        if not isinstance(records, list):
            return None
        record = next(
            (
                item
                for item in records
                if isinstance(item, dict) and item.get("name") == "PowerMeter"
            ),
            None,
        )
        if record is None:
            return None
        raw_data = record.get("data")
        try:
            values = json.loads(raw_data) if isinstance(raw_data, str) else raw_data
            return bool(int(values[9]))
        except (IndexError, TypeError, ValueError):
            return None
