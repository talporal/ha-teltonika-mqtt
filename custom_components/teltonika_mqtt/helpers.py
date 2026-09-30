"""Telemetry helpers for Teltonika MQTT."""

from __future__ import annotations

import re
from typing import Any

from .const import DEFAULT_MODEL


def nested(data: dict[str, Any], *path: str) -> Any:
    value: Any = data
    for key in path:
        if not isinstance(value, dict):
            return None
        value = value.get(key)
    return value


def device_name(data: dict[str, Any]) -> str | None:
    value = nested(data, "device_info", "device_name")
    return value.strip() if isinstance(value, str) and value.strip() else None


def device_model(data: dict[str, Any]) -> str:
    code = nested(data, "mnf_info", "name")
    if isinstance(code, str):
        match = re.match(r"^(RUT\d{3})", code.strip(), re.IGNORECASE)
        if match:
            return match.group(1).upper()
    return DEFAULT_MODEL


def firmware_version(data: dict[str, Any]) -> str | None:
    value = nested(data, "base", "fw")
    return value.strip() if isinstance(value, str) and value.strip() else None


def hardware_version(data: dict[str, Any]) -> str | None:
    value = nested(data, "mnf_info", "hwver")
    return value.strip() if isinstance(value, str) and value.strip() else None
