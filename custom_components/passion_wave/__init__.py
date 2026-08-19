"""PassionWave Home Assistant integration."""

from __future__ import annotations

import asyncio
import json
import logging
import secrets
from datetime import timedelta
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import (
    CONF_ENTITY_ID,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
    Platform,
)
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
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.event import (
    async_call_later,
    async_track_state_change_event,
    async_track_time_interval,
)

from .broker import (
    async_handle_command,
    async_sync_light_states,
    async_sync_runtime_state,
    cancel_playback_coordinator,
    command_entity_id,
)
from .const import (
    ATTR_CONFIG_ENTRY_ID,
    ATTR_LIMIT,
    ATTR_MEDIA_TYPE,
    ATTR_OFFSET,
    ATTR_PLAYLIST_ID,
    BRIDGE_COMMAND_ORIGINAL_NAME,
    BRIDGE_REGISTRATION_ORIGINAL_NAME,
    CONF_BRIDGE_REGISTRATION_ENTITY,
    CONF_BRIDGE_REGISTRATION_UNIQUE_ID,
    CONF_MA_CONFIG_ENTRY_ID,
    CONF_MEDIA_PLAYER,
    CONF_S3_CONFIG_ENTRY_ID,
    DEFAULT_PAGE_SIZE,
    DOMAIN,
    FIRMWARE_UPDATE_ORIGINAL_NAME,
    INTEGRATION_VERSION,
    LIGHT_ENTITY_ORIGINAL_NAMES,
    LIGHT_LABEL_ORIGINAL_NAMES,
    LIGHT_SLOT_KEYS,
    is_configured_light_entity,
    LIBRARY_FILTER_KEYS,
    LIBRARY_SELECTION_LIMIT,
    MAX_LIBRARY_PAGE_SIZE,
    MAX_TRACK_PAGE_SIZE,
    MEDIA_ENTITY_ORIGINAL_NAME,
    MEDIA_LABEL_ORIGINAL_NAME,
    canonical_original_name,
    original_name_matches,
    SERVICE_GET_LIBRARY,
    SERVICE_GET_PLAYLIST_TRACKS,
    SHOW_ALL,
    SUPPORTED_LIBRARY_TYPES,
)
from .entity import entity_by_original_name
from .media import (
    bounded_page,
    filter_library_page,
    normalize_browse_page,
    normalize_library_page,
)

type PassionWaveConfigEntry = config_entries.ConfigEntry[dict[str, Any]]

PLATFORMS = (
    Platform.BINARY_SENSOR,
    Platform.SELECT,
    Platform.SENSOR,
    Platform.SWITCH,
    Platform.UPDATE,
)

MEDIA_PRESENTATION_SETTLE_SECONDS = 0.25
_LOGGER = logging.getLogger(__name__)
_RUNTIME_SYNC: dict[str, dict[str, Any]] = {}


