"""Tests for the sole customer-facing dual-MCU firmware update."""

import asyncio
from types import SimpleNamespace

import pytest

from homeassistant.exceptions import HomeAssistantError

import custom_components.passion_wave.update as update_module
from custom_components.passion_wave.update import PassionWaveFirmwareUpdate


def _entity() -> PassionWaveFirmwareUpdate:
    entry = SimpleNamespace(
        unique_id="rotaryknob_20:6e:f1:00:00:01",
        entry_id="entry",
        title="PassionWave RotaryKnob",
    )
    entity = PassionWaveFirmwareUpdate(entry)
    entity._target_version = "3.0.0-beta.17"
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
        (0, "3.0.0-beta.17"),
        (1, "3.0.0-beta.17"),
    ]
    assert entity._phase == "complete"
    assert entity._attr_update_percentage == 100


def test_bridge_failure_stops_before_s3():
    entity = _entity()
    calls = []
    entity._installed_versions = lambda: (
        "3.0.0-beta.15",
        "3.0.0-beta.15",
    )

    async def install_endpoint(index, target):
        calls.append((index, target))
        if index == 0:
            raise RuntimeError("bridge failed")

    entity._install_endpoint = install_endpoint
    asyncio.run(entity._async_run_job())

    assert calls == [(0, "3.0.0-beta.17")]
    assert entity._phase == "failed"
    assert entity._last_error == "bridge failed"


def test_failed_job_reconciles_when_both_processors_reached_target():
    entity = _entity()
    entity._installed_versions = lambda: (
        "3.0.0-beta.17",
        "3.0.0-beta.17",
    )
    entity._both_internal_actions_available = lambda: True
    disabled = []
    entity._disable_legacy_sources = lambda: disabled.append(True)

    assert entity._reconcile_completed_target()
    assert entity._phase == "complete"
    assert entity._target_version is None
    assert entity._last_error is None
    assert not entity._attr_in_progress
    assert entity._attr_update_percentage == 100
    assert disabled == [True]


def test_failed_job_does_not_reconcile_a_mixed_pair():
    entity = _entity()
    entity._installed_versions = lambda: (
        "3.0.0-beta.17",
        "3.0.0-beta.15",
    )

    assert not entity._reconcile_completed_target()
    assert entity._target_version == "3.0.0-beta.17"


def test_manifest_versions_must_match():
    entity = _entity()
    entity._manifest_versions = ("3.0.0-beta.17", "3.0.0-beta.15")
    assert entity.latest_version is None

    entity._manifest_versions = ("3.0.0-beta.17", "3.0.0-beta.17")
    assert entity.latest_version == "3.0.0-beta.17"


def test_mixed_pair_can_upgrade_but_not_downgrade_newer_processor():
    entity = _entity()
    entity._installed_versions = lambda: (
        "3.0.0-beta.15",
        "3.0.0-beta.17",
    )

    assert entity.version_is_newer("3.0.0-beta.17", "mixed")
    assert not entity.version_is_newer("3.0.0-beta.15", "mixed")


def test_legacy_transport_is_refreshed_before_install():
    entity = _entity()
    state = SimpleNamespace(
        state="off", attributes={"latest_version": "3.0.0-beta.15"}
    )
    calls = []

    class Services:
        async def async_call(self, domain, service, data, *, blocking):
            calls.append((domain, service, data, blocking))
            state.attributes["latest_version"] = "3.0.0-beta.17"

    entity.hass = SimpleNamespace(
        services=Services(), states=SimpleNamespace(get=lambda entity_id: state)
    )

    asyncio.run(
        entity._refresh_legacy_source(
            "update.bridge_firmware", "3.0.0-beta.17"
        )
    )

    assert calls == [
        (
            "homeassistant",
            "update_entity",
            {"entity_id": "update.bridge_firmware"},
            True,
        )
    ]


def test_legacy_transport_rejects_stale_manifest(monkeypatch):
    entity = _entity()
    state = SimpleNamespace(
        state="off", attributes={"latest_version": "3.0.0-beta.15"}
    )

    class Services:
        async def async_call(self, domain, service, data, *, blocking):
            return None

    async def no_wait(_seconds):
        return None

    monkeypatch.setattr(asyncio, "sleep", no_wait)
    entity.hass = SimpleNamespace(
        services=Services(), states=SimpleNamespace(get=lambda entity_id: state)
    )

    with pytest.raises(
        HomeAssistantError,
        match=(
            "update.bridge_firmware advertises 3.0.0-beta.15 "
            "instead of 3.0.0-beta.17"
        ),
    ):
        asyncio.run(
            entity._refresh_legacy_source(
                "update.bridge_firmware", "3.0.0-beta.17"
            )
        )


