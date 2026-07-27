"""PassionWave Home Assistant integration."""

from __future__ import annotations

import asyncio
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_ENTITY_ID, Platform
from homeassistant.core import (
    Event,
    EventStateChangedData,
    HomeAssistant,
    ServiceCall,
    ServiceResponse,
    SupportsResponse,
    callback,
)
from homeassistant.exceptions import ConfigEntryNotReady, HomeAssistantError
from homeassistant.helpers import device_registry as dr, entity_registry as er
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.event import async_track_state_change_event

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
    CONF_S3_CONFIG_ENTRY_ID,
    DEFAULT_PAGE_SIZE,
    DOMAIN,
    INTEGRATION_VERSION,
    LIGHT_ENTITY_ORIGINAL_NAMES,
    LIGHT_LABEL_ORIGINAL_NAMES,
    LIGHT_SLOT_KEYS,
    LIBRARY_FILTER_KEYS,
    LIBRARY_SELECTION_LIMIT,
    MAX_LIBRARY_PAGE_SIZE,
    MAX_TRACK_PAGE_SIZE,
    MEDIA_ENTITY_ORIGINAL_NAME,
    MEDIA_LABEL_ORIGINAL_NAME,
    MEDIA_RUNTIME_ARTIST_ORIGINAL_NAME,
    MEDIA_RUNTIME_COVER_URL_ORIGINAL_NAME,
    MEDIA_RUNTIME_STATE_ORIGINAL_NAME,
    MEDIA_RUNTIME_TITLE_ORIGINAL_NAME,
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

PLATFORMS = (Platform.BINARY_SENSOR, Platform.SELECT, Platform.SENSOR)

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


def _s3_text_entities(
    hass: HomeAssistant,
    entry: PassionWaveConfigEntry,
) -> dict[str, str]:
    """Resolve all firmware-owned S3 texts with one registry pass."""
    s3_entry_id = _entry_value(entry, CONF_S3_CONFIG_ENTRY_ID)
    return {
        registry_entry.original_name: registry_entry.entity_id
        for registry_entry in er.async_get(hass).entities.values()
        if registry_entry.platform == "esphome"
        and registry_entry.config_entry_id == s3_entry_id
        and registry_entry.original_name
    }


def _friendly_name(hass: HomeAssistant, entity_id: str) -> str:
    """Return the customer-visible Home Assistant entity name."""
    if not entity_id:
        return ""
    state = hass.states.get(entity_id)
    if state and (friendly_name := state.attributes.get("friendly_name")):
        return str(friendly_name)
    registry_entry = er.async_get(hass).async_get(entity_id)
    if registry_entry:
        return (
            registry_entry.name
            or registry_entry.original_name
            or registry_entry.entity_id
        )
    return entity_id


async def _async_set_s3_text_values(
    hass: HomeAssistant,
    entry: PassionWaveConfigEntry,
    values: dict[str, str],
) -> None:
    """Write changed values concurrently to firmware-owned S3 texts."""
    calls = []
    text_entities = _s3_text_entities(hass, entry)
    for original_name, value in values.items():
        if (entity_id := text_entities.get(original_name)) is None:
            raise HomeAssistantError(
                f"The selected PassionWave display is missing {original_name}"
            )
        current = hass.states.get(entity_id)
        if current is not None and current.state == value:
            continue
        calls.append(
            hass.services.async_call(
                "text",
                "set_value",
                {CONF_ENTITY_ID: entity_id, "value": value},
                blocking=True,
            )
        )
    if calls:
        await asyncio.gather(*calls)


async def _async_sync_media_runtime(
    hass: HomeAssistant, entry: PassionWaveConfigEntry
) -> None:
    """Mirror the selected player's current presentation state to the S3."""
    media_player = _entry_value(entry, CONF_MEDIA_PLAYER)
    state = hass.states.get(media_player)
    await _async_set_s3_text_values(
        hass,
        entry,
        {
            MEDIA_RUNTIME_STATE_ORIGINAL_NAME: (
                state.state[:32] if state else "unavailable"
            ),
            MEDIA_RUNTIME_TITLE_ORIGINAL_NAME: str(
                (state.attributes.get("media_title") or "") if state else ""
            )[:160],
            MEDIA_RUNTIME_ARTIST_ORIGINAL_NAME: str(
                (
                    state.attributes.get("media_artist")
                    or state.attributes.get("media_album_artist")
                    or ""
                )
                if state
                else ""
            )[:160],
            MEDIA_RUNTIME_COVER_URL_ORIGINAL_NAME: str(
                (
                    state.attributes.get("entity_picture")
                    or state.attributes.get("entity_picture_local")
                    or state.attributes.get("media_image_url")
                    or ""
                )
                if state
                else ""
            )[:255],
        },
    )


