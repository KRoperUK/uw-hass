"""Tests for the expired-session repair flow."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import uw_api
from homeassistant.data_entry_flow import FlowResultType

from custom_components.utility_warehouse.const import (
    CONF_SESSION_COOKIE,
    CONF_USER_AGENT,
)
from custom_components.utility_warehouse.repairs import (
    SessionExpiredRepairFlow,
    async_create_fix_flow,
)

from .conftest import ACCOUNT_NUMBER

REPAIRS = "custom_components.utility_warehouse.repairs"
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Chrome/158.0.0.0"


def _flow(hass, entry) -> SessionExpiredRepairFlow:
    flow = SessionExpiredRepairFlow()
    flow.hass = hass
    flow.data = {"entry_id": entry.entry_id}
    return flow


async def test_create_fix_flow_returns_the_session_flow(hass, mock_entry):
    flow = await async_create_fix_flow(hass, "session_expired_x", {"entry_id": mock_entry.entry_id})

    assert isinstance(flow, SessionExpiredRepairFlow)


async def test_fix_flow_shows_a_form(hass, mock_entry):
    result = await _flow(hass, mock_entry).async_step_init()

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "init"
    assert result["errors"] == {}


async def test_fix_flow_stores_the_new_cookie(hass, mock_entry):
    mock_entry.add_to_hass(hass)
    flow = _flow(hass, mock_entry)

    with (
        patch(
            f"{REPAIRS}.async_validate_session",
            AsyncMock(return_value=SimpleNamespace(account_number=ACCOUNT_NUMBER)),
        ),
        patch.object(hass.config_entries, "async_reload", AsyncMock()) as reload,
    ):
        result = await flow.async_step_init({CONF_SESSION_COOKIE: "_csrf=new; uw-user-session=new"})

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert mock_entry.data[CONF_SESSION_COOKIE] == "_csrf=new; uw-user-session=new"
    reload.assert_awaited_once_with(mock_entry.entry_id)


async def test_fix_flow_stores_the_user_agent(hass, mock_entry):
    """A pasted user agent is saved and used for validation."""
    mock_entry.add_to_hass(hass)
    flow = _flow(hass, mock_entry)
    validate = AsyncMock(return_value=SimpleNamespace(account_number=ACCOUNT_NUMBER))

    with (
        patch(f"{REPAIRS}.async_validate_session", validate),
        patch.object(hass.config_entries, "async_reload", AsyncMock()),
    ):
        result = await flow.async_step_init(
            {CONF_SESSION_COOKIE: "_csrf=new", CONF_USER_AGENT: USER_AGENT}
        )

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert mock_entry.data[CONF_USER_AGENT] == USER_AGENT
    validate.assert_awaited_once_with(hass, "_csrf=new", USER_AGENT)


async def test_fix_flow_rejects_a_bad_cookie(hass, mock_entry):
    flow = _flow(hass, mock_entry)

    with patch(
        f"{REPAIRS}.async_validate_session",
        AsyncMock(side_effect=uw_api.UWSessionExpiredError("expired")),
    ):
        result = await flow.async_step_init({CONF_SESSION_COOKIE: "_csrf=stale"})

    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {"base": "auth_error"}


async def test_fix_flow_reports_connection_errors(hass, mock_entry):
    flow = _flow(hass, mock_entry)

    with patch(
        f"{REPAIRS}.async_validate_session",
        AsyncMock(side_effect=OSError("offline")),
    ):
        result = await flow.async_step_init({CONF_SESSION_COOKIE: "_csrf=abc"})

    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {"base": "connection_error"}
