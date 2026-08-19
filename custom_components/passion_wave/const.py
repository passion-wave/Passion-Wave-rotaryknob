"""Constants for the PassionWave integration."""

from __future__ import annotations

DOMAIN = "passion_wave"
INTEGRATION_VERSION = "3.0.1-beta.2"

CONF_S3_HOST = "s3_host"
CONF_BRIDGE_HOST = "bridge_host"
CONF_BRIDGE_REGISTRATION_ENTITY = "bridge_registration_entity"
CONF_BRIDGE_REGISTRATION_UNIQUE_ID = "bridge_registration_unique_id"
CONF_S3_CONFIG_ENTRY_ID = "s3_config_entry_id"
CONF_MA_CONFIG_ENTRY_ID = "music_assistant_config_entry_id"
CONF_MEDIA_PLAYER = "media_player"
CONF_LIGHT_SLOT_1 = "light_slot_1"
CONF_LIGHT_SLOT_2 = "light_slot_2"
CONF_LIGHT_SLOT_3 = "light_slot_3"
CONF_LIGHT_SLOT_4 = "light_slot_4"
CONF_VISIBLE_PLAYLISTS = "visible_playlists"
CONF_VISIBLE_RADIOS = "visible_radios"
CONF_VISIBLE_PODCASTS = "visible_podcasts"

SERVICE_GET_LIBRARY = "get_library"
SERVICE_GET_PLAYLIST_TRACKS = "get_playlist_tracks"

BRIDGE_COMMAND_ORIGINAL_NAME = "PassionWave Command Envelope"
BRIDGE_RECEIVE_LIBRARY_ACTION = "passion_wave_receive_library"
BRIDGE_RECEIVE_FORECAST_ACTION = "passion_wave_receive_forecast"
BRIDGE_RECEIVE_LIGHT_CATALOG_ACTION = "passion_wave_receive_light_catalog"
BRIDGE_RECEIVE_LIGHT_STATE_ACTION = "passion_wave_receive_light_state"
BRIDGE_RECEIVE_RUNTIME_STATE_ACTION = "passion_wave_receive_runtime_state"
BRIDGE_COMPLETE_MEDIA_ACTION = "passion_wave_complete_media"
BRIDGE_RECEIVE_INTEGRATION_VERSION_ACTION = (
    "passion_wave_receive_integration_version"
)
COMMAND_PROTOCOL_VERSION = 1
MAX_COMMAND_STATE_LENGTH = 255
LATENCY_REQUEST_ENTITY = "input_button.passion_wave_latency_request"

ATTR_CONFIG_ENTRY_ID = "config_entry_id"
ATTR_MEDIA_TYPE = "media_type"
ATTR_OFFSET = "offset"
ATTR_LIMIT = "limit"
ATTR_PLAYLIST_ID = "playlist_id"

SUPPORTED_LIBRARY_TYPES = ("playlist", "radio", "podcast")
DEFAULT_PAGE_SIZE = 40
MAX_LIBRARY_PAGE_SIZE = 100
MAX_TRACK_PAGE_SIZE = 64
LIBRARY_SELECTION_LIMIT = 500
SHOW_ALL = "__all__"

LIBRARY_FILTER_KEYS = {
    "playlist": CONF_VISIBLE_PLAYLISTS,
    "radio": CONF_VISIBLE_RADIOS,
    "podcast": CONF_VISIBLE_PODCASTS,
}

LIGHT_SLOT_KEYS = (
    CONF_LIGHT_SLOT_1,
    CONF_LIGHT_SLOT_2,
    CONF_LIGHT_SLOT_3,
    CONF_LIGHT_SLOT_4,
)
LIGHT_PLACEHOLDER_PREFIX = "light.passion_wave_light_"


def is_configured_light_entity(value: object) -> bool:
    """Return whether a value names a real customer light target."""
    return (
        isinstance(value, str)
        and value.startswith("light.")
        and not value.startswith(LIGHT_PLACEHOLDER_PREFIX)
    )

BRIDGE_REGISTRATION_ORIGINAL_NAME = "PassionWave Integration Entry ID"
FIRMWARE_UPDATE_ORIGINAL_NAME = "Firmware"
FIRMWARE_UPDATE_STATUS_ORIGINAL_NAME = "Firmware Update Status"
MEDIA_ENTITY_ORIGINAL_NAME = "Rotaryknob Media Entity ID"
MEDIA_LABEL_ORIGINAL_NAME = "Rotaryknob Media Label"
LIGHT_ENTITY_ORIGINAL_NAMES = (
    "Rotaryknob Light Slot 1 Entity ID",
    "Rotaryknob Light Slot 2 Entity ID",
    "Rotaryknob Light Slot 3 Entity ID",
    "Rotaryknob Light Slot 4 Entity ID",
)
LIGHT_LABEL_ORIGINAL_NAMES = (
    "Rotaryknob Light Slot 1 Label",
    "Rotaryknob Light Slot 2 Label",
    "Rotaryknob Light Slot 3 Label",
    "Rotaryknob Light Slot 4 Label",
)


def canonical_original_name(original_name: str | None) -> str | None:
    """Normalize the historical Rotaryknob/RotaryKnob registry contract."""
    if original_name and original_name.startswith("RotaryKnob "):
        return f"Rotaryknob {original_name.removeprefix('RotaryKnob ')}"
    return original_name


def original_name_matches(actual: str | None, expected: str) -> bool:
    """Match one ESPHome original name across the Beta.16/Beta.19 casing."""
    return canonical_original_name(actual) == canonical_original_name(expected)

ESPHOME_API_PORT = 6053
S3_PROJECT_NAME = "passion-wave.rotaryknob-s3"
BRIDGE_PROJECT_NAME = "passion-wave.rotaryknob-bridge"
