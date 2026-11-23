"""Tests for the Utility Warehouse sensors."""

from __future__ import annotations

from datetime import date, datetime
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock

import pytest
from homeassistant.components.sensor import SensorStateClass

from custom_components.utility_warehouse.sensor import SENSOR_TYPES, UWSensor

from .conftest import make_uw_data

# NOTE: the shared fixture has no meter readings, so the two *_meter_reading
# sensors resolve to None here; the reading path is covered separately below.
EXPECTED_VALUES: dict[str, Any] = {
    "electricity_consumption": 12.5,
    "electricity_cost": 3.75,
    "gas_consumption": 30.0,
    "gas_cost": 1.2,
    "electricity_meter_reading": None,
    "gas_meter_reading": None,
    "last_reading_date": datetime(2026, 1, 3, 3, 4, 5),
    "electricity_meter_number": "E-1",
    "gas_meter_number": "G-1",
    "tariff_name": "UW Flex",
    "unit_rate": 24.5,
    "standing_charge": 53.1,
    "last_bill_amount": 88.75,
    "last_bill_date": date(2026, 1, 5),
    "bill_status": "overdue",
}


def _coordinator(data: Any, available: bool = True) -> MagicMock:
    coordinator = MagicMock()
    coordinator.data = data
    coordinator.available = available
    return coordinator


def _build(entry: Any, sensor_id: str, data: Any, available: bool = True) -> UWSensor:
    return UWSensor(_coordinator(data, available), entry, sensor_id, SENSOR_TYPES[sensor_id])


def test_expected_values_cover_every_sensor_type():
    """Guard against adding a sensor type without a test expectation."""
    assert set(EXPECTED_VALUES) == set(SENSOR_TYPES)


@pytest.mark.parametrize("sensor_id", sorted(SENSOR_TYPES))
def test_native_value(mock_entry, sensor_id):
    """Each sensor resolves its value from the coordinator payload."""
    sensor = _build(mock_entry, sensor_id, make_uw_data())

    assert sensor.native_value == EXPECTED_VALUES[sensor_id]


def test_native_value_is_none_without_data(mock_entry):
    """No payload means no value."""
    sensor = _build(mock_entry, "tariff_name", None)

    assert sensor.native_value is None


def test_native_value_is_none_when_resolution_fails(mock_entry):
    """A malformed payload degrades to None instead of raising."""
    sensor = _build(mock_entry, "electricity_consumption", {"consumption": SimpleNamespace()})

    assert sensor.native_value is None


def test_available_delegates_to_coordinator(mock_entry):
    """Availability mirrors the coordinator."""
    assert _build(mock_entry, "tariff_name", make_uw_data(), available=False).available is False
    assert _build(mock_entry, "tariff_name", make_uw_data(), available=True).available is True


def test_unique_id_and_device_info(mock_entry):
    """Entities are namespaced by entry unique id and share device info."""
    sensor = _build(mock_entry, "tariff_name", make_uw_data())

    assert sensor.unique_id == f"{mock_entry.unique_id}_tariff_name"
    assert sensor.device_info is not None
    assert sensor.device_info["model"] == "Account A-12345"


def test_gbp_sensors_get_display_precision(mock_entry):
    """Monetary sensors round to two decimals."""
    sensor = _build(mock_entry, "last_bill_amount", make_uw_data())

    assert sensor.suggested_display_precision == 2


def test_meter_readings_are_none_when_meter_missing(mock_entry):
    """A missing meter of the right type yields None."""
    data = make_uw_data()
    data["meters"] = [
        SimpleNamespace(
            meter_id="G-M1",
            meter_type=SimpleNamespace(value="GAS"),
            meter_number="G-1",
            last_reading_date=datetime(2026, 1, 3),
            is_smart=False,
        )
    ]

    assert _build(mock_entry, "electricity_meter_number", data).native_value is None
    assert _build(mock_entry, "electricity_meter_reading", data).native_value is None


