"""Config flow for Teltonika MQTT."""

from __future__ import annotations

import re

from homeassistant import config_entries
from homeassistant.helpers.service_info.mqtt import MqttServiceInfo

from .const import CONF_SERIAL, DOMAIN

_TOPIC_RE = re.compile(r"^teltonika/([^/]+)/telemetry$")


class TeltonikaMqttConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for a Teltonika router discovered over MQTT."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize flow."""
        self._serial: str | None = None

    async def async_step_mqtt(
        self, discovery_info: MqttServiceInfo
    ) -> config_entries.ConfigFlowResult:
        """Handle MQTT discovery."""
        match = _TOPIC_RE.match(discovery_info.topic)
        if not match:
            return self.async_abort(reason="invalid_topic")

        self._serial = match.group(1)
        await self.async_set_unique_id(self._serial)
        self._abort_if_unique_id_configured()

        self.context["title_placeholders"] = {"serial": self._serial}
        return await self.async_step_confirm()

    async def async_step_confirm(
        self, user_input: dict | None = None
    ) -> config_entries.ConfigFlowResult:
        """Confirm a discovered router."""
        if self._serial is None:
            return self.async_abort(reason="invalid_topic")

        if user_input is not None:
            return self.async_create_entry(
                title=f"Teltonika RUT956 {self._serial}",
                data={CONF_SERIAL: self._serial},
            )

        self._set_confirm_only()
        return self.async_show_form(
            step_id="confirm",
            description_placeholders={"serial": self._serial},
        )

    async def async_step_user(
        self, user_input: dict | None = None
    ) -> config_entries.ConfigFlowResult:
        """Direct users to MQTT discovery."""
        return self.async_abort(reason="mqtt_discovery_required")
