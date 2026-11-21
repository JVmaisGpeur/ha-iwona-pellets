"""Data update coordinator for the Iwona Pellets integration."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
import time
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.util import dt as dt_util
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    CONF_FRAMING,
    CONF_SCAN_INTERVAL,
    CONF_SLAVE,
    CONF_START_COMMAND,
    CONF_SYNC_CLOCK,
    CLOCK_MAX_DRIFT,
    CLOCK_RETRY_SECONDS,
    DEFAULT_SYNC_CLOCK,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_START_COMMAND,
    DOMAIN,
)
from .display import decode_display, render_png
from .protocol import ModbusClient, ModbusError, ModbusTimeout
from .registers import (
    BLOCK_COUNTERS,
    BLOCK_DISPLAY,
    BLOCK_ERROR_LOG,
    REG_ERRORS_1,
    REG_ERRORS_2,
    parse_error_log,
    BLOCK_FUEL,
    BLOCK_INFO,
    BLOCK_MAX,
    BLOCK_MIN,
    BLOCK_SETTINGS,
    KEYS,
    REG_KEYBOARD,
    BLOCK_STATES,
    CLOCK_REGISTERS,
    REG_CLOCK_START,
    FUEL_MODES,
    LIMIT_MAX_OFFSET,
    LIMIT_MIN_OFFSET,
    REG_FUEL_MODE,
    REG_INFO_COUNT,
    REG_INFO_START,
    REG_PROCESS_STATE,
    WRITABLE_REGISTERS,
    decode_text,
    fuel_change_allowed,
    signed16,
    to_address,
)

_LOGGER = logging.getLogger(__name__)


class IwonaCoordinator(DataUpdateCoordinator[dict[int, int]]):
    """Poll the controller and hold the raw value of every register we use.

    ``data`` maps the *logical* register number (as in the manufacturer's
    documentation) to its raw 16-bit value.
    """

    def __init__(self, hass: HomeAssistant, entry: IwonaConfigEntry) -> None:
        interval = int(entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL))
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=timedelta(seconds=interval),
        )
        self.client = ModbusClient(
            entry.data[CONF_HOST],
            entry.data[CONF_PORT],
            entry.data[CONF_SLAVE],
            entry.data[CONF_FRAMING],
        )
        self.start_command = int(
            entry.options.get(CONF_START_COMMAND, DEFAULT_START_COMMAND)
        )
        # Limits of the settings, from registers 200..399: {setting: (min, max)}
        self.limits: dict[int, tuple[int, int]] = {}
        self.producer: str | None = None
        self.model: str | None = None
        self.firmware: str | None = None
        # callbacks (async) run after a virtual key press, to refresh the display image
        self.display_listeners: list = []
        self.sync_clock = bool(entry.options.get(CONF_SYNC_CLOCK, DEFAULT_SYNC_CLOCK))
        self._last_clock_attempt: float | None = None
        # decoded error log (oldest first), refreshed when the error registers change
        self.error_log: list[dict] = []
        self._error_signature: tuple[int, int] | None = None

    @property
    def device_info(self) -> DeviceInfo:
        """Device shared by all entities of the entry."""
        return DeviceInfo(
            identifiers={(DOMAIN, self.config_entry.entry_id)},
            name=self.config_entry.title,
            manufacturer=self.producer or "P.W. KEY",
            model=self.model or "RK-2014K/KW",
            sw_version=self.firmware,
        )

    async def _read_block(self, block: tuple[int, int]) -> dict[int, int]:
        start, count = block
        values = await self.client.read_holding(to_address(start), count)
        return {start + offset: value for offset, value in enumerate(values)}

    async def async_read_range(self, start: int, count: int) -> dict[int, int]:
        """Read any range of registers (read-only), in chunks the controller accepts."""
        values: dict[int, int] = {}
        for first in range(start, start + count, 100):
            chunk = min(100, start + count - first)
            values.update(await self._read_block((first, chunk)))
        return values

    async def _async_setup(self) -> None:
        """Read the static information once (device identity, setting limits)."""
        try:
            info = await self._read_block(BLOCK_INFO)
        except ModbusError as err:
            _LOGGER.debug("Cannot read device information: %s", err)
        else:
            chars = [info[REG_INFO_START + i] for i in range(REG_INFO_COUNT)]
            self.producer = decode_text(chars[0:32]) or None
            self.model = decode_text(chars[32:56]) or None
            self.firmware = decode_text(chars[56:64]) or None

        try:
            minimums = await self._read_block(BLOCK_MIN)
            maximums = await self._read_block(BLOCK_MAX)
        except ModbusError as err:
            _LOGGER.debug("Cannot read setting limits: %s", err)
            return
        for setting in range(100, 109):
            low = minimums.get(setting + LIMIT_MIN_OFFSET)
            high = maximums.get(setting + LIMIT_MAX_OFFSET)
            if low is not None and high is not None and signed16(high) > signed16(low):
                self.limits[setting] = (signed16(low), signed16(high))

    async def _async_update_data(self) -> dict[int, int]:
        data: dict[int, int] = {}
        try:
            for block in (BLOCK_STATES, BLOCK_SETTINGS, BLOCK_COUNTERS, BLOCK_FUEL):
                data.update(await self._read_block(block))
        except ModbusError as err:
            raise UpdateFailed(f"Error communicating with the stove: {err}") from err
        await self._async_auto_sync_clock(data)
        await self._async_refresh_error_log(data)
        return data

    async def _async_refresh_error_log(self, data: dict[int, int]) -> None:
        """Read the error log at start and whenever the error registers change."""
        signature = (data.get(REG_ERRORS_1, 0), data.get(REG_ERRORS_2, 0))
        if signature == self._error_signature:
            return
        try:
            start, count = BLOCK_ERROR_LOG
            values = await self.async_read_range(start, count)
        except ModbusError as err:
            _LOGGER.debug("Cannot read the error log: %s", err)
            return
        self.error_log = parse_error_log([values[start + i] for i in range(count)])
        self._error_signature = signature


    @staticmethod
    def controller_clock(data: dict[int, int]) -> datetime | None:
        """Controller date and time from registers 109..115, None if invalid."""
        try:
            year, month, day, _weekday, hour, minute, second = (
                data[r] for r in CLOCK_REGISTERS
            )
            return datetime(year, month, day, hour, minute, second)
        except (KeyError, ValueError):
            return None

    async def _async_auto_sync_clock(self, data: dict[int, int]) -> None:
        """Set the controller clock from Home Assistant when it is wrong (power loss)."""
        if not self.sync_clock:
            return
        now = dt_util.now().replace(tzinfo=None)
        clock = self.controller_clock(data)
        if clock is not None and abs((now - clock).total_seconds()) <= CLOCK_MAX_DRIFT:
            return
        if (
            self._last_clock_attempt is not None
            and time.monotonic() - self._last_clock_attempt < CLOCK_RETRY_SECONDS
        ):
            return
        self._last_clock_attempt = time.monotonic()
        try:
            data.update(await self.async_sync_clock())
        except HomeAssistantError as err:
            _LOGGER.warning("Cannot set the stove clock: %s", err)

    async def async_sync_clock(self) -> dict[int, int]:
        """Write the current Home Assistant date and time to the controller."""
        now = dt_util.now().replace(tzinfo=None)
        values = [
            now.year, now.month, now.day, now.weekday(), now.hour, now.minute, now.second
        ]
        try:
            for register, value in zip(CLOCK_REGISTERS, values):
                await self.client.write_register(to_address(register), value)
            readback = await self._read_block((REG_CLOCK_START, len(CLOCK_REGISTERS)))
        except ModbusTimeout as err:
            raise HomeAssistantError(
                "The controller ignored the clock change (Modbus access level too low?)."
            ) from err
        except ModbusError as err:
            raise HomeAssistantError(f"Cannot set the clock: {err}") from err
        clock = self.controller_clock(readback)
        if clock is None or abs((now - clock).total_seconds()) > 60:
            raise HomeAssistantError("The controller did not keep the new date and time.")
        if self.data is not None:
            self.async_set_updated_data({**self.data, **readback})
        return readback

    async def async_write(self, register: int, value: int) -> None:
        """Write a basic setting, then refresh.

        Only the registers listed in ``WRITABLE_REGISTERS`` (settings 100..123,
        never the installer settings) can be written.
        """
        if register not in WRITABLE_REGISTERS:
            raise ValueError(f"Register {register} is not writable by this integration")
        try:
            await self.client.write_register(to_address(register), value)
        except ModbusTimeout as err:
            raise HomeAssistantError(
                "The controller did not acknowledge the write. The value may be out of "
                "range, or the Modbus access level in the stove settings is too low "
                "(it must be 'USER')."
            ) from err
        except ModbusError as err:
            raise HomeAssistantError(f"Cannot write to the stove: {err}") from err
        if self.data is not None:
            self.async_set_updated_data({**self.data, register: value})
        await self.async_request_refresh()

    async def async_set_fuel_mode(self, mode: int) -> None:
        """Change the fuel mode (register 10102), with safety checks.

        This is the only write outside the documented basic registers. It is
        limited to register 10102 and to the values 0, 1 and 2. The current mode
        and process state are read again right before writing, and the result is
        read back: a value silently ignored by the controller becomes an error.
        """
        if mode not in FUEL_MODES:
            raise ValueError(f"Invalid fuel mode {mode}")
        try:
            state = (await self._read_block((REG_PROCESS_STATE, 1)))[REG_PROCESS_STATE]
            current = (await self._read_block(BLOCK_FUEL))[REG_FUEL_MODE]
        except ModbusError as err:
            raise HomeAssistantError(f"Cannot read the stove before the change: {err}") from err
        if current == mode:
            return
        if not fuel_change_allowed(current, mode, state):
            raise HomeAssistantError(
                "Changing to or from pellet only is possible when the stove is stopped. "
                "Switching between wood and wood and pellet is possible while running."
            )
        try:
            await self.client.write_register(to_address(REG_FUEL_MODE), mode)
        except ModbusTimeout as err:
            raise HomeAssistantError(
                "The controller ignored the change (value out of its allowed range, or the "
                "Modbus access level in the stove settings does not allow this setting)."
            ) from err
        except ModbusError as err:
            raise HomeAssistantError(f"Cannot write to the stove: {err}") from err
        try:
            applied = (await self._read_block(BLOCK_FUEL))[REG_FUEL_MODE]
        except ModbusError as err:
            raise HomeAssistantError(f"Cannot verify the change: {err}") from err
        if self.data is not None:
            self.async_set_updated_data({**self.data, REG_FUEL_MODE: applied})
        if applied != mode:
            raise HomeAssistantError(
                f"The controller kept the fuel mode value {applied} instead of {mode}."
            )
        await self.async_request_refresh()

    async def async_read_display(self) -> bytes:
        """Read the controller's LCD and return it as a PNG (read-only)."""
        try:
            values = await self.async_read_range(*BLOCK_DISPLAY)
        except ModbusError as err:
            raise HomeAssistantError(f"Cannot read the display: {err}") from err
        start, count = BLOCK_DISPLAY
        return render_png(decode_display([values[start + i] for i in range(count)]))


    async def async_press_key(self, key: str) -> None:
        """Press a virtual key of the controller (register 41512).

        Only the five keys of ``KEYS`` can be sent; nothing else is written to the
        terminal region. The controller clears the register itself, so no read-back.
        """
        if key not in KEYS:
            raise ValueError(f"Unknown key {key}")
        try:
            await self.client.write_register(to_address(REG_KEYBOARD), KEYS[key])
        except ModbusTimeout as err:
            raise HomeAssistantError(
                "The controller ignored the key press (terminal access is not allowed "
                "at the current Modbus access level)."
            ) from err
        except ModbusError as err:
            raise HomeAssistantError(f"Cannot press the key: {err}") from err
        await asyncio.sleep(0.4)
        for listener in list(self.display_listeners):
            await listener()


type IwonaConfigEntry = ConfigEntry[IwonaCoordinator]
