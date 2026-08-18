"""Regression tests for stable ESPHome entity contracts."""

from custom_components.passion_wave.const import (
    LIGHT_ENTITY_ORIGINAL_NAMES,
    LIGHT_LABEL_ORIGINAL_NAMES,
    MEDIA_ENTITY_ORIGINAL_NAME,
    MEDIA_LABEL_ORIGINAL_NAME,
    canonical_original_name,
    original_name_matches,
)


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
