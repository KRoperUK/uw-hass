from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.helpers.httpx_client import get_async_client

from .const import CONF_SESSION_COOKIE, DOMAIN
from .session import async_validate_session

_LOGGER = logging.getLogger(__name__)

STEP_CREDENTIALS_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_EMAIL): str,
        vol.Required(CONF_PASSWORD): str,
    }
)

STEP_SESSION_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_SESSION_COOKIE): str,
    }
)


class UWConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        return self.async_show_menu(
            step_id="user",
            menu_options=["session", "credentials"],
        )

    async def async_step_session(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}

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
            except OSError as err:
                _LOGGER.info(
                    "Utility Warehouse session check failed: connection problem (%s)",
                    type(err).__name__,
                )
                errors["base"] = "connection_error"
            except Exception:
                _LOGGER.exception("Unexpected error checking the browser session")
                errors["base"] = "connection_error"
            else:
                await self.async_set_unique_id(account.account_number)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=f"UW - {account.account_number}",
                    data={
                        CONF_SESSION_COOKIE: cookie_string,
                        "account_number": account.account_number,
                    },
                )

        return self.async_show_form(
            step_id="session",
            data_schema=STEP_SESSION_DATA_SCHEMA,
            errors=errors,
        )

    async def async_step_credentials(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            email = user_input[CONF_EMAIL].strip()
            password = user_input[CONF_PASSWORD]

            _LOGGER.debug("Utility Warehouse setup attempt started")
            stage = "login"
            try:
                from uw_api import UWAuthError, UWClient, UWRateLimitError, UWSessionExpiredError

                http_client = get_async_client(self.hass)

                async with UWClient(
                    email=email,
                    password=password,
                    http_client=http_client,
                ) as client:
                    await client.login()
                    stage = "account fetch"
                    account = await client.gql.get_account()
            except ImportError:
                _LOGGER.exception("uw-api library not installed")
                errors["base"] = "connection_error"
            except (UWAuthError, UWSessionExpiredError) as err:
                # Wrong credentials (or a session that died during setup) —
                # never log the password, and keep the identifier at debug.
                _LOGGER.info(
                    "Utility Warehouse %s failed: invalid credentials (%s)",
                    stage,
                    type(err).__name__,
                )
                _LOGGER.debug("Credential rejection for identifier %s", email)
                errors["base"] = "auth_error"
            except UWRateLimitError:
                _LOGGER.info("Utility Warehouse %s failed: rate limited, retry later", stage)
                errors["base"] = "connection_error"
            except OSError as err:
                # DNS, refused connections, resets, timeouts — connectivity,
                # not credentials.
                _LOGGER.info(
                    "Utility Warehouse %s failed: connection problem (%s)",
                    stage,
                    type(err).__name__,
                )
                errors["base"] = "connection_error"
            except Exception:
                _LOGGER.exception("Unexpected error during config flow (%s)", stage)
                errors["base"] = "connection_error"
            else:
                await self.async_set_unique_id(email.lower())
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=f"UW - {email}",
                    data={
                        CONF_EMAIL: email,
                        CONF_PASSWORD: password,
                        "account_number": account.account_number,
                    },
                )

        return self.async_show_form(
            step_id="credentials",
            data_schema=STEP_CREDENTIALS_DATA_SCHEMA,
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
                self.hass.config_entries.async_update_entry(
                    entry,
                    title=f"UW - {account.account_number}",
                    data={
                        **entry.data,
                        CONF_SESSION_COOKIE: cookie_string,
                        "account_number": account.account_number,
                    },
                )
                return self.async_abort(reason="reauth_successful")

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=STEP_SESSION_DATA_SCHEMA,
            errors=errors,
            description_placeholders={"account": entry.title},
        )
