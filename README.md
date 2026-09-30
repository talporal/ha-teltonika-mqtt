# Teltonika MQTT for Home Assistant

Custom Home Assistant integration for a fleet of Teltonika RUT routers using stock MQTT/Data to Server and MQTT Modbus Gateway features.

## MQTT contract

- `teltonika/<serial>/telemetry`
- `teltonika/<serial>/modbus/request`
- `teltonika/<serial>/modbus/response`

RUT956 Data to Server topic: `teltonika/%sn/telemetry`

MQTT Modbus Gateway request: `teltonika/$$SERIAL/modbus/request`

MQTT Modbus Gateway response: `teltonika/$$SERIAL/modbus/response`

## v0.1

The integration discovers routers from `teltonika/+/telemetry` and asks the Home Assistant user to confirm adding each router.

Telemetry: analog input voltage, relay state, isolated input/output state, mobile connection/registration, operator, network type, mobile IP, RSSI, RSRP, RSRQ, SINR, and firmware.

Control: RUT956 relay using the hardware-verified MQTT Modbus Gateway mapping: function 6, register 203, value 1 = closed and 0 = open.

Isolated-output control is intentionally not implemented until its Modbus mapping is verified on hardware.

v0.1 is based on telemetry captured from a RUT956 running `RUT9M_R_00.07.24.3`.

## Installation

Add this repository as a HACS custom repository (Integration), or copy `custom_components/teltonika_mqtt` into Home Assistant's `custom_components` directory and restart Home Assistant.

The built-in Home Assistant MQTT integration must already be configured.

## Status

Experimental. Test on the reference RUT956 before fleet deployment.


## Local geocoding data

The optional local **Geocoded Location** sensor performs offline lookup from bundled locality data. Turkey locality coordinates are derived from [Open Admin Data](https://openadmindata.org/tr/) and are licensed CC BY 4.0. Northern Cyprus uses Turkish district names and representative points maintained by this integration. No coordinates are sent to an external geocoding service.
