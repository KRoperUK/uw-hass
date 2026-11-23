"""Tests for the Utility Warehouse diagnostics."""

from __future__ import annotations

from unittest.mock import MagicMock

from custom_components.utility_warehouse.const import CONF_SESSION_COOKIE
from custom_components.utility_warehouse.diagnostics import (
    async_get_config_entry_diagnostics,
)

from .conftest import ACCOUNT_NUMBER, make_uw_data


async def test_credentials_are_redacted(hass, mock_entry):
    """The session cookie must never appear in diagnostics output."""
    mock_entry.add_to_hass(hass)
    mock_entry.runtime_data = MagicMock(last_update_success=True, data=make_uw_data())

    diagnostics = await async_get_config_entry_diagnostics(hass, mock_entry)

    data = diagnostics["entry"]["data"]
    assert data[CONF_SESSION_COOKIE] == "**REDACTED**"
    assert data["account_number"] == "**REDACTED**"
    assert "uw-user-session=def" not in str(diagnostics)


async def test_resources_and_health_are_included(hass, mock_entry):
    """Diagnostics list the fetched resources without exporting their values."""
    mock_entry.add_to_hass(hass)
    mock_entry.runtime_data = MagicMock(
        last_update_success=False, data={"account": object(), "bills": []}
    )

    diagnostics = await async_get_config_entry_diagnostics(hass, mock_entry)

    assert diagnostics["coordinator"] == {
        "last_update_success": False,
        "resources": ["account", "bills"],
    }
    assert ACCOUNT_NUMBER not in str(diagnostics)


async def test_diagnostics_before_setup(hass, mock_entry):
    """An entry that never finished setup still produces safe diagnostics."""
    mock_entry.add_to_hass(hass)

    diagnostics = await async_get_config_entry_diagnostics(hass, mock_entry)

    assert diagnostics["coordinator"] == {
        "last_update_success": None,
        "resources": [],
    }
