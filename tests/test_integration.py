"""Smoke test of the HA-facing code against the stub Home Assistant modules."""

from __future__ import annotations

import asyncio
import importlib
import json
import sys
from types import SimpleNamespace

import pytest

import ha_stubs
from fake_stove import FakeStove

ha_stubs.install()

pkg = "custom_components.iwona_pellets"
coordinator_mod = importlib.import_module(f"{pkg}.coordinator")
config_flow = importlib.import_module(f"{pkg}.config_flow")
reg = importlib.import_module(f"{pkg}.registers")
proto = importlib.import_module(f"{pkg}.protocol")
const = importlib.import_module(f"{pkg}.const")
init_mod = importlib.import_module(pkg)
platforms = {
    name: importlib.import_module(f"{pkg}.{name}")
    for name in ("sensor", "binary_sensor", "switch", "number", "select", "button", "image")
}
HomeAssistantError = sys.modules["homeassistant.exceptions"].HomeAssistantError


def run(coro):
    return asyncio.run(coro)


def make_entry(stove, framing, **options):
    return SimpleNamespace(
        entry_id="abc123",
        title="Iwona Pellets",
        data={"host": "127.0.0.1", "port": stove.port, "slave": 1, "framing": framing},
        options=options,
        runtime_data=None,
    )


def seed(stove):
    # registers are 1-based in the doc, 0-based on the wire
    def set_reg(r, v):
        stove.regs[r - 1] = v

    set_reg(1, 62)          # boiler 62 degC
    set_reg(5, 148)         # exhaust 148 degC
    set_reg(6, 10)          # modulated power
    set_reg(7, 0b1000_0000_0000_0000)  # only "power loss"
    set_reg(12, 2)          # flame visible
    set_reg(16, 80)
    set_reg(18, 1)          # feeder on
    set_reg(36, 215)        # room 21.5 degC
    for r, v in zip(range(109, 116), (2026, 11, 18, 2, 12, 40, 5)):
        set_reg(r, v)       # clock already right (same as the stubbed HA time)
    set_reg(102, 1)         # running
    set_reg(100, 65)
    set_reg(107, 205)
    set_reg(108, 180)
    set_reg(116, 0)         # day
    set_reg(10102, 1)       # fuel mode: wood
    set_reg(40064, 1234)
    set_reg(40065, 87)
    # limits (min/max of settings 100, 107, 108)
    set_reg(200, 50); set_reg(300, 80)
    set_reg(207, 50); set_reg(307, 300)
    set_reg(208, 50); set_reg(308, 300)
    for i, ch in enumerate("P.W. KEY"):
        set_reg(40000 + i, ord(ch))
    for i, ch in enumerate("RK-2014K"):
        set_reg(40032 + i, ord(ch))
    for i, ch in enumerate("1.2.3"):
        set_reg(40056 + i, ord(ch))


async def setup(framing=proto.FRAMING_RTU_OVER_TCP, **options):
    stove = FakeStove(framing)
    seed(stove)
    await stove.start()
    entry = make_entry(stove, framing, **options)
    coordinator = coordinator_mod.IwonaCoordinator(None, entry)
    coordinator.config_entry = entry
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    entities = {}
    for name, module in platforms.items():
        added = []
        await module.async_setup_entry(None, entry, lambda e, a=added: a.extend(e))
        entities[name] = added
    return stove, coordinator, entities


