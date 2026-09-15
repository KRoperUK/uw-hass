"""Tests for the small helper modules."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

from custom_components.utility_warehouse.device_helpers import build_uw_device_info
from custom_components.utility_warehouse.entity_platform_helpers import create_uw_entity_adder


def test_build_uw_device_info() -> None:
    """Device info carries the identifiers and account-derived model."""
    info = build_uw_device_info("A-12345", "uid-1")

    assert info["identifiers"] == {("utility_warehouse", "uid-1")}
    assert info["name"] == "Utility Warehouse"
    assert info["manufacturer"] == "Utility Warehouse"
    assert info["model"] == "Account A-12345"


class _FakeEntity:
    def __init__(self, coordinator: Any, entry: Any, **kwargs: Any) -> None:
        self.coordinator = coordinator
        self.entry = entry
        self.kwargs = kwargs


def test_create_uw_entity_adder_builds_and_registers_entities() -> None:
    """The adder constructs one entity per config and registers them."""
    added: list[_FakeEntity] = []
    coordinator = MagicMock()
    entry = MagicMock()

    create_uw_entity_adder(
        entry,
        added.extend,
        coordinator,
        _FakeEntity,
        [{"sensor_id": "a"}, {"sensor_id": "b"}],
    )

    assert [entity.kwargs["sensor_id"] for entity in added] == ["a", "b"]
    assert all(entity.coordinator is coordinator for entity in added)
    assert all(entity.entry is entry for entity in added)
