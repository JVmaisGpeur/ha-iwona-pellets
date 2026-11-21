"""Minimal asynchronous Modbus client for the RK-2014K/KW controller.

Two framings are supported, both over a TCP socket (e.g. an Elfin EW11 or any
RS485 <-> Ethernet/WiFi converter):

* ``rtu_over_tcp``: raw Modbus RTU frames (slave, function, data, CRC16) are
  tunnelled through the socket. This is the "transparent" mode of the converter.
* ``modbus_tcp``: standard Modbus TCP (MBAP header). The converter does the
  RTU <-> TCP translation itself ("Modbus gateway" mode).

Only the two functions the controller needs are implemented:
``03h`` (read holding registers) and ``06h`` (preset single register).

This module has no Home Assistant dependency so that it can be unit tested.
"""

from __future__ import annotations

import asyncio
import struct

FRAMING_RTU_OVER_TCP = "rtu_over_tcp"
FRAMING_MODBUS_TCP = "modbus_tcp"
FRAMINGS = (FRAMING_RTU_OVER_TCP, FRAMING_MODBUS_TCP)

FUNC_READ_HOLDING = 0x03
FUNC_WRITE_SINGLE = 0x06

# The controller refuses to return more than 127 registers per request.
MAX_READ_COUNT = 127


class ModbusError(Exception):
    """Base class for all errors raised by this module."""


class ModbusConnectionError(ModbusError):
    """The TCP connection could not be established or was lost."""


class ModbusTimeout(ModbusError):
    """The device did not answer in time.

    Note: the RK-2014K/KW silently ignores bad requests (wrong CRC, unknown
    register, read-only register, value out of range), so a rejected write also
    shows up as a timeout.
    """


class ModbusProtocolError(ModbusError):
    """The answer is malformed (bad CRC, wrong slave, wrong length...)."""


class ModbusException(ModbusError):
    """The device answered with a Modbus exception response."""

    def __init__(self, code: int) -> None:
        super().__init__(f"Modbus exception code {code}")
        self.code = code


def crc16(data: bytes) -> int:
    """Return the Modbus CRC16 of ``data``."""
    crc = 0xFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            crc = (crc >> 1) ^ 0xA001 if crc & 1 else crc >> 1
    return crc


def _with_crc(frame: bytes) -> bytes:
    return frame + struct.pack("<H", crc16(frame))


