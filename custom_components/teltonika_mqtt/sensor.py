"""Sensor platform for Teltonika MQTT."""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    EntityCategory,
    PERCENTAGE,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfFrequency,
    UnitOfPower,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import DOMAIN
from .entity import TeltonikaEntity
from .helpers import nested
from .geocoding import geocode_location


@dataclass(frozen=True)
class SensorDescription:
    key: str
    name: str
    path: tuple[str, ...]
    unit: str | None = None
    device_class: SensorDeviceClass | None = None
    category: EntityCategory | None = None
    suggested_precision: int | None = None
    icon: str | None = None
    scale: float | None = None
    state_class: SensorStateClass | None = None


SENSORS = (
    SensorDescription("router_status", "Status", ("base", "time"), icon="mdi:router-wireless"),
    SensorDescription("analog_input", "Battery Voltage (DC)", ("analog_input", "value"), UnitOfElectricPotential.VOLT, SensorDeviceClass.VOLTAGE, suggested_precision=1, icon="mdi:flash"),
    SensorDescription("mobile_operator", "Mobile operator", ("gsm", "operator"), category=EntityCategory.DIAGNOSTIC, icon="mdi:cellphone-wireless"),
    SensorDescription("network_type", "Network type", ("gsm", "conntype"), category=EntityCategory.DIAGNOSTIC, icon="mdi:network"),
    SensorDescription("mobile_ip", "Mobile IP address", ("gsm", "ip"), icon="mdi:ip-network"),
    SensorDescription("rssi", "RSSI", ("gsm", "rssi"), "dBm", SensorDeviceClass.SIGNAL_STRENGTH, EntityCategory.DIAGNOSTIC, icon="mdi:signal"),
    SensorDescription("rsrp", "RSRP", ("gsm", "rsrp"), "dBm", SensorDeviceClass.SIGNAL_STRENGTH, EntityCategory.DIAGNOSTIC, icon="mdi:signal"),
    SensorDescription("rsrq", "RSRQ", ("gsm", "rsrq"), "dB", category=EntityCategory.DIAGNOSTIC, icon="mdi:signal"),
    SensorDescription("sinr", "SINR", ("gsm", "sinr"), "dB", category=EntityCategory.DIAGNOSTIC, icon="mdi:signal"),
    SensorDescription("registration", "Mobile registration", ("gsm", "netstate"), category=EntityCategory.DIAGNOSTIC, icon="mdi:access-point-network"),
    SensorDescription("connection", "Mobile connection", ("gsm", "connstate"), icon="mdi:connection"),
    SensorDescription("modem_temperature", "Internal temperature", ("gsm", "temp"), UnitOfTemperature.CELSIUS, SensorDeviceClass.TEMPERATURE, suggested_precision=1, icon="mdi:thermometer", scale=0.1),
    SensorDescription("uptime", "Uptime", ("device_info", "uptime"), category=EntityCategory.DIAGNOSTIC, icon="mdi:timer-outline"),
    SensorDescription("gnss_latitude", "GNSS latitude", ("gnss", "latitude"), "°", category=EntityCategory.DIAGNOSTIC, suggested_precision=6, icon="mdi:latitude"),
    SensorDescription("gnss_longitude", "GNSS longitude", ("gnss", "longitude"), "°", category=EntityCategory.DIAGNOSTIC, suggested_precision=6, icon="mdi:longitude"),
    SensorDescription("gnss_satellites", "GNSS satellites", ("gnss", "satellites"), category=EntityCategory.DIAGNOSTIC, icon="mdi:satellite-variant"),
    SensorDescription("geocoded_location", "Geocoded Location", ("gnss", "latitude"), icon="mdi:map-marker"),
    SensorDescription("environment_temperature", "Cabinet Temperature", (), UnitOfTemperature.CELSIUS, SensorDeviceClass.TEMPERATURE, suggested_precision=1, icon="mdi:thermometer", state_class=SensorStateClass.MEASUREMENT),
    SensorDescription("environment_humidity", "Cabinet Humidity", (), PERCENTAGE, SensorDeviceClass.HUMIDITY, suggested_precision=1, icon="mdi:water-percent", state_class=SensorStateClass.MEASUREMENT),
    SensorDescription("power_voltage", "AC Voltage", (), UnitOfElectricPotential.VOLT, SensorDeviceClass.VOLTAGE, suggested_precision=1, icon="mdi:sine-wave", state_class=SensorStateClass.MEASUREMENT),
    SensorDescription("power_current", "AC Current", (), UnitOfElectricCurrent.AMPERE, SensorDeviceClass.CURRENT, suggested_precision=3, icon="mdi:current-ac", state_class=SensorStateClass.MEASUREMENT),
    SensorDescription("power_active", "AC Active Power", (), UnitOfPower.WATT, SensorDeviceClass.POWER, suggested_precision=1, icon="mdi:flash", state_class=SensorStateClass.MEASUREMENT),
    SensorDescription("power_energy", "AC Energy", (), UnitOfEnergy.WATT_HOUR, SensorDeviceClass.ENERGY, suggested_precision=0, icon="mdi:counter", state_class=SensorStateClass.TOTAL_INCREASING),
    SensorDescription("power_frequency", "AC Frequency", (), UnitOfFrequency.HERTZ, SensorDeviceClass.FREQUENCY, suggested_precision=1, icon="mdi:sine-wave", state_class=SensorStateClass.MEASUREMENT),
    SensorDescription("power_factor", "AC Power Factor", (), None, SensorDeviceClass.POWER_FACTOR, suggested_precision=2, icon="mdi:angle-acute", state_class=SensorStateClass.MEASUREMENT),
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
        self._attr_suggested_display_precision = description.suggested_precision
        self._attr_icon = description.icon
        self._attr_state_class = description.state_class

    @property
    def available(self) -> bool:
        """Keep the status sensor available so it can explicitly report Offline."""
        if self.description.key == "router_status":
            return True
        return super().available

    @property
    def icon(self) -> str | None:
        """Return a dynamic signal icon where appropriate."""
        value = nested(self.router.data, *self.description.path)
        if not isinstance(value, (int, float)):
            return self.description.icon

        if self.description.key in ("rssi", "rsrp"):
            if value >= -70:
                return "mdi:signal-cellular-3"
            if value >= -85:
                return "mdi:signal-cellular-2"
            if value >= -100:
                return "mdi:signal-cellular-1"
            return "mdi:signal-cellular-outline"

        if self.description.key == "rsrq":
            if value >= -10:
                return "mdi:signal-cellular-3"
            if value >= -15:
                return "mdi:signal-cellular-2"
            if value >= -20:
                return "mdi:signal-cellular-1"
            return "mdi:signal-cellular-outline"

        if self.description.key == "sinr":
            if value >= 20:
                return "mdi:signal-cellular-3"
            if value >= 13:
                return "mdi:signal-cellular-2"
            if value >= 0:
                return "mdi:signal-cellular-1"
            return "mdi:signal-cellular-outline"

        return self.description.icon

    @property
    def native_value(self) -> Any:
        """Return current telemetry value."""
        if self.description.key.startswith(("environment_", "power_")):
            return self._modbus_value()
        value = nested(self.router.data, *self.description.path)
        if self.description.key == "router_status":
            return self.router.connection_state.capitalize()
        if self.description.key == "geocoded_location":
            fix_status = nested(self.router.data, "gnss", "fix_status")
            satellites = nested(self.router.data, "gnss", "satellites")
            latitude = nested(self.router.data, "gnss", "latitude")
            longitude = nested(self.router.data, "gnss", "longitude")
            if (
                not fix_status
                or not isinstance(satellites, (int, float))
                or satellites <= 0
                or not isinstance(latitude, (int, float))
                or not isinstance(longitude, (int, float))
                or (latitude == 0 and longitude == 0)
            ):
                return None
            return geocode_location(float(latitude), float(longitude))
        if self.description.key == "uptime" and isinstance(value, (int, float)):
            seconds = max(0, int(value))
            days, remainder = divmod(seconds, 86400)
            hours, remainder = divmod(remainder, 3600)
            minutes, seconds = divmod(remainder, 60)
            if days:
                return f"{days}d {hours}h {minutes}m"
            if hours:
                return f"{hours}h {minutes}m {seconds}s"
            if minutes:
                return f"{minutes}m {seconds}s"
            return f"{seconds}s"
        if self.description.key == "mobile_ip" and isinstance(value, list):
            return value[0] if value else None
        if self.description.key in ("gnss_latitude", "gnss_longitude"):
            fix_status = nested(self.router.data, "gnss", "fix_status")
            satellites = nested(self.router.data, "gnss", "satellites")
            if not fix_status or not isinstance(satellites, (int, float)) or satellites <= 0:
                return None
        if self.description.scale is not None and isinstance(value, (int, float)):
            return value * self.description.scale
        return value

    def _modbus_value(self) -> Any:
        """Decode supported Modbus request payloads from Data to Server."""
        records = self.router.data.get("Modbus")
        if not isinstance(records, list):
            return None
        request_name = "Environment" if self.description.key.startswith("environment_") else "PowerMeter"
        record = next((item for item in records if isinstance(item, dict) and item.get("name") == request_name), None)
        if record is None:
            return None
        raw_data = record.get("data")
        try:
            values = json.loads(raw_data) if isinstance(raw_data, str) else raw_data
        except (TypeError, ValueError):
            return None
        if not isinstance(values, list):
            return None
        try:
            if self.description.key == "environment_temperature":
                return float(values[0]) / 10
            if self.description.key == "environment_humidity":
                return float(values[1]) / 10
            if self.description.key == "power_voltage":
                return float(values[0]) / 10
            if self.description.key == "power_current":
                return (int(values[1]) + (int(values[2]) << 16)) / 1000
            if self.description.key == "power_active":
                return (int(values[3]) + (int(values[4]) << 16)) / 10
            if self.description.key == "power_energy":
                return int(values[5]) + (int(values[6]) << 16)
            if self.description.key == "power_frequency":
                return float(values[7]) / 10
            if self.description.key == "power_factor":
                return float(values[8]) / 100
        except (IndexError, TypeError, ValueError):
            return None
        return None