@pytest.mark.parametrize("framing", [proto.FRAMING_RTU_OVER_TCP, proto.FRAMING_MODBUS_TCP])
def test_first_refresh_and_entities(framing):
    async def scenario():
        stove, coord, ents = await setup(framing)
        try:
            assert coord.data[1] == 62 and coord.data[40065] == 87
            assert (coord.producer, coord.model, coord.firmware) == ("P.W. KEY", "RK-2014K", "1.2.3")
            assert coord.limits[107] == (50, 300)
            assert coord.device_info["manufacturer"] == "P.W. KEY"

            by_key = {e._attr_translation_key: e for group in ents.values() for e in group}
            assert by_key["boiler_temperature"].native_value == 62
            assert by_key["room_temperature"].native_value == 21.5
            assert by_key["burner_hours"].native_value == 1234
            assert by_key["process_state"].native_value == "modulated_power"
            assert by_key["process_state"].extra_state_attributes == {"code": 10}
            assert by_key["flame"].is_on is True
            assert by_key["feeder"].is_on is True
            assert by_key["ignition"].is_on is False
            assert by_key["stove"].is_on is True
            # "power loss" alone is not a problem, but it is listed
            assert by_key["problem"].is_on is False
            assert by_key["problem"].extra_state_attributes["errors"] == ["power_loss"]
            assert by_key["program_mode"].current_option == "day"
            n = by_key["target_room_temperature_day"]
            assert (n.native_value, n.native_min_value, n.native_max_value) == (20.5, 5.0, 30.0)
            b = by_key["target_boiler_temperature"]
            assert (b.native_value, b.native_min_value, b.native_max_value) == (65, 50, 80)
        finally:
            await coord.client.close()
            await stove.stop()

    run(scenario())


def test_commands():
    async def scenario():
        stove, coord, ents = await setup(start_command=2)
        try:
            by_key = {e._attr_translation_key: e for group in ents.values() for e in group}
            await by_key["stove"].async_turn_off()
            await by_key["stove"].async_turn_on()
            await by_key["target_room_temperature_day"].async_set_native_value(21.5)
            await by_key["target_boiler_temperature"].async_set_native_value(70)
            await by_key["program_mode"].async_select_option("off")
            await by_key["clear_errors"].async_press()
            assert "start_short" not in by_key
            assert "start_long" not in by_key
            assert stove.writes == [
                (101, 0),   # register 102 STOP
                (101, 2),   # register 102 START, long press (option)
                (106, 215),  # register 107, 21.5 degC in 0.1 units
                (99, 70),   # register 100
                (115, 2),   # register 116 program "off"
                (104, 0),   # register 105 clear errors
            ]
            assert coord.refresh_requests == 6
        finally:
            await coord.client.close()
            await stove.stop()

    run(scenario())


def test_write_guards():
    async def scenario():
        stove, coord, _ = await setup()
        try:
            with pytest.raises(ValueError):
                await coord.async_write(124, 1)       # installer area: refused
            with pytest.raises(ValueError):
                await coord.async_write(40064, 1)     # read-only counters
            stove.read_only.add(99)                   # controller ignores writes to reg 100
            coord.client.timeout = 0.3
            with pytest.raises(HomeAssistantError):
                await coord.async_write(100, 70)
        finally:
            await coord.client.close()
            await stove.stop()

    run(scenario())


def test_update_failure_when_stove_is_silent():
    async def scenario():
        stove, coord, _ = await setup()
        try:
            stove.silent = True
            coord.client.timeout = 0.3
            with pytest.raises(ha_stubs.UpdateFailed):
                await coord.async_refresh()
        finally:
            await coord.client.close()
            await stove.stop()

    run(scenario())


