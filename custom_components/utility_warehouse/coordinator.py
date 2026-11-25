from __future__ import annotations

import logging
import time
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.httpx_client import create_async_httpx_client
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    AVAILABILITY_GRACE_SECONDS,
    CONF_SESSION_COOKIE,
    CONF_USER_AGENT,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MAX_SCAN_INTERVAL,
    session_issue_id,
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
        # Resource keys (see _async_collect) whose last fetch failed. Entities
        # for these resources report unavailable instead of showing old data.
        self.failed_resources: set[str] = set()

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
        except UWSessionExpiredError as exc:
            # Soft failure: keep the last data available for the grace window,
            # stop hammering the portal, and raise a repairable issue.
            self._async_report_expired_session()
            self._apply_backoff()
            raise UpdateFailed("Utility Warehouse session has expired") from exc
        except ConfigEntryAuthFailed:
            raise
        except UWAuthError as exc:
            raise ConfigEntryAuthFailed from exc
        except Exception as exc:
            self._apply_backoff()
            raise UpdateFailed(f"Failed to fetch UW data: {exc}") from exc

        self._last_success_time = time.monotonic()
        self._reset_backoff()
        self._async_clear_expired_session_issue()
        return data

    def _async_report_expired_session(self) -> None:
        _LOGGER.warning(
            "Utility Warehouse session for %s has expired; a repair has been raised",
            self._entry.title,
        )
        ir.async_create_issue(
            self.hass,
            DOMAIN,
            session_issue_id(self._entry.entry_id),
            is_fixable=True,
            is_persistent=True,
            severity=ir.IssueSeverity.WARNING,
            translation_key="session_expired",
            translation_placeholders={"account": self._entry.title},
            data={"entry_id": self._entry.entry_id},
        )

    def _async_clear_expired_session_issue(self) -> None:
        ir.async_delete_issue(self.hass, DOMAIN, session_issue_id(self._entry.entry_id))

    async def _async_fetch_all(self) -> dict[str, Any]:
        from uw_api import UWClient

        cookie = self._entry.data.get(CONF_SESSION_COOKIE)
        if not cookie:
            # Entries created before session auth have no cookie; reauth collects one.
            raise ConfigEntryAuthFailed("No browser session stored")

        # Session clients need their own cookie jar; the shared HA client must
        # not carry one account's cookies for every entry.
        http_client = create_async_httpx_client(self.hass, auto_cleanup=False)
        user_agent = self._entry.data.get(CONF_USER_AGENT)
        if user_agent:
            http_client.headers["User-Agent"] = user_agent
        try:
            async with UWClient.from_session(cookie, http_client=http_client) as client:
                return await self._async_collect(client)
        finally:
            await http_client.aclose()

    def resource_available(self, *keys: str) -> bool:
        """Return True when none of the given resource keys last failed."""
        return not self.failed_resources.intersection(keys)

    async def _async_collect(self, client: Any) -> dict[str, Any]:
        data: dict[str, Any] = {}

        data["account"] = await client.gql.get_account()

        failed: set[str] = set()
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
                failed.add(key)

        self.failed_resources = failed
        if len(failed) == 6:
            # Nothing optional came back: report failure so the refresh is
            # retried and entities go unavailable instead of looking fresh.
            raise UpdateFailed("All Utility Warehouse data fetches failed")

        return data
