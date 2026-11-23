"""Tests for the Utility Warehouse config flow."""

from __future__ import annotations

import logging
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import uw_api
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResultType

from custom_components.utility_warehouse.const import (
    CONF_SESSION_COOKIE,
    CONF_USER_AGENT,
    DOMAIN,
)

from .conftest import ACCOUNT_NUMBER, fake_client_class

CONFIG_FLOW = "custom_components.utility_warehouse.config_flow"
SESSION = "custom_components.utility_warehouse.session"
COOKIE = "_csrf=abc; uw-user-session=def"
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Chrome/158.0.0.0"


def _http_client() -> MagicMock:
    client = MagicMock()
    client.headers = {}
    client.aclose = AsyncMock()
    return client


async def _start(hass):
    return await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )


async def _submit(hass, flow_id, cookie: str = COOKIE, user_agent: str = ""):
    return await hass.config_entries.flow.async_configure(
        flow_id,
        user_input={CONF_SESSION_COOKIE: cookie, CONF_USER_AGENT: user_agent},
    )


async def test_form_is_shown(hass):
    """The user step asks for a browser session."""
    result = await _start(hass)

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {}


async def test_setup(hass):
    """A valid browser session creates an entry keyed on the account number."""
    result = await _start(hass)

    with (
        patch(f"{SESSION}.create_async_httpx_client", return_value=_http_client()),
        patch("uw_api.UWClient", fake_client_class()),
    ):
        result = await _submit(hass, result["flow_id"])

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["title"] == f"UW - {ACCOUNT_NUMBER}"
    assert result["data"][CONF_SESSION_COOKIE] == COOKIE
    assert result["data"]["account_number"] == ACCOUNT_NUMBER
    assert result["result"].unique_id == ACCOUNT_NUMBER


async def test_user_agent_is_stored_when_supplied(hass):
    """An optional browser user agent is saved with the session."""
    result = await _start(hass)

    with (
        patch(f"{SESSION}.create_async_httpx_client", return_value=_http_client()),
        patch("uw_api.UWClient", fake_client_class()),
    ):
        result = await _submit(hass, result["flow_id"], user_agent=USER_AGENT)

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_USER_AGENT] == USER_AGENT


async def test_user_agent_is_omitted_when_blank(hass):
    """An empty user agent is not written to the entry."""
    result = await _start(hass)

    with (
        patch(f"{SESSION}.create_async_httpx_client", return_value=_http_client()),
        patch("uw_api.UWClient", fake_client_class()),
    ):
        result = await _submit(hass, result["flow_id"], user_agent="  ")

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert CONF_USER_AGENT not in result["data"]


async def test_user_agent_is_applied_to_the_validation_client(hass):
    """The pasted user agent is used for the validation request."""
    http_client = _http_client()
    result = await _start(hass)

    with (
        patch(f"{SESSION}.create_async_httpx_client", return_value=http_client),
        patch("uw_api.UWClient", fake_client_class()),
    ):
        await _submit(hass, result["flow_id"], user_agent=USER_AGENT)

    assert http_client.headers["User-Agent"] == USER_AGENT


async def test_rejected_session_shows_auth_error(hass):
    """Expired or incomplete cookies surface an auth_error."""
    result = await _start(hass)

    with (
        patch(f"{SESSION}.create_async_httpx_client", return_value=_http_client()),
        patch(
            "uw_api.UWClient",
            fake_client_class(account_error=uw_api.UWSessionExpiredError("expired")),
        ),
    ):
        result = await _submit(hass, result["flow_id"])

    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {"base": "auth_error"}


async def test_connection_error_shows_connection_error(hass, caplog):
    """A network failure is connectivity, not credentials."""
    result = await _start(hass)

    with (
        patch(f"{SESSION}.create_async_httpx_client", return_value=_http_client()),
        patch("uw_api.UWClient", fake_client_class(account_error=OSError("dns failed"))),
        caplog.at_level(logging.INFO, logger=CONFIG_FLOW),
    ):
        result = await _submit(hass, result["flow_id"])

    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {"base": "connection_error"}
    assert "connection problem" in caplog.text


async def test_unexpected_error_shows_connection_error(hass):
    """An unexpected exception surfaces a connection_error on the form."""
    result = await _start(hass)

    with (
        patch(f"{SESSION}.create_async_httpx_client", return_value=_http_client()),
        patch("uw_api.UWClient", fake_client_class(account_error=RuntimeError("kaboom"))),
    ):
        result = await _submit(hass, result["flow_id"])

    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {"base": "connection_error"}


async def test_missing_library_shows_connection_error(hass):
    """A missing uw-api install surfaces a connection_error on the form."""
    result = await _start(hass)

    with patch.dict(sys.modules, {"uw_api": None}):
        result = await _submit(hass, result["flow_id"])

    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {"base": "connection_error"}


async def test_duplicate_account_aborts(hass, mock_entry):
    """A second entry for the same account aborts."""
    mock_entry.add_to_hass(hass)
    result = await _start(hass)

    with (
        patch(f"{SESSION}.create_async_httpx_client", return_value=_http_client()),
        patch("uw_api.UWClient", fake_client_class()),
    ):
        result = await _submit(hass, result["flow_id"])

    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_reauth_updates_the_stored_cookie(hass, mock_entry):
    """Reauthentication replaces the stored session and user agent."""
    mock_entry.add_to_hass(hass)
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_REAUTH, "entry_id": mock_entry.entry_id},
    )

    with (
        patch(f"{SESSION}.create_async_httpx_client", return_value=_http_client()),
        patch("uw_api.UWClient", fake_client_class()),
    ):
        result = await _submit(
            hass, result["flow_id"], "_csrf=new; uw-user-session=new", USER_AGENT
        )

    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert mock_entry.data[CONF_SESSION_COOKIE] == "_csrf=new; uw-user-session=new"
    assert mock_entry.data[CONF_USER_AGENT] == USER_AGENT


async def test_reauth_drops_legacy_password_data(hass, mock_entry):
    """An entry from the password era loses its unused credentials."""
    mock_entry.add_to_hass(hass)
    hass.config_entries.async_update_entry(
        mock_entry,
        data={"email": "old@example.com", "password": "hunter2"},
    )
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_REAUTH, "entry_id": mock_entry.entry_id},
    )

    with (
        patch(f"{SESSION}.create_async_httpx_client", return_value=_http_client()),
        patch("uw_api.UWClient", fake_client_class()),
    ):
        result = await _submit(hass, result["flow_id"])

    assert result["reason"] == "reauth_successful"
    assert "password" not in mock_entry.data
    assert mock_entry.data[CONF_SESSION_COOKIE] == COOKIE
