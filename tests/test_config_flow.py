"""Tests for the Utility Warehouse config flow."""

from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import uw_api
from homeassistant import config_entries
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.data_entry_flow import FlowResultType

from custom_components.utility_warehouse.const import DOMAIN

from .conftest import ACCOUNT_NUMBER, EMAIL, PASSWORD, fake_client_class

CONFIG_FLOW = "custom_components.utility_warehouse.config_flow"


async def _start(hass):
    return await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )


async def _submit(hass, flow_id):
    return await hass.config_entries.flow.async_configure(
        flow_id, user_input={CONF_EMAIL: EMAIL, CONF_PASSWORD: PASSWORD}
    )


async def test_form_is_shown(hass):
    """The user step renders an empty form."""
    result = await _start(hass)

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {}


async def test_successful_setup(hass):
    """A valid login creates the config entry."""
    result = await _start(hass)

    with (
        patch(f"{CONFIG_FLOW}.get_async_client", return_value=MagicMock()),
        patch("uw_api.UWClient", fake_client_class()),
    ):
        result = await _submit(hass, result["flow_id"])

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["title"] == f"UW - {EMAIL}"
    assert result["data"][CONF_EMAIL] == EMAIL
    assert result["data"]["account_number"] == ACCOUNT_NUMBER


async def test_auth_error_shows_error(hass):
    """Bad credentials surface an auth_error on the form."""
    result = await _start(hass)

    with (
        patch(f"{CONFIG_FLOW}.get_async_client", return_value=MagicMock()),
        patch("uw_api.UWClient", fake_client_class(login_error=uw_api.UWAuthError("nope"))),
    ):
        result = await _submit(hass, result["flow_id"])

    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {"base": "auth_error"}


async def test_network_error_shows_connection_error_and_logs_stage(hass, caplog):
    """A DNS/reset/timeout failure is connectivity, not credentials."""
    import logging

    result = await _start(hass)

    with (
        patch(f"{CONFIG_FLOW}.get_async_client", return_value=MagicMock()),
        patch("uw_api.UWClient", fake_client_class(login_error=OSError("dns failed"))),
        caplog.at_level(logging.INFO, logger="custom_components.utility_warehouse.config_flow"),
    ):
        result = await _submit(hass, result["flow_id"])

    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {"base": "connection_error"}
    assert "login failed: connection problem" in caplog.text


async def test_rate_limit_shows_connection_error(hass):
    """Rate limiting asks for a retry, not new credentials."""
    result = await _start(hass)

    with (
        patch(f"{CONFIG_FLOW}.get_async_client", return_value=MagicMock()),
        patch(
            "uw_api.UWClient", fake_client_class(login_error=uw_api.UWRateLimitError("slow down"))
        ),
    ):
        result = await _submit(hass, result["flow_id"])

    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {"base": "connection_error"}


async def test_session_expired_shows_auth_error(hass):
    """A session that dies during setup needs re-authentication."""
    result = await _start(hass)

    with (
        patch(f"{CONFIG_FLOW}.get_async_client", return_value=MagicMock()),
        patch(
            "uw_api.UWClient",
            fake_client_class(login_error=uw_api.UWSessionExpiredError("expired")),
        ),
    ):
        result = await _submit(hass, result["flow_id"])

    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {"base": "auth_error"}


async def test_account_fetch_failure_does_not_create_entry(hass, caplog):
    """A login that succeeds but an account fetch that fails stays on the form."""
    import logging

    result = await _start(hass)

    with (
        patch(f"{CONFIG_FLOW}.get_async_client", return_value=MagicMock()),
        patch("uw_api.UWClient", fake_client_class(fail_fields={"get_account"})),
        caplog.at_level(logging.INFO, logger="custom_components.utility_warehouse.config_flow"),
    ):
        result = await _submit(hass, result["flow_id"])

    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {"base": "connection_error"}
    assert "account fetch" in caplog.text


async def test_unexpected_error_shows_connection_error(hass):
    """An unexpected exception surfaces a connection_error on the form."""
    result = await _start(hass)

    with (
        patch(f"{CONFIG_FLOW}.get_async_client", return_value=MagicMock()),
        patch("uw_api.UWClient", fake_client_class(login_error=RuntimeError("kaboom"))),
    ):
        result = await _submit(hass, result["flow_id"])

    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {"base": "connection_error"}


async def test_missing_library_shows_connection_error(hass):
    """A missing uw-api install surfaces a connection_error on the form."""
    result = await _start(hass)

    with (
        patch.dict(sys.modules, {"uw_api": None}),
        patch(f"{CONFIG_FLOW}.get_async_client", return_value=MagicMock()),
    ):
        result = await _submit(hass, result["flow_id"])

    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {"base": "connection_error"}


async def test_duplicate_account_aborts(hass, mock_entry):
    """A second entry for the same email aborts."""
    mock_entry.add_to_hass(hass)
    result = await _start(hass)

    with (
        patch(f"{CONFIG_FLOW}.get_async_client", return_value=MagicMock()),
        patch("uw_api.UWClient", fake_client_class()),
    ):
        result = await _submit(hass, result["flow_id"])

    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "already_configured"
