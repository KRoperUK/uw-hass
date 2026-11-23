from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.redact import async_redact_data

from .coordinator import UWDataUpdateCoordinator

TO_REDACT = {
    "email",
    "password",
    "account_number",
    "session_cookie",
}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics with credentials and account identifiers removed."""
    coordinator: UWDataUpdateCoordinator | None = getattr(entry, "runtime_data", None)

    return {
        "entry": {
            "data": async_redact_data(dict(entry.data), TO_REDACT),
            "options": async_redact_data(dict(entry.options), TO_REDACT),
        },
        "coordinator": {
            "last_update_success": coordinator.last_update_success if coordinator else None,
            "resources": sorted(coordinator.data) if coordinator and coordinator.data else [],
        },
    }
