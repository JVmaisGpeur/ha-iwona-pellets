from __future__ import annotations

import asyncio

import pytest

from conftest import load
from fake_stove import FakeStove

protocol = load("protocol")

FRAMINGS = [protocol.FRAMING_RTU_OVER_TCP, protocol.FRAMING_MODBUS_TCP]


def run(coro):
    return asyncio.run(coro)


def test_crc16_known_vector():
    # Classic example: 01 03 00 00 00 0A -> CRC C5 CD (sent low byte first)
    assert protocol.crc16(bytes.fromhex("01030000000A")) == 0xCDC5


@pytest.mark.parametrize("framing", FRAMINGS)
def test_read_and_write(framing):
    async def scenario():
        stove = FakeStove(framing)
        stove.regs.update({0: 62, 4: 150, 35: 215, 99: 65, 106: 205})
        await stove.start()
        client = protocol.ModbusClient("127.0.0.1", stove.port, 1, framing, timeout=1)
        try:
            states = await client.read_holding(0, 38)
            assert len(states) == 38
            assert states[0] == 62 and states[4] == 150 and states[35] == 215
            assert await client.read_holding(99, 1) == [65]
            await client.write_register(101, 1)  # register 102 = boiler work
            assert stove.writes == [(101, 1)]
            assert (await client.read_holding(101, 1)) == [1]
            assert stove.connections == 1  # connection is reused
        finally:
            await client.close()
            await stove.stop()

    run(scenario())


@pytest.mark.parametrize("framing", FRAMINGS)
def test_read_only_write_times_out_then_recovers(framing):
    async def scenario():
        stove = FakeStove(framing)
        stove.regs[0] = 55
        await stove.start()
        client = protocol.ModbusClient("127.0.0.1", stove.port, 1, framing, timeout=0.3)
        try:
            with pytest.raises(protocol.ModbusTimeout):
                await client.write_register(0, 1)  # read-only: silently ignored
            assert stove.regs[0] == 55
            assert await client.read_holding(0, 1) == [55]  # reconnects
            assert stove.connections == 2
        finally:
            await client.close()
            await stove.stop()

    run(scenario())


@pytest.mark.parametrize("framing", FRAMINGS)
def test_wrong_slave_times_out(framing):
    async def scenario():
        stove = FakeStove(framing, slave=1)
        await stove.start()
        client = protocol.ModbusClient("127.0.0.1", stove.port, 7, framing, timeout=0.3)
        try:
            with pytest.raises(protocol.ModbusTimeout):
                await client.read_holding(0, 1)
        finally:
            await client.close()
            await stove.stop()

    run(scenario())


def test_connection_refused():
    async def scenario():
        client = protocol.ModbusClient("127.0.0.1", 1, 1, timeout=0.5)
        with pytest.raises(protocol.ModbusConnectionError):
            await client.read_holding(0, 1)

    run(scenario())


def test_argument_validation():
    client = protocol.ModbusClient("127.0.0.1", 1, 1)
    with pytest.raises(ValueError):
        run(client.read_holding(0, 128))
    with pytest.raises(ValueError):
        run(client.write_register(0, 70000))
    with pytest.raises(ValueError):
        protocol.ModbusClient("h", 1, 1, framing="nope")


def test_exception_response_rtu():
    async def scenario():
        stove = FakeStove(protocol.FRAMING_RTU_OVER_TCP)
        await stove.start()
        client = protocol.ModbusClient("127.0.0.1", stove.port, 1, timeout=1)
        try:
            # Function 0x04 is not implemented by the fake: it answers an exception
            with pytest.raises(protocol.ModbusException) as info:
                await client._transact(bytes([0x04, 0, 0, 0, 1]))
            assert info.value.code == 1
        finally:
            await client.close()
            await stove.stop()

    run(scenario())