def test_meter_reading_uses_the_newest_reading(mock_entry):
    """A meter reading sensor reports the latest register reading for its meter."""
    data = make_uw_data()
    data["readings"] = [
        SimpleNamespace(meter_id="E-M1", reading_date=datetime(2026, 1, 1), value=100.0),
        SimpleNamespace(meter_id="E-M1", reading_date=datetime(2026, 1, 5), value=250.0),
        SimpleNamespace(meter_id="G-M1", reading_date=datetime(2026, 1, 6), value=42.0),
    ]

    assert _build(mock_entry, "electricity_meter_reading", data).native_value == 250.0
    assert _build(mock_entry, "gas_meter_reading", data).native_value == 42.0


def test_meter_reading_ignores_other_meters(mock_entry):
    """Readings for an unrelated meter id do not leak into a fuel type."""
    data = make_uw_data()
    data["readings"] = [
        SimpleNamespace(meter_id="OTHER", reading_date=datetime(2026, 1, 5), value=999.0)
    ]

    assert _build(mock_entry, "electricity_meter_reading", data).native_value is None


def test_latest_bill_is_the_newest_by_date(mock_entry):
    """Bill sensors use the newest bill, not whichever is first in the list."""
    data = make_uw_data()
    data["bills"] = [
        SimpleNamespace(
            total_amount_gbp=10.0,
            bill_date=date(2025, 12, 1),
            status=SimpleNamespace(value="paid"),
        ),
        SimpleNamespace(
            total_amount_gbp=20.0,
            bill_date=date(2026, 2, 1),
            status=SimpleNamespace(value="pending"),
        ),
    ]

    assert _build(mock_entry, "last_bill_amount", data).native_value == 20.0
    assert _build(mock_entry, "last_bill_date", data).native_value == date(2026, 2, 1)
    assert _build(mock_entry, "bill_status", data).native_value == "pending"


def test_rate_sensors_are_not_monetary(mock_entry):
    """p/kWh and p/day are not currencies, so they must not use MONETARY."""
    for sensor_id, unit in (("unit_rate", "p/kWh"), ("standing_charge", "p/day")):
        sensor = _build(mock_entry, sensor_id, make_uw_data())
        assert sensor.device_class is None
        assert sensor.native_unit_of_measurement == unit
        assert sensor.state_class == SensorStateClass.MEASUREMENT
        assert sensor.suggested_display_precision == 2


def test_gas_meter_number_is_none_when_no_gas_meter(mock_entry):
    """A missing gas meter yields None for the gas meter number."""
    data = make_uw_data()
    data["meters"] = [
        SimpleNamespace(
            meter_type=SimpleNamespace(value="ELECTRICITY"),
            meter_number="E-1",
            last_reading_date=datetime(2026, 1, 3),
            is_smart=True,
        )
    ]

    assert _build(mock_entry, "gas_meter_number", data).native_value is None


def test_unknown_sensor_id_returns_none(mock_entry):
    """An unrecognised sensor id resolves to None."""
    sensor = UWSensor(_coordinator(make_uw_data()), mock_entry, "unknown", {})

    assert sensor.native_value is None


def test_optional_fields_absent_yield_none(mock_entry):
    """Absent optional resources resolve to None."""
    assert _build(mock_entry, "tariff_name", {}).native_value is None
    assert _build(mock_entry, "last_bill_amount", {}).native_value is None
    assert _build(mock_entry, "last_reading_date", {}).native_value is None


def test_zero_rate_and_charge_are_treated_as_missing(mock_entry):
    """A zero tariff value is surfaced as None."""
    data = make_uw_data()
    data["tariff"] = SimpleNamespace(tariff_name="Zero", unit_rate_pence=0, standing_charge_pence=0)

    assert _build(mock_entry, "unit_rate", data).native_value is None
    assert _build(mock_entry, "standing_charge", data).native_value is None
