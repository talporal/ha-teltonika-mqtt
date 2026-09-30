"""Config flow for Teltonika MQTT."""

from __future__ import annotations

import json
import re

from homeassistant import config_entries
from homeassistant.helpers.service_info.mqtt import MqttServiceInfo

from .const import CONF_SERIAL, DEFAULT_MODEL, DOMAIN
from .entity import device_model, device_name

_TOPIC_RE = re.compile(r"^teltonika/([^/]+)/telemetry$")


class TeltonikaMqttConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for a Teltonika router discovered over MQTT."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize flow."""
        self._serial: str | None = None
        self._model = DEFAULT_MODEL
        self._device_name: str | None = None
        self._firmware: str | None = None
        self._operator: str | None = None
        self._network: str | None = None

    def _title(self) -> str:
        """Return the fleet-friendly discovery/config entry title."""
        if self._device_name:
            return f"{self._device_name} — {self._model} — {self._serial}"
        return f"Teltonika {self._model} — {self._serial}"

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

        try:
            payload = json.loads(discovery_info.payload)
        except (TypeError, ValueError):
            payload = {}

        if isinstance(payload, dict):
            self._model = device_model(payload)
            self._device_name = device_name(payload)

            base = payload.get("base")
            gsm = payload.get("gsm")
            if isinstance(base, dict):
                firmware = base.get("fw")
                if isinstance(firmware, str) and firmware.strip():
                    self._firmware = firmware.strip()
            if isinstance(gsm, dict):
                operator = gsm.get("operator")
                network = gsm.get("conntype")
                if isinstance(operator, str) and operator:
                    self._operator = operator
                if isinstance(network, str) and network:
                    self._network = network

        self.context["title_placeholders"] = {
            "name": self._title(),
            "serial": self._serial,
            "model": self._model,
        }
        return await self.async_step_confirm()

    async def async_step_confirm(
        self, user_input: dict | None = None
    ) -> config_entries.ConfigFlowResult:
        """Confirm a discovered router."""
        if self._serial is None:
            return self.async_abort(reason="invalid_topic")

        if user_input is not None:
            return self.async_create_entry(
                title=self._title(),
                data={CONF_SERIAL: self._serial},
            )

        details = []
        if self._device_name:
            details.append(f"Device name: {self._device_name}")
        if self._firmware:
            details.append(f"Firmware: {self._firmware}")
        if self._operator:
            details.append(f"Mobile operator: {self._operator}")
        if self._network:
            details.append(f"Network: {self._network}")

        return self.async_show_form(
            step_id="confirm",
            description_placeholders={
                "serial": self._serial,
                "model": self._model,
                "details": "\n".join(details) if details else "Telemetry received",
            },
        )

    async def async_step_user(
        self, user_input: dict | None = None
    ) -> config_entries.ConfigFlowResult:
        """Direct users to MQTT discovery."""
        return self.async_abort(reason="mqtt_discovery_required")
