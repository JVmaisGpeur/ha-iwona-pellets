from __future__ import annotations

from conftest import load

reg = load("registers")


def test_signed16():
    assert reg.signed16(65535) == -1
    assert reg.signed16(215) == 215


def test_scale_value():
    assert reg.scale_value(215, 0.1, True) == 21.5
    assert reg.scale_value(65526, 0.1, True) == -1.0
    assert reg.scale_value(62, 1, True) == 62
    assert reg.scale_value(65535, 1, False) == 65535


def test_decode_errors_and_problem():
    assert reg.decode_errors(0, 0) == []
    assert reg.decode_errors(0b1000_0000_0000_0001, 0b10) == [
        "boiler_sensor",
        "power_loss",
        "too_much_wood",
    ]
    assert not reg.has_problem(["power_loss"])
    assert reg.has_problem(["power_loss", "no_pellets"])
    assert not reg.has_problem([])


def test_decode_text():
    chars = [ord(c) for c in "RK-2014KW"] + [0] * 5
    assert reg.decode_text(chars) == "RK-2014KW"
    assert reg.decode_text([0] * 8) == ""


def test_to_address():
    assert reg.to_address(1) == 0
    assert reg.to_address(102) == 101
    assert reg.to_address(40064) == 40063


def test_specs_are_consistent():
    keys = [s.key for s in reg.SENSORS + reg.BINARY_SENSORS + reg.NUMBERS + reg.SELECTS]
    assert len(keys) == len(set(keys)), "duplicate entity keys"
    # every register used by a spec is inside a block read by the coordinator
    def covered(r):
        blocks = (reg.BLOCK_STATES, reg.BLOCK_SETTINGS, reg.BLOCK_COUNTERS)
        return any(start <= r < start + n for start, n in blocks)

    for spec in reg.SENSORS + reg.BINARY_SENSORS + reg.NUMBERS + reg.SELECTS:
        assert covered(spec.reg), spec
    # blocks never exceed what the controller accepts
    for _, n in (reg.BLOCK_STATES, reg.BLOCK_SETTINGS, reg.BLOCK_INFO, reg.BLOCK_MIN, reg.BLOCK_MAX):
        assert n <= 127
    # nothing in the installer area can be written
    assert max(reg.WRITABLE_REGISTERS) <= 123
    # the limits of every number are inside the limit blocks
    for n in reg.NUMBERS:
        assert reg.BLOCK_MIN[0] <= n.reg + reg.LIMIT_MIN_OFFSET < reg.BLOCK_MIN[0] + reg.BLOCK_MIN[1]
        assert reg.BLOCK_MAX[0] <= n.reg + reg.LIMIT_MAX_OFFSET < reg.BLOCK_MAX[0] + reg.BLOCK_MAX[1]


def test_parse_error_log_ring_buffer_with_dates():
    from conftest import load
    r = load("registers")
    values = [0] * 200
    # date marker 2026-11-18, then two errors, then empty slot, then older stale data
    values[0:2] = [50 + 26, 11 | (18 << 8)]
    values[2:4] = [10, 7 | (30 << 8)]       # flame vanished 07:30
    values[4:6] = [8, 22 | (5 << 8)]        # no pellets 22:05
    # slot 3 empty: log starts right after it, at slot 4 (older stale event)
    values[8:10] = [13, 1 | (2 << 8)]
    log = r.parse_error_log(values)
    assert [e["error"] for e in log] == ["power_loss", "flame_vanished", "no_pellets"]
    assert log[1]["date"] == "2026-11-18" and log[1]["time"] == "07:30"
    assert log[0]["date"] is None



def test_translations_have_the_same_keys():
    import json
    from pathlib import Path

    folder = Path(__file__).parent.parent / "custom_components" / "iwona_pellets" / "translations"

    def keys(obj, prefix=""):
        out = set()
        for key, value in obj.items():
            path = f"{prefix}/{key}"
            out |= keys(value, path) if isinstance(value, dict) else {path}
        return out

    reference = keys(json.loads((folder / "en.json").read_text()))
    files = sorted(folder.glob("*.json"))
    assert {f.stem for f in files} >= {"en", "fr", "de", "es", "it", "nl", "pl"}
    for f in files:
        assert keys(json.loads(f.read_text())) == reference, f.name