def test_config_flow():
    async def scenario():
        stove = FakeStove(proto.FRAMING_RTU_OVER_TCP)
        seed(stove)
        await stove.start()
        base = {"name": "Poêle", "host": "127.0.0.1", "port": stove.port, "slave": 1,
                "framing": proto.FRAMING_RTU_OVER_TCP}
        try:
            flow = config_flow.IwonaConfigFlow()
            assert (await flow.async_step_user())["type"] == "form"
            result = await flow.async_step_user(dict(base))
            assert result["type"] == "create_entry" and result["title"] == "Poêle"
            assert result["data"] == {k: base[k] for k in ("host", "port", "slave", "framing")}
            assert flow.unique_id == f"127.0.0.1:{stove.port}:1"

            result = await config_flow.IwonaConfigFlow().async_step_user({**base, "slave": 9})
            assert result["errors"] == {"base": "no_response"}
            result = await config_flow.IwonaConfigFlow().async_step_user({**base, "port": 1})
            assert result["errors"] == {"base": "cannot_connect"}
        finally:
            await stove.stop()

    # a short timeout for the "no_response" case
    orig = proto.ModbusClient.__init__.__defaults__
    proto.ModbusClient.__init__.__defaults__ = (proto.FRAMING_RTU_OVER_TCP, 0.4)
    try:
        run(scenario())
    finally:
        proto.ModbusClient.__init__.__defaults__ = orig


def test_options_flow():
    async def scenario():
        flow = config_flow.IwonaOptionsFlow()
        flow.config_entry = SimpleNamespace(options={})
        assert (await flow.async_step_init())["type"] == "form"
        result = await flow.async_step_init({"scan_interval": 30.0, "start_command": "2", "sync_clock": False})
        assert result["data"] == {"scan_interval": 30, "start_command": 2, "sync_clock": False}

    run(scenario())


def test_translations_match_entities():
    async def scenario():
        stove, coord, ents = await setup()
        await coord.client.close()
        await stove.stop()
        return ents

    ents = run(scenario())
    base = importlib.import_module(pkg).__file__.rsplit("/", 1)[0]
    for lang in ("en", "fr"):
        tr = json.load(open(f"{base}/translations/{lang}.json", encoding="utf-8"))
        for platform, entities in ents.items():
            for entity in entities:
                key = entity._attr_translation_key
                entry = tr["entity"][platform].get(key)
                assert entry and entry["name"], f"{lang}: missing {platform}.{key}"
        # enum sensor and selects: every state needs a translation
        states = tr["entity"]["sensor"]["process_state"]["state"]
        assert set(states) == set(reg.PROCESS_STATES.values()), lang
        for spec in reg.SELECTS:
            assert set(tr["entity"]["select"][spec.key]["state"]) == set(spec.options.values()), lang
        # config-flow keys
        user = tr["config"]["step"]["user"]["data"]
        assert set(user) == {"name", "host", "port", "slave", "framing"}
        assert {"cannot_connect", "no_response", "invalid_response", "unknown"} <= set(tr["config"]["error"])
        assert set(tr["selector"]["framing"]["options"]) == set(proto.FRAMINGS)
        assert set(tr["selector"]["start_command"]["options"]) == set(const.START_COMMANDS)


def test_setup_and_unload_entry():
    class ConfigEntries:
        def __init__(self):
            self.forwarded, self.unloaded, self.reloaded = None, None, None

        async def async_forward_entry_setups(self, entry, platforms_):
            self.forwarded = list(platforms_)

        async def async_unload_platforms(self, entry, platforms_):
            self.unloaded = list(platforms_)
            return True

        def async_schedule_reload(self, entry_id):
            self.reloaded = entry_id

    async def scenario():
        stove = FakeStove(proto.FRAMING_RTU_OVER_TCP)
        seed(stove)
        await stove.start()
        entry = make_entry(stove, proto.FRAMING_RTU_OVER_TCP)
        entry.async_on_unload = lambda cb: None
        entry.add_update_listener = lambda cb: cb
        hass = SimpleNamespace(config_entries=ConfigEntries())
        try:
            assert await init_mod.async_setup_entry(hass, entry) is True
            assert entry.runtime_data.data[1] == 62
            assert sorted(hass.config_entries.forwarded) == sorted(
                p.value for p in init_mod.PLATFORMS
            )
            assert await init_mod.async_unload_entry(hass, entry) is True
            await init_mod._async_options_updated(hass, entry)
            assert hass.config_entries.reloaded == "abc123"
        finally:
            await entry.runtime_data.client.close()
            await stove.stop()

    run(scenario())


