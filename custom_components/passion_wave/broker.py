"""Permission-free command broker between ESPHome and Home Assistant."""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from homeassistant.const import CONF_ENTITY_ID
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.util import slugify

from .const import (
    ATTR_CONFIG_ENTRY_ID,
    ATTR_LIMIT,
    ATTR_MEDIA_TYPE,
    ATTR_OFFSET,
    ATTR_PLAYLIST_ID,
    BRIDGE_COMMAND_ORIGINAL_NAME,
    BRIDGE_COMPLETE_MEDIA_ACTION,
    BRIDGE_RECEIVE_FORECAST_ACTION,
    BRIDGE_RECEIVE_LIBRARY_ACTION,
    BRIDGE_RECEIVE_LIGHT_CATALOG_ACTION,
    BRIDGE_RECEIVE_LIGHT_STATE_ACTION,
    BRIDGE_RECEIVE_RUNTIME_STATE_ACTION,
    COMMAND_PROTOCOL_VERSION,
    LATENCY_REQUEST_ENTITY,
    CONF_BRIDGE_REGISTRATION_ENTITY,
    CONF_MEDIA_PLAYER,
    INTEGRATION_VERSION,
    LIGHT_SLOT_KEYS,
    is_configured_light_entity,
    MAX_COMMAND_STATE_LENGTH,
    SERVICE_GET_LIBRARY,
    SERVICE_GET_PLAYLIST_TRACKS,
)
from .entity import PassionWaveConfigEntry, entry_value, entity_by_original_name
from .media import LatestPlaybackQueue, PlaybackCommand

_LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class _PlaybackCoordinator:
    """Runtime-only latest-command-wins state for one config entry."""

    queue: LatestPlaybackQueue = field(default_factory=LatestPlaybackQueue)
    mutation_lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    task: asyncio.Task[None] | None = None
    stopped: bool = False


_PLAYBACK_COORDINATORS: dict[str, _PlaybackCoordinator] = {}
_TRACK_CONFIRM_TIMEOUT_SECONDS = 10.0
_TRACK_CONFIRM_POLL_SECONDS = 0.1
_TRACK_CONFIRM_STABLE_SECONDS = 0.4

_ACTION_KIND_TO_SERVICE: dict[int, tuple[str, str]] = {
    1: ("media_player", "media_previous_track"),
    2: ("media_player", "media_play_pause"),
    3: ("media_player", "media_next_track"),
    4: ("media_player", "volume_set"),
    5: ("media_player", "shuffle_set"),
    6: ("media_player", "repeat_set"),
    10: ("light", "turn_off"),
    11: ("light", "turn_on"),
    12: ("light", "turn_on"),
    13: ("select", "select_option"),
    14: ("scene", "turn_on"),
}


def bridge_config_entry_id(hass: HomeAssistant, entry: PassionWaveConfigEntry) -> str:
    """Return the ESPHome config-entry ID owning the selected bridge."""
    registration = er.async_get(hass).async_get(
        entry_value(entry, CONF_BRIDGE_REGISTRATION_ENTITY)
    )
    if (
        registration is None
        or registration.platform != "esphome"
        or registration.config_entry_id is None
    ):
        raise HomeAssistantError("The selected PassionWave bridge is unavailable")
    return registration.config_entry_id


def command_entity_id(hass: HomeAssistant, entry: PassionWaveConfigEntry) -> str | None:
    """Resolve the bridge-owned command envelope entity."""
    return entity_by_original_name(
        hass,
        bridge_config_entry_id(hass, entry),
        BRIDGE_COMMAND_ORIGINAL_NAME,
    )


def _bridge_action_name(
    hass: HomeAssistant,
    entry: PassionWaveConfigEntry,
    action: str,
) -> str:
    bridge_entry = hass.config_entries.async_get_entry(
        bridge_config_entry_id(hass, entry)
    )
    if bridge_entry is None:
        raise HomeAssistantError("The selected PassionWave bridge is unavailable")
    device_name = bridge_entry.data.get("device_name")
    if not isinstance(device_name, str) or not device_name:
        raise HomeAssistantError("The ESPHome bridge has no stable device name")
    return f"{slugify(device_name)}_{action}"


async def _async_send_to_bridge(
    hass: HomeAssistant,
    entry: PassionWaveConfigEntry,
    action: str,
    data: dict[str, Any],
) -> None:
    service = _bridge_action_name(hass, entry, action)
    if not hass.services.has_service("esphome", service):
        raise HomeAssistantError(
            f"The bridge firmware action esphome.{service} is unavailable"
        )
    await hass.services.async_call("esphome", service, data, blocking=True)


def cancel_playback_coordinator(entry_id: str) -> None:
    """Cancel and remove one entry's transient playback worker."""
    coordinator = _PLAYBACK_COORDINATORS.pop(entry_id, None)
    if coordinator:
        coordinator.stopped = True
    if coordinator and coordinator.task and not coordinator.task.done():
        coordinator.task.cancel()


async def async_sync_light_states(
    hass: HomeAssistant,
    entry: PassionWaveConfigEntry,
    only_entity: str | None = None,
) -> None:
    """Push configured light state to the Bridge without compile-time targets."""
    for slot, key in enumerate(LIGHT_SLOT_KEYS):
        entity_id = entry_value(entry, key)
        if (
            not is_configured_light_entity(entity_id)
            or (only_entity is not None and entity_id != only_entity)
        ):
            continue
        state = hass.states.get(entity_id)
        brightness = state.attributes.get("brightness") if state else None
        try:
            brightness_pct = round(float(brightness) * 100 / 255)
        except (TypeError, ValueError):
            brightness_pct = 100 if state and state.state == "on" else 0
        await _async_send_to_bridge(
            hass,
            entry,
            BRIDGE_RECEIVE_LIGHT_STATE_ACTION,
            {
                "slot": slot,
                "is_on": bool(state and state.state == "on"),
                "brightness": min(max(brightness_pct, 0), 100),
            },
        )


def _percentage(value: Any, *, scale: float = 1.0, fallback: int = 0) -> int:
    """Return one bounded integral percentage."""
    try:
        return min(max(round(float(value) * scale), 0), 100)
    except (TypeError, ValueError):
        return fallback


async def async_sync_runtime_state(
    hass: HomeAssistant,
    entry: PassionWaveConfigEntry,
    session: int,
    sequence: int,
) -> None:
    """Push one ordered, complete media/light snapshot to the Bridge."""
    media = hass.states.get(entry_value(entry, CONF_MEDIA_PLAYER))
    attributes = media.attributes if media else {}
    state_code = {
        "idle": 1,
        "paused": 2,
        "playing": 3,
        "off": 4,
    }.get(media.state if media else "", 1)
    lights: list[dict[str, Any]] = []
    for key in LIGHT_SLOT_KEYS:
        entity_id = entry_value(entry, key)
        light = (
            hass.states.get(entity_id)
            if is_configured_light_entity(entity_id)
            else None
        )
        fallback = 100 if light and light.state == "on" else 0
        lights.append(
            {
                "on": bool(light and light.state == "on"),
                "brightness": _percentage(
                    light.attributes.get("brightness") if light else None,
                    scale=100 / 255,
                    fallback=fallback,
                ),
            }
        )
    payload = {
        "integration_version": INTEGRATION_VERSION,
        "state": state_code,
        "title": str(attributes.get("media_title") or "")[:120],
        "artist": str(
            attributes.get("media_artist")
            or attributes.get("media_album_artist")
            or ""
        )[:120],
        "friendly_name": str(attributes.get("friendly_name") or "")[:64],
        "volume": _percentage(attributes.get("volume_level"), scale=100),
        "position": max(0, round(float(attributes.get("media_position") or 0))),
        "duration": max(0, round(float(attributes.get("media_duration") or 0))),
        "shuffle": bool(attributes.get("shuffle")),
        "repeat_one": attributes.get("repeat") == "one",
        "cover_url": str(
            attributes.get("entity_picture")
            or attributes.get("entity_picture_local")
            or attributes.get("media_image_url")
            or ""
        )[:512],
        "lights": lights,
    }
    await _async_send_to_bridge(
        hass,
        entry,
        BRIDGE_RECEIVE_RUNTIME_STATE_ACTION,
        {
            "session": session,
            "sequence": sequence,
            # Keep non-ASCII metadata compact enough for the Bridge's bounded
            # 2048-byte action payload. ArduinoJson consumes UTF-8 directly.
            "payload": json.dumps(
                payload, ensure_ascii=False, separators=(",", ":")
            ),
        },
    )


