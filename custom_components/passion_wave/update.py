"""One persistent customer update for both PassionWave processors."""

from __future__ import annotations

import asyncio
import re
from datetime import timedelta
from typing import Any

from aiohttp import ClientError
from awesomeversion import AwesomeVersion

from homeassistant.components.update import (
    UpdateDeviceClass,
    UpdateEntity,
    UpdateEntityFeature,
)
from homeassistant.const import ATTR_ENTITY_ID, STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.storage import Store
from homeassistant.util import slugify

from . import async_rehydrate_runtime_snapshot
from .broker import bridge_config_entry_id
from .const import (
    BRIDGE_RECEIVE_INTEGRATION_VERSION_ACTION,
    CONF_S3_CONFIG_ENTRY_ID,
    FIRMWARE_UPDATE_ORIGINAL_NAME,
    FIRMWARE_UPDATE_STATUS_ORIGINAL_NAME,
    INTEGRATION_VERSION,
)
from .entity import (
    PassionWaveConfigEntry,
    PassionWaveEntity,
    entity_by_original_name,
    entry_value,
)

ATTR_INSTALLED_VERSION = "installed_version"
ATTR_LATEST_VERSION = "latest_version"
INSTALL_ACTION = "passion_wave_install_firmware"
JOB_STORAGE_VERSION = 1
JOB_WAIT_SECONDS = 24 * 60 * 60
LEGACY_ACTIVATION_TIMEOUT_SECONDS = 30
RECONNECT_TIMEOUT_SECONDS = 5 * 60
TRANSPORT_START_TIMEOUT_SECONDS = 90
VERSION_METADATA_REFRESH_SECONDS = 10
VERSION_METADATA_REFRESH_RETRY_SECONDS = 30
VERSION_METADATA_REFRESH_ATTEMPTS = 2
VERSION_SYNC_ATTEMPTS = 30
SCAN_INTERVAL = timedelta(hours=6)
S3_MANIFEST_URL = (
    "https://www.passion-wave.com/"
    "firmware/rotaryknob/s3/manifest.json"
)
BRIDGE_MANIFEST_URL = (
    "https://www.passion-wave.com/"
    "firmware/rotaryknob/esp32/manifest.json"
)
_VERSION_PREFIX = re.compile(r"^(\S+)")


def _endpoint_entry_ids(
    hass: HomeAssistant, entry: PassionWaveConfigEntry
) -> tuple[str | None, str | None]:
    """Return Bridge first and S3 second."""
    try:
        bridge = bridge_config_entry_id(hass, entry)
    except HomeAssistantError:
        bridge = None
    s3 = entry_value(entry, CONF_S3_CONFIG_ENTRY_ID)
    return bridge, s3 if isinstance(s3, str) else None


def _legacy_update_entities(
    hass: HomeAssistant, entry: PassionWaveConfigEntry
) -> tuple[str | None, str | None]:
    """Resolve the Beta-15 source entities used for the one-time transition."""
    bridge_entry_id, s3_entry_id = _endpoint_entry_ids(hass, entry)
    bridge = (
        entity_by_original_name(
            hass, bridge_entry_id, FIRMWARE_UPDATE_ORIGINAL_NAME
        )
        if bridge_entry_id
        else None
    )
    s3 = (
        entity_by_original_name(hass, s3_entry_id, FIRMWARE_UPDATE_ORIGINAL_NAME)
        if s3_entry_id
        else None
    )
    return bridge, s3


def _firmware_status_entities(
    hass: HomeAssistant, entry: PassionWaveConfigEntry
) -> tuple[str | None, str | None]:
    """Resolve the per-processor OTA diagnostic entities."""
    bridge_entry_id, s3_entry_id = _endpoint_entry_ids(hass, entry)
    bridge = (
        entity_by_original_name(
            hass, bridge_entry_id, FIRMWARE_UPDATE_STATUS_ORIGINAL_NAME
        )
        if bridge_entry_id
        else None
    )
    s3 = (
        entity_by_original_name(
            hass, s3_entry_id, FIRMWARE_UPDATE_STATUS_ORIGINAL_NAME
        )
        if s3_entry_id
        else None
    )
    return bridge, s3