def test_setup_fails_cleanly_when_stove_unreachable():
    async def scenario():
        stove = FakeStove(proto.FRAMING_RTU_OVER_TCP)
        entry = make_entry(stove, proto.FRAMING_RTU_OVER_TCP)
        entry.data["port"] = 1  # nothing listens there
        with pytest.raises(ha_stubs.UpdateFailed):
            await init_mod.async_setup_entry(SimpleNamespace(config_entries=None), entry)

    run(scenario())


def test_read_registers_service():
    services = importlib.import_module(f"{pkg}.services")
    registered = {}

    class Services:
        def async_register(self, domain, name, handler, schema=None, supports_response=None):
            registered[(domain, name)] = (handler, supports_response)

    async def scenario():
        stove, coord, _ = await setup()
        entry = coord.config_entry
        entries = SimpleNamespace(async_entries=lambda domain: [entry])
        class Http:
            async def async_register_static_paths(self, paths):
                pass

        hass = SimpleNamespace(services=Services(), config_entries=entries, http=Http(), js=[])
        assert await init_mod.async_setup(hass, {}) is True
        handler, support = registered[("iwona_pellets", "read_registers")]
        assert str(support) in ("only", "SupportsResponse.ONLY")

        def call(**data):
            return SimpleNamespace(hass=hass, data={"include_zero": False, **data})

        try:
            # settings 100..108 are seeded; the range spans two 100-register chunks
            out = await handler(call(start=90, count=130))
            assert out["registers"]["100"] == 65 and out["registers"]["107"] == 205
            assert all(v != 0 for v in out["registers"].values())
            assert "101" not in out["registers"]
            full = await handler(call(start=99, count=3, include_zero=True))
            assert full["registers"] == {"99": 0, "100": 65, "101": 0}
            # a read must never write anything
            assert stove.writes == []
            with pytest.raises(sys.modules["homeassistant.exceptions"].ServiceValidationError):
                await handler(call(start=65000, count=1000))
            with pytest.raises(sys.modules["homeassistant.exceptions"].ServiceValidationError):
                await handler(call(start=1, count=1, config_entry_id="nope"))
            stove.silent = True
            coord.client.timeout = 0.3
            with pytest.raises(HomeAssistantError):
                await handler(call(start=1, count=1))
        finally:
            await coord.client.close()
            await stove.stop()

    run(scenario())


def test_fuel_mode():
    async def scenario():
        stove, coord, ents = await setup()
        sel = {e._attr_translation_key: e for e in ents["select"]}["fuel_mode"]
        assert sel.current_option == "wood"
        assert sel._attr_entity_registry_enabled_default is False
        try:
            # running (state 10): wood <-> wood and pellet allowed
            await sel.async_select_option("wood_pellet")
            assert stove.writes[-1] == (10101, 2) and sel.current_option == "wood_pellet"
            await sel.async_select_option("wood")
            assert stove.writes[-1] == (10101, 1)
            n = len(stove.writes)
            await sel.async_select_option("wood")      # nothing to do
            assert len(stove.writes) == n
            # running: a change involving pellet is refused, nothing is written
            with pytest.raises(HomeAssistantError):
                await sel.async_select_option("pellet")
            assert len(stove.writes) == n
            # stopped (state 0): pellet allowed, and back
            stove.regs[5] = 0
            await sel.async_select_option("pellet")
            assert stove.writes[-1] == (10101, 0) and sel.current_option == "pellet"
            with pytest.raises(HomeAssistantError):
                stove.regs[5] = 10                       # running again
                await sel.async_select_option("wood")    # pellet -> wood while running: refused
            stove.regs[5] = 0
            await sel.async_select_option("wood")
            assert stove.regs[10101] == 1
            # the generic write path stays locked for this register
            with pytest.raises(ValueError):
                await coord.async_write(10102, 1)
            with pytest.raises(ValueError):
                await coord.async_set_fuel_mode(3)
            # controller ignores the write: clear error, state unchanged
            stove.read_only.add(10101)
            coord.client.timeout = 0.3
            with pytest.raises(HomeAssistantError):
                await sel.async_select_option("wood_pellet")
            assert stove.regs[10101] == 1
        finally:
            await coord.client.close()
            await stove.stop()

    run(scenario())


