"""Register map of the P.W. KEY RK-2014K/KW controller (Iwona Pellets stoves).

Numbers in this file are the *logical* register numbers used by the
manufacturer's documentation. The address sent on the wire is one less
(register 1 is transmitted as address 0): see :func:`to_address`.

This module has no Home Assistant dependency so that it can be unit tested.
"""

from __future__ import annotations

from dataclasses import dataclass

# --------------------------------------------------------------------------- #
# Read-only states (1..99)
# --------------------------------------------------------------------------- #
REG_BOILER_TEMP = 1
REG_HOT_WATER_TEMP = 2
REG_FEEDER_TEMP = 3
REG_EXHAUST_TEMP = 5
REG_PROCESS_STATE = 6
REG_ERRORS_1 = 7
REG_ERRORS_2 = 8
REG_THERMOSTAT = 9
REG_FLAME = 12
REG_SAFETY_INPUT = 14
REG_EXHAUST_FAN_POWER = 16
REG_BLOW_IN_FAN_POWER = 17
REG_FEEDER_OUTPUT = 18
REG_IGNITION_OUTPUT = 20
REG_HEATING_PUMP = 21
REG_HOT_WATER_PUMP = 22
REG_CLEANING_OUTPUT = 23
REG_ALARM_OUTPUT = 24
REG_THROTTLE = 31
REG_EXTERNAL_ENABLE = 32
REG_ROOM_TEMP_INTERNAL = 33
REG_ROOM_TEMP_EXTRA = 34
REG_ROOM_TEMP = 36
REG_BUFFER_TEMP = 37
REG_FAN_SPEED = 38

# --------------------------------------------------------------------------- #
# Basic settings (100..399). Only these are ever written by the integration.
# --------------------------------------------------------------------------- #
REG_TARGET_BOILER = 100
REG_TARGET_HOT_WATER = 101
REG_BOILER_WORK = 102  # 0 = STOP, 1 = START (2 = long press: only gives work_wood, see docs)
REG_WORK_MODE = 103  # 0 = winter, 1 = summer
REG_ERROR_FLAG = 105  # 0 = OK, 1 = error, write 0 to clear
REG_TARGET_ROOM_DAY = 107  # 0.1 degC
REG_TARGET_ROOM_NIGHT = 108  # 0.1 degC
REG_PROGRAM_MODE = 116
# Controller clock: year (4 digits), month, day, weekday, hour, minute, second.
# The weekday is sent as Monday = 0 ... Sunday = 6 (the weekly programs start on
# Monday midnight); verify it on the stove display after the first synchronisation.
REG_CLOCK_START = 109
CLOCK_REGISTERS = tuple(range(109, 116))

# Fuel mode: not a documented basic register. It is the "setting by number" of
# section 01, parameter 02, found by comparing dumps taken in each mode on the
# stove's display (0 = pellet, 1 = wood, 2 = wood and pellet).
REG_FUEL_MODE = 10102

# Minimum / maximum allowed values of setting N are in N + 100 / N + 200.
LIMIT_MIN_OFFSET = 100
LIMIT_MAX_OFFSET = 200

# --------------------------------------------------------------------------- #
# Device information (40000..40999)
# --------------------------------------------------------------------------- #
REG_INFO_START = 40000  # 64 registers, one ASCII character per register
REG_INFO_COUNT = 64
REG_BURNER_HOURS = 40064
REG_IGNITION_COUNT = 40065

# Blocks read by the coordinator: (first logical register, number of registers)
BLOCK_STATES = (1, 38)
BLOCK_SETTINGS = (100, 24)  # 100..123
BLOCK_COUNTERS = (REG_BURNER_HOURS, 2)
BLOCK_FUEL = (REG_FUEL_MODE, 1)
# Virtual keyboard of the terminal region: writing a key code is the same as pressing
# the key on the controller (the controller clears the register by itself).
REG_KEYBOARD = 41512
# Code 2 ("Esc" in the documentation) is the Start/Stop key on this controller: it is
# deliberately not exposed, the Start/Stop switch is used instead.
KEYS = {"menu": 5, "ok": 1, "plus": 3, "minus": 4}

