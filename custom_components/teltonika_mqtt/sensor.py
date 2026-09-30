"""Sensor platform for Teltonika MQTT."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory, UnitOfElectricPotential
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import DOMAIN
from .entity import TeltonikaEntity, nested


@dataclass(frozen=True)
class SensorDescription:
    key: str
    name: str
    path: tuple[str, ...]
    unit: str | None = None
    device_class: SensorDeviceClass | None = None
    category: EntityCategory | None = None


SENSORS = (
    SensorDescription("analog_input", "Analog input", ("analog_input", "value"), UnitOfElectricPotential.VOLT, SensorDeviceClass.VOLTAGE),
    SensorDescription("mobile_operator", "Mobile operator", ("gsm", "operator"), category=EntityCategory.DIAGNOSTIC),
    SensorDescription("network_type", "Network type", ("gsm", "conntype"), category=EntityCategory.DIAGNOSTIC),
    SensorDescription("mobile_ip", "Mobile IP address", ("gsm", "ip"), category=EntityCategory.DIAGNOSTIC),
    SensorDescription("rssi", "RSSI", ("gsm", "rssi"), "dBm", category=EntityCategory.DIAGNOSTIC),
    SensorDescription("rsrp", "RSRP", ("gsm", "rsrp"), "dBm", category=EntityCategory.DIAGNOSTIC),
    SensorDescription("rsrq", "RSRQ", ("gsm", "rsrq"), "dB", category=EntityCategory.DIAGNOSTIC),
    SensorDescription("sinr", "SINR", ("gsm", "sinr"), "dB", category=EntityCategory.DIAGNOSTIC),
    SensorDescription("registration", "Mobile registration", ("gsm", "netstate"), category=EntityCategory.DIAGNOSTIC),
    SensorDescription("connection", "Mobile connection", ("gsm", "connstate"), category=EntityCategory.DIAGNOSTIC),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Teltonika sensors."""
    router = hass.data[DOMAIN][entry.entry_id]["router"]
    async_add_entities(TeltonikaSensor(router, description) for description in SENSORS)


class TeltonikaSensor(TeltonikaEntity, SensorEntity):
    """Telemetry sensor."""

    def __init__(self, router, description: SensorDescription) -> None:
        super().__init__(router, description.key)
        self.description = description
        self._attr_name = description.name
        self._attr_native_unit_of_measurement = description.unit
        self._attr_device_class = description.device_class
        self._attr_entity_category = description.category

    @property
    def native_value(self) -> Any:
        """Return current telemetry value."""
        value = nested(self.router.data, *self.description.path)
        if self.description.key == "mobile_ip" and isinstance(value, list):
            return value[0] if value else None
        return value
