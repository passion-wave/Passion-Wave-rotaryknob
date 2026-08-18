"""Regression tests for stable ESPHome entity contracts."""

from types import SimpleNamespace
from unittest.mock import patch

from custom_components.passion_wave.const import (
    LIGHT_ENTITY_ORIGINAL_NAMES,
    LIGHT_LABEL_ORIGINAL_NAMES,
    MEDIA_ENTITY_ORIGINAL_NAME,
    MEDIA_LABEL_ORIGINAL_NAME,
    canonical_original_name,
    original_name_matches,
)
from custom_components.passion_wave.entity import entity_by_original_name


class FakeStates:
    """Minimal state machine for registry resolution tests."""

    def __init__(self, states):
        self._states = states

    def get(self, entity_id):
        return self._states.get(entity_id)


def _registry_entity(entity_id, *, disabled_by=None):
    return SimpleNamespace(
        entity_id=entity_id,
        platform="esphome",
        config_entry_id="s3-entry",
        original_name="RotaryKnob Media Entity ID",
        disabled_by=disabled_by,
    )


def _state(value):
    return SimpleNamespace(state=value)


def test_s3_text_original_names_preserve_registry_casing() -> None:
    """Match existing ESPHome registry entries exactly, including case."""
    assert MEDIA_ENTITY_ORIGINAL_NAME == "Rotaryknob Media Entity ID"
    assert MEDIA_LABEL_ORIGINAL_NAME == "Rotaryknob Media Label"
    assert LIGHT_ENTITY_ORIGINAL_NAMES == tuple(
        f"Rotaryknob Light Slot {slot} Entity ID" for slot in range(1, 5)
    )
    assert LIGHT_LABEL_ORIGINAL_NAMES == tuple(
        f"Rotaryknob Light Slot {slot} Label" for slot in range(1, 5)
    )


def test_beta19_registry_casing_matches_the_historical_contract() -> None:
    current = "RotaryKnob Media Entity ID"

    assert canonical_original_name(current) == MEDIA_ENTITY_ORIGINAL_NAME
    assert original_name_matches(current, MEDIA_ENTITY_ORIGINAL_NAME)
    assert not original_name_matches(
        "Unrelated Media Entity ID", MEDIA_ENTITY_ORIGINAL_NAME
    )


def test_live_entity_wins_over_stale_ota_registry_duplicate() -> None:
    """A Beta.19 entity must win over its unavailable Beta.16 duplicate."""
    stale = _registry_entity("text.passion_wave_rotaryknob_media_entity_id")
    live = _registry_entity("text.marco_rotaryknob_media_entity_id")
    registry = SimpleNamespace(
        entities={stale.entity_id: stale, live.entity_id: live}
    )
    hass = SimpleNamespace(
        states=FakeStates(
            {
                stale.entity_id: _state("unavailable"),
                live.entity_id: _state("media_player.airport"),
            }
        )
    )

    with patch(
        "custom_components.passion_wave.entity.er.async_get",
        return_value=registry,
    ):
        resolved = entity_by_original_name(
            hass,
            "s3-entry",
            MEDIA_ENTITY_ORIGINAL_NAME,
        )

    assert resolved == live.entity_id


def test_enabled_entity_wins_when_duplicate_states_are_not_loaded() -> None:
    """Registry resolution stays deterministic before ESPHome publishes state."""
    disabled = _registry_entity("text.disabled", disabled_by="integration")
    enabled = _registry_entity("text.enabled")
    registry = SimpleNamespace(
        entities={disabled.entity_id: disabled, enabled.entity_id: enabled}
    )
    hass = SimpleNamespace(states=FakeStates({}))

    with patch(
        "custom_components.passion_wave.entity.er.async_get",
        return_value=registry,
    ):
        resolved = entity_by_original_name(
            hass,
            "s3-entry",
            MEDIA_ENTITY_ORIGINAL_NAME,
        )

    assert resolved == enabled.entity_id
