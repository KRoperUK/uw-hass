"""Shared fixtures and helpers for the Utility Warehouse integration tests."""

from __future__ import annotations

from datetime import date, datetime
from types import SimpleNamespace
from typing import Any

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.utility_warehouse.const import DOMAIN

EMAIL = "user@example.com"
PASSWORD = "hunter2"
ACCOUNT_NUMBER = "A-12345"


def make_uw_data() -> dict[str, Any]:
    """Build a representative coordinator payload."""
    return {
        "account": SimpleNamespace(account_number=ACCOUNT_NUMBER),
        "balance": SimpleNamespace(amount_gbp=42.5),
        "tariff": SimpleNamespace(
            tariff_name="UW Flex",
            unit_rate_pence=24.5,
            standing_charge_pence=53.1,
        ),
        "consumption": SimpleNamespace(
            electricity_kwh=12.5,
            electricity_cost_gbp=3.75,
            gas_kwh=30.0,
            gas_cost_gbp=1.2,
        ),
        "meters": [
            SimpleNamespace(
                meter_type=SimpleNamespace(value="ELECTRICITY"),
                meter_number="E-1",
                last_reading_date=datetime(2026, 1, 2, 3, 4, 5),
                is_smart=True,
            ),
            SimpleNamespace(
                meter_type=SimpleNamespace(value="GAS"),
                meter_number="G-1",
                last_reading_date=datetime(2026, 1, 3, 3, 4, 5),
                is_smart=False,
            ),
        ],
        "readings": [],
        "bills": [
            SimpleNamespace(
                total_amount_gbp=88.75,
                bill_date=date(2026, 1, 5),
                status=SimpleNamespace(value="overdue"),
            )
        ],
    }


class FakeGql:
    """Stand-in for the ``uw_api`` GraphQL facade."""

    def __init__(self, data: dict[str, Any], fail_fields: set[str]) -> None:
        self._data = data
        self._fail = fail_fields

    async def _fetch(self, method: str, key: str) -> Any:
        if method in self._fail:
            raise RuntimeError(f"boom: {method}")
        return self._data.get(key)

    async def get_account(self) -> Any:
        return await self._fetch("get_account", "account")

    async def get_balance(self) -> Any:
        return await self._fetch("get_balance", "balance")

    async def get_tariff(self) -> Any:
        return await self._fetch("get_tariff", "tariff")

    async def get_consumption(self) -> Any:
        return await self._fetch("get_consumption", "consumption")

    async def get_meters(self) -> Any:
        return await self._fetch("get_meters", "meters")

    async def get_meter_readings(self) -> Any:
        return await self._fetch("get_meter_readings", "readings")

    async def get_bills(self) -> Any:
        return await self._fetch("get_bills", "bills")


class FakeUWClient:
    """Minimal async-context-manager double for ``uw_api.UWClient``."""

    def __init__(
        self,
        data: dict[str, Any] | None = None,
        fail_fields: set[str] | None = None,
        login_error: Exception | None = None,
    ) -> None:
        self._login_error = login_error
        self.gql = FakeGql(data if data is not None else make_uw_data(), fail_fields or set())

    async def __aenter__(self) -> FakeUWClient:
        return self

    async def __aexit__(self, *exc_info: object) -> bool:
        return False

    async def login(self) -> None:
        if self._login_error is not None:
            raise self._login_error


def fake_client_class(
    *,
    data: dict[str, Any] | None = None,
    fail_fields: set[str] | None = None,
    login_error: Exception | None = None,
) -> type[FakeUWClient]:
    """Return a ``UWClient`` replacement pre-configured for a test."""

    class _Client(FakeUWClient):
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            super().__init__(data=data, fail_fields=fail_fields, login_error=login_error)

    return _Client


@pytest.fixture
def mock_entry() -> MockConfigEntry:
    """Return a mock config entry."""
    return MockConfigEntry(
        domain=DOMAIN,
        data={"email": EMAIL, "password": PASSWORD},
        unique_id=EMAIL,
        title=f"UW - {EMAIL}",
    )


@pytest.fixture
def uw_data() -> dict[str, Any]:
    """Return a representative coordinator payload."""
    return make_uw_data()


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: Any) -> Any:
    """Enable loading of custom integrations for every test."""
    yield