def test_legacy_endpoint_refreshes_before_install(monkeypatch):
    entity = _entity()
    calls = []

    class Services:
        async def async_call(self, domain, service, data, *, blocking):
            calls.append((domain, service, data["entity_id"]))

        def has_service(self, domain, service):
            return False

    class ConfigEntries:
        async def async_reload(self, entry_id):
            calls.append(("reload", entry_id))

    async def refresh(entity_id, target):
        calls.append(("refresh", entity_id, target))

    async def wait_for_version(entry_id, target):
        calls.append(("verify", entry_id, target))

    entity.hass = SimpleNamespace(
        services=Services(), config_entries=ConfigEntries()
    )
    entity._device_version = lambda entry_id: "3.0.0-beta.15"
    entity._service_name = lambda entry_id, action=None: None
    entity._legacy_source_available = lambda entity_id: True
    entity._refresh_legacy_source = refresh
    entity._wait_for_version = wait_for_version
    monkeypatch.setattr(
        update_module,
        "_endpoint_entry_ids",
        lambda hass, entry: ("bridge_entry", "s3_entry"),
    )
    monkeypatch.setattr(
        update_module,
        "_legacy_update_entities",
        lambda hass, entry: ("update.bridge_firmware", "update.s3_firmware"),
    )

    asyncio.run(entity._install_endpoint(0, "3.0.0-beta.17"))

    assert calls == [
        ("refresh", "update.bridge_firmware", "3.0.0-beta.17"),
        ("update", "install", "update.bridge_firmware"),
        ("verify", "bridge_entry", "3.0.0-beta.17"),
        ("reload", "bridge_entry"),
    ]


def test_legacy_endpoint_verifies_an_install_already_in_progress(monkeypatch):
    entity = _entity()
    calls = []

    class Services:
        async def async_call(self, domain, service, data, *, blocking):
            calls.append((domain, service, data["entity_id"]))
            raise HomeAssistantError(
                "Update installation already in progress for update.s3_firmware"
            )

        def has_service(self, domain, service):
            return False

    async def refresh(entity_id, target):
        calls.append(("refresh", entity_id, target))

    async def wait_for_version(entry_id, target):
        calls.append(("verify", entry_id, target))

    entity.hass = SimpleNamespace(services=Services())
    entity._device_version = lambda entry_id: "3.0.0-beta.15"
    entity._service_name = lambda entry_id, action=None: None
    entity._legacy_source_available = lambda entity_id: True
    entity._refresh_legacy_source = refresh
    entity._wait_for_version = wait_for_version
    monkeypatch.setattr(
        update_module,
        "_endpoint_entry_ids",
        lambda hass, entry: ("bridge_entry", "s3_entry"),
    )
    monkeypatch.setattr(
        update_module,
        "_legacy_update_entities",
        lambda hass, entry: ("update.bridge_firmware", "update.s3_firmware"),
    )

    asyncio.run(entity._install_endpoint(1, "3.0.0-beta.17"))

    assert calls == [
        ("refresh", "update.s3_firmware", "3.0.0-beta.17"),
        ("update", "install", "update.s3_firmware"),
        ("verify", "s3_entry", "3.0.0-beta.17"),
    ]


def test_bridge_version_sync_retries_a_disconnected_action(monkeypatch):
    entity = _entity()
    calls = []

    class Services:
        def has_service(self, domain, service):
            return True

        async def async_call(self, domain, service, data, *, blocking):
            calls.append((domain, service, data, blocking))
            if len(calls) == 1:
                raise HomeAssistantError("Bridge is not connected")

    async def no_wait(seconds):
        calls.append(("sleep", seconds))

    entity.hass = SimpleNamespace(services=Services())
    entity._service_name = lambda entry_id, action=None: "bridge_version"
    monkeypatch.setattr(asyncio, "sleep", no_wait)

    asyncio.run(entity._sync_bridge_integration_version("bridge_entry"))

    assert calls == [
        (
            "esphome",
            "bridge_version",
            {"version": update_module.INTEGRATION_VERSION},
            True,
        ),
        ("sleep", 2),
        (
            "esphome",
            "bridge_version",
            {"version": update_module.INTEGRATION_VERSION},
            True,
        ),
    ]


def test_bridge_version_sync_timeout_does_not_fail_firmware(monkeypatch):
    entity = _entity()
    calls = []

    class Services:
        def has_service(self, domain, service):
            return True

        async def async_call(self, domain, service, data, *, blocking):
            calls.append("call")
            raise HomeAssistantError("Bridge is not connected")

    async def no_wait(seconds):
        calls.append(("sleep", seconds))

    entity.hass = SimpleNamespace(services=Services())
    entity._service_name = lambda entry_id, action=None: "bridge_version"
    monkeypatch.setattr(update_module, "VERSION_SYNC_ATTEMPTS", 2)
    monkeypatch.setattr(asyncio, "sleep", no_wait)

    asyncio.run(entity._sync_bridge_integration_version("bridge_entry"))

    assert calls == ["call", ("sleep", 2), "call"]
