"""Image of the controller's display."""

from __future__ import annotations

from datetime import timedelta
import logging

from homeassistant.components.image import ImageEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.util import dt as dt_util

from .const import DISPLAY_REFRESH_SECONDS
from .coordinator import IwonaConfigEntry, IwonaCoordinator
from .entity import IwonaEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: IwonaConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    async_add_entities([IwonaDisplayImage(entry.runtime_data)])


class IwonaDisplayImage(IwonaEntity, ImageEntity):
    """What the stove's LCD shows. Disabled by default (extra polling)."""

    _attr_content_type = "image/png"
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator: IwonaCoordinator) -> None:
        IwonaEntity.__init__(self, coordinator, "display")
        ImageEntity.__init__(self, coordinator.hass)
        self._png: bytes | None = None

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        await self._async_refresh()
        self.coordinator.display_listeners.append(self._async_refresh)
        self.async_on_remove(lambda: self.coordinator.display_listeners.remove(self._async_refresh))
        self.async_on_remove(
            async_track_time_interval(
                self.hass, self._async_refresh, timedelta(seconds=DISPLAY_REFRESH_SECONDS)
            )
        )

    async def _async_refresh(self, _now=None) -> None:
        try:
            png = await self.coordinator.async_read_display()
        except Exception as err:  # keep the last image on any read problem
            _LOGGER.debug("Cannot read the display: %s", err)
            return
        if png != self._png:
            self._png = png
            self._attr_image_last_updated = dt_util.utcnow()
            self.async_write_ha_state()

    async def async_image(self) -> bytes | None:
        return self._png