def decode_command(state: str) -> dict[str, Any]:
    """Decode and validate one bounded firmware command envelope."""
    if not state or len(state) > MAX_COMMAND_STATE_LENGTH:
        raise ValueError("Command envelope has an invalid length")
    command = json.loads(state)
    if not isinstance(command, dict):
        raise ValueError("Command envelope must be an object")
    if command.get("v") != COMMAND_PROTOCOL_VERSION:
        raise ValueError("Unsupported command protocol")
    sequence = command.get("seq")
    command_type = command.get("type")
    if not isinstance(sequence, int) or sequence < 1:
        raise ValueError("Command sequence is invalid")
    if not isinstance(command_type, str) or not command_type:
        raise ValueError("Command type is invalid")
    return command


def _selected_lights(entry: PassionWaveConfigEntry) -> set[str]:
    return {
        value
        for key in LIGHT_SLOT_KEYS
        if is_configured_light_entity(
            (value := entry_value(entry, key))
        )
    }


def _validated_media_target(entry: PassionWaveConfigEntry) -> str:
    entity_id = entry_value(entry, CONF_MEDIA_PLAYER)
    if not isinstance(entity_id, str) or not entity_id.startswith("media_player."):
        raise HomeAssistantError("The configured media player is invalid")
    return entity_id


async def _async_execute_ha_action(
    hass: HomeAssistant,
    entry: PassionWaveConfigEntry,
    command: Mapping[str, Any],
) -> None:
    kind = int(command.get("kind", 0))
    value = int(command.get("value", 0))
    requested_entity = str(command.get("entity", ""))
    action = _ACTION_KIND_TO_SERVICE.get(kind)
    if action is None:
        raise HomeAssistantError(f"Unsupported PassionWave action kind: {kind}")

    domain, service = action
    data: dict[str, Any]
    if domain == "media_player":
        data = {CONF_ENTITY_ID: _validated_media_target(entry)}
        if kind == 4:
            data["volume_level"] = min(max(value, 0), 100) / 100
        elif kind == 5:
            data["shuffle"] = value != 0
        elif kind == 6:
            data["repeat"] = "one" if value else "off"
    elif domain == "light":
        if requested_entity not in _selected_lights(entry):
            raise HomeAssistantError("The requested light is not assigned to this knob")
        data = {CONF_ENTITY_ID: requested_entity}
        if kind in (11, 12):
            data["brightness_pct"] = min(max(value, 1), 100)
            data["transition"] = 0.15
    elif domain == "scene":
        allowed_scenes = {
            str(item["command"])
            for slot, light_entity in enumerate(_selected_lights(entry))
            for item in _light_catalog(hass, entry, slot, light_entity)["items"]
            if str(item["command"]).startswith("scene.")
        }
        if requested_entity not in allowed_scenes:
            raise HomeAssistantError("The requested scene is not assigned to this knob")
        data = {CONF_ENTITY_ID: requested_entity}
    else:
        option = str(command.get("option", ""))
        allowed = False
        for slot, key in enumerate(LIGHT_SLOT_KEYS):
            light_entity = entry_value(entry, key)
            if not is_configured_light_entity(light_entity):
                continue
            catalog = _light_catalog(hass, entry, slot, light_entity)
            if catalog["kind"] != "wled" or catalog["target"] != requested_entity:
                continue
            allowed = any(
                str(item["command"]) == option for item in catalog["items"]
            )
            break
        if not allowed:
            raise HomeAssistantError(
                "The requested preset is not assigned to this knob"
            )
        data = {
            CONF_ENTITY_ID: requested_entity,
            "option": option,
        }
    await hass.services.async_call(domain, service, data, blocking=False)


async def _async_execute_text_action(
    hass: HomeAssistant,
    entry: PassionWaveConfigEntry,
    command: Mapping[str, Any],
) -> None:
    if int(command.get("kind", 0)) != 15:
        raise HomeAssistantError("Unsupported PassionWave text action")
    entity_id = str(command.get("entity", ""))
    option = str(command.get("option", ""))
    allowed = False
    for slot, key in enumerate(LIGHT_SLOT_KEYS):
        light_entity = entry_value(entry, key)
        if not is_configured_light_entity(light_entity):
            continue
        catalog = _light_catalog(hass, entry, slot, light_entity)
        if catalog["kind"] != "wled" or catalog["target"] != entity_id:
            continue
        allowed = any(
            str(item["command"]) == option for item in catalog["items"]
        )
        break
    if not allowed:
        raise HomeAssistantError("Invalid PassionWave select command")
    await hass.services.async_call(
        "select",
        "select_option",
        {CONF_ENTITY_ID: entity_id, "option": option},
        blocking=False,
    )


