"""Base entity for the Iwona Pellets integration."""

from __future__ import annotations

from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .coordinator import IwonaCoordinator


class IwonaEntity(CoordinatorEntity[IwonaCoordinator]):
    """Entity attached to the stove device, named from the translations."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: IwonaCoordinator, key: str) -> None:
        super().__init__(coordinator)
        self._attr_translation_key = key
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{key}"
        self._attr_device_info = coordinator.device_info

    def raw(self, register: int) -> int | None:
        """Raw value of a register from the last successful poll."""
        return self.coordinator.data.get(register)
