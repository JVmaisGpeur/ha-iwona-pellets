"""Mode selectors for the Iwona Pellets integration."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import IwonaConfigEntry, IwonaCoordinator
from .entity import IwonaEntity
from .registers import FUEL_MODES, REG_FUEL_MODE, SELECTS, SelectSpec


async def async_setup_entry(
    hass: HomeAssistant,
    entry: IwonaConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    entities: list[SelectEntity] = [IwonaSelect(coordinator, spec) for spec in SELECTS]
    entities.append(IwonaFuelModeSelect(coordinator))
    async_add_entities(entities)


class IwonaSelect(IwonaEntity, SelectEntity):
    """Program mode (day / night / off / programs) and winter / summer mode."""

    def __init__(self, coordinator: IwonaCoordinator, spec: SelectSpec) -> None:
        super().__init__(coordinator, spec.key)
        self._spec = spec
        self._attr_options = list(spec.options.values())
        self._attr_entity_registry_enabled_default = spec.enabled
        if spec.diagnostic:
            self._attr_entity_category = EntityCategory.CONFIG

    @property
    def current_option(self) -> str | None:
        raw = self.raw(self._spec.reg)
        return None if raw is None else self._spec.options.get(raw)

    async def async_select_option(self, option: str) -> None:
        code = next(c for c, name in self._spec.options.items() if name == option)
        await self.coordinator.async_write(self._spec.reg, code)


class IwonaFuelModeSelect(IwonaEntity, SelectEntity):
    """Fuel mode (setting 10102). Disabled by default: it writes a setting that is
    outside the documented basic registers, and needs the controller's Modbus
    access level to allow it."""

    _attr_options = list(FUEL_MODES.values())
    _attr_entity_registry_enabled_default = False
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: IwonaCoordinator) -> None:
        super().__init__(coordinator, "fuel_mode")

    @property
    def current_option(self) -> str | None:
        raw = self.raw(REG_FUEL_MODE)
        return None if raw is None else FUEL_MODES.get(raw)

    async def async_select_option(self, option: str) -> None:
        code = next(c for c, name in FUEL_MODES.items() if name == option)
        await self.coordinator.async_set_fuel_mode(code)
