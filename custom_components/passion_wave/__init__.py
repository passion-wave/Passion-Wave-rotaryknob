"""PassionWave Home Assistant integration."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_ENTITY_ID
from homeassistant.core import (
    HomeAssistant,
    ServiceCall,
    ServiceResponse,
    SupportsResponse,
)
from homeassistant.exceptions import ConfigEntryNotReady, HomeAssistantError
from homeassistant.helpers import device_registry as dr, entity_registry as er
import homeassistant.helpers.config_validation as cv

from .const import (
    ATTR_CONFIG_ENTRY_ID,
    ATTR_LIMIT,
    ATTR_MEDIA_TYPE,
    ATTR_OFFSET,
    ATTR_PLAYLIST_ID,
    CONF_BRIDGE_REGISTRATION_ENTITY,
    CONF_BRIDGE_REGISTRATION_UNIQUE_ID,
    CONF_MA_CONFIG_ENTRY_ID,
    CONF_MEDIA_PLAYER,
    DEFAULT_PAGE_SIZE,
    DOMAIN,
    LIBRARY_FILTER_KEYS,
    LIBRARY_SELECTION_LIMIT,
    MAX_LIBRARY_PAGE_SIZE,
    MAX_TRACK_PAGE_SIZE,
    SERVICE_GET_LIBRARY,
    SERVICE_GET_PLAYLIST_TRACKS,
    SHOW_ALL,
    SUPPORTED_LIBRARY_TYPES,
)
from .media import (
    bounded_page,
    filter_library_page,
    normalize_browse_page,
    normalize_library_page,
)

type PassionWaveConfigEntry = config_entries.ConfigEntry[dict[str, Any]]

_LIBRARY_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_CONFIG_ENTRY_ID): cv.string,
        vol.Required(ATTR_MEDIA_TYPE): vol.In(SUPPORTED_LIBRARY_TYPES),
        vol.Optional(ATTR_OFFSET, default=0): vol.Coerce(int),
        vol.Optional(ATTR_LIMIT, default=DEFAULT_PAGE_SIZE): vol.Coerce(int),
    }
)

_TRACK_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_CONFIG_ENTRY_ID): cv.string,
        vol.Required(ATTR_PLAYLIST_ID): cv.string,
        vol.Optional(ATTR_OFFSET, default=0): vol.Coerce(int),
        vol.Optional(ATTR_LIMIT, default=16): vol.Coerce(int),
    }
)


def _entry_value(entry: PassionWaveConfigEntry, key: str) -> Any:
    return entry.options.get(key, entry.data.get(key))


def _get_loaded_entry(hass: HomeAssistant, entry_id: str) -> PassionWaveConfigEntry:
    entry = hass.config_entries.async_get_entry(entry_id)
    if entry is None or entry.domain != DOMAIN:
        raise HomeAssistantError("Unknown PassionWave configuration entry")
    return entry


async def _async_sync_bridge(
    hass: HomeAssistant, entry: PassionWaveConfigEntry
) -> None:
    """Write this stable config-entry ID to the selected ESPHome bridge."""
    registry = er.async_get(hass)
    unique_id = _entry_value(entry, CONF_BRIDGE_REGISTRATION_UNIQUE_ID)
    entity_id = registry.async_get_entity_id("text", "esphome", unique_id)
    if entity_id is None:
        configured_entity = _entry_value(entry, CONF_BRIDGE_REGISTRATION_ENTITY)
        registry_entry = registry.async_get(configured_entity)
        entity_id = registry_entry.entity_id if registry_entry else None
    if entity_id is None:
        raise HomeAssistantError("The PassionWave bridge is not available")

    await hass.services.async_call(
        "text",
        "set_value",
        {CONF_ENTITY_ID: entity_id, "value": entry.entry_id},
        blocking=True,
    )


async def async_setup(hass: HomeAssistant, config: dict[str, Any]) -> bool:
    """Register the bounded PassionWave service API."""

    async def async_get_library(call: ServiceCall) -> ServiceResponse:
        entry = _get_loaded_entry(hass, call.data[ATTR_CONFIG_ENTRY_ID])
        media_type = call.data[ATTR_MEDIA_TYPE]
        offset, limit = bounded_page(
            call.data[ATTR_OFFSET], call.data[ATTR_LIMIT], MAX_LIBRARY_PAGE_SIZE
        )
        configured = _entry_value(entry, LIBRARY_FILTER_KEYS[media_type])
        if isinstance(configured, str):
            configured = [configured]
        allowed = (
            None
            if configured is None or SHOW_ALL in configured
            else tuple(configured)
        )
        if allowed == ():
            return {
                "offset": offset,
                "limit": limit,
                "returned": 0,
                "total": 0,
                "has_more": False,
                "items": [],
            }
        response = await hass.services.async_call(
            "music_assistant",
            "get_library",
            {
                "config_entry_id": _entry_value(entry, CONF_MA_CONFIG_ENTRY_ID),
                "media_type": media_type,
                "offset": 0 if allowed is not None else offset,
                "limit": LIBRARY_SELECTION_LIMIT if allowed is not None else limit,
            },
            blocking=True,
            return_response=True,
        )
        if allowed is not None:
            return filter_library_page(
                response, media_type, offset, limit, allowed
            )
        return normalize_library_page(response, media_type, offset, limit)

    async def async_get_playlist_tracks(call: ServiceCall) -> ServiceResponse:
        entry = _get_loaded_entry(hass, call.data[ATTR_CONFIG_ENTRY_ID])
        entity_id = _entry_value(entry, CONF_MEDIA_PLAYER)
        offset, limit = bounded_page(
            call.data[ATTR_OFFSET], call.data[ATTR_LIMIT], MAX_TRACK_PAGE_SIZE
        )
        response = await hass.services.async_call(
            "media_player",
            "browse_media",
            {
                "entity_id": entity_id,
                "media_content_type": "playlist",
                "media_content_id": call.data[ATTR_PLAYLIST_ID],
            },
            blocking=True,
            return_response=True,
        )
        return normalize_browse_page(response, entity_id, offset, limit)

    hass.services.async_register(
        DOMAIN,
        SERVICE_GET_LIBRARY,
        async_get_library,
        schema=_LIBRARY_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_GET_PLAYLIST_TRACKS,
        async_get_playlist_tracks,
        schema=_TRACK_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )
    return True


async def async_setup_entry(
    hass: HomeAssistant, entry: PassionWaveConfigEntry
) -> bool:
    """Set up one physical PassionWave system."""
    dr.async_get(hass).async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, entry.unique_id or entry.entry_id)},
        manufacturer="PassionWave",
        model="Rotaryknob Dual MCU",
        name="PassionWave Rotaryknob",
        sw_version="3.0.0-beta.0",
    )
    try:
        await _async_sync_bridge(hass, entry)
    except HomeAssistantError as err:
        raise ConfigEntryNotReady(
            "Waiting for the selected ESPHome bridge"
        ) from err
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def _async_update_listener(
    hass: HomeAssistant, entry: PassionWaveConfigEntry
) -> None:
    await _async_sync_bridge(hass, entry)


async def async_unload_entry(
    hass: HomeAssistant, entry: PassionWaveConfigEntry
) -> bool:
    """Unload a PassionWave entry."""
    return True