async def async_setup_entry(
    hass: HomeAssistant,
    entry: PassionWaveConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the sole customer-facing dual firmware update."""
    async_add_entities([PassionWaveFirmwareUpdate(entry)])


class PassionWaveFirmwareUpdate(PassionWaveEntity, UpdateEntity):
    """Queue, install and verify Bridge then S3 as one transaction."""

    _attr_device_class = UpdateDeviceClass.FIRMWARE
    _attr_entity_category = EntityCategory.CONFIG
    _attr_supported_features = (
        UpdateEntityFeature.INSTALL | UpdateEntityFeature.PROGRESS
    )
    _attr_translation_key = "firmware"
    _attr_title = "PassionWave RotaryKnob"
    _attr_should_poll = True

    def __init__(self, entry: PassionWaveConfigEntry) -> None:
        super().__init__(entry, "firmware")
        self._attr_in_progress = False
        self._attr_update_percentage: int | None = None
        self._phase = "idle"
        self._target_version: str | None = None
        self._last_error: str | None = None
        self._manifest_versions: tuple[str | None, str | None] = (None, None)
        self._job_task: asyncio.Task[None] | None = None
        self._store: Store[dict[str, Any]] | None = None

    @property
    def available(self) -> bool:
        """Keep the customer update visible while a sleeping device reconnects."""
        return all(_endpoint_entry_ids(self.hass, self._entry))

    def _device_version(self, config_entry_id: str | None) -> str | None:
        if not config_entry_id:
            return None
        entity_registry = er.async_get(self.hass)
        device_registry = dr.async_get(self.hass)
        device_ids = {
            item.device_id
            for item in entity_registry.entities.values()
            if item.config_entry_id == config_entry_id and item.device_id
        }
        for device_id in device_ids:
            device = device_registry.async_get(device_id)
            if device and device.sw_version:
                match = _VERSION_PREFIX.match(device.sw_version.strip())
                if match:
                    return match.group(1)
        return None

    def _installed_versions(self) -> tuple[str | None, str | None]:
        bridge_entry_id, s3_entry_id = _endpoint_entry_ids(self.hass, self._entry)
        return (
            self._device_version(bridge_entry_id),
            self._device_version(s3_entry_id),
        )

    @property
    def installed_version(self) -> str | None:
        versions = self._installed_versions()
        if not all(versions):
            return None
        if versions[0] == versions[1]:
            return versions[0]
        return f"Bridge {versions[0]} / S3 {versions[1]}"

    @property
    def latest_version(self) -> str | None:
        bridge, s3 = self._manifest_versions
        if bridge and bridge == s3:
            return bridge
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        installed = self._installed_versions()
        transport_status = tuple(
            self._transport_status(entity_id)
            for entity_id in _firmware_status_entities(self.hass, self._entry)
        )
        return {
            "phase": self._phase,
            "target_version": self._target_version,
            "bridge_installed_version": installed[0],
            "s3_installed_version": installed[1],
            "bridge_latest_version": self._manifest_versions[0],
            "s3_latest_version": self._manifest_versions[1],
            "bridge_transport_status": transport_status[0],
            "s3_transport_status": transport_status[1],
            "queued": self._phase == "waiting_for_devices",
            "last_error": self._last_error,
        }

    def _transport_status(self, entity_id: str | None) -> str | None:
        state = self.hass.states.get(entity_id) if entity_id else None
        if not state or state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN):
            return None
        return state.state

    def version_is_newer(self, latest_version: str, installed_version: str) -> bool:
        del installed_version
        installed = self._installed_versions()
        if not all(installed):
            return False
        latest = AwesomeVersion(latest_version)
        current = tuple(AwesomeVersion(version) for version in installed)
        return all(version <= latest for version in current) and any(
            version < latest for version in current
        )

    async def async_update(self) -> None:
        """Read the immutable public manifests independently of ESPHome UI entities."""
        session = async_get_clientsession(self.hass)

        async def version(url: str) -> str | None:
            try:
                async with asyncio.timeout(20):
                    response = await session.get(url)
                    response.raise_for_status()
                    payload = await response.json()
                value = payload.get("version")
                return str(value).strip() if value else None
            except (ClientError, TimeoutError, ValueError, OSError):
                return None

        self._manifest_versions = tuple(
            await asyncio.gather(
                version(BRIDGE_MANIFEST_URL), version(S3_MANIFEST_URL)
            )
        )
        if self._both_diagnostic_transports_available():
            self._disable_legacy_sources()
        if self._reconcile_completed_target():
            await self._save_job()

    def _reconcile_completed_target(self) -> bool:
        """Clear a stale job when both processors already run its target."""
        target = self._target_version
        if not target or any(
            version != target for version in self._installed_versions()
        ):
            return False
        self._phase = "complete"
        self._target_version = None
        self._last_error = None
        self._attr_in_progress = False
        self._attr_update_percentage = 100
        if self._both_internal_actions_available():
            self._disable_legacy_sources()
        return True

    def _service_name(
        self, config_entry_id: str | None, action: str = INSTALL_ACTION
    ) -> str | None:
        if not config_entry_id:
            return None
        config_entry = self.hass.config_entries.async_get_entry(config_entry_id)
        if config_entry is None:
            return None
        device_name = config_entry.data.get("device_name")
        if not isinstance(device_name, str) or not device_name:
            return None
        return f"{slugify(device_name)}_{action}"

    def _internal_action_available(self, config_entry_id: str | None) -> bool:
        service = self._service_name(config_entry_id)
        return bool(service and self.hass.services.has_service("esphome", service))

    def _both_internal_actions_available(self) -> bool:
        return all(
            self._internal_action_available(config_entry_id)
            for config_entry_id in _endpoint_entry_ids(self.hass, self._entry)
        )

    def _both_diagnostic_transports_available(self) -> bool:
        return self._both_internal_actions_available() and all(
            self._transport_status(entity_id) is not None
            for entity_id in _firmware_status_entities(self.hass, self._entry)
        )

    def _disable_legacy_sources(self) -> None:
        registry = er.async_get(self.hass)
        for entity_id in _legacy_update_entities(self.hass, self._entry):
            registry_entry = registry.async_get(entity_id) if entity_id else None
            if registry_entry and registry_entry.disabled_by is None:
                registry.async_update_entity(
                    entity_id, disabled_by=er.RegistryEntryDisabler.INTEGRATION
                )

    def _legacy_source_available(self, entity_id: str | None) -> bool:
        state = self.hass.states.get(entity_id) if entity_id else None
        return bool(
            state and state.state not in (STATE_UNAVAILABLE, STATE_UNKNOWN)
        )

    async def _refresh_legacy_source(self, entity_id: str, target: str) -> None:
        """Refresh a Beta-15 transport and require its target before install."""
        await self.hass.services.async_call(
            "homeassistant",
            "update_entity",
            {ATTR_ENTITY_ID: entity_id},
            blocking=True,
        )
        for _ in range(10):
            state = self.hass.states.get(entity_id)
            if state and state.attributes.get(ATTR_LATEST_VERSION) == target:
                return
            await asyncio.sleep(1)
        state = self.hass.states.get(entity_id)
        advertised = (
            state.attributes.get(ATTR_LATEST_VERSION) if state else None
        )
        raise HomeAssistantError(
            f"Firmware transport {entity_id} advertises "
            f"{advertised or 'no release'} instead of {target}"
        )

    async def _prepare_legacy_source(self, index: int) -> str | None:
        """Temporarily activate a hidden pre-Beta.19 update transport."""
        entity_id = _legacy_update_entities(self.hass, self._entry)[index]
        if not entity_id or self._legacy_source_available(entity_id):
            return entity_id
        registry = er.async_get(self.hass)
        registry_entry = registry.async_get(entity_id)
        if (
            registry_entry is None
            or registry_entry.disabled_by
            != er.RegistryEntryDisabler.INTEGRATION
        ):
            return None
        registry.async_update_entity(entity_id, disabled_by=None)
        config_entry_id = _endpoint_entry_ids(self.hass, self._entry)[index]
        if config_entry_id:
            await self.hass.config_entries.async_reload(config_entry_id)
        deadline = self.hass.loop.time() + LEGACY_ACTIVATION_TIMEOUT_SECONDS
        while self.hass.loop.time() < deadline:
            if self._legacy_source_available(entity_id):
                return entity_id
            await asyncio.sleep(1)
        raise HomeAssistantError(
            f"Firmware recovery transport {entity_id} did not become available"
        )

    async def _save_job(self) -> None:
        if self._store is None:
            return
        if self._target_version is None:
            await self._store.async_remove()
            return
        await self._store.async_save(
            {"target_version": self._target_version, "phase": self._phase}
        )

    async def async_install(
        self, version: str | None, backup: bool, **kwargs: Any
    ) -> None:
        del kwargs
        if backup:
            raise HomeAssistantError("Firmware backups are not supported")
        target = version or self.latest_version
        if not target or target != self.latest_version:
            raise HomeAssistantError("S3 and Bridge do not advertise the same release")
        if self._attr_in_progress or (
            self._job_task and not self._job_task.done()
        ):
            raise HomeAssistantError("A PassionWave firmware update is already queued")
        self._target_version = target
        self._last_error = None
        self._phase = "waiting_for_devices"
        self._attr_in_progress = True
        self._attr_update_percentage = 0
        await self._save_job()
        self.async_write_ha_state()
        await self._async_run_job(raise_on_failure=True)

    def _start_job(self) -> None:
        if self._job_task and not self._job_task.done():
            return
        self._job_task = self.hass.async_create_task(
            self._async_run_job(), "PassionWave coordinated firmware update"
        )

    async def _wait_for_transports(self) -> None:
        bridge_entry, s3_entry = _endpoint_entry_ids(self.hass, self._entry)
        deadline = self.hass.loop.time() + JOB_WAIT_SECONDS
        while self.hass.loop.time() < deadline:
            legacy_bridge, legacy_s3 = _legacy_update_entities(self.hass, self._entry)
            bridge_ready = self._internal_action_available(
                bridge_entry
            ) or self._legacy_source_available(legacy_bridge)
            s3_ready = self._internal_action_available(
                s3_entry
            ) or self._legacy_source_available(legacy_s3)
            if bridge_ready and s3_ready:
                return
            await asyncio.sleep(10)
        raise HomeAssistantError("Timed out waiting for both RotaryKnob processors")

    async def _async_run_job(self, *, raise_on_failure: bool = False) -> None:
        target = self._target_version
        if not target:
            return
        failure: Exception | None = None
        try:
            await self._wait_for_transports()
            self._phase = "updating_bridge"
            await self._save_job()
            self._attr_update_percentage = 10
            self.async_write_ha_state()
            await self._install_endpoint(0, target)
            self._attr_update_percentage = 50
            self._phase = "updating_s3"
            await self._save_job()
            self.async_write_ha_state()
            await self._install_endpoint(1, target)
            self._attr_update_percentage = 100
            self._phase = "complete"
            if self._both_internal_actions_available():
                self._disable_legacy_sources()
        except asyncio.CancelledError:
            raise
        except Exception as err:  # noqa: BLE001 - surface firmware transport failures
            if not self._reconcile_completed_target():
                self._phase = "failed"
                self._last_error = str(err)
                failure = err
        finally:
            if self._phase in {"complete", "failed"}:
                self._attr_in_progress = False
            if self._phase == "complete":
                self._target_version = None
            await self._save_job()
            self.async_write_ha_state()
        if failure is not None and raise_on_failure:
            raise HomeAssistantError(str(failure)) from failure

    async def _install_endpoint(self, index: int, target: str) -> None:
        entry_ids = _endpoint_entry_ids(self.hass, self._entry)
        if self._device_version(entry_ids[index]) == target:
            return
        service = self._service_name(entry_ids[index])
        status_entity = _firmware_status_entities(self.hass, self._entry)[index]
        diagnostic_service = (
            service
            if (
                service
                and self.hass.services.has_service("esphome", service)
                and status_entity
                and self._transport_status(status_entity) is not None
            )
            else None
        )
        legacy = None
        if not diagnostic_service:
            legacy = await self._prepare_legacy_source(index)
        if diagnostic_service and status_entity:
            status_state = self.hass.states.get(status_entity)
            await self.hass.services.async_call(
                "esphome",
                diagnostic_service,
                {"target_version": target},
                blocking=True,
            )
            await self._wait_for_transport_start(
                index, target, status_entity, status_state
            )
        elif legacy and self._legacy_source_available(legacy):
            await self._refresh_legacy_source(legacy, target)
            try:
                await self.hass.services.async_call(
                    "update", "install", {ATTR_ENTITY_ID: legacy}, blocking=True
                )
            except HomeAssistantError as err:
                if "already in progress" not in str(err).lower():
                    raise
            status_entity = None
        elif service and self.hass.services.has_service("esphome", service):
            raise HomeAssistantError(
                "Pre-Beta.19 firmware has no refreshable Home Assistant "
                "update transport; install Beta.19 once with ESPHome OTA, "
                "then retry"
            )
        else:
            raise HomeAssistantError("Firmware transport became unavailable")
        await self._wait_for_version(
            entry_ids[index], target, index=index, status_entity=status_entity
        )
        if index == 0:
            await self.hass.config_entries.async_reload(entry_ids[index])
            await self._sync_bridge_integration_version(entry_ids[index])
            await async_rehydrate_runtime_snapshot(self.hass, self._entry)

    async def _sync_bridge_integration_version(
        self, config_entry_id: str | None
    ) -> None:
        """Best-effort metadata sync after the Bridge entry reconnects."""
        service = self._service_name(
            config_entry_id, BRIDGE_RECEIVE_INTEGRATION_VERSION_ACTION
        )
        if not service:
            return
        for attempt in range(VERSION_SYNC_ATTEMPTS):
            if self.hass.services.has_service("esphome", service):
                try:
                    await self.hass.services.async_call(
                        "esphome",
                        service,
                        {"version": INTEGRATION_VERSION},
                        blocking=True,
                    )
                    return
                except HomeAssistantError:
                    pass
            if attempt + 1 < VERSION_SYNC_ATTEMPTS:
                await asyncio.sleep(2)

    def _transport_error(self, status: str, target: str) -> str | None:
        if status == "manifest_error":
            return f"Device could not download the firmware manifest for {target}"
        if status.startswith("manifest_mismatch:"):
            advertised = status.partition(":")[2] or "no release"
            return f"Device manifest advertises {advertised} instead of {target}"
        if status == "manifest_not_installable":
            return f"Device manifest does not offer an installable {target} image"
        if status.startswith("ota_error:"):
            code = status.partition(":")[2] or "unknown"
            return f"Device reported OTA download/flash error {code} for {target}"
        return None

    def _apply_transport_progress(self, index: int, status: str) -> None:
        if not status.startswith("ota_progress:"):
            return
        try:
            progress = min(100.0, max(0.0, float(status.partition(":")[2])))
        except ValueError:
            return
        start, span = ((10.0, 40.0) if index == 0 else (50.0, 50.0))
        self._attr_update_percentage = round(start + span * progress / 100.0)
        self.async_write_ha_state()

    async def _wait_for_transport_start(
        self,
        index: int,
        target: str,
        status_entity: str,
        previous_state: Any,
    ) -> None:
        """Require a fresh manifest result or OTA start from new firmware."""
        config_entry_id = _endpoint_entry_ids(self.hass, self._entry)[index]
        previous_updated = (
            previous_state.last_updated if previous_state is not None else None
        )
        reconciled_fresh_idle = False
        deadline = self.hass.loop.time() + TRANSPORT_START_TIMEOUT_SECONDS
        while self.hass.loop.time() < deadline:
            if self._device_version(config_entry_id) == target:
                return
            state = self.hass.states.get(status_entity)
            if state is None or state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN):
                await asyncio.sleep(1)
                continue
            status = state.state
            is_fresh = (
                previous_updated is None or state.last_updated != previous_updated
            )
            if is_fresh:
                error = self._transport_error(status, target)
                if error:
                    if status == "manifest_not_installable" and config_entry_id:
                        await self.hass.config_entries.async_reload(config_entry_id)
                        if self._device_version(config_entry_id) == target:
                            return
                    raise HomeAssistantError(error)
                self._apply_transport_progress(index, status)
                if status in {"ota_started", "ota_complete"} or status.startswith(
                    (
                        f"checking:{target}",
                        f"manifest_ready:{target}",
                        "ota_progress:",
                    )
                ):
                    return
                # A completed OTA can reboot between the blocking service call
                # and this observer. A fresh idle state is then the only status
                # left, while ESPHome's registry can still hold the old version.
                if (
                    status == "idle"
                    and config_entry_id
                    and not reconciled_fresh_idle
                ):
                    reconciled_fresh_idle = True
                    await self.hass.config_entries.async_reload(config_entry_id)
                    if self._device_version(config_entry_id) == target:
                        return
            await asyncio.sleep(1)
        if config_entry_id:
            await self.hass.config_entries.async_reload(config_entry_id)
            if self._device_version(config_entry_id) == target:
                return
        raise HomeAssistantError(
            f"Device did not confirm a fresh manifest or OTA start for {target}"
        )

    async def _wait_for_version(
        self,
        config_entry_id: str | None,
        target: str,
        *,
        index: int,
        status_entity: str | None,
    ) -> None:
        started = self.hass.loop.time()
        deadline = started + RECONNECT_TIMEOUT_SECONDS
        next_metadata_refresh = started + VERSION_METADATA_REFRESH_SECONDS
        metadata_refreshes = 0
        while self.hass.loop.time() < deadline:
            if self._device_version(config_entry_id) == target:
                return
            status = self._transport_status(status_entity)
            if status:
                error = self._transport_error(status, target)
                if error:
                    if status == "manifest_not_installable" and config_entry_id:
                        await self.hass.config_entries.async_reload(config_entry_id)
                        if self._device_version(config_entry_id) == target:
                            return
                    raise HomeAssistantError(error)
                self._apply_transport_progress(index, status)
            transport_active = bool(
                status
                and (
                    status == "ota_started"
                    or status.startswith(
                        ("checking:", "manifest_ready:", "ota_progress:")
                    )
                )
            )
            if (
                config_entry_id
                and status is not None
                and not transport_active
                and metadata_refreshes < VERSION_METADATA_REFRESH_ATTEMPTS
                and self.hass.loop.time() >= next_metadata_refresh
            ):
                await self.hass.config_entries.async_reload(config_entry_id)
                metadata_refreshes += 1
                if self._device_version(config_entry_id) == target:
                    return
                next_metadata_refresh = (
                    self.hass.loop.time() + VERSION_METADATA_REFRESH_RETRY_SECONDS
                )
            await asyncio.sleep(2)
        raise HomeAssistantError(
            f"Processor did not reconnect with firmware {target}"
        )

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self._store = Store(
            self.hass,
            JOB_STORAGE_VERSION,
            f"passion_wave.firmware_update.{self._entry.entry_id}",
        )
        stored = await self._store.async_load()
        if stored and stored.get("target_version"):
            self._target_version = str(stored["target_version"])
            stored_phase = str(stored.get("phase") or "waiting_for_devices")
            if self._reconcile_completed_target():
                await self._save_job()
            elif stored_phase == "failed":
                self._phase = "failed"
            else:
                self._phase = "waiting_for_devices"
                self._attr_in_progress = True
                self._start_job()

    async def async_will_remove_from_hass(self) -> None:
        if self._job_task and not self._job_task.done():
            self._job_task.cancel()
        await super().async_will_remove_from_hass()
