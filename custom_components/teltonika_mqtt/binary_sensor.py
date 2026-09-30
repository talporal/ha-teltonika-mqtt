"""Binary sensor platform for Teltonika MQTT."""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
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
    async_add_entities([TeltonikaIsolatedInput(router), TeltonikaIsolatedOutputState(router)])


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
