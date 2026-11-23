from __future__ import annotations

import logging
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

_LOGGER = logging.getLogger(__name__)

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
        "state_class": SensorStateClass.MEASUREMENT,
    },
    "standing_charge": {
        "unit": "p/day",
        "state_class": SensorStateClass.MEASUREMENT,
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
PRECISION_UNITS = {"GBP", "p/kWh", "p/day"}


def latest_bill(bills: list[Any]) -> Any | None:
    """Return the most recent bill by date, whatever order the API used."""
    return max(bills, key=lambda bill: bill.bill_date) if bills else None


def latest_meter_reading(data: dict[str, Any], meter_type: str) -> float | None:
    """Return the newest register reading for the first meter of a fuel type."""
    meters = data.get("meters") or []
    readings = data.get("readings") or []
    meter_ids = {
        meter.meter_id
        for meter in meters
        if meter.meter_type.value.upper() == meter_type and getattr(meter, "meter_id", "")
    }
    candidates = [reading for reading in readings if reading.meter_id in meter_ids]
    if not candidates:
        return None
    return float(max(candidates, key=lambda reading: reading.reading_date).value)


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
        if sensor_def.get("unit") in PRECISION_UNITS:
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
            _LOGGER.debug("Could not resolve %s", self._sensor_id, exc_info=True)
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
            want = "ELECTRICITY" if sid.startswith("electricity") else "GAS"
            return latest_meter_reading(data, want)

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
            bill = latest_bill(data.get("bills") or [])
            return bill.total_amount_gbp if bill else None

        if sid == "last_bill_date":
            bill = latest_bill(data.get("bills") or [])
            return bill.bill_date if bill else None

        if sid == "bill_status":
            bill = latest_bill(data.get("bills") or [])
            return bill.status.value if bill else None

        return None