async def _async_library_request(
    hass: HomeAssistant,
    entry: PassionWaveConfigEntry,
    command: Mapping[str, Any],
) -> None:
    kind = int(command.get("kind", 0))
    offset = max(0, int(command.get("offset", 0)))
    limit = max(1, int(command.get("limit", 1)))
    if kind in (1, 2, 3, 4):
        media_type = {1: "playlist", 2: "radio", 3: "podcast", 4: "playlist"}[kind]
        response = await hass.services.async_call(
            "passion_wave",
            SERVICE_GET_LIBRARY,
            {
                ATTR_CONFIG_ENTRY_ID: entry.entry_id,
                ATTR_MEDIA_TYPE: media_type,
                ATTR_OFFSET: offset,
                ATTR_LIMIT: limit,
            },
            blocking=True,
            return_response=True,
        )
    elif kind == 5:
        playlist_id = str(command.get("playlist_id", ""))
        if not playlist_id:
            raise HomeAssistantError("Playlist ID is missing")
        response = await hass.services.async_call(
            "passion_wave",
            SERVICE_GET_PLAYLIST_TRACKS,
            {
                ATTR_CONFIG_ENTRY_ID: entry.entry_id,
                ATTR_PLAYLIST_ID: playlist_id,
                ATTR_OFFSET: offset,
                ATTR_LIMIT: limit,
            },
            blocking=True,
            return_response=True,
        )
    else:
        raise HomeAssistantError("Unsupported library request")

    payload = dict(response or {})
    payload["request_id"] = str(command.get("request_id", ""))
    if kind == 5:
        payload["generation"] = int(command.get("context", 0))
    encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    await _async_send_to_bridge(
        hass,
        entry,
        BRIDGE_RECEIVE_LIBRARY_ACTION,
        {"kind": kind, "payload": encoded},
    )


async def _async_forecast_request(
    hass: HomeAssistant,
    entry: PassionWaveConfigEntry,
    command: Mapping[str, Any],
) -> None:
    weather_entity = str(command.get("entity", ""))
    if not weather_entity.startswith("weather."):
        raise HomeAssistantError("The requested weather entity is invalid")
    for period in ("daily", "hourly"):
        response = await hass.services.async_call(
            "weather",
            "get_forecasts",
            {CONF_ENTITY_ID: weather_entity, "type": period},
            blocking=True,
            return_response=True,
        )
        root = response or {}
        weather_data = (
            root.get(weather_entity, root) if isinstance(root, Mapping) else {}
        )
        forecasts = (
            weather_data.get("forecast", [])
            if isinstance(weather_data, Mapping)
            else []
        )
        maximum = 5 if period == "daily" else 48
        compact = {
            "forecast": [
                {
                    key: item[key]
                    for key in (
                        "datetime",
                        "condition",
                        "temperature",
                        "templow",
                        "precipitation",
                        "precipitation_probability",
                    )
                    if key in item
                }
                for item in list(forecasts)[:maximum]
                if isinstance(item, Mapping)
            ]
        }
        await _async_send_to_bridge(
            hass,
            entry,
            BRIDGE_RECEIVE_FORECAST_ACTION,
            {
                "period": period,
                "entity": weather_entity,
                "payload": json.dumps(
                    compact, ensure_ascii=False, separators=(",", ":")
                ),
            },
        )


