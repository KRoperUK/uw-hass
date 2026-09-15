"""Tests for the Utility Warehouse data update coordinator."""

from __future__ import annotations

import time
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import timedelta
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
import uw_api
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.utility_warehouse.const import (
    AVAILABILITY_GRACE_SECONDS,
    DEFAULT_SCAN_INTERVAL,
    MAX_SCAN_INTERVAL,
)
from custom_components.utility_warehouse.coordinator import UWDataUpdateCoordinator

from .conftest import ACCOUNT_NUMBER, fake_client_class

COORDINATOR = "custom_components.utility_warehouse.coordinator"


def _build(hass: Any, entry: Any) -> UWDataUpdateCoordinator:
    return UWDataUpdateCoordinator(hass, entry)


@contextmanager
def _patched(client_class: type) -> Iterator[None]:
    """Patch the HTTP client and the uw_api client used by the coordinator."""
    with (
        patch(f"{COORDINATOR}.get_async_client", return_value=MagicMock()),
        patch("uw_api.UWClient", client_class),
    ):
        yield


async def test_update_data_success(hass, mock_entry):
    """A happy-path refresh returns the assembled payload."""
    coordinator = _build(hass, mock_entry)

    with _patched(fake_client_class()):
        data = await coordinator._async_update_data()

    assert data["account"].account_number == ACCOUNT_NUMBER
    assert data["bills"][0].total_amount_gbp == 88.75
    assert coordinator._current_interval == DEFAULT_SCAN_INTERVAL
    assert coordinator._last_success_time > 0


async def test_update_data_auth_error_raises_config_entry_auth_failed(hass, mock_entry):
    """A failed login is reported as an auth failure."""
    coordinator = _build(hass, mock_entry)

    with (
        _patched(fake_client_class(login_error=uw_api.UWAuthError("login failed"))),
        pytest.raises(ConfigEntryAuthFailed),
    ):
        await coordinator._async_update_data()


async def test_update_data_generic_auth_message_raises_auth_failed(hass, mock_entry):
    """Any error mentioning auth is treated as an auth failure."""
    coordinator = _build(hass, mock_entry)

    with (
        _patched(fake_client_class(login_error=RuntimeError("Auth rejected"))),
        pytest.raises(ConfigEntryAuthFailed),
    ):
        await coordinator._async_update_data()


async def test_update_data_failure_raises_update_failed_and_backs_off(hass, mock_entry):
    """A transport failure raises UpdateFailed and lengthens the interval."""
    coordinator = _build(hass, mock_entry)

    with (
        _patched(fake_client_class(login_error=RuntimeError("socket down"))),
        pytest.raises(UpdateFailed),
    ):
        await coordinator._async_update_data()

    assert coordinator._current_interval == DEFAULT_SCAN_INTERVAL * 2


async def test_update_data_survives_partial_field_failures(hass, mock_entry):
    """Optional resources failing individually do not fail the refresh."""
    coordinator = _build(hass, mock_entry)
    failing = {
        "get_balance",
        "get_tariff",
        "get_consumption",
        "get_meters",
        "get_meter_readings",
        "get_bills",
    }

    with _patched(fake_client_class(fail_fields=failing)):
        data = await coordinator._async_update_data()

    assert data["account"].account_number == ACCOUNT_NUMBER
    for key in ("balance", "tariff", "consumption", "meters", "readings", "bills"):
        assert key not in data


def test_available_when_last_update_succeeded(hass, mock_entry):
    """Availability is true after a successful refresh."""
    coordinator = _build(hass, mock_entry)
    coordinator.last_update_success = True

    assert coordinator.available is True


def test_available_within_grace_period(hass, mock_entry, uw_data):
    """Cached data keeps the integration available inside the grace window."""
    coordinator = _build(hass, mock_entry)
    coordinator.last_update_success = False
    coordinator.data = uw_data
    coordinator._last_success_time = time.monotonic()

    assert coordinator.available is True


def test_unavailable_without_cached_data(hass, mock_entry):
    """No data and a failed refresh means unavailable."""
    coordinator = _build(hass, mock_entry)
    coordinator.last_update_success = False
    coordinator.data = None

    assert coordinator.available is False


def test_unavailable_after_grace_period(hass, mock_entry, uw_data):
    """Cached data older than the grace window marks the entity unavailable."""
    coordinator = _build(hass, mock_entry)
    coordinator.last_update_success = False
    coordinator.data = uw_data
    coordinator._last_success_time = time.monotonic() - (AVAILABILITY_GRACE_SECONDS + 60)

    assert coordinator.available is False


def test_apply_backoff_doubles_then_caps(hass, mock_entry):
    """Backoff doubles the interval and never exceeds the maximum."""
    coordinator = _build(hass, mock_entry)

    coordinator._apply_backoff()
    assert coordinator._current_interval == DEFAULT_SCAN_INTERVAL * 2
    assert coordinator.update_interval == timedelta(seconds=DEFAULT_SCAN_INTERVAL * 2)

    for _ in range(20):
        coordinator._apply_backoff()

    assert coordinator._current_interval == MAX_SCAN_INTERVAL


def test_reset_backoff_restores_default_interval(hass, mock_entry):
    """A successful refresh restores the default polling interval."""
    coordinator = _build(hass, mock_entry)
    coordinator._apply_backoff()

    coordinator._reset_backoff()

    assert coordinator._current_interval == DEFAULT_SCAN_INTERVAL
    assert coordinator.update_interval == timedelta(seconds=DEFAULT_SCAN_INTERVAL)


def test_reset_backoff_is_noop_when_already_default(hass, mock_entry):
    """Reset is harmless when no backoff is active."""
    coordinator = _build(hass, mock_entry)

    coordinator._reset_backoff()

    assert coordinator._current_interval == DEFAULT_SCAN_INTERVAL
