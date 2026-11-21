"""Temperature setpoints for the Iwona Pellets integration."""

from __future__ import annotations

from homeassistant.components.number import NumberDeviceClass, NumberEntity, NumberMode
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import IwonaConfigEntry, IwonaCoordinator
from .entity import IwonaEntity
from .registers import NUMBERS, NumberSpec, scale_value


async def async_setup_entry(
    hass: HomeAssistant,
    entry: IwonaConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(IwonaNumber(coordinator, spec) for spec in NUMBERS)


class IwonaNumber(IwonaEntity, NumberEntity):
    """A basic setting. Limits come from the controller itself when available."""

    _attr_device_class = NumberDeviceClass.TEMPERATURE
    _attr_mode = NumberMode.BOX

    def __init__(self, coordinator: IwonaCoordinator, spec: NumberSpec) -> None:
        super().__init__(coordinator, spec.key)
        self._spec = spec
        self._attr_native_unit_of_measurement = spec.unit
        self._attr_native_step = spec.step
        self._attr_entity_registry_enabled_default = spec.enabled

    @property
    def native_min_value(self) -> float:
        limits = self.coordinator.limits.get(self._spec.reg)
        if limits:
            return round(limits[0] * self._spec.scale, 3)
        return self._spec.default_min

    @property
    def native_max_value(self) -> float:
        limits = self.coordinator.limits.get(self._spec.reg)
        if limits:
            return round(limits[1] * self._spec.scale, 3)
        return self._spec.default_max

    @property
    def native_value(self) -> float | None:
        raw = self.raw(self._spec.reg)
        if raw is None:
            return None
        return scale_value(raw, self._spec.scale, True)

    async def async_set_native_value(self, value: float) -> None:
        await self.coordinator.async_write(
            self._spec.reg, round(value / self._spec.scale)
        )

