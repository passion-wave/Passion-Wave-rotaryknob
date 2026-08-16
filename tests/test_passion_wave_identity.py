"""Regression tests for one logical product identity per S3 endpoint."""

from types import SimpleNamespace

from custom_components.passion_wave.identity import (
    configured_product_unique_id,
    s3_product_unique_id,
)


class FakeConfigEntries:
    """Minimal config-entry manager for identity tests."""

    def __init__(self, entries):
        self._entries = {entry.entry_id: entry for entry in entries}

    def async_get_entry(self, entry_id):
        return self._entries.get(entry_id)


def _hass(*entries):
    return SimpleNamespace(config_entries=FakeConfigEntries(entries))


def test_product_identity_uses_selected_s3_mac_not_bridge_identity():
    """Manual onboarding must never fall back to the Bridge registration ID."""
    s3 = SimpleNamespace(
        entry_id="s3-timo",
        domain="esphome",
        unique_id="20:6E:F1:A1:3C:8C",
    )
    passion_wave = SimpleNamespace(
        data={"s3_config_entry_id": "s3-timo"},
        options={},
    )

    assert s3_product_unique_id(_hass(s3), "s3-timo") == (
        "rotaryknob_20:6e:f1:a1:3c:8c"
    )
    assert configured_product_unique_id(_hass(s3), passion_wave) == (
        "rotaryknob_20:6e:f1:a1:3c:8c"
    )


def test_product_identity_rejects_non_mac_esphome_unique_id():
    s3 = SimpleNamespace(
        entry_id="s3-invalid",
        domain="esphome",
        unique_id="bridge-registration-entity",
    )

    assert s3_product_unique_id(_hass(s3), "s3-invalid") is None


def test_product_identity_rejects_wrong_domain():
    entry = SimpleNamespace(
        entry_id="not-esphome",
        domain="mqtt",
        unique_id="20:6e:f1:a1:3c:8c",
    )

    assert s3_product_unique_id(_hass(entry), "not-esphome") is None
