from __future__ import annotations

from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .coordinator import UWDataUpdateCoordinator
from .device_helpers import build_uw_device_info

BINARY_SENSOR_TYPES: dict[str, dict[str, Any]] = {
    "bill_overdue": {
        "device_class": BinarySensorDeviceClass.PROBLEM,
    },
    "smart_meter": {
        "device_class": BinarySensorDeviceClass.CONNECTIVITY,
    },
}

# Coordinator resource keys backing each binary sensor.
BINARY_SENSOR_RESOURCES: dict[str, tuple[str, ...]] = {
    "bill_overdue": ("bills",),
    "smart_meter": ("meters",),
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: UWDataUpdateCoordinator = entry.runtime_data

    entities = [
        UWBinarySensor(coordinator, entry, sensor_id, sensor_def)
        for sensor_id, sensor_def in BINARY_SENSOR_TYPES.items()
    ]

    async_add_entities(entities)


class UWBinarySensor(CoordinatorEntity[UWDataUpdateCoordinator], BinarySensorEntity):
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: UWDataUpdateCoordinator,
        entry: ConfigEntry,
        sensor_id: str,
        sensor_def: dict[str, Any],
    ) -> None:
        super().__init__(coordinator)
        self._sensor_id = sensor_id
        self._attr_unique_id = f"{entry.unique_id}_{sensor_id}"
        self._attr_device_class = sensor_def.get("device_class")

        account = (coordinator.data or {}).get("account")
        account_number = account.account_number if account else "unknown"

        self._attr_device_info = build_uw_device_info(
            account_number, entry.unique_id or entry.entry_id
        )

    @property
    def available(self) -> bool:
        resources = BINARY_SENSOR_RESOURCES.get(self._sensor_id, ())
        resource_available = getattr(self.coordinator, "resource_available", None)
        if resource_available is None:
            return self.coordinator.available
        return self.coordinator.available and resource_available(*resources)

    @property
    def is_on(self) -> bool | None:
        data = self.coordinator.data
        if not data:
            return None

        sid = self._sensor_id

        if sid == "bill_overdue":
            bills = data.get("bills") or []
            if not bills:
                return None
            newest = max(bills, key=lambda bill: bill.bill_date)
            return bool(newest.status.value == "overdue")

        if sid == "smart_meter":
            meters = data.get("meters", [])
            if not meters:
                return None
            return any(m.is_smart for m in meters)

        return None
