from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant.components.repairs import RepairsFlow
from homeassistant.core import HomeAssistant

from .const import CONF_SESSION_COOKIE
from .session import async_validate_session

_LOGGER = logging.getLogger(__name__)

STEP_SESSION_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_SESSION_COOKIE): str,
    }
)


class SessionExpiredRepairFlow(RepairsFlow):
    """Ask for a fresh browser Cookie header when the session expires."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> Any:
        errors: dict[str, str] = {}
        entry_id = str((self.data or {}).get("entry_id", ""))
        entry = self.hass.config_entries.async_get_entry(entry_id)

        if user_input is not None:
            cookie_string = user_input[CONF_SESSION_COOKIE].strip()
            try:
                from uw_api import UWAuthError, UWSessionExpiredError

                account = await async_validate_session(self.hass, cookie_string)
            except ImportError:
                _LOGGER.exception("uw-api library not installed")
                errors["base"] = "connection_error"
            except (UWAuthError, UWSessionExpiredError) as err:
                _LOGGER.warning("Utility Warehouse session rejected: %s", err)
                errors["base"] = "auth_error"
            except Exception:
                _LOGGER.exception("Unexpected error checking the browser session")
                errors["base"] = "connection_error"
            else:
                if entry is not None:
                    self.hass.config_entries.async_update_entry(
                        entry,
                        data={
                            **entry.data,
                            CONF_SESSION_COOKIE: cookie_string,
                            "account_number": account.account_number,
                        },
                    )
                    await self.hass.config_entries.async_reload(entry.entry_id)
                return self.async_create_entry(title="", data={})

        return self.async_show_form(
            step_id="init",
            data_schema=STEP_SESSION_DATA_SCHEMA,
            errors=errors,
        )


async def async_create_fix_flow(
    hass: HomeAssistant,
    issue_id: str,
    data: dict[str, str | int | float | None] | None,
) -> RepairsFlow:
    return SessionExpiredRepairFlow()
