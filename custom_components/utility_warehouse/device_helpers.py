from __future__ import annotations

from homeassistant.helpers.entity import DeviceInfo


def build_uw_device_info(account_number: str, entry_unique_id: str) -> DeviceInfo:
    return DeviceInfo(
        identifiers={("utility_warehouse", entry_unique_id)},
        name="Utility Warehouse",
        manufacturer="Utility Warehouse",
        model=f"Account {account_number}",
    )