def _light_catalog(
    hass: HomeAssistant,
    entry: PassionWaveConfigEntry,
    slot: int,
    light_entity: str,
) -> dict[str, Any]:
    if light_entity not in _selected_lights(entry):
        raise HomeAssistantError("The requested light is not assigned to this knob")
    registry = er.async_get(hass)
    light = registry.async_get(light_entity)
    if light is None:
        return {
            "entity_id": light_entity,
            "kind": "retry",
            "target": "",
            "selected": "",
            "items": [],
        }

    device_registry = dr.async_get(hass)
    if light.platform == "wled" and light.device_id:
        candidates = [
            candidate
            for candidate in registry.entities.values()
            if candidate.device_id == light.device_id
            and candidate.domain == "select"
            and "preset" in (candidate.original_name or candidate.entity_id).casefold()
        ]
        if candidates:
            target = candidates[0].entity_id
            state = hass.states.get(target)
            options = state.attributes.get("options", []) if state else []
            return {
                "entity_id": light_entity,
                "kind": "wled",
                "target": target,
                "selected": state.state if state else "",
                "items": [
                    {"label": str(option), "command": str(option)}
                    for option in list(options)[:32]
                ],
            }

    if light.platform == "hue":
        area_id = light.area_id
        if area_id is None and light.device_id:
            device = device_registry.async_get(light.device_id)
            area_id = device.area_id if device else None
        scenes = [
            candidate
            for candidate in registry.entities.values()
            if candidate.domain == "scene"
            and candidate.platform == "hue"
            and candidate.disabled_by is None
            and (
                candidate.area_id == area_id
                or (
                    candidate.device_id
                    and (device := device_registry.async_get(candidate.device_id))
                    and device.area_id == area_id
                )
            )
        ][:32]
        return {
            "entity_id": light_entity,
            "kind": "hue",
            "target": "",
            "selected": "",
            "items": [
                {
                    "label": (
                        (state := hass.states.get(scene.entity_id))
                        and state.attributes.get("friendly_name")
                    )
                    or scene.name
                    or scene.original_name
                    or scene.entity_id,
                    "command": scene.entity_id,
                }
                for scene in scenes
            ],
        }

    return {
        "entity_id": light_entity,
        "kind": "none",
        "target": "",
        "selected": "",
        "items": [],
    }


async def _async_light_catalog_request(
    hass: HomeAssistant,
    entry: PassionWaveConfigEntry,
    command: Mapping[str, Any],
) -> None:
    slot = int(command.get("slot", -1))
    if slot < 0 or slot >= len(LIGHT_SLOT_KEYS):
        raise HomeAssistantError("Invalid PassionWave light slot")
    # The Bridge firmware is shared by every customer and may still carry a
    # compile-time placeholder. The Config Entry is the authoritative mapping.
    light_entity = entry_value(entry, LIGHT_SLOT_KEYS[slot])
    if not is_configured_light_entity(light_entity):
        payload = {
            "entity_id": "",
            "kind": "none",
            "target": "",
            "selected": "",
            "items": [],
        }
    else:
        payload = _light_catalog(hass, entry, slot, light_entity)
    await _async_send_to_bridge(
        hass,
        entry,
        BRIDGE_RECEIVE_LIGHT_CATALOG_ACTION,
        {
            "slot": slot,
            "payload": json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
        },
    )


async def _async_complete_media(
    hass: HomeAssistant,
    entry: PassionWaveConfigEntry,
    command: PlaybackCommand,
    result: int,
) -> None:
    """Send a final result only for the generation still owned by the device."""
    await _async_send_to_bridge(
        hass,
        entry,
        BRIDGE_COMPLETE_MEDIA_ACTION,
        {"kind": command.kind, "index": command.index, "result": result},
    )


async def _async_wait_for_track(
    hass: HomeAssistant,
    entry: PassionWaveConfigEntry,
    coordinator: _PlaybackCoordinator,
    command: PlaybackCommand,
) -> tuple[bool, bool]:
    """Wait for the requested track or a superseding user command."""
    if command.kind != 5:
        return coordinator.queue.is_current(command.generation), True

    loop = asyncio.get_running_loop()
    deadline = loop.time() + _TRACK_CONFIRM_TIMEOUT_SECONDS
    stable_since: float | None = None
    observable = False
    target = _validated_media_target(entry)
    while loop.time() < deadline:
        if not coordinator.queue.is_current(command.generation):
            return False, False
        state = hass.states.get(target)
        current_media_id = str(
            state.attributes.get("media_content_id") if state else ""
        )
        observable = observable or bool(current_media_id)
        if current_media_id == command.media_id:
            if stable_since is None:
                stable_since = loop.time()
            elif loop.time() - stable_since >= _TRACK_CONFIRM_STABLE_SECONDS:
                return True, True
        else:
            stable_since = None
        await asyncio.sleep(_TRACK_CONFIRM_POLL_SECONDS)
    return coordinator.queue.is_current(command.generation), not observable


