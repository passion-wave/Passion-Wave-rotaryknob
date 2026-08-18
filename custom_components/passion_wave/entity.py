"""Shared entity helpers for PassionWave."""

from __future__ import annotations

from collections import Counter
from typing import Any

from homeassistant import config_entries
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import Entity

from .const import DOMAIN, original_name_matches

type PassionWaveConfigEntry = config_entries.ConfigEntry[dict[str, Any]]


def entry_value(entry: PassionWaveConfigEntry, key: str) -> Any:
    """Read the latest value regardless of initial or options storage."""
    return entry.options.get(key, entry.data.get(key))


def device_info(entry: PassionWaveConfigEntry) -> DeviceInfo:
    """Attach every PassionWave entity to its logical physical device."""
    return DeviceInfo(
        identifiers={(DOMAIN, entry.unique_id or entry.entry_id)},
        manufacturer="PassionWave",
        model="RotaryKnob Dual MCU",
        name=entry.title,
    )


def entity_by_original_name(
    hass: HomeAssistant,
    config_entry_id: str,
    original_name: str,
) -> str | None:
    """Resolve one ESPHome entity by its stable firmware contract."""
    candidates = (
        registry_entry
        for registry_entry in er.async_get(hass).entities.values()
        if registry_entry.platform == "esphome"
        and registry_entry.config_entry_id == config_entry_id
        and original_name_matches(registry_entry.original_name, original_name)
    )
    resolved = max(
        candidates,
        key=lambda registry_entry: _entity_resolution_rank(hass, registry_entry),
        default=None,
    )
    return resolved.entity_id if resolved else None


def _entity_resolution_rank(
    hass: HomeAssistant,
    registry_entry: er.RegistryEntry,
) -> tuple[bool, bool, bool]:
    """Prefer the live entity when an OTA leaves a stale registry duplicate."""
    state = hass.states.get(registry_entry.entity_id)
    available = state is not None and state.state not in (
        STATE_UNAVAILABLE,
        STATE_UNKNOWN,
    )
    return (
        available,
        registry_entry.disabled_by is None,
        state is not None,
    )


def target_options(
    hass: HomeAssistant,
    *,
    domain: str,
    platform: str | None = None,
    include_unassigned: bool = False,
) -> dict[str, str]:
    """Return unique, readable option labels mapped to stable entity IDs."""
    registry_entries = [
        registry_entry
        for registry_entry in er.async_get(hass).entities.values()
        if registry_entry.domain == domain
        and registry_entry.disabled_by is None
        and (platform is None or registry_entry.platform == platform)
    ]
    base_labels: dict[str, str] = {}
    for registry_entry in registry_entries:
        state = hass.states.get(registry_entry.entity_id)
        friendly_name = state.attributes.get("friendly_name") if state else None
        base_labels[registry_entry.entity_id] = str(
            friendly_name
            or registry_entry.name
            or registry_entry.original_name
            or registry_entry.entity_id
        )

    counts = Counter(base_labels.values())
    options: dict[str, str] = {}
    if include_unassigned:
        unassigned = (
            "Nicht belegt" if hass.config.language.startswith("de") else "Not assigned"
        )
        options[unassigned] = ""
    for entity_id, label in sorted(
        base_labels.items(), key=lambda item: item[1].casefold()
    ):
        display_label = f"{label} · {entity_id}" if counts[label] > 1 else label
        options[display_label] = entity_id
    return options


class PassionWaveEntity(Entity):
    """Base entity attached to one logical PassionWave device."""

    _attr_has_entity_name = True

    def __init__(self, entry: PassionWaveConfigEntry, suffix: str) -> None:
        """Initialize stable entity identity and device ownership."""
        self._entry = entry
        stable_id = entry.unique_id or entry.entry_id
        self._attr_unique_id = f"{stable_id}_{suffix}"
        self._attr_device_info = device_info(entry)
