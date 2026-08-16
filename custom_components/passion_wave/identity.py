"""Stable product identity derived from the selected S3 endpoint."""

from __future__ import annotations

import re

from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr

from .const import CONF_S3_CONFIG_ENTRY_ID

_NORMALIZED_MAC = re.compile(r"^[0-9a-f]{2}(?::[0-9a-f]{2}){5}$")


def entry_value(entry, key: str):
    """Read config data while respecting options-flow overrides."""
    return entry.options.get(key, entry.data.get(key))


def s3_product_unique_id(
    hass: HomeAssistant,
    s3_config_entry_id: str,
) -> str | None:
    """Return the logical product ID owned by one ESPHome S3 endpoint."""
    s3_entry = hass.config_entries.async_get_entry(s3_config_entry_id)
    if s3_entry is None or s3_entry.domain != "esphome":
        return None
    raw_unique_id = s3_entry.unique_id
    if not isinstance(raw_unique_id, str) or not raw_unique_id.strip():
        return None
    normalized = dr.format_mac(raw_unique_id)
    if not _NORMALIZED_MAC.fullmatch(normalized):
        return None
    return f"rotaryknob_{normalized}"


def configured_product_unique_id(hass: HomeAssistant, entry) -> str | None:
    """Return the product ID for the S3 selected by a PassionWave entry."""
    s3_entry_id = entry_value(entry, CONF_S3_CONFIG_ENTRY_ID)
    if not isinstance(s3_entry_id, str) or not s3_entry_id:
        return None
    return s3_product_unique_id(hass, s3_entry_id)
