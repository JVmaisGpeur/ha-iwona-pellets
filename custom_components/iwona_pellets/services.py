"""Read-only diagnostic service: dump any range of controller registers.

Useful to find settings that are not part of the documented basic registers
(for example the fuel mode), by comparing two dumps taken before and after a
change made on the stove's display. It never writes anything.
"""

from __future__ import annotations

import voluptuous as vol

from homeassistant.core import (
    HomeAssistant,
    ServiceCall,
    ServiceResponse,
    SupportsResponse,
)
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError

from .const import DOMAIN
from .coordinator import IwonaCoordinator
from .display import FONT, decode_display, extract_text
from .protocol import ModbusError
from .registers import BLOCK_DISPLAY, KEYS, VTHERMO_COUNT, VTHERMO_MAX_SECONDS

SERVICE_READ_REGISTERS = "read_registers"
SERVICE_EXPLORE_MENU = "explore_menu"
SERVICE_SET_VTHERMO = "set_virtual_thermostat"
SERVICE_EXPORT_SETTINGS = "export_settings"
WATCHED_BLOCKS = ((100, 24), (10100, 30))  # settings compared before / after an exploration

ATTR_ENTRY = "config_entry_id"
ATTR_START = "start"
ATTR_COUNT = "count"
ATTR_INCLUDE_ZERO = "include_zero"

MAX_COUNT = 5000
LAST_REGISTER = 65535

READ_REGISTERS_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_ENTRY): str,
        vol.Required(ATTR_START): vol.All(vol.Coerce(int), vol.Range(min=1, max=LAST_REGISTER)),
        vol.Required(ATTR_COUNT): vol.All(vol.Coerce(int), vol.Range(min=1, max=MAX_COUNT)),
        vol.Optional(ATTR_INCLUDE_ZERO, default=False): bool,
    }
)


EXPLORE_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_ENTRY): str,
        vol.Optional("keys", default=[]): [vol.In(list(KEYS))],
        vol.Optional("delay", default=0.8): vol.All(vol.Coerce(float), vol.Range(min=0, max=5)),
        vol.Optional("each", default=False): bool,
        vol.Optional("labels", default={}): {str: str},
        vol.Optional("export_font", default=False): bool,
    }
)


def _get_coordinator(call: ServiceCall) -> IwonaCoordinator:
    entries = [
        entry
        for entry in call.hass.config_entries.async_entries(DOMAIN)
        if getattr(entry, "runtime_data", None) is not None
    ]
    wanted = call.data.get(ATTR_ENTRY)
    if wanted:
        entries = [entry for entry in entries if entry.entry_id == wanted]
    if len(entries) != 1:
        raise ServiceValidationError(
            "Select the stove with config_entry_id (none or several loaded stoves found)"
        )
    return entries[0].runtime_data


async def _async_read_registers(call: ServiceCall) -> ServiceResponse:
    coordinator = _get_coordinator(call)
    start, count = call.data[ATTR_START], call.data[ATTR_COUNT]
    if start + count - 1 > LAST_REGISTER:
        raise ServiceValidationError(f"The range must end at register {LAST_REGISTER} at most")
    try:
        values = await coordinator.async_read_range(start, count)
    except ModbusError as err:
        raise HomeAssistantError(f"Cannot read the registers: {err}") from err
    include_zero = call.data[ATTR_INCLUDE_ZERO]
    return {
        "start": start,
        "count": count,
        "registers": {
            str(register): value
            for register, value in values.items()
            if include_zero or value != 0
        },
    }


async def _read_screen(coordinator: IwonaCoordinator, font: dict[str, str]) -> dict:
    start, count = BLOCK_DISPLAY
    values = await coordinator.async_read_range(start, count)
    pixels = decode_display([values[start + i] for i in range(count)])
    lines, unknown = extract_text(pixels, font)
    menu = (await coordinator.async_read_range(41513, 1)).get(41513)
    return {
        "menu_state": menu,
        "lines": [
            f"{l['y']}@{l['x']}{'*' if l['inverted'] else ''}: {l['text']}" for l in lines
        ],
        "unknown": unknown,
    }


