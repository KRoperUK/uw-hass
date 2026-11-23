from __future__ import annotations

import logging
import time
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.httpx_client import create_async_httpx_client, get_async_client
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    AVAILABILITY_GRACE_SECONDS,
    CONF_SESSION_COOKIE,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MAX_SCAN_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)


class UWDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
    ) -> None:
        scan_seconds = DEFAULT_SCAN_INTERVAL
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            config_entry=entry,
            update_interval=timedelta(seconds=scan_seconds),
        )
        self._entry = entry
        self._last_success_time: float = 0.0
        self._current_interval = scan_seconds

    def _apply_backoff(self) -> None:
        self._current_interval = min(self._current_interval * 2, MAX_SCAN_INTERVAL)
        self.update_interval = timedelta(seconds=self._current_interval)
        _LOGGER.warning("Backing off to %ss between updates", self._current_interval)

    def _reset_backoff(self) -> None:
        if self._current_interval != DEFAULT_SCAN_INTERVAL:
            self._current_interval = DEFAULT_SCAN_INTERVAL
            self.update_interval = timedelta(seconds=DEFAULT_SCAN_INTERVAL)

    @property
    def available(self) -> bool:
        if self.last_update_success:
            return True
        return bool(
            self.data and time.monotonic() - self._last_success_time < AVAILABILITY_GRACE_SECONDS
        )

    async def _async_update_data(self) -> dict[str, Any]:
        from uw_api import UWAuthError, UWSessionExpiredError

        try:
            data = await self._async_fetch_all()
        except (UWAuthError, UWSessionExpiredError) as exc:
            raise ConfigEntryAuthFailed from exc
        except Exception as exc:
            self._apply_backoff()
            raise UpdateFailed(f"Failed to fetch UW data: {exc}") from exc

        self._last_success_time = time.monotonic()
        self._reset_backoff()
        return data

    async def _async_fetch_all(self) -> dict[str, Any]:
        from uw_api import UWClient

        cookie = self._entry.data.get(CONF_SESSION_COOKIE)
        if cookie:
            # Session clients need their own cookie jar; the shared HA client
            # must not carry one account's cookies for every entry.
            http_client = create_async_httpx_client(self.hass, auto_cleanup=False)
            try:
                async with UWClient.from_session(cookie, http_client=http_client) as client:
                    return await self._async_collect(client)
            finally:
                await http_client.aclose()

        async with UWClient(
            email=self._entry.data[CONF_EMAIL],
            password=self._entry.data[CONF_PASSWORD],
            http_client=get_async_client(self.hass),
        ) as client:
            await client.login()
            return await self._async_collect(client)

    async def _async_collect(self, client: Any) -> dict[str, Any]:
        data: dict[str, Any] = {}

        data["account"] = await client.gql.get_account()

        for key, method in (
            ("balance", client.gql.get_balance),
            ("tariff", client.gql.get_tariff),
            ("consumption", client.gql.get_consumption),
            ("meters", client.gql.get_meters),
            ("readings", client.gql.get_meter_readings),
            ("bills", client.gql.get_bills),
        ):
            try:
                data[key] = await method()
            except Exception as exc:
                _LOGGER.warning("Failed to fetch %s: %s", key, exc)

        return data
