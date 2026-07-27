"""Constants for the PassionWave integration."""

from __future__ import annotations

DOMAIN = "passion_wave"

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

BRIDGE_REGISTRATION_ORIGINAL_NAME = "PassionWave Integration Entry ID"
MEDIA_ENTITY_ORIGINAL_NAME = "Rotaryknob Media Entity ID"
MEDIA_LABEL_ORIGINAL_NAME = "Rotaryknob Media Label"
MEDIA_RUNTIME_STATE_ORIGINAL_NAME = "Rotaryknob Media Runtime State"
MEDIA_RUNTIME_TITLE_ORIGINAL_NAME = "Rotaryknob Media Runtime Title"
MEDIA_RUNTIME_ARTIST_ORIGINAL_NAME = "Rotaryknob Media Runtime Artist"
MEDIA_RUNTIME_COVER_URL_ORIGINAL_NAME = "Rotaryknob Media Runtime Cover URL"
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

ESPHOME_API_PORT = 6053
S3_PROJECT_NAME = "passion-wave.rotaryknob-s3"
BRIDGE_PROJECT_NAME = "passion-wave.rotaryknob-bridge"
