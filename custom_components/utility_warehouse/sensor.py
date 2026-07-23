from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfEnergy
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .coordinator import UWDataUpdateCoordinator
from .device_helpers import build_uw_device_info

SENSOR_TYPES: dict[str, dict[str, Any]] = {
    "electricity_consumption": {
        "unit": UnitOfEnergy.KILO_WATT_HOUR,
        "device_class": SensorDeviceClass.ENERGY,
        "state_class": SensorStateClass.TOTAL_INCREASING,
    },
    "electricity_cost": {
        "unit": "GBP",
        "device_class": SensorDeviceClass.MONETARY,
        "state_class": SensorStateClass.MEASUREMENT,
    },
    "gas_consumption": {
        "unit": UnitOfEnergy.KILO_WATT_HOUR,
        "device_class": SensorDeviceClass.ENERGY,
        "state_class": SensorStateClass.TOTAL_INCREASING,
    },
    "gas_cost": {
        "unit": "GBP",
        "device_class": SensorDeviceClass.MONETARY,
        "state_class": SensorStateClass.MEASUREMENT,
    },
    "electricity_meter_reading": {
        "unit": UnitOfEnergy.KILO_WATT_HOUR,
        "device_class": SensorDeviceClass.ENERGY,
        "state_class": SensorStateClass.TOTAL_INCREASING,
    },
    "gas_meter_reading": {
        "unit": UnitOfEnergy.KILO_WATT_HOUR,
        "device_class": SensorDeviceClass.ENERGY,
        "state_class": SensorStateClass.TOTAL_INCREASING,
    },
    "last_reading_date": {
        "device_class": SensorDeviceClass.TIMESTAMP,
    },
    "electricity_meter_number": {},
    "gas_meter_number": {},
    "tariff_name": {},
    "unit_rate": {
        "unit": "p/kWh",
        "device_class": SensorDeviceClass.MONETARY,
    },
    "standing_charge": {
        "unit": "p/day",
        "device_class": SensorDeviceClass.MONETARY,
    },
    "last_bill_amount": {
        "unit": "GBP",
        "device_class": SensorDeviceClass.MONETARY,
        "state_class": SensorStateClass.MEASUREMENT,
    },
    "last_bill_date": {
        "device_class": SensorDeviceClass.DATE,
    },
    "bill_status": {},
}

SUGGESTED_DISPLAY_PRECISION = 2


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: UWDataUpdateCoordinator = entry.runtime_data

    entities = [
        UWSensor(coordinator, entry, sensor_id, sensor_def)
        for sensor_id, sensor_def in SENSOR_TYPES.items()
    ]

    async_add_entities(entities)


class UWSensor(CoordinatorEntity[UWDataUpdateCoordinator], SensorEntity):
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
        self._attr_native_unit_of_measurement = sensor_def.get("unit")
        self._attr_device_class = sensor_def.get("device_class")
        self._attr_state_class = sensor_def.get("state_class")
        if sensor_def.get("unit") == "GBP":
            self._attr_suggested_display_precision = SUGGESTED_DISPLAY_PRECISION

        account = (coordinator.data or {}).get("account")
        account_number = account.account_number if account else "unknown"

        self._attr_device_info = build_uw_device_info(
            account_number, entry.unique_id or entry.entry_id
        )

    @property
    def available(self) -> bool:
        return self.coordinator.available

    @property
    def native_value(self) -> Any:
        data = self.coordinator.data
        if not data:
            return None

        try:
            return self._resolve_value(data)
        except Exception:
            return None

    def _resolve_value(self, data: dict[str, Any]) -> Any:
        sid = self._sensor_id

        if sid == "electricity_consumption":
            c = data.get("consumption")
            return c.electricity_kwh if c else None

        if sid == "electricity_cost":
            c = data.get("consumption")
            return c.electricity_cost_gbp if c else None

        if sid == "gas_consumption":
            c = data.get("consumption")
            return c.gas_kwh if c else None

        if sid == "gas_cost":
            c = data.get("consumption")
            return c.gas_cost_gbp if c else None

        if sid in ("electricity_meter_reading", "gas_meter_reading"):
            meters = data.get("meters", [])
            want = "ELECTRICITY" if sid.startswith("electricity") else "GAS"
            for m in meters:
                if m.meter_type.value.upper() == want:
                    return (m.last_reading_date is not None and 0.0) or None
            return None

        if sid == "last_reading_date":
            meters = data.get("meters", [])
            dates = [m.last_reading_date for m in meters if m.last_reading_date]
            return max(dates) if dates else None

        if sid == "electricity_meter_number":
            meters = data.get("meters", [])
            for m in meters:
                if m.meter_type.value.upper() == "ELECTRICITY":
                    return m.meter_number
            return None

        if sid == "gas_meter_number":
            meters = data.get("meters", [])
            for m in meters:
                if m.meter_type.value.upper() == "GAS":
                    return m.meter_number
            return None

        if sid == "tariff_name":
            t = data.get("tariff")
            return t.tariff_name if t else None

        if sid == "unit_rate":
            t = data.get("tariff")
            if t and t.unit_rate_pence > 0:
                return t.unit_rate_pence
            return None

        if sid == "standing_charge":
            t = data.get("tariff")
            if t and t.standing_charge_pence > 0:
                return t.standing_charge_pence
            return None

        if sid == "last_bill_amount":
            bills = data.get("bills", [])
            return bills[0].total_amount_gbp if bills else None

        if sid == "last_bill_date":
            bills = data.get("bills", [])
            return bills[0].bill_date if bills else None

        if sid == "bill_status":
            bills = data.get("bills", [])
            return bills[0].status.value if bills else None

        return None
