"""Constants for the Iwona Pellets integration."""

from __future__ import annotations

DOMAIN = "iwona_pellets"

CONF_SLAVE = "slave"
CONF_FRAMING = "framing"
CONF_SCAN_INTERVAL = "scan_interval"
CONF_START_COMMAND = "start_command"
CONF_SYNC_CLOCK = "sync_clock"

DEFAULT_NAME = "Iwona Pellets"
DEFAULT_PORT = 8899  # default TCP port of the Elfin EW11
DEFAULT_SLAVE = 1
DISPLAY_REFRESH_SECONDS = 10  # refresh of the display image
DEFAULT_SCAN_INTERVAL = 15  # seconds
MIN_SCAN_INTERVAL = 5
MAX_SCAN_INTERVAL = 300

# Value written to register 102 to start the stove: 1 = START (short key press),
# 2 = START with a long key press.
START_COMMANDS = ("1", "2")
DEFAULT_START_COMMAND = 1
DEFAULT_SYNC_CLOCK = True
CLOCK_MAX_DRIFT = 120  # seconds of difference tolerated before the clock is rewritten
CLOCK_RETRY_SECONDS = 3600  # minimum delay between two automatic attempts

CONF_ROOM_SENSOR = "room_sensor"  # external room temperature sensor (entity id)
SENSOR_MAX_AGE = 900  # seconds: an older external reading stops the heating demand
DEFAULT_EXT_SETPOINT = 21.0
DEFAULT_EXT_HYSTERESIS = 0.5
