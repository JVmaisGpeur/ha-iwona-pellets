"""Start / stop switch for the Iwona Pellets integration."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import IwonaConfigEntry, IwonaCoordinator
from .entity import IwonaEntity
from .registers import REG_BOILER_WORK


async def async_setup_entry(
    hass: HomeAssistant,
    entry: IwonaConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    entities = [IwonaStoveSwitch(coordinator)]
    if coordinator.room_sensor:
        entities.append(IwonaRegulationSwitch(coordinator))
    async_add_entities(entities)


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


class IwonaRegulationSwitch(IwonaEntity, SwitchEntity, RestoreEntity):
    """Regulate the stove from the external room sensor (virtual thermostat 0)."""

    def __init__(self, coordinator: IwonaCoordinator) -> None:
        super().__init__(coordinator, "external_regulation")

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last = await self.async_get_last_state()
        if last is not None and last.state == "on":
            self.coordinator.ext_enabled = True

    @property
    def is_on(self) -> bool:
        return self.coordinator.ext_enabled

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        c = self.coordinator
        return {
            "sensor": c.room_sensor,
            "temperature": c.ext_temperature,
            "setpoint": c.ext_setpoint,
            "heating_demand": c.ext_demand,
        }

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.coordinator.async_set_regulation(enabled=True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.async_set_regulation(enabled=False)
