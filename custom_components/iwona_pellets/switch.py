"""Start / stop switch for the Iwona Pellets integration."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import IwonaConfigEntry, IwonaCoordinator
from .entity import IwonaEntity
from .registers import REG_BOILER_WORK


async def async_setup_entry(
    hass: HomeAssistant,
    entry: IwonaConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    async_add_entities([IwonaStoveSwitch(entry.runtime_data)])


class IwonaStoveSwitch(IwonaEntity, SwitchEntity):
    """Register 102: 0 = STOP, 1 (or 2) = START."""

    def __init__(self, coordinator: IwonaCoordinator) -> None:
        super().__init__(coordinator, "stove")

    @property
    def is_on(self) -> bool | None:
        raw = self.raw(REG_BOILER_WORK)
        return None if raw is None else raw != 0

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.coordinator.async_write(REG_BOILER_WORK, self.coordinator.start_command)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.async_write(REG_BOILER_WORK, 0)

