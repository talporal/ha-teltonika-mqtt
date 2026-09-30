"""Constants for Teltonika MQTT."""

DOMAIN = "teltonika_mqtt"
PLATFORMS = ["sensor", "binary_sensor", "switch", "button", "device_tracker"]

CONF_SERIAL = "serial"

TOPIC_TELEMETRY = "teltonika/{serial}/telemetry"
TOPIC_MODBUS_REQUEST = "teltonika/{serial}/modbus/request"
TOPIC_MODBUS_RESPONSE = "teltonika/{serial}/modbus/response"

MANUFACTURER = "Teltonika Networks"
DEFAULT_MODEL = "Teltonika router"