def test_fuel_change_rules():
    allowed = reg.fuel_change_allowed
    assert allowed(1, 2, 21) and allowed(2, 1, 21)          # wood <-> both, running
    assert not allowed(1, 0, 21) and not allowed(0, 2, 21)  # pellet, running
    assert allowed(1, 0, 0) and allowed(0, 2, 0)            # pellet, stopped
    assert not allowed(1, 3, 0)                              # invalid value
    assert not allowed(1, 0, None)                           # unknown state: refused


def test_display_image():
    import pathlib, struct, zlib
    display = importlib.import_module(f"{pkg}.display")
    sample = {}
    for item in (pathlib.Path(__file__).parent / "display_sample.txt").read_text().strip().split(","):
        k, v = item.split(":")
        sample[int(k)] = int(v)

    async def scenario():
        stove, coord, ents = await setup()
        try:
            for addr, val in sample.items():
                stove.regs[addr - 1] = val
            png = await coord.async_read_display()
            assert png.startswith(b"\x89PNG\r\n\x1a\n")
            w, h = struct.unpack(">II", png[16:24])
            assert (w, h) == (512, 256)
            img = ents["image"][0]
            assert img._attr_entity_registry_enabled_default is False
            await img._async_refresh()
            assert await img.async_image() == png and img.state_writes == 1
            await img._async_refresh()  # unchanged: no new state write
            assert img.state_writes == 1
        finally:
            await coord.client.close()
            await stove.stop()

    run(scenario())
    px = display.decode_display([0x0001] + [0] * 511)
    assert px[0][0] == 1 and sum(map(sum, px)) == 1
    px = display.decode_display([0x0100] + [0] * 511)
    assert px[0][1] == 1 and sum(map(sum, px)) == 1
    px = display.decode_display([0] * 64 + [0x0002] + [0] * 447)
    assert px[9][0] == 1
    with pytest.raises(ValueError):
        display.decode_display([0] * 10)


def test_virtual_keys():
    async def scenario():
        stove, coord, ents = await setup()
        try:
            btns = {e._attr_translation_key: e for e in ents["button"]}
            calls = []

            async def listener():
                calls.append(1)

            coord.display_listeners.append(listener)
            await btns["key_menu"].async_press()
            assert stove.writes[-1] == (41511, 5) and calls == [1]
            await btns["key_minus"].async_press()
            assert stove.writes[-1] == (41511, 4)
            assert all(btns[f"key_{k}"]._attr_entity_registry_enabled_default is False
                       for k in reg.KEYS)
            with pytest.raises(ValueError):
                await coord.async_press_key("power")
            stove.read_only.add(41511)
            coord.client.timeout = 0.3
            with pytest.raises(HomeAssistantError):
                await btns["key_ok"].async_press()
        finally:
            await coord.client.close()
            await stove.stop()

    run(scenario())


def test_state_22_is_known():
    assert reg.PROCESS_STATES[22] == "add_wood"


def test_card_registered_and_files_exist():
    import pathlib

    registered = []

    class Http:
        async def async_register_static_paths(self, paths):
            registered.extend(paths)

    hass = SimpleNamespace(http=Http(), js=[], services=SimpleNamespace(
        async_register=lambda *a, **k: None))
    run(init_mod.async_setup(hass, {}))
    assert registered and hass.js[0].startswith("/iwona_pellets/iwona-stove-card.js")
    root = pathlib.Path(init_mod.__file__).parent
    for f in ("www/iwona-stove-card.js", "www/stove.jpg", "brand/icon.png", "brand/logo.png"):
        assert (root / f).is_file()
    manifest = json.loads((root / "manifest.json").read_text())
    assert {"http", "frontend"} <= set(manifest["dependencies"])


