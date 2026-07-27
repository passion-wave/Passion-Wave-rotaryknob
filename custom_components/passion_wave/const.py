"""Constants for the PassionWave integration."""

from __future__ import annotations

DOMAIN = "passion_wave"

CONF_BRIDGE_REGISTRATION_ENTITY = "bridge_registration_entity"
CONF_BRIDGE_REGISTRATION_UNIQUE_ID = "bridge_registration_unique_id"
CONF_MA_CONFIG_ENTRY_ID = "music_assistant_config_entry_id"
CONF_MEDIA_PLAYER = "media_player"
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

BRIDGE_REGISTRATION_ORIGINAL_NAME = "PassionWave Integration Entry ID"
