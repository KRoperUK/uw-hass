from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.helpers.httpx_client import get_async_client

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_EMAIL): str,
        vol.Required(CONF_PASSWORD): str,
    }
)


class UWConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            email = user_input[CONF_EMAIL].strip()
            password = user_input[CONF_PASSWORD]

            try:
                from uw_api import UWAuthError, UWClient

                http_client = get_async_client(self.hass)

                async with UWClient(
                    email=email,
                    password=password,
                    http_client=http_client,
                ) as client:
                    await client.login()
                    account = await client.gql.get_account()
            except ImportError:
                _LOGGER.exception("uw-api library not installed")
                errors["base"] = "connection_error"
            except UWAuthError:
                errors["base"] = "auth_error"
            except Exception:
                _LOGGER.exception("Unexpected error during config flow")
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
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )
