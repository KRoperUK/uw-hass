from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import UWDataUpdateCoordinator


def create_uw_entity_adder(
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
    coordinator: UWDataUpdateCoordinator,
    entity_class: type,
    configs: list[dict[str, Any]],
) -> None:
    entities = [entity_class(coordinator, entry, **cfg) for cfg in configs]
    async_add_entities(entities)