class ModbusClient:
    """Tiny Modbus master. Requests are serialised with a lock."""

    def __init__(
        self,
        host: str,
        port: int,
        slave: int,
        framing: str = FRAMING_RTU_OVER_TCP,
        timeout: float = 3.0,
    ) -> None:
        if framing not in FRAMINGS:
            raise ValueError(f"Unknown framing {framing!r}")
        self.host = host
        self.port = port
        self.slave = slave
        self.framing = framing
        self.timeout = timeout
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None
        self._lock = asyncio.Lock()
        self._transaction_id = 0

    # ------------------------------------------------------------------ #
    # Connection handling
    # ------------------------------------------------------------------ #
    async def _ensure_connected(self) -> None:
        if self._writer is not None and not self._writer.is_closing():
            return
        await self._close()
        try:
            async with asyncio.timeout(self.timeout):
                self._reader, self._writer = await asyncio.open_connection(
                    self.host, self.port
                )
        except TimeoutError as err:
            raise ModbusConnectionError(
                f"Timeout connecting to {self.host}:{self.port}"
            ) from err
        except OSError as err:
            raise ModbusConnectionError(
                f"Cannot connect to {self.host}:{self.port}: {err}"
            ) from err

    async def _close(self) -> None:
        writer, self._reader, self._writer = self._writer, None, None
        if writer is None:
            return
        writer.close()
        try:
            await writer.wait_closed()
        except (OSError, TimeoutError):
            pass

    async def close(self) -> None:
        """Close the connection (it is reopened automatically on next use)."""
        async with self._lock:
            await self._close()

    # ------------------------------------------------------------------ #
    # Public API (addresses are the 0-based addresses sent on the wire)
    # ------------------------------------------------------------------ #
    async def read_holding(self, address: int, count: int) -> list[int]:
        """Read ``count`` holding registers starting at ``address``."""
        if not 1 <= count <= MAX_READ_COUNT:
            raise ValueError(f"count must be 1..{MAX_READ_COUNT}")
        if not 0 <= address <= 0xFFFF - count + 1:
            raise ValueError("address out of range")
        pdu = struct.pack(">BHH", FUNC_READ_HOLDING, address, count)
        body = await self._transact(pdu)
        # body = function, byte count, data...
        if len(body) < 2 or body[1] != 2 * count or len(body) != 2 + 2 * count:
            raise ModbusProtocolError("Unexpected read response length")
        return list(struct.unpack(f">{count}H", body[2:]))

    async def write_register(self, address: int, value: int) -> None:
        """Write a single holding register."""
        if not 0 <= address <= 0xFFFF:
            raise ValueError("address out of range")
        if not 0 <= value <= 0xFFFF:
            raise ValueError("value out of range")
        pdu = struct.pack(">BHH", FUNC_WRITE_SINGLE, address, value)
        body = await self._transact(pdu)
        if body != pdu:
            raise ModbusProtocolError("Write response does not echo the request")

    # ------------------------------------------------------------------ #
    # Framing
    # ------------------------------------------------------------------ #
    async def _transact(self, pdu: bytes) -> bytes:
        """Send a PDU and return the PDU of the answer."""
        async with self._lock:
            await self._ensure_connected()
            assert self._reader is not None and self._writer is not None
            try:
                async with asyncio.timeout(self.timeout):
                    if self.framing == FRAMING_RTU_OVER_TCP:
                        return await self._transact_rtu(pdu)
                    return await self._transact_tcp(pdu)
            except TimeoutError as err:
                await self._close()
                raise ModbusTimeout("No answer from the device") from err
            except (OSError, asyncio.IncompleteReadError) as err:
                await self._close()
                raise ModbusConnectionError(f"Connection lost: {err}") from err
            except ModbusException:
                # A clean exception response: the stream is still in sync.
                raise
            except ModbusError:
                # Garbage on the line: drop the connection to resync.
                await self._close()
                raise

    async def _transact_rtu(self, pdu: bytes) -> bytes:
        reader, writer = self._reader, self._writer
        assert reader is not None and writer is not None
        writer.write(_with_crc(bytes([self.slave]) + pdu))
        await writer.drain()

        head = await reader.readexactly(2)
        if head[0] != self.slave:
            raise ModbusProtocolError(f"Answer from slave {head[0]}, expected {self.slave}")
        function = head[1]
        if function & 0x80:
            rest = await reader.readexactly(3)
            frame = head + rest
            self._check_crc(frame)
            raise ModbusException(rest[0])
        if function != pdu[0]:
            raise ModbusProtocolError(f"Unexpected function {function:#04x}")
        if function == FUNC_READ_HOLDING:
            byte_count = await reader.readexactly(1)
            data = await reader.readexactly(byte_count[0] + 2)
            frame = head + byte_count + data
        else:
            data = await reader.readexactly(6)
            frame = head + data
        self._check_crc(frame)
        return frame[1:-2]

    async def _transact_tcp(self, pdu: bytes) -> bytes:
        reader, writer = self._reader, self._writer
        assert reader is not None and writer is not None
        self._transaction_id = (self._transaction_id + 1) & 0xFFFF
        tid = self._transaction_id
        writer.write(struct.pack(">HHHB", tid, 0, len(pdu) + 1, self.slave) + pdu)
        await writer.drain()

        header = await reader.readexactly(7)
        rx_tid, protocol, length, unit = struct.unpack(">HHHB", header)
        if rx_tid != tid or protocol != 0 or not 2 <= length <= 260:
            raise ModbusProtocolError("Invalid MBAP header")
        if unit != self.slave:
            raise ModbusProtocolError(f"Answer from unit {unit}, expected {self.slave}")
        body = await reader.readexactly(length - 1)
        if body[0] & 0x80:
            raise ModbusException(body[1] if len(body) > 1 else 0)
        if body[0] != pdu[0]:
            raise ModbusProtocolError(f"Unexpected function {body[0]:#04x}")
        return body

    @staticmethod
    def _check_crc(frame: bytes) -> None:
        if struct.unpack("<H", frame[-2:])[0] != crc16(frame[:-2]):
            raise ModbusProtocolError("CRC error")
