from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult

from .const import CONF_SESSION_COOKIE, CONF_USER_AGENT, DOMAIN
from .session import async_validate_session

_LOGGER = logging.getLogger(__name__)

STEP_SESSION_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_SESSION_COOKIE): str,
        vol.Optional(CONF_USER_AGENT, default=""): str,
    }
)


class UWConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def _async_validate(
        self, cookie_string: str, user_agent: str | None
    ) -> tuple[dict[str, str], Any]:
        try:
            from uw_api import UWAuthError, UWSessionExpiredError

            account = await async_validate_session(self.hass, cookie_string, user_agent)
        except ImportError:
            _LOGGER.exception("uw-api library not installed")
            return {"base": "connection_error"}, None
        except (UWAuthError, UWSessionExpiredError) as err:
            _LOGGER.warning("Utility Warehouse session rejected: %s", err)
            return {"base": "auth_error"}, None
        except OSError as err:
            _LOGGER.info(
                "Utility Warehouse session check failed: connection problem (%s)",
                type(err).__name__,
            )
            return {"base": "connection_error"}, None
        except Exception:
            _LOGGER.exception("Unexpected error checking the browser session")
            return {"base": "connection_error"}, None
        return {}, account

    @staticmethod
    def _entry_data(cookie_string: str, user_agent: str | None, account: Any) -> dict[str, Any]:
        data: dict[str, Any] = {
            CONF_SESSION_COOKIE: cookie_string,
            "account_number": account.account_number,
        }
        if user_agent:
            data[CONF_USER_AGENT] = user_agent
        return data

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            cookie_string = user_input[CONF_SESSION_COOKIE].strip()
            user_agent = (user_input.get(CONF_USER_AGENT) or "").strip() or None
            errors, account = await self._async_validate(cookie_string, user_agent)
            if account is not None:
                await self.async_set_unique_id(account.account_number)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=f"UW - {account.account_number}",
                    data=self._entry_data(cookie_string, user_agent, account),
                )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_SESSION_DATA_SCHEMA,
            errors=errors,
        )

    async def async_step_reauth(self, entry_data: Mapping[str, Any]) -> ConfigFlowResult:
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        entry = self._get_reauth_entry()

        if user_input is not None:
            cookie_string = user_input[CONF_SESSION_COOKIE].strip()
            user_agent = (user_input.get(CONF_USER_AGENT) or "").strip() or None
            errors, account = await self._async_validate(cookie_string, user_agent)
            if account is not None:
                self.hass.config_entries.async_update_entry(
                    entry,
                    title=f"UW - {account.account_number}",
                    data=self._entry_data(cookie_string, user_agent, account),
                )
                return self.async_abort(reason="reauth_successful")

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=STEP_SESSION_DATA_SCHEMA,
            errors=errors,
            description_placeholders={"account": entry.title},
        )
