"""Tests for the sole customer-facing dual-MCU firmware update."""

import asyncio
from types import SimpleNamespace

from custom_components.passion_wave.update import PassionWaveFirmwareUpdate


def _entity() -> PassionWaveFirmwareUpdate:
    entry = SimpleNamespace(
        unique_id="rotaryknob_20:6e:f1:00:00:01",
        entry_id="entry",
        title="PassionWave Rotaryknob",
    )
    entity = PassionWaveFirmwareUpdate(entry)
    entity._target_version = "3.0.0-beta.16"
    entity.async_write_ha_state = lambda: None

    async def save_job():
        return None

    async def transports():
        return None

    entity._save_job = save_job
    entity._wait_for_transports = transports
    entity._both_internal_actions_available = lambda: False
    entity._disable_legacy_sources = lambda: None
    return entity


def test_update_installs_bridge_before_s3():
    entity = _entity()
    calls = []

    async def install_endpoint(index, target):
        calls.append((index, target))

    entity._install_endpoint = install_endpoint
    asyncio.run(entity._async_run_job())

    assert calls == [
        (0, "3.0.0-beta.16"),
        (1, "3.0.0-beta.16"),
    ]
    assert entity._phase == "complete"
    assert entity._attr_update_percentage == 100


def test_bridge_failure_stops_before_s3():
    entity = _entity()
    calls = []

    async def install_endpoint(index, target):
        calls.append((index, target))
        if index == 0:
            raise RuntimeError("bridge failed")

    entity._install_endpoint = install_endpoint
    asyncio.run(entity._async_run_job())

    assert calls == [(0, "3.0.0-beta.16")]
    assert entity._phase == "failed"
    assert entity._last_error == "bridge failed"


def test_manifest_versions_must_match():
    entity = _entity()
    entity._manifest_versions = ("3.0.0-beta.16", "3.0.0-beta.15")
    assert entity.latest_version is None

    entity._manifest_versions = ("3.0.0-beta.16", "3.0.0-beta.16")
    assert entity.latest_version == "3.0.0-beta.16"


def test_mixed_pair_can_upgrade_but_not_downgrade_newer_processor():
    entity = _entity()
    entity._installed_versions = lambda: (
        "3.0.0-beta.15",
        "3.0.0-beta.16",
    )

    assert entity.version_is_newer("3.0.0-beta.16", "mixed")
    assert not entity.version_is_newer("3.0.0-beta.15", "mixed")
