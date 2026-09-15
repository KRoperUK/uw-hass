"""Tests for the Utility Warehouse binary sensors."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock

from custom_components.utility_warehouse.binary_sensor import (
    BINARY_SENSOR_TYPES,
    UWBinarySensor,
)

from .conftest import make_uw_data


def _coordinator(data: Any, available: bool = True) -> MagicMock:
    coordinator = MagicMock()
    coordinator.data = data
    coordinator.available = available
    return coordinator


def _build(entry: Any, sensor_id: str, data: Any, available: bool = True) -> UWBinarySensor:
    return UWBinarySensor(
        _coordinator(data, available), entry, sensor_id, BINARY_SENSOR_TYPES[sensor_id]
    )


def test_bill_overdue_is_on_when_overdue(mock_entry):
    assert _build(mock_entry, "bill_overdue", make_uw_data()).is_on is True


def test_bill_overdue_is_off_when_not_overdue(mock_entry):
    data = make_uw_data()
    data["bills"][0].status = SimpleNamespace(value="paid")

    assert _build(mock_entry, "bill_overdue", data).is_on is False


def test_bill_overdue_is_none_without_bills(mock_entry):
    data = make_uw_data()
    data["bills"] = []

    assert _build(mock_entry, "bill_overdue", data).is_on is None


def test_smart_meter_is_on_when_any_meter_is_smart(mock_entry):
    assert _build(mock_entry, "smart_meter", make_uw_data()).is_on is True


def test_smart_meter_is_off_when_no_meter_is_smart(mock_entry):
    data = make_uw_data()
    for meter in data["meters"]:
        meter.is_smart = False

    assert _build(mock_entry, "smart_meter", data).is_on is False


def test_smart_meter_is_none_without_meters(mock_entry):
    data = make_uw_data()
    data["meters"] = []

    assert _build(mock_entry, "smart_meter", data).is_on is None


def test_is_on_is_none_without_data(mock_entry):
    for sensor_id in BINARY_SENSOR_TYPES:
        assert _build(mock_entry, sensor_id, None).is_on is None


def test_unknown_sensor_id_returns_none(mock_entry):
    sensor = UWBinarySensor(_coordinator(make_uw_data()), mock_entry, "unknown", {})

    assert sensor.is_on is None


def test_available_delegates_to_coordinator(mock_entry):
    assert _build(mock_entry, "bill_overdue", make_uw_data(), available=False).available is False
    assert _build(mock_entry, "bill_overdue", make_uw_data(), available=True).available is True


def test_unique_id_and_device_class(mock_entry):
    sensor = _build(mock_entry, "bill_overdue", make_uw_data())

    assert sensor.unique_id == f"{mock_entry.unique_id}_bill_overdue"
    assert sensor.device_class is not None
    assert sensor.device_info is not None
