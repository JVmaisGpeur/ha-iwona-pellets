"""Temperature setpoints for the Iwona Pellets integration."""

from __future__ import annotations

from homeassistant.components.number import NumberDeviceClass, NumberEntity, NumberMode
from homeassistant.core import HomeAssistant
from homeassistant.helpers.restore_state import RestoreEntity
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
    entities: list[NumberEntity] = [IwonaNumber(coordinator, spec) for spec in NUMBERS]
    if coordinator.room_sensor:
        entities.append(IwonaRegulationNumber(coordinator, "external_setpoint", "ext_setpoint", 5, 30, 0.5))
        entities.append(IwonaRegulationNumber(coordinator, "external_hysteresis", "ext_hysteresis", 0.1, 3, 0.1))
    async_add_entities(entities)


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


class IwonaRegulationNumber(IwonaEntity, NumberEntity, RestoreEntity):
    """Setpoint / hysteresis of the regulation from the external room sensor."""

    _attr_device_class = NumberDeviceClass.TEMPERATURE
    _attr_mode = NumberMode.BOX
    _attr_native_unit_of_measurement = "\u00b0C"

    def __init__(self, coordinator, key, attribute, low, high, step) -> None:
        super().__init__(coordinator, key)
        self._attribute = attribute
        self._attr_native_min_value = low
        self._attr_native_max_value = high
        self._attr_native_step = step

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last = await self.async_get_last_state()
        if last is not None:
            try:
                setattr(self.coordinator, self._attribute, float(last.state))
            except ValueError:
                pass

    @property
    def native_value(self) -> float:
        return getattr(self.coordinator, self._attribute)

    async def async_set_native_value(self, value: float) -> None:
        await self.coordinator.async_set_regulation(**{self._attribute.removeprefix("ext_"): value})
