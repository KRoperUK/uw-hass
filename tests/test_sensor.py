"""Tests for the Utility Warehouse sensors."""

from __future__ import annotations

from datetime import date, datetime
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock

import pytest

from custom_components.utility_warehouse.sensor import SENSOR_TYPES, UWSensor

from .conftest import make_uw_data

# NOTE: the two *_meter_reading entries report None because the resolver does
# ``(last_reading_date is not None and 0.0) or None`` — the 0.0 is falsy so it
# always collapses to None. Asserted here as current behaviour; flagged as a
# latent bug rather than silently "fixed".
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
            meter_type=SimpleNamespace(value="GAS"),
            meter_number="G-1",
            last_reading_date=datetime(2026, 1, 3),
            is_smart=False,
        )
    ]

    assert _build(mock_entry, "electricity_meter_number", data).native_value is None
    assert _build(mock_entry, "electricity_meter_reading", data).native_value is None


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
