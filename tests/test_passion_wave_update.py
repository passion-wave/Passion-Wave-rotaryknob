"""Tests for the customer-facing dual-MCU firmware update."""

import asyncio
from types import SimpleNamespace

from custom_components.passion_wave.update import PassionWaveFirmwareUpdate


def _entity() -> PassionWaveFirmwareUpdate:
    entry = SimpleNamespace(
        unique_id="device",
        entry_id="entry",
        title="PassionWave Rotaryknob",
    )
    entity = PassionWaveFirmwareUpdate(entry, "update.bridge", "update.s3")
    entity.async_write_ha_state = lambda: None
    return entity


def test_update_installs_bridge_before_s3():
    """The safe sequence must never start with the display processor."""
    entity = _entity()
    calls = []

    async def install_source(entity_id, target):
        calls.append((entity_id, target))

    async def reload_bridge():
        calls.append(("reload", None))

    entity._async_install_source = install_source
    entity._async_reload_bridge_entry = reload_bridge
    asyncio.run(entity.async_install("3.0.0-beta.12", False))

    assert calls == [
        ("update.bridge", "3.0.0-beta.12"),
        ("reload", None),
        ("update.s3", "3.0.0-beta.12"),
    ]
    assert entity._phase == "complete"


def test_bridge_failure_stops_before_s3():
    """A failed Bridge verification must preserve the untouched S3."""
    entity = _entity()
    calls = []

    async def fail_bridge(entity_id, target):
        calls.append((entity_id, target))
        raise RuntimeError("bridge failed")

    entity._async_install_source = fail_bridge
    entity._async_reload_bridge_entry = lambda: None
    try:
        asyncio.run(entity.async_install("3.0.0-beta.12", False))
    except RuntimeError:
        pass
    else:
        raise AssertionError("Bridge failure did not propagate")

    assert calls == [("update.bridge", "3.0.0-beta.12")]
    assert entity._phase == "failed"


def test_bridge_reload_failure_stops_before_s3():
    """The S3 must stay untouched until refreshed Bridge actions are ready."""
    entity = _entity()
    calls = []

    async def install_source(entity_id, target):
        calls.append((entity_id, target))

    async def fail_reload():
        calls.append(("reload", None))
        raise RuntimeError("bridge actions unavailable")

    entity._async_install_source = install_source
    entity._async_reload_bridge_entry = fail_reload
    try:
        asyncio.run(entity.async_install("3.0.0-beta.12", False))
    except RuntimeError:
        pass
    else:
        raise AssertionError("Bridge reload failure did not propagate")

    assert calls == [
        ("update.bridge", "3.0.0-beta.12"),
        ("reload", None),
    ]
    assert entity._phase == "failed"


def test_older_release_source_never_offers_downgrade():
    entity = _entity()
    entity._versions = lambda attribute: (
        ("3.0.0-beta.14", "3.0.0-beta.14")
        if attribute == "installed_version"
        else ("3.0.0-beta.12", "3.0.0-beta.12")
    )

    assert entity.latest_version == "3.0.0-beta.14"
    assert not entity.version_is_newer("3.0.0-beta.12", "3.0.0-beta.14")


def test_mixed_pair_can_upgrade_but_not_downgrade_newer_processor():
    entity = _entity()
    entity._versions = lambda _attribute: (
        "3.0.0-beta.12",
        "3.0.0-beta.14",
    )

    assert entity.version_is_newer("3.0.0-beta.14", "mixed")
    assert not entity.version_is_newer("3.0.0-beta.12", "mixed")
