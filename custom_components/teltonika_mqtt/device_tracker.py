"""GNSS device tracker for Teltonika MQTT."""

from __future__ import annotations

from homeassistant.components.device_tracker import SourceType
from homeassistant.components.device_tracker.config_entry import TrackerEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import DOMAIN
from .entity import TeltonikaEntity, nested


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the router GNSS tracker."""
    router = hass.data[DOMAIN][entry.entry_id]["router"]
    async_add_entities([TeltonikaGnssTracker(router)])


class TeltonikaGnssTracker(TeltonikaEntity, TrackerEntity):
    """Track a Teltonika router from its GNSS telemetry."""

    _attr_name = "GNSS location"
    _attr_source_type = SourceType.GPS

    def __init__(self, router) -> None:
        super().__init__(router, "gnss_location")

    def _has_fix(self) -> bool:
        """Return whether telemetry contains a usable GNSS fix."""
        fix_status = nested(self.router.data, "gnss", "fix_status")
        satellites = nested(self.router.data, "gnss", "satellites")
        latitude = nested(self.router.data, "gnss", "latitude")
        longitude = nested(self.router.data, "gnss", "longitude")
        return (
            bool(fix_status)
            and isinstance(satellites, (int, float))
            and satellites > 0
            and isinstance(latitude, (int, float))
            and isinstance(longitude, (int, float))
            and not (latitude == 0 and longitude == 0)
        )

    @property
    def latitude(self) -> float | None:
        if not self._has_fix():
            return None
        return float(nested(self.router.data, "gnss", "latitude"))

    @property
    def longitude(self) -> float | None:
        if not self._has_fix():
            return None
        return float(nested(self.router.data, "gnss", "longitude"))

    @property
    def location_accuracy(self) -> float:
        if not self._has_fix():
            return 0
        accuracy = nested(self.router.data, "gnss", "accuracy")
        return float(accuracy) if isinstance(accuracy, (int, float)) else 0
