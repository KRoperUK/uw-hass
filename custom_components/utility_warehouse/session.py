from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.httpx_client import create_async_httpx_client


async def async_validate_session(hass: HomeAssistant, cookie_string: str) -> Any:
    """Fetch the account with a pasted browser session, raising on a bad one."""
    from uw_api import UWClient

    http_client = create_async_httpx_client(hass, auto_cleanup=False)
    try:
        async with UWClient.from_session(cookie_string, http_client=http_client) as client:
            return await client.gql.get_account()
    finally:
        await http_client.aclose()
