"""Binary sensors for the Iwona Pellets integration."""

from __future__ import annotations

from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import IwonaConfigEntry, IwonaCoordinator
from .entity import IwonaEntity
from .registers import (
    BINARY_SENSORS,
    REG_ERROR_FLAG,
    REG_ERRORS_1,
    REG_ERRORS_2,
    BinarySpec,
    decode_errors,
    has_problem,
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: IwonaConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    entities: list[BinarySensorEntity] = [
        IwonaBinarySensor(coordinator, spec) for spec in BINARY_SENSORS
    ]
    entities.append(IwonaProblemSensor(coordinator))
    async_add_entities(entities)


class IwonaBinarySensor(IwonaEntity, BinarySensorEntity):
    """An output or input of the controller."""

    def __init__(self, coordinator: IwonaCoordinator, spec: BinarySpec) -> None:
        super().__init__(coordinator, spec.key)
        self._spec = spec
        self._attr_device_class = (
            BinarySensorDeviceClass(spec.device_class) if spec.device_class else None
        )
        self._attr_entity_registry_enabled_default = spec.enabled
        if spec.diagnostic:
            self._attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def is_on(self) -> bool | None:
        raw = self.raw(self._spec.reg)
        if raw is None:
            return None
        if self._spec.on_value is None:
            return raw != 0
        return raw == self._spec.on_value


class IwonaProblemSensor(IwonaEntity, BinarySensorEntity):
    """On when the controller reports an error (see the ``errors`` attribute)."""

    _attr_device_class = BinarySensorDeviceClass.PROBLEM

    def __init__(self, coordinator: IwonaCoordinator) -> None:
        super().__init__(coordinator, "problem")

    def _errors(self) -> list[str]:
        return decode_errors(
            self.raw(REG_ERRORS_1) or 0, self.raw(REG_ERRORS_2) or 0
        )

    @property
    def is_on(self) -> bool | None:
        if self.raw(REG_ERRORS_1) is None:
            return None
        return has_problem(self._errors())

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {"errors": self._errors(), "error_flag": self.raw(REG_ERROR_FLAG)}
