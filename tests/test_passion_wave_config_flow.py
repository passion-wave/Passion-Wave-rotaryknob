"""Focused tests for the PassionWave customer target flow."""

from types import SimpleNamespace
from unittest.mock import patch

from custom_components.passion_wave.config_flow import (
    _connection_schema,
    _current_s3_light_defaults,
    _lights_schema,
)
from custom_components.passion_wave.const import (
    BRIDGE_REGISTRATION_ORIGINAL_NAME,
    CONF_BRIDGE_REGISTRATION_ENTITY,
    CONF_LIGHT_SLOT_1,
    CONF_LIGHT_SLOT_2,
    CONF_LIGHT_SLOT_3,
    CONF_LIGHT_SLOT_4,
    CONF_MA_CONFIG_ENTRY_ID,
    CONF_MEDIA_PLAYER,
    CONF_S3_CONFIG_ENTRY_ID,
    LIGHT_ENTITY_ORIGINAL_NAMES,
    MEDIA_ENTITY_ORIGINAL_NAME,
)


class FakeStates:
    """Small state-machine subset used by schema builders."""

    def __init__(self, states):
        self._states = states

    def get(self, entity_id):
        return self._states.get(entity_id)


class FakeConfigEntries:
    """Small config-entry manager subset used by schema builders."""

    def __init__(self, entries):
        self._entries = entries

    def async_entries(self, domain):
        return [entry for entry in self._entries if entry.domain == domain]

    def async_get_entry(self, entry_id):
        return next(
            (entry for entry in self._entries if entry.entry_id == entry_id),
            None,
        )


def _entity(
    entity_id,
    *,
    platform,
    original_name=None,
    config_entry_id=None,
    disabled_by=None,
):
    return SimpleNamespace(
        entity_id=entity_id,
        domain=entity_id.split(".", 1)[0],
        platform=platform,
        original_name=original_name,
        config_entry_id=config_entry_id,
        disabled_by=disabled_by,
        name=None,
    )


def _state(value, friendly_name=None):
    return SimpleNamespace(
        state=value,
        attributes=({"friendly_name": friendly_name} if friendly_name else {}),
    )


def test_connection_schema_exposes_all_customer_assignments():
    """Display, Bridge and Music Assistant choices remain visible."""
    entities = {
        "text.media": _entity(
            "text.media",
            platform="esphome",
            original_name=MEDIA_ENTITY_ORIGINAL_NAME,
            config_entry_id="s3-entry",
        ),
        "text.registration": _entity(
            "text.registration",
            platform="esphome",
            original_name=BRIDGE_REGISTRATION_ORIGINAL_NAME,
            config_entry_id="bridge-entry",
        ),
        "media_player.living_room": _entity(
            "media_player.living_room",
            platform="music_assistant",
            config_entry_id="ma-entry",
        ),
    }
    registry = SimpleNamespace(entities=entities)
    hass = SimpleNamespace(
        states=FakeStates(
            {
                "text.registration": _state("", "Rotaryknob Bridge registration"),
                "media_player.living_room": _state("idle", "Living room"),
            }
        ),
        config_entries=FakeConfigEntries(
            [
                SimpleNamespace(
                    entry_id="s3-entry",
                    domain="esphome",
                    title="PassionWave Rotaryknob",
                ),
                SimpleNamespace(
                    entry_id="ma-entry",
                    domain="music_assistant",
                    title="Music Assistant",
                ),
            ]
        ),
    )

    with patch(
        "custom_components.passion_wave.config_flow.er.async_get",
        return_value=registry,
    ):
        result = _connection_schema(hass)(
            {
                CONF_S3_CONFIG_ENTRY_ID: "s3-entry",
                CONF_BRIDGE_REGISTRATION_ENTITY: "text.registration",
                CONF_MA_CONFIG_ENTRY_ID: "ma-entry",
                CONF_MEDIA_PLAYER: "media_player.living_room",
            }
        )

    assert result[CONF_S3_CONFIG_ENTRY_ID] == "s3-entry"
    assert result[CONF_BRIDGE_REGISTRATION_ENTITY] == "text.registration"
    assert result[CONF_MA_CONFIG_ENTRY_ID] == "ma-entry"
    assert result[CONF_MEDIA_PLAYER] == "media_player.living_room"


def test_light_schema_supports_order_and_empty_positions():
    """Four ordered positions accept real lights and explicit empty slots."""
    light = _entity("light.vitrine", platform="hue")
    registry = SimpleNamespace(entities={light.entity_id: light})
    hass = SimpleNamespace(
        states=FakeStates({light.entity_id: _state("off", "Vitrine")})
    )

    with patch(
        "custom_components.passion_wave.config_flow.er.async_get",
        return_value=registry,
    ):
        result = _lights_schema(hass)(
            {
                CONF_LIGHT_SLOT_1: "light.vitrine",
                CONF_LIGHT_SLOT_2: "",
                CONF_LIGHT_SLOT_3: "",
                CONF_LIGHT_SLOT_4: "",
            }
        )

    assert result[CONF_LIGHT_SLOT_1] == "light.vitrine"
    assert result[CONF_LIGHT_SLOT_2] == ""


def test_existing_s3_light_targets_become_onboarding_defaults():
    """A retired blueprint's existing target values are adopted."""
    entities = {}
    states = {}
    for index, original_name in enumerate(LIGHT_ENTITY_ORIGINAL_NAMES, start=1):
        entity_id = f"text.light_slot_{index}"
        entities[entity_id] = _entity(
            entity_id,
            platform="esphome",
            original_name=original_name,
            config_entry_id="s3-entry",
        )
        states[entity_id] = _state(f"light.customer_{index}")
    registry = SimpleNamespace(entities=entities)
    hass = SimpleNamespace(states=FakeStates(states))

    with patch(
        "custom_components.passion_wave.config_flow.er.async_get",
        return_value=registry,
    ):
        defaults = _current_s3_light_defaults(hass, "s3-entry")

    assert defaults == {
        CONF_LIGHT_SLOT_1: "light.customer_1",
        CONF_LIGHT_SLOT_2: "light.customer_2",
        CONF_LIGHT_SLOT_3: "light.customer_3",
        CONF_LIGHT_SLOT_4: "light.customer_4",
    }