async def _async_execute_playback(
    hass: HomeAssistant,
    entry: PassionWaveConfigEntry,
    coordinator: _PlaybackCoordinator,
    command: PlaybackCommand,
) -> bool:
    """Replace the MA queue and confirm a track with one bounded retry."""
    for attempt in range(2):
        await hass.services.async_call(
            "music_assistant",
            "play_media",
            {
                CONF_ENTITY_ID: _validated_media_target(entry),
                "media_id": command.media_id,
                "media_type": command.media_type,
                "enqueue": "replace",
            },
            blocking=True,
        )
        current, confirmed = await _async_wait_for_track(
            hass, entry, coordinator, command
        )
        if not current:
            return False
        if confirmed:
            return True
        if attempt == 0:
            _LOGGER.warning(
                "PassionWave playback generation %s was not reflected by %s; retrying",
                command.generation,
                _validated_media_target(entry),
            )
    return False


async def _async_run_playback_coordinator(
    hass: HomeAssistant,
    entry: PassionWaveConfigEntry,
    coordinator: _PlaybackCoordinator,
) -> None:
    """Execute only the newest desired playback target until caught up."""
    handled_generation = 0
    try:
        while (
            command := coordinator.queue.latest_after(handled_generation)
        ) is not None:
            handled_generation = command.generation
            try:
                succeeded = await _async_execute_playback(
                    hass, entry, coordinator, command
                )
            except asyncio.CancelledError:
                raise
            except Exception as err:  # noqa: BLE001 - isolate external providers
                succeeded = False
                _LOGGER.warning(
                    "PassionWave playback generation %s failed: %s",
                    command.generation,
                    err,
                )

            async with coordinator.mutation_lock:
                if not coordinator.queue.is_current(command.generation):
                    continue
                await _async_complete_media(
                    hass, entry, command, 0 if succeeded else 5
                )
                coordinator.queue.complete(command.generation)
    finally:
        coordinator.task = None
        if (
            not coordinator.stopped
            and coordinator.queue.latest_after(handled_generation) is not None
        ):
            coordinator.task = hass.async_create_task(
                _async_run_playback_coordinator(hass, entry, coordinator),
                f"Run latest PassionWave playback for {entry.entry_id}",
            )


async def _async_play_media(
    hass: HomeAssistant,
    entry: PassionWaveConfigEntry,
    command: Mapping[str, Any],
) -> None:
    """Submit one validated playback target to the per-entry latest-wins worker."""
    kind = int(command.get("kind", 0))
    index = int(command.get("index", 0))
    media_id = str(command.get("uri", ""))
    media_type = str(command.get("media_type", ""))
    if not media_id or not media_type:
        raise HomeAssistantError("The requested media item is invalid")

    coordinator = _PLAYBACK_COORDINATORS.setdefault(
        entry.entry_id, _PlaybackCoordinator()
    )
    async with coordinator.mutation_lock:
        coordinator.queue.submit(
            kind=kind,
            index=index,
            media_id=media_id,
            media_type=media_type,
        )
        if coordinator.task is None or coordinator.task.done():
            coordinator.task = hass.async_create_task(
                _async_run_playback_coordinator(hass, entry, coordinator),
                f"Run latest PassionWave playback for {entry.entry_id}",
            )


async def async_handle_command(
    hass: HomeAssistant,
    entry: PassionWaveConfigEntry,
    state: str,
) -> None:
    """Validate and execute one command published by the selected bridge."""
    command = decode_command(state)
    command_type = command["type"]
    if command_type == "ha_action":
        await _async_execute_ha_action(hass, entry, command)
    elif command_type == "ha_text_action":
        if int(command.get("kind", 0)) == 13:
            await _async_execute_ha_action(hass, entry, command)
        else:
            await _async_execute_text_action(hass, entry, command)
    elif command_type == "library":
        await _async_library_request(hass, entry, command)
    elif command_type == "forecast":
        await _async_forecast_request(hass, entry, command)
    elif command_type == "light_catalog":
        await _async_light_catalog_request(hass, entry, command)
    elif command_type == "play_media":
        await _async_play_media(hass, entry, command)
    elif command_type == "latency_probe":
        entity_id = str(command.get("entity", ""))
        if entity_id == LATENCY_REQUEST_ENTITY:
            await hass.services.async_call(
                "input_button",
                "press",
                {CONF_ENTITY_ID: entity_id},
                blocking=False,
            )
        else:
            raise HomeAssistantError("The latency probe target is invalid")
    else:
        raise HomeAssistantError(f"Unsupported PassionWave command: {command_type}")