async def _async_sync_targets(
    hass: HomeAssistant, entry: PassionWaveConfigEntry
) -> None:
    """Apply every customer-facing target owned by one PassionWave entry."""
    await _async_sync_bridge(hass, entry)
    media_player = _entry_value(entry, CONF_MEDIA_PLAYER)
    target_values = {
        MEDIA_ENTITY_ORIGINAL_NAME: media_player,
        MEDIA_LABEL_ORIGINAL_NAME: _friendly_name(hass, media_player),
    }
    for key, entity_original_name, label_original_name in zip(
        LIGHT_SLOT_KEYS,
        LIGHT_ENTITY_ORIGINAL_NAMES,
        LIGHT_LABEL_ORIGINAL_NAMES,
        strict=True,
    ):
        light_entity = _entry_value(entry, key) or ""
        target_values[entity_original_name] = light_entity
        target_values[label_original_name] = _friendly_name(hass, light_entity)
    await _async_set_s3_text_values(hass, entry, target_values)
    await _async_sync_media_runtime(hass, entry)


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
            None if configured is None or SHOW_ALL in configured else tuple(configured)
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
            return filter_library_page(response, media_type, offset, limit, allowed)
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


async def async_migrate_entry(
    hass: HomeAssistant, entry: PassionWaveConfigEntry
) -> bool:
    """Adopt targets previously written by the retired blueprint."""
    if entry.version >= 2:
        return True

    registry = er.async_get(hass)
    candidates: dict[str, str] = {}
    for registry_entry in registry.entities.values():
        if (
            registry_entry.platform == "esphome"
            and registry_entry.config_entry_id
            and registry_entry.original_name == MEDIA_ENTITY_ORIGINAL_NAME
        ):
            candidates[registry_entry.config_entry_id] = registry_entry.entity_id

    selected_s3: str | None = None
    configured_player = _entry_value(entry, CONF_MEDIA_PLAYER)
    for config_entry_id, entity_id in candidates.items():
        state = hass.states.get(entity_id)
        if state is not None and state.state == configured_player:
            selected_s3 = config_entry_id
            break
    if selected_s3 is None and len(candidates) == 1:
        selected_s3 = next(iter(candidates))
    if selected_s3 is None:
        return False

    data = dict(entry.data)
    data[CONF_S3_CONFIG_ENTRY_ID] = selected_s3
    for key, original_name in zip(
        LIGHT_SLOT_KEYS, LIGHT_ENTITY_ORIGINAL_NAMES, strict=True
    ):
        value = ""
        for registry_entry in registry.entities.values():
            if (
                registry_entry.platform == "esphome"
                and registry_entry.config_entry_id == selected_s3
                and registry_entry.original_name == original_name
            ):
                state = hass.states.get(registry_entry.entity_id)
                if state is not None and state.state.startswith("light."):
                    value = state.state
                break
        data[key] = value

    hass.config_entries.async_update_entry(entry, data=data, version=2)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: PassionWaveConfigEntry) -> bool:
    """Set up one physical PassionWave system."""
    dr.async_get(hass).async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, entry.unique_id or entry.entry_id)},
        manufacturer="PassionWave",
        model="Rotaryknob Dual MCU",
        name="PassionWave Rotaryknob",
        sw_version=INTEGRATION_VERSION,
    )
    try:
        await _async_sync_targets(hass, entry)
    except HomeAssistantError as err:
        raise ConfigEntryNotReady(
            "Waiting for the selected PassionWave processors"
        ) from err

    @callback
    def async_media_state_changed(
        event: Event[EventStateChangedData],
    ) -> None:
        """Schedule a bounded media presentation update."""
        hass.async_create_task(
            _async_sync_media_runtime(hass, entry),
            "Sync PassionWave media presentation",
        )

    entry.async_on_unload(
        async_track_state_change_event(
            hass,
            [_entry_value(entry, CONF_MEDIA_PLAYER)],
            async_media_state_changed,
        )
    )

    @callback
    def async_entity_registry_updated(event: Event[dict[str, Any]]) -> None:
        """Keep renamed customer targets and their labels in sync."""
        old_entity_id = event.data.get("old_entity_id")
        entity_id = event.data.get("entity_id")
        configured_keys = (CONF_MEDIA_PLAYER, *LIGHT_SLOT_KEYS)
        if old_entity_id:
            changed_key = next(
                (
                    key
                    for key in configured_keys
                    if _entry_value(entry, key) == old_entity_id
                ),
                None,
            )
            if changed_key and entity_id:
                options = dict(entry.options)
                options[changed_key] = entity_id
                hass.config_entries.async_update_entry(entry, options=options)
                return
        if entity_id and any(
            _entry_value(entry, key) == entity_id for key in configured_keys
        ):
            hass.async_create_task(
                _async_sync_targets(hass, entry),
                "Refresh PassionWave target labels",
            )

    entry.async_on_unload(
        hass.bus.async_listen(
            er.EVENT_ENTITY_REGISTRY_UPDATED,
            async_entity_registry_updated,
        )
    )
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def _async_update_listener(
    hass: HomeAssistant, entry: PassionWaveConfigEntry
) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(
    hass: HomeAssistant, entry: PassionWaveConfigEntry
) -> bool:
    """Unload a PassionWave entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