def test_explore_menu_service():
    import json, pathlib
    services = importlib.import_module(f"{pkg}.services")
    display = importlib.import_module(f"{pkg}.display")
    registered = {}

    class Services:
        def async_register(self, domain, name, handler, schema=None, supports_response=None):
            registered[(domain, name)] = handler

    # a screen with the caption of the real menu (captured from a stove)
    sample = json.loads((pathlib.Path(__file__).parent / "menu_screen.json").read_text())

    async def scenario():
        stove, coord, _ = await setup()
        entry = coord.config_entry
        entries = SimpleNamespace(async_entries=lambda domain: [entry])

        class Http:
            async def async_register_static_paths(self, paths):
                pass

        hass = SimpleNamespace(services=Services(), config_entries=entries, http=Http(), js=[])
        await init_mod.async_setup(hass, {})
        handler = registered[("iwona_pellets", "explore_menu")]
        try:
            for addr, val in sample.items():
                stove.regs[int(addr) - 1] = val
            stove.regs[41512 - 1] = 0
            stove.regs[41513 - 1] = 1
            data = {"keys": ["menu", "ok"], "delay": 0, "each": True, "labels": {}, "export_font": True}
            out = await handler(SimpleNamespace(hass=hass, data=data))
            assert [s["after"] for s in out["screens"]] == ["menu", "ok"]
            assert out["screens"][-1]["menu_state"] == 1
            assert out["screens"][-1]["lines"] and out["unknown"]
            assert out["changed"] == {}
            assert [w for w in stove.writes if w[0] == 41511] == [(41511, 5), (41511, 1)]
            # labelled glyphs come out as text
            key = next(iter(out["unknown"]))
            out = await handler(SimpleNamespace(hass=hass, data={**data, "labels": {key: "Q"}}))
            assert "Q" in out["screens"][-1]["lines"][0] and out["font"][key] == "Q"
            # a register that changed during the exploration is reported
            stove.on_write = lambda a, v: stove.regs.__setitem__(106, 222) if a == 41511 else None
            out = await handler(SimpleNamespace(hass=hass, data={**data, "keys": ["plus"]}))
            assert out["changed"] == {"107": [205, 222]}
        finally:
            await coord.client.close()
            await stove.stop()

    run(scenario())


def test_clock_sync():
    from datetime import datetime

    async def scenario():
        stove, coord, ents = await setup()
        try:
            # controller clock lost (2014-01-01): the next poll rewrites it from HA
            for r, v in zip(range(109, 116), (2014, 1, 1, 0, 0, 0, 0)):
                stove.regs[r - 1] = v
            await coord.async_refresh()
            assert coord.controller_clock(coord.data) == datetime(2026, 11, 18, 12, 40, 5)
            assert [stove.regs[r - 1] for r in range(109, 116)] == [2026, 11, 18, 2, 12, 40, 5]
            # within tolerance: no new write
            n = len(stove.writes)
            await coord.async_refresh()
            assert len(stove.writes) == n
            # drift, but the option is off: untouched
            coord.sync_clock = False
            stove.regs[113] = 0
            await coord.async_refresh()
            assert stove.regs[113] == 0
            # manual button always works
            btn = {e._attr_translation_key: e for e in ents["button"]}["sync_clock"]
            await btn.async_press()
            assert stove.regs[113] == 40
            # controller ignores the write: clear error, and no retry storm
            stove.regs[113] = 0
            stove.read_only.add(112)
            coord.client.timeout = 0.3
            with pytest.raises(HomeAssistantError):
                await btn.async_press()
        finally:
            await coord.client.close()
            await stove.stop()

    run(scenario())

