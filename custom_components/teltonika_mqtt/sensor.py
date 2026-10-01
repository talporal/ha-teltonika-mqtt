"""Sensor platform for Teltonika MQTT."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    EntityCategory,
    UnitOfElectricPotential,
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


SENSORS = (
    SensorDescription("router_status", "Status", ("base", "time"), category=EntityCategory.DIAGNOSTIC, icon="mdi:router-wireless"),
    SensorDescription("analog_input", "Analog input", ("analog_input", "value"), UnitOfElectricPotential.VOLT, SensorDeviceClass.VOLTAGE, suggested_precision=1, icon="mdi:flash"),
    SensorDescription("mobile_operator", "Mobile operator", ("gsm", "operator"), category=EntityCategory.DIAGNOSTIC, icon="mdi:cellphone-wireless"),
    SensorDescription("network_type", "Network type", ("gsm", "conntype"), category=EntityCategory.DIAGNOSTIC, icon="mdi:network"),
    SensorDescription("mobile_ip", "Mobile IP address", ("gsm", "ip"), category=EntityCategory.DIAGNOSTIC, icon="mdi:ip-network"),
    SensorDescription("rssi", "RSSI", ("gsm", "rssi"), "dBm", SensorDeviceClass.SIGNAL_STRENGTH, EntityCategory.DIAGNOSTIC, icon="mdi:signal"),
    SensorDescription("rsrp", "RSRP", ("gsm", "rsrp"), "dBm", SensorDeviceClass.SIGNAL_STRENGTH, EntityCategory.DIAGNOSTIC, icon="mdi:signal"),
    SensorDescription("rsrq", "RSRQ", ("gsm", "rsrq"), "dB", category=EntityCategory.DIAGNOSTIC, icon="mdi:signal"),
    SensorDescription("sinr", "SINR", ("gsm", "sinr"), "dB", category=EntityCategory.DIAGNOSTIC, icon="mdi:signal"),
    SensorDescription("registration", "Mobile registration", ("gsm", "netstate"), category=EntityCategory.DIAGNOSTIC, icon="mdi:access-point-network"),
    SensorDescription("connection", "Mobile connection", ("gsm", "connstate"), category=EntityCategory.DIAGNOSTIC, icon="mdi:connection"),
    SensorDescription("modem_temperature", "Internal temperature", ("gsm", "temp"), UnitOfTemperature.CELSIUS, SensorDeviceClass.TEMPERATURE, EntityCategory.DIAGNOSTIC, suggested_precision=1, icon="mdi:thermometer", scale=0.1),
    SensorDescription("uptime", "Uptime", ("device_info", "uptime"), category=EntityCategory.DIAGNOSTIC, icon="mdi:timer-outline"),
    SensorDescription("gnss_latitude", "GNSS latitude", ("gnss", "latitude"), "°", category=EntityCategory.DIAGNOSTIC, suggested_precision=6, icon="mdi:latitude"),
    SensorDescription("gnss_longitude", "GNSS longitude", ("gnss", "longitude"), "°", category=EntityCategory.DIAGNOSTIC, suggested_precision=6, icon="mdi:longitude"),
    SensorDescription("gnss_satellites", "GNSS satellites", ("gnss", "satellites"), category=EntityCategory.DIAGNOSTIC, icon="mdi:satellite-variant"),
    SensorDescription("geocoded_location", "Geocoded Location", ("gnss", "latitude"), category=EntityCategory.DIAGNOSTIC, icon="mdi:map-marker"),
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