def _hide_native_entities(
    hass: HomeAssistant, entry: PassionWaveConfigEntry
) -> None:
    """Hide both native processor surfaces behind the logical product."""
    registry = er.async_get(hass)
    bridge_registration = registry.async_get(
        _entry_value(entry, CONF_BRIDGE_REGISTRATION_ENTITY)
    )
    bridge_entry_id = (
        bridge_registration.config_entry_id if bridge_registration else None
    )
    s3_entry_id = _entry_value(entry, CONF_S3_CONFIG_ENTRY_ID)
    for registry_entry in list(registry.entities.values()):
        if (
            registry_entry.platform == "esphome"
            and registry_entry.config_entry_id in {s3_entry_id, bridge_entry_id}
            and registry_entry.hidden_by is None
        ):
            registry.async_update_entity(
                registry_entry.entity_id,
                hidden_by=er.RegistryEntryHider.INTEGRATION,
            )


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
    """Resolve every firmware-owned S3 target to its live registry entity."""
    s3_entry_id = _entry_value(entry, CONF_S3_CONFIG_ENTRY_ID)
    names = {
        MEDIA_ENTITY_ORIGINAL_NAME,
        MEDIA_LABEL_ORIGINAL_NAME,
        *LIGHT_ENTITY_ORIGINAL_NAMES,
        *LIGHT_LABEL_ORIGINAL_NAMES,
    }
    return {
        original_name: entity_id
        for original_name in names
        if (
            entity_id := entity_by_original_name(
                hass,
                s3_entry_id,
                original_name,
            )
        )
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


async def _async_sync_s3_targets(
    hass: HomeAssistant, entry: PassionWaveConfigEntry
) -> None:
    """Reconcile customer target IDs and labels once the S3 is reachable."""
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
        configured = _entry_value(entry, key)
        light_entity = configured if is_configured_light_entity(configured) else ""
        target_values[entity_original_name] = light_entity
        target_values[label_original_name] = _friendly_name(hass, light_entity)
    await _async_set_s3_text_values(hass, entry, target_values)


async def _async_sync_targets(
    hass: HomeAssistant, entry: PassionWaveConfigEntry
) -> None:
    """Apply every customer-facing target owned by one PassionWave entry."""
    try:
        await _async_sync_bridge(hass, entry)
        await async_sync_light_states(hass, entry)
    except HomeAssistantError as err:
        raise ConfigEntryNotReady(
            "Waiting for the PassionWave bridge command services"
        ) from err

    @callback
    def async_light_state_changed(
        event: Event[EventStateChangedData],
    ) -> None:
        """Push only the changed configured light through the local API."""
        hass.async_create_task(
            async_sync_light_states(hass, entry, event.data["entity_id"]),
            "Sync PassionWave light state",
        )
        hass.async_create_task(
            _async_push_runtime_snapshot(hass, entry),
            "Sync PassionWave runtime state",
        )

    configured_lights = [
        entity_id
        for key in LIGHT_SLOT_KEYS
        if is_configured_light_entity(
            (entity_id := _entry_value(entry, key))
        )
    ]
    if configured_lights:
        entry.async_on_unload(
            async_track_state_change_event(
                hass,
                configured_lights,
                async_light_state_changed,
            )
        )
    await _async_sync_s3_targets(hass, entry)


async def _async_push_runtime_snapshot(
    hass: HomeAssistant, entry: PassionWaveConfigEntry
) -> None:
    """Serialize complete runtime snapshots so their sequence stays ordered."""
    runtime = _RUNTIME_SYNC[entry.entry_id]
    async with runtime["lock"]:
        runtime["sequence"] += 1
        await async_sync_runtime_state(
            hass,
            entry,
            runtime["session"],
            runtime["sequence"],
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
    registry = er.async_get(hass)
    if entry.version < 2:
        candidates: dict[str, str] = {}
        for registry_entry in registry.entities.values():
            if (
                registry_entry.platform == "esphome"
                and registry_entry.config_entry_id
                and original_name_matches(
                    registry_entry.original_name, MEDIA_ENTITY_ORIGINAL_NAME
                )
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
                    and original_name_matches(
                        registry_entry.original_name, original_name
                    )
                ):
                    state = hass.states.get(registry_entry.entity_id)
                    if state is not None and state.state.startswith("light."):
                        value = state.state
                    break
            data[key] = value
        hass.config_entries.async_update_entry(entry, data=data, version=2)

    if entry.version < 3:
        s3_entry_id = _entry_value(entry, CONF_S3_CONFIG_ENTRY_ID)
        bridge_registration = registry.async_get(
            _entry_value(entry, CONF_BRIDGE_REGISTRATION_ENTITY)
        )
        bridge_entry_id = (
            bridge_registration.config_entry_id if bridge_registration else None
        )
        logical_disabled_suffixes = {
            "integration_version",
            "s3_connection",
            "bridge_connection",
            "playback_device",
            *(f"light_position_{index}" for index in range(1, 5)),
        }
        contract_names = {
            MEDIA_ENTITY_ORIGINAL_NAME,
            MEDIA_LABEL_ORIGINAL_NAME,
            *LIGHT_ENTITY_ORIGINAL_NAMES,
            *LIGHT_LABEL_ORIGINAL_NAMES,
        }
        for registry_entry in list(registry.entities.values()):
            disable = False
            hide = False
            if (
                registry_entry.platform == DOMAIN
                and registry_entry.config_entry_id == entry.entry_id
            ):
                disable = any(
                    registry_entry.unique_id.endswith(f"_{suffix}")
                    for suffix in logical_disabled_suffixes
                )
            elif (
                registry_entry.platform == "esphome"
                and registry_entry.config_entry_id in {s3_entry_id, bridge_entry_id}
            ):
                disable = (
                    registry_entry.entity_category == EntityCategory.DIAGNOSTIC
                    and registry_entry.original_name != BRIDGE_COMMAND_ORIGINAL_NAME
                )
                hide = (
                    canonical_original_name(registry_entry.original_name)
                    in contract_names
                    or registry_entry.original_name
                    in {
                        BRIDGE_REGISTRATION_ORIGINAL_NAME,
                        BRIDGE_COMMAND_ORIGINAL_NAME,
                        FIRMWARE_UPDATE_ORIGINAL_NAME,
                    }
                )
            changes: dict[str, Any] = {}
            if disable and registry_entry.disabled_by is None:
                changes["disabled_by"] = er.RegistryEntryDisabler.INTEGRATION
            if hide and registry_entry.hidden_by is None:
                changes["hidden_by"] = er.RegistryEntryHider.INTEGRATION
            if changes:
                registry.async_update_entity(registry_entry.entity_id, **changes)
        hass.config_entries.async_update_entry(entry, version=3)

    if entry.version < 4:
        _hide_native_entities(hass, entry)
        hass.config_entries.async_update_entry(entry, version=4)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: PassionWaveConfigEntry) -> bool:
    """Set up one physical PassionWave system."""
    _RUNTIME_SYNC[entry.entry_id] = {
        "session": secrets.randbelow(0x7FFFFFFE) + 1,
        "sequence": 0,
        "lock": asyncio.Lock(),
    }
    dr.async_get(hass).async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, entry.unique_id or entry.entry_id)},
        manufacturer="PassionWave",
        model="RotaryKnob Dual MCU",
        name="PassionWave RotaryKnob",
        sw_version=INTEGRATION_VERSION,
    )
    _hide_native_entities(hass, entry)
    try:
        await _async_sync_targets(hass, entry)
        await _async_push_runtime_snapshot(hass, entry)
        bridge_command_entity = command_entity_id(hass, entry)
        if bridge_command_entity is None:
            raise HomeAssistantError(
                "The bridge firmware does not expose the PassionWave command broker"
            )
    except HomeAssistantError as err:
        raise ConfigEntryNotReady(
            "Waiting for the selected PassionWave processors"
        ) from err

    last_command_state = ""

    @callback
    def async_bridge_command_changed(
        event: Event[EventStateChangedData],
    ) -> None:
        """Dispatch a new bounded command without granting ESPHome HA actions."""
        nonlocal last_command_state
        new_state = event.data["new_state"]
        if new_state is None:
            return
        if not new_state.state or new_state.state in (
            STATE_UNKNOWN,
            STATE_UNAVAILABLE,
        ):
            return
        try:
            command = json.loads(new_state.state)
            sequence = int(command.get("seq", 0))
        except (TypeError, ValueError, AttributeError):
            _LOGGER.warning("Ignoring malformed PassionWave command envelope")
            return
        if new_state.state == last_command_state:
            return
        # The firmware sequence deliberately resets after a bridge reboot.
        # State equality, not numeric ordering, suppresses duplicate delivery
        # without discarding the first post-reboot command.
        last_command_state = new_state.state

        async def dispatch() -> None:
            try:
                await async_handle_command(hass, entry, new_state.state)
            except Exception as err:  # noqa: BLE001 - isolate malformed device input
                _LOGGER.warning("PassionWave command %s failed: %s", sequence, err)

        hass.async_create_task(
            dispatch(),
            f"Dispatch PassionWave command {sequence}",
        )

    entry.async_on_unload(
        async_track_state_change_event(
            hass,
            [bridge_command_entity],
            async_bridge_command_changed,
        )
    )
    # Re-assert registration after the listener exists. On a cold setup the
    # first registration write can make the bridge request its bootstrap
    # catalogs before Home Assistant has attached the command listener.
    await _async_sync_bridge(hass, entry)

    @callback
    def async_media_state_changed(
        event: Event[EventStateChangedData],
    ) -> None:
        """Coalesce transitional player attributes into one complete snapshot."""
        runtime = _RUNTIME_SYNC[entry.entry_id]
        cancel_pending = runtime.get("cancel_media_sync")
        if cancel_pending is not None:
            cancel_pending()

        @callback
        def async_push_settled_snapshot(_now: Any) -> None:
            runtime["cancel_media_sync"] = None
            hass.async_create_task(
                _async_push_runtime_snapshot(hass, entry),
                "Sync settled PassionWave media presentation",
            )

        # Music Assistant/player platforms commonly emit state, title,
        # artist and artwork as a short series of state_changed events. Sending
        # every intermediate event made the previous title/cover visible again
        # during track transitions. Latest-wins settling keeps the UART
        # presentation complete while adding only a quarter-second latency.
        runtime["cancel_media_sync"] = async_call_later(
            hass,
            MEDIA_PRESENTATION_SETTLE_SECONDS,
            async_push_settled_snapshot,
        )

    entry.async_on_unload(
        async_track_state_change_event(
            hass,
            [_entry_value(entry, CONF_MEDIA_PLAYER)],
            async_media_state_changed,
        )
    )

    @callback
    def async_periodic_runtime_snapshot(_now: Any) -> None:
        """Reconcile the complete device state even without HA state events."""

        async def reconcile() -> None:
            try:
                # Reasserting a changed S3 media target intentionally clears
                # its old presentation cache. Always follow the target write
                # with the authoritative runtime snapshot so the visible title
                # cannot remain on the firmware fallback.
                await _async_sync_s3_targets(hass, entry)
                await _async_push_runtime_snapshot(hass, entry)
            except HomeAssistantError as err:
                _LOGGER.debug("PassionWave periodic reconciliation deferred: %s", err)

        hass.async_create_task(reconcile(), "Refresh PassionWave runtime snapshot")

    entry.async_on_unload(
        async_track_time_interval(
            hass,
            async_periodic_runtime_snapshot,
            timedelta(minutes=15),
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
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        cancel_playback_coordinator(entry.entry_id)
        runtime = _RUNTIME_SYNC.pop(entry.entry_id, None)
        if runtime is not None and runtime.get("cancel_media_sync") is not None:
            runtime["cancel_media_sync"]()
    return unloaded
