"""Home Assistant integration for Iwona Pellets stoves (P.W. KEY RK-2014K/KW).

The controller is reached through its RS485 Modbus port with an RS485 <-> WiFi /
Ethernet converter such as the Elfin EW11.
"""

from __future__ import annotations

from pathlib import Path

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN
from .coordinator import IwonaConfigEntry, IwonaCoordinator
from .services import async_register_services

CARD_VERSION = "14"  # bump when www/iwona-stove-card.js changes (cache busting)

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.IMAGE,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.SENSOR,
    Platform.SWITCH,
]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Register the services and the stove card (served from the integration folder)."""
    async_register_services(hass)
    www = Path(__file__).parent / "www"
    await hass.http.async_register_static_paths(
        [StaticPathConfig(f"/{DOMAIN}", str(www), cache_headers=False)]
    )
    add_extra_js_url(hass, f"/{DOMAIN}/iwona-stove-card.js?v={CARD_VERSION}")
    return True


async def async_setup_entry(hass: HomeAssistant, entry: IwonaConfigEntry) -> bool:
    """Set up Iwona Pellets from a config entry."""
    coordinator = IwonaCoordinator(hass, entry)
    try:
        await coordinator.async_config_entry_first_refresh()
    except Exception:
        await coordinator.client.close()
        raise
    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_options_updated))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: IwonaConfigEntry) -> bool:
    """Unload a config entry."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        await entry.runtime_data.client.close()
    return unloaded


async def _async_options_updated(hass: HomeAssistant, entry: IwonaConfigEntry) -> None:
    """Reload the entry when the options change."""
    hass.config_entries.async_schedule_reload(entry.entry_id)