BLOCK_ERROR_LOG = (44000, 200)  # 100 events of two registers

BLOCK_DISPLAY = (41000, 512)  # LCD image, read on demand (not by the poll)
BLOCK_INFO = (REG_INFO_START, REG_INFO_COUNT)
BLOCK_MIN = (200, 9)  # limits of settings 100..108
BLOCK_MAX = (300, 9)


def to_address(register: int) -> int:
    """Convert a logical register number to the address sent on the wire."""
    return register - 1


# --------------------------------------------------------------------------- #
# Decoding helpers
# --------------------------------------------------------------------------- #
# Register 6. Code 12 ("blow-in / gas removal") is shared by pellet and wood.
PROCESS_STATES: dict[int, str] = {
    0: "stop",
    1: "fuelling",
    5: "standby",
    6: "ignition_cleaning",
    7: "ignition",
    8: "power_stabilization",
    9: "maximum_power",
    10: "modulated_power",
    11: "minimum_power",
    12: "blow_in",
    13: "extinction",
    14: "postcombustion",
    15: "cleaning_opening",
    16: "cleaning_closing",
    17: "alarm",
    18: "manual_opening",
    19: "start_dose",
    20: "stabilization_wood",
    21: "work_wood",
    22: "add_wood",  # not in the documentation: seen while "blow / add wood" is active
}

# Register 7, bit -> error key
ERRORS_1: dict[int, str] = {
    0: "boiler_sensor",
    1: "feeder_sensor",
    2: "exhaust_sensor",
    3: "stb_protection",
    4: "safety_input",
    5: "capacitive_unjamming",
    6: "capacitive_critical",
    7: "boiler_overheat",
    8: "feeder_ignition",
    9: "feeder_ignition_detected",
    10: "no_pellets",
    11: "no_wood",
    12: "flame_vanished",
    13: "buffer_sensor",
    14: "buffer_overheat",
    15: "power_loss",
}
# Register 8, bit -> error key (newer firmware only)
ERRORS_2: dict[int, str] = {0: "fan_jammed", 1: "too_much_wood"}

# "Power loss" also covers a manual power off, so it is reported in the list of
# errors but does not by itself raise the "problem" binary sensor.
ERROR_POWER_LOSS = "power_loss"

PROGRAM_MODES: dict[int, str] = {
    0: "day",
    1: "night",
    2: "off",
    3: "prg1",
    4: "prg2",
    5: "prg3",
}
WORK_MODES: dict[int, str] = {0: "winter", 1: "summer"}

FUEL_MODES: dict[int, str] = {0: "pellet", 1: "wood", 2: "wood_pellet"}
FUEL_PELLET = 0
PROCESS_STATE_STOP = 0


def fuel_change_allowed(current: int | None, new: int, process_state: int | None) -> bool:
    """Whether the fuel mode may be changed right now.

    Switching between "wood" and "wood and pellet" is possible while the stove is
    running (as with the original controls). Any change involving "pellet" needs
    the stove to be stopped.
    """
    if new not in FUEL_MODES:
        return False
    if current in (1, 2) and new in (1, 2):
        return True
    return process_state == PROCESS_STATE_STOP


# Event ids 1..15 of the error log (44000..), -> error key used by the translations
ERROR_LOG_KEYS: dict[int, str] = {
    1: "boiler_sensor",
    2: "feeder_sensor",
    3: "exhaust_sensor",
    4: "safety_input",
    5: "capacitive_unjamming",
    6: "boiler_overheat",
    7: "feeder_ignition",
    8: "no_pellets",
    9: "no_wood",
    10: "flame_vanished",
    11: "hot_water_sensor",
    12: "buffer_overheat",
    13: "power_loss",
    14: "buffer_sensor",
    15: "power_loss",
}


def parse_error_log(values: list[int]) -> list[dict]:
    """Decode the error log region (44000..44199), oldest event first.

    Each event is two registers: the id, then argument 1 (low byte) and argument 2
    (high byte). Ids 1..49 are errors (hour, minute), ids 50..249 are date markers
    (year = id - 50 + 2000, month, day) that apply to the errors that follow them.
    The log is a ring buffer: it starts right after the topmost empty event.
    """
    count = len(values) // 2
    events = [(values[2 * i], values[2 * i + 1]) for i in range(count)]
    empty = [i for i, (event_id, _) in enumerate(events) if event_id in (0, 255)]
    start = (empty[0] + 1) % count if empty else 0
    if empty and empty[0] == count - 1:
        start = 0
    ordered = events[start:] + events[:start]
    result: list[dict] = []
    date: str | None = None
    for event_id, args in ordered:
        arg1, arg2 = args & 0xFF, (args >> 8) & 0xFF
        if event_id in (0, 255):
            continue
        if 50 <= event_id <= 249:
            date = f"{event_id - 50 + 2000:04d}-{arg1:02d}-{arg2:02d}"
        elif event_id in ERROR_LOG_KEYS:
            result.append(
                {
                    "error": ERROR_LOG_KEYS[event_id],
                    "code": event_id,
                    "date": date,
                    "time": f"{arg1:02d}:{arg2:02d}",
                }
            )
    return result


def signed16(value: int) -> int:
    """Interpret a raw register as a signed 16-bit integer."""
    return value - 0x10000 if value & 0x8000 else value


def decode_errors(reg7: int, reg8: int) -> list[str]:
    """Return the keys of all active errors."""
    errors = [key for bit, key in ERRORS_1.items() if reg7 & (1 << bit)]
    errors += [key for bit, key in ERRORS_2.items() if reg8 & (1 << bit)]
    return errors


def has_problem(errors: list[str]) -> bool:
    """True if at least one error other than a plain power loss is active."""
    return any(error != ERROR_POWER_LOSS for error in errors)


def decode_text(values: list[int]) -> str:
    """Decode registers holding one ASCII character each."""
    chars: list[str] = []
    for value in values:
        if value == 0:
            break
        chars.append(chr(value) if 32 <= value < 127 else "?")
    return "".join(chars).strip()


def scale_value(raw: int, scale: float, signed: bool) -> int | float:
    """Convert a raw register value to its physical value."""
    value = signed16(raw) if signed else raw
    if scale == 1:
        return value
    return round(value * scale, 3)


# --------------------------------------------------------------------------- #
# Entity specifications (plain data, turned into HA entities by the platforms)
# --------------------------------------------------------------------------- #
@dataclass(frozen=True, slots=True)
class SensorSpec:
    key: str
    reg: int
    unit: str | None = None
    scale: float = 1
    device_class: str | None = None
    state_class: str | None = "measurement"
    signed: bool = True
    precision: int | None = None
    enabled: bool = True
    diagnostic: bool = False


@dataclass(frozen=True, slots=True)
class BinarySpec:
    key: str
    reg: int
    on_value: int | None = None  # None: any non-zero value means "on"
    device_class: str | None = None
    enabled: bool = True
    diagnostic: bool = False


@dataclass(frozen=True, slots=True)
class NumberSpec:
    key: str
    reg: int
    unit: str
    scale: float
    step: float
    default_min: float
    default_max: float
    enabled: bool = True


@dataclass(frozen=True, slots=True)
class SelectSpec:
    key: str
    reg: int
    options: dict[int, str]
    enabled: bool = True
    diagnostic: bool = False


@dataclass(frozen=True, slots=True)
class ButtonSpec:
    key: str
    reg: int
    value: int


TEMP = "°C"

SENSORS: tuple[SensorSpec, ...] = (
    SensorSpec("boiler_temperature", REG_BOILER_TEMP, TEMP, device_class="temperature", precision=0),
    SensorSpec("exhaust_temperature", REG_EXHAUST_TEMP, TEMP, device_class="temperature", precision=0),
    SensorSpec("room_temperature", REG_ROOM_TEMP, TEMP, 0.1, "temperature", precision=1),
    SensorSpec("feeder_temperature", REG_FEEDER_TEMP, TEMP, device_class="temperature", precision=0, diagnostic=True),
    SensorSpec("hot_water_temperature", REG_HOT_WATER_TEMP, TEMP, device_class="temperature", precision=0, enabled=False),
    SensorSpec("buffer_temperature", REG_BUFFER_TEMP, TEMP, device_class="temperature", precision=0, enabled=False),
    SensorSpec("room_temperature_internal", REG_ROOM_TEMP_INTERNAL, TEMP, 0.1, "temperature", precision=1, enabled=False, diagnostic=True),
    SensorSpec("room_temperature_extra", REG_ROOM_TEMP_EXTRA, TEMP, 0.1, "temperature", precision=1, enabled=False, diagnostic=True),
    SensorSpec("exhaust_fan_power", REG_EXHAUST_FAN_POWER, "%", signed=False),
    SensorSpec("blow_in_fan_power", REG_BLOW_IN_FAN_POWER, "%", signed=False),
    SensorSpec("fan_speed", REG_FAN_SPEED, "rpm", signed=False, enabled=False),
    SensorSpec("throttle_position", REG_THROTTLE, "%", signed=False, enabled=False),
    SensorSpec("burner_hours", REG_BURNER_HOURS, "h", device_class="duration", state_class="total_increasing", signed=False),
    SensorSpec("ignition_count", REG_IGNITION_COUNT, state_class="total_increasing", signed=False),
)

BINARY_SENSORS: tuple[BinarySpec, ...] = (
    BinarySpec("flame", REG_FLAME, on_value=2),
    BinarySpec("feeder", REG_FEEDER_OUTPUT, diagnostic=True),
    BinarySpec("ignition", REG_IGNITION_OUTPUT, diagnostic=True),
    BinarySpec("heating_pump", REG_HEATING_PUMP, device_class="running", diagnostic=True),
    BinarySpec("hot_water_pump", REG_HOT_WATER_PUMP, device_class="running", diagnostic=True, enabled=False),
    BinarySpec("cleaning", REG_CLEANING_OUTPUT, diagnostic=True, enabled=False),
    BinarySpec("alarm_output", REG_ALARM_OUTPUT, diagnostic=True, enabled=False),
    BinarySpec("safety_input", REG_SAFETY_INPUT, diagnostic=True, enabled=False),
    BinarySpec("thermostat", REG_THERMOSTAT, diagnostic=True, enabled=False),
    BinarySpec("external_enable", REG_EXTERNAL_ENABLE, diagnostic=True, enabled=False),
)

NUMBERS: tuple[NumberSpec, ...] = (
    NumberSpec("target_boiler_temperature", REG_TARGET_BOILER, TEMP, 1, 1, 30, 90),
    NumberSpec("target_hot_water_temperature", REG_TARGET_HOT_WATER, TEMP, 1, 1, 30, 90, enabled=False),
    NumberSpec("target_room_temperature_day", REG_TARGET_ROOM_DAY, TEMP, 0.1, 0.5, 5, 30),
    NumberSpec("target_room_temperature_night", REG_TARGET_ROOM_NIGHT, TEMP, 0.1, 0.5, 5, 30),
)

SELECTS: tuple[SelectSpec, ...] = (
    SelectSpec("program_mode", REG_PROGRAM_MODE, PROGRAM_MODES),
    SelectSpec("work_mode", REG_WORK_MODE, WORK_MODES, enabled=False, diagnostic=True),
)

BUTTONS: tuple[ButtonSpec, ...] = (
    ButtonSpec("clear_errors", REG_ERROR_FLAG, 0),
)

# Registers written by the integration. Anything else is refused by the
# coordinator so a bug can never touch the installer settings (> 123).
WRITABLE_REGISTERS = frozenset(
    {
        REG_TARGET_BOILER,
        REG_TARGET_HOT_WATER,
        REG_BOILER_WORK,
        REG_WORK_MODE,
        REG_ERROR_FLAG,
        REG_TARGET_ROOM_DAY,
        REG_TARGET_ROOM_NIGHT,
        REG_PROGRAM_MODE,
        *CLOCK_REGISTERS,
    }
)
