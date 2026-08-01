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

    entity._async_install_source = install_source
    asyncio.run(entity.async_install("3.0.0-beta.11", False))

    assert calls == [
        ("update.bridge", "3.0.0-beta.11"),
        ("update.s3", "3.0.0-beta.11"),
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
    try:
        asyncio.run(entity.async_install("3.0.0-beta.11", False))
    except RuntimeError:
        pass
    else:
        raise AssertionError("Bridge failure did not propagate")

    assert calls == [("update.bridge", "3.0.0-beta.11")]
    assert entity._phase == "failed"
