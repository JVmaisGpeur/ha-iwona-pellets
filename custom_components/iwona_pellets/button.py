"""Command buttons for the Iwona Pellets integration."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import IwonaConfigEntry, IwonaCoordinator
from .entity import IwonaEntity
from .registers import BUTTONS, KEYS, ButtonSpec


async def async_setup_entry(
    hass: HomeAssistant,
    entry: IwonaConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    entities: list[ButtonEntity] = [
        IwonaButton(coordinator, spec) for spec in BUTTONS
    ]
    entities.append(IwonaSyncClockButton(coordinator))
    entities.extend(IwonaKeyButton(coordinator, key) for key in KEYS)
    async_add_entities(entities)


class IwonaButton(IwonaEntity, ButtonEntity):
    """Write a fixed value to a register.

    * clear_errors: register 105 = 0
    """

    def __init__(self, coordinator: IwonaCoordinator, spec: ButtonSpec) -> None:
        super().__init__(coordinator, spec.key)
        self._spec = spec

    async def async_press(self) -> None:
        await self.coordinator.async_write(self._spec.reg, self._spec.value)



class IwonaKeyButton(IwonaEntity, ButtonEntity):
    """Virtual key of the controller (Menu, OK, Esc, +, -). Disabled by default."""

    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator: IwonaCoordinator, key: str) -> None:
        super().__init__(coordinator, f"key_{key}")
        self._key = key

    async def async_press(self) -> None:
        await self.coordinator.async_press_key(self._key)


class IwonaSyncClockButton(IwonaEntity, ButtonEntity):
    """Set the controller clock from Home Assistant's date and time."""

    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: IwonaCoordinator) -> None:
        super().__init__(coordinator, "sync_clock")

    async def async_press(self) -> None:
        await self.coordinator.async_sync_clock()
