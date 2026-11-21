"""A tiny fake RK-2014K/KW speaking Modbus over TCP, for tests."""

from __future__ import annotations

import asyncio
import struct

from conftest import load

protocol = load("protocol")


class FakeStove:
    def __init__(self, framing: str, slave: int = 1) -> None:
        self.framing = framing
        self.slave = slave
        self.regs: dict[int, int] = {}  # 0-based wire address -> value
        self.read_only = set(range(0, 38))
        self.writes: list[tuple[int, int]] = []
        self.server: asyncio.AbstractServer | None = None
        self.port = 0
        self.silent = False
        self.connections = 0
        self.on_write = None  # optional callback(addr, value) after a write is applied

    async def start(self) -> None:
        self.server = await asyncio.start_server(self._handle, "127.0.0.1", 0)
        self.port = self.server.sockets[0].getsockname()[1]

    async def stop(self) -> None:
        assert self.server
        self.server.close()
        await self.server.wait_closed()

    def _answer_pdu(self, pdu: bytes) -> bytes | None:
        func = pdu[0]
        if func == 3:
            _, addr, count = struct.unpack(">BHH", pdu)
            values = [self.regs.get(addr + i, 0) for i in range(count)]
            return bytes([3, 2 * count]) + struct.pack(f">{count}H", *values)
        if func == 6:
            _, addr, value = struct.unpack(">BHH", pdu)
            if addr in self.read_only:
                return None  # the controller silently ignores such writes
            self.regs[addr] = value
            self.writes.append((addr, value))
            if self.on_write:
                self.on_write(addr, value)
            return pdu
        return bytes([func | 0x80, 1])  # illegal function

    async def _handle(self, reader, writer) -> None:
        self.connections += 1
        try:
            while True:
                if self.framing == protocol.FRAMING_RTU_OVER_TCP:
                    head = await reader.readexactly(2)
                    func = head[1]
                    rest = await reader.readexactly(4)
                    crc = await reader.readexactly(2)
                    frame = head + rest
                    if struct.unpack("<H", crc)[0] != protocol.crc16(frame):
                        continue
                    pdu = frame[1:]
                    unit = frame[0]
                else:
                    header = await reader.readexactly(7)
                    tid, _, length, unit = struct.unpack(">HHHB", header)
                    pdu = await reader.readexactly(length - 1)
                if self.silent or unit != self.slave:
                    continue
                answer = self._answer_pdu(pdu)
                if answer is None:
                    continue
                if self.framing == protocol.FRAMING_RTU_OVER_TCP:
                    frame = bytes([unit]) + answer
                    writer.write(frame + struct.pack("<H", protocol.crc16(frame)))
                else:
                    writer.write(struct.pack(">HHHB", tid, 0, len(answer) + 1, unit) + answer)
                await writer.drain()
        except (asyncio.IncompleteReadError, ConnectionError):
            pass
        finally:
            writer.close()
