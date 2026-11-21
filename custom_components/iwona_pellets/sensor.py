"""Sensors for the Iwona Pellets integration."""

from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import IwonaConfigEntry, IwonaCoordinator
from .entity import IwonaEntity
from .registers import (
    ERROR_LOG_KEYS,
    PROCESS_STATES,
    REG_PROCESS_STATE,
    SENSORS,
    SensorSpec,
    scale_value,
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: IwonaConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    entities: list[SensorEntity] = [IwonaSensor(coordinator, spec) for spec in SENSORS]
    entities.append(IwonaProcessStateSensor(coordinator))
    entities.append(IwonaLastErrorSensor(coordinator))
    async_add_entities(entities)


class IwonaSensor(IwonaEntity, SensorEntity):
    """A numeric value read from one register."""

    def __init__(self, coordinator: IwonaCoordinator, spec: SensorSpec) -> None:
        super().__init__(coordinator, spec.key)
        self._spec = spec
        self._attr_native_unit_of_measurement = spec.unit
        self._attr_device_class = (
            SensorDeviceClass(spec.device_class) if spec.device_class else None
        )
        self._attr_state_class = (
            SensorStateClass(spec.state_class) if spec.state_class else None
        )
        self._attr_suggested_display_precision = spec.precision
        self._attr_entity_registry_enabled_default = spec.enabled
        if spec.diagnostic:
            self._attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def native_value(self) -> int | float | None:
        raw = self.raw(self._spec.reg)
        if raw is None:
            return None
        return scale_value(raw, self._spec.scale, self._spec.signed)


class IwonaProcessStateSensor(IwonaEntity, SensorEntity):
    """What the stove is doing (ignition, running, extinction...)."""

    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = list(PROCESS_STATES.values())

    def __init__(self, coordinator: IwonaCoordinator) -> None:
        super().__init__(coordinator, "process_state")

    @property
    def native_value(self) -> str | None:
        raw = self.raw(REG_PROCESS_STATE)
        return None if raw is None else PROCESS_STATES.get(raw)

    @property
    def extra_state_attributes(self) -> dict[str, int | None]:
        """Raw code, useful when the controller reports an unknown state."""
        return {"code": self.raw(REG_PROCESS_STATE)}


class IwonaLastErrorSensor(IwonaEntity, SensorEntity):
    """Last event of the controller's error log (full log in the attributes)."""

    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = sorted(set(ERROR_LOG_KEYS.values()))
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: IwonaCoordinator) -> None:
        super().__init__(coordinator, "last_error")

    @property
    def native_value(self) -> str | None:
        log = self.coordinator.error_log
        return log[-1]["error"] if log else None

    @property
    def extra_state_attributes(self) -> dict:
        log = self.coordinator.error_log
        last = log[-1] if log else {}
        return {
            "date": last.get("date"),
            "time": last.get("time"),
            "history": list(reversed(log))[:30],
        }