async def _async_explore_menu(call: ServiceCall) -> ServiceResponse:
    """Navigate the controller's menus with the virtual keys and read the screens as text.

    Only the Menu / OK / + / - keys can be sent. The settings registers are read before
    and after and the differences are reported, so an accidental change is visible.
    """
    import asyncio

    coordinator = _get_coordinator(call)
    font = getattr(coordinator, "font", None)
    if font is None:
        font = coordinator.font = dict(FONT)
    font.update(call.data["labels"])
    try:
        before = {}
        for block in WATCHED_BLOCKS:
            before.update(await coordinator.async_read_range(*block))
        screens: list[dict] = []
        keys = call.data["keys"]
        for index, key in enumerate(keys):
            await coordinator.async_press_key(key)
            await asyncio.sleep(call.data["delay"])
            if call.data["each"] and index < len(keys) - 1:
                shot = await _read_screen(coordinator, font)
                shot["after"] = key
                screens.append(shot)
        last = await _read_screen(coordinator, font)
        last["after"] = keys[-1] if keys else None
        screens.append(last)
        after = {}
        for block in WATCHED_BLOCKS:
            after.update(await coordinator.async_read_range(*block))
    except ModbusError as err:
        raise HomeAssistantError(f"Cannot explore the menu: {err}") from err
    seen: dict[str, list[str]] = {}
    for shot in screens:
        seen.update(shot.pop("unknown"))
    result: dict = {
        "screens": screens,
        "unknown": seen,
        "changed": {str(r): [before[r], after[r]] for r in after if before.get(r) != after[r]},
    }
    if call.data["export_font"]:
        result["font"] = font
    return result


VTHERMO_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_ENTRY): str,
        vol.Optional("index", default=0): vol.All(
            vol.Coerce(int), vol.Range(min=0, max=VTHERMO_COUNT - 1)
        ),
        vol.Required("seconds"): vol.All(
            vol.Coerce(int), vol.Range(min=0, max=VTHERMO_MAX_SECONDS)
        ),
    }
)
EXPORT_SCHEMA = vol.Schema({vol.Optional(ATTR_ENTRY): str})


async def _async_set_vthermo(call: ServiceCall) -> ServiceResponse:
    coordinator = _get_coordinator(call)
    index, seconds = call.data["index"], call.data["seconds"]
    remaining = await coordinator.async_set_virtual_thermostat(index, seconds)
    return {"index": index, "requested": seconds, "read_back": remaining}


async def _async_export_settings(call: ServiceCall) -> ServiceResponse:
    """Dump every setting (value, min, max) keyed by its register, read-only."""
    coordinator = _get_coordinator(call)
    try:
        values = await coordinator.async_read_range(10101, 1400)
        minimums = await coordinator.async_read_range(15101, 1400)
        maximums = await coordinator.async_read_range(20101, 1400)
    except ModbusError as err:
        raise HomeAssistantError(f"Cannot read the settings: {err}") from err
    settings = {}
    for register, value in values.items():
        low = minimums.get(register + 5000, 0)
        high = maximums.get(register + 10000, 0)
        if value or low or high:
            settings[str(register)] = {"value": value, "min": low, "max": high}
    return {"model": coordinator.model, "firmware": coordinator.firmware, "settings": settings}


def async_register_services(hass: HomeAssistant) -> None:
    """Register the integration services (once, at component setup)."""
    hass.services.async_register(
        DOMAIN,
        SERVICE_READ_REGISTERS,
        _async_read_registers,
        schema=READ_REGISTERS_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_EXPLORE_MENU,
        _async_explore_menu,
        schema=EXPLORE_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_VTHERMO,
        _async_set_vthermo,
        schema=VTHERMO_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_EXPORT_SETTINGS,
        _async_export_settings,
        schema=EXPORT_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )
