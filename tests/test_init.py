"""Tests for setting up and tearing down the integration."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from custom_components.utility_warehouse import async_setup_entry, async_unload_entry

COORDINATOR = "custom_components.utility_warehouse.UWDataUpdateCoordinator"


async def test_setup_entry_creates_coordinator_and_forwards_platforms(hass, mock_entry):
    """Setup builds a coordinator, stores it on the entry and forwards platforms."""
    forward = AsyncMock()

    with (
        patch(COORDINATOR) as coordinator_cls,
        patch.object(hass.config_entries, "async_forward_entry_setups", forward),
    ):
        coordinator_cls.return_value.async_config_entry_first_refresh = AsyncMock()

        assert await async_setup_entry(hass, mock_entry) is True

    coordinator_cls.assert_called_once_with(hass, mock_entry)
    coordinator_cls.return_value.async_config_entry_first_refresh.assert_awaited_once()
    forward.assert_awaited_once()
    assert mock_entry.runtime_data is coordinator_cls.return_value


async def test_unload_entry_forwards_to_platform_unload(hass, mock_entry):
    """Unload delegates to the platform unload helper."""
    mock_entry.runtime_data = None

    with patch.object(
        hass.config_entries, "async_unload_platforms", AsyncMock(return_value=True)
    ) as unload:
        assert await async_unload_entry(hass, mock_entry) is True

    unload.assert_awaited_once()
