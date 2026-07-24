from __future__ import annotations

import logging
import time
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.httpx_client import get_async_client
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    AVAILABILITY_GRACE_SECONDS,
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
        try:
            from uw_api import UWClient

            email = self._entry.data[CONF_EMAIL]
            password = self._entry.data[CONF_PASSWORD]
            http_client = get_async_client(self.hass)

            data: dict[str, Any] = {}

            async with UWClient(
                email=email,
                password=password,
                http_client=http_client,
            ) as client:
                await client.login()

                account = await client.gql.get_account()
                data["account"] = account

                try:
                    data["balance"] = await client.gql.get_balance()
                except Exception as exc:
                    _LOGGER.warning("Failed to fetch balance: %s", exc)

                try:
                    data["tariff"] = await client.gql.get_tariff()
                except Exception as exc:
                    _LOGGER.warning("Failed to fetch tariff: %s", exc)

                try:
                    data["consumption"] = await client.gql.get_consumption()
                except Exception as exc:
                    _LOGGER.warning("Failed to fetch consumption: %s", exc)

                try:
                    data["meters"] = await client.gql.get_meters()
                except Exception as exc:
                    _LOGGER.warning("Failed to fetch meters: %s", exc)

                try:
                    data["readings"] = await client.gql.get_meter_readings()
                except Exception as exc:
                    _LOGGER.warning("Failed to fetch readings: %s", exc)

                try:
                    data["bills"] = await client.gql.get_bills()
                except Exception as exc:
                    _LOGGER.warning("Failed to fetch bills: %s", exc)

            self._last_success_time = time.monotonic()
            self._reset_backoff()
            return data

        except Exception as exc:
            msg = str(exc).lower()
            if "auth" in msg or "credential" in msg or "login failed" in msg:
                raise ConfigEntryAuthFailed from exc
            self._apply_backoff()
            raise UpdateFailed(f"Failed to fetch UW data: {exc}") from exc
