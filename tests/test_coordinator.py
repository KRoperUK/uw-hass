"""Tests for the Utility Warehouse data update coordinator."""

from __future__ import annotations

import time
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import uw_api
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.utility_warehouse.const import (
    AVAILABILITY_GRACE_SECONDS,
    CONF_USER_AGENT,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MAX_SCAN_INTERVAL,
    session_issue_id,
)
from custom_components.utility_warehouse.coordinator import UWDataUpdateCoordinator

from .conftest import ACCOUNT_NUMBER, fake_client_class

COORDINATOR = "custom_components.utility_warehouse.coordinator"
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Chrome/158.0.0.0"


def _build(hass: Any, entry: Any) -> UWDataUpdateCoordinator:
    return UWDataUpdateCoordinator(hass, entry)


@contextmanager
def _patched_session(client_class: type, http_client: Any | None = None) -> Iterator[Any]:
    """Patch the dedicated cookie-jar client used for session auth."""
    client = http_client if http_client is not None else MagicMock()
    client.headers = {}
    client.aclose = AsyncMock()
    with (
        patch(f"{COORDINATOR}.create_async_httpx_client", return_value=client),
        patch("uw_api.UWClient", client_class),
    ):
        yield client


async def test_update_data_success(hass, mock_entry):
    """A happy-path refresh returns the assembled payload."""
    coordinator = _build(hass, mock_entry)

    with _patched_session(fake_client_class()):
        data = await coordinator._async_update_data()

    assert data["account"].account_number == ACCOUNT_NUMBER
    assert data["bills"][0].total_amount_gbp == 88.75
    assert coordinator._current_interval == DEFAULT_SCAN_INTERVAL
    assert coordinator._last_success_time > 0


async def test_update_data_auth_error_raises_config_entry_auth_failed(hass, mock_entry):
    """A rejected session is reported as an auth failure."""
    coordinator = _build(hass, mock_entry)

    with (
        _patched_session(fake_client_class(account_error=uw_api.UWAuthError("rejected"))),
        pytest.raises(ConfigEntryAuthFailed),
    ):
        await coordinator._async_update_data()


async def test_missing_cookie_raises_config_entry_auth_failed(hass, mock_entry):
    """Entries created before session auth prompt for reauthentication."""
    mock_entry.add_to_hass(hass)
    hass.config_entries.async_update_entry(
        mock_entry, data={"email": "old@example.com", "password": "hunter2"}
    )
    coordinator = _build(hass, mock_entry)

    with pytest.raises(ConfigEntryAuthFailed):
        await coordinator._async_update_data()


async def test_user_agent_is_applied(hass, mock_entry):
    """A stored browser user agent is sent with forbidden-by-WAF requests."""
    mock_entry.add_to_hass(hass)
    hass.config_entries.async_update_entry(
        mock_entry, data={**mock_entry.data, CONF_USER_AGENT: USER_AGENT}
    )
    coordinator = _build(hass, mock_entry)

    with _patched_session(fake_client_class()) as http_client:
        await coordinator._async_update_data()

    assert http_client.headers["User-Agent"] == USER_AGENT


async def test_update_data_session_expiry_raises_update_failed_and_reports_repair(hass, mock_entry):
    """An expired session degrades softly and raises a repairable issue."""
    coordinator = _build(hass, mock_entry)

    with (
        _patched_session(
            fake_client_class(account_error=uw_api.UWSessionExpiredError("expired"))
        ) as http_client,
        pytest.raises(UpdateFailed),
    ):
        await coordinator._async_update_data()

    http_client.aclose.assert_awaited_once()
    assert coordinator._current_interval == DEFAULT_SCAN_INTERVAL * 2

    issue = ir.async_get(hass).async_get_issue(DOMAIN, session_issue_id(mock_entry.entry_id))
    assert issue is not None
    assert issue.is_fixable
    assert issue.translation_key == "session_expired"


async def test_successful_update_clears_session_issue(hass, mock_entry):
    """A successful refresh removes a stale session repair issue."""
    ir.async_create_issue(
        hass,
        DOMAIN,
        session_issue_id(mock_entry.entry_id),
        is_fixable=True,
        is_persistent=True,
        severity=ir.IssueSeverity.WARNING,
        translation_key="session_expired",
        data={"entry_id": mock_entry.entry_id},
    )
    coordinator = _build(hass, mock_entry)

    with _patched_session(fake_client_class()):
        await coordinator._async_update_data()

    assert ir.async_get(hass).async_get_issue(DOMAIN, session_issue_id(mock_entry.entry_id)) is None


async def test_update_data_uses_a_dedicated_cookie_client(hass, mock_entry):
    """The coordinator never touches the shared HA client for session auth."""
    coordinator = _build(hass, mock_entry)

    with _patched_session(fake_client_class()) as http_client:
        data = await coordinator._async_update_data()

    assert data["account"].account_number == ACCOUNT_NUMBER
    http_client.aclose.assert_awaited_once()


async def test_update_data_failure_raises_update_failed_and_backs_off(hass, mock_entry):
    """A transport failure raises UpdateFailed and lengthens the interval."""
    coordinator = _build(hass, mock_entry)

    with (
        _patched_session(fake_client_class(account_error=RuntimeError("socket down"))),
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

    with _patched_session(fake_client_class(fail_fields=failing)):
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
