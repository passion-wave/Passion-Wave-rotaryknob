"""One coordinated firmware update for a dual-MCU PassionWave device."""

from __future__ import annotations

import asyncio
from typing import Any

from homeassistant.components.update import (
    UpdateDeviceClass,
    UpdateEntity,
    UpdateEntityFeature,
)
from homeassistant.const import ATTR_ENTITY_ID, STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import Event, EventStateChangedData, HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.event import async_track_state_change_event

from .const import (
    CONF_BRIDGE_REGISTRATION_ENTITY,
    CONF_S3_CONFIG_ENTRY_ID,
    FIRMWARE_UPDATE_ORIGINAL_NAME,
)
from .entity import (
    PassionWaveConfigEntry,
    PassionWaveEntity,
    entity_by_original_name,
    entry_value,
)

ATTR_INSTALLED_VERSION = "installed_version"
ATTR_LATEST_VERSION = "latest_version"
UPDATE_TIMEOUT_SECONDS = 300


def _bridge_config_entry_id(
    hass: HomeAssistant, entry: PassionWaveConfigEntry
) -> str | None:
    registration = er.async_get(hass).async_get(
        entry_value(entry, CONF_BRIDGE_REGISTRATION_ENTITY)
    )
    return registration.config_entry_id if registration else None


def _source_update_entities(
    hass: HomeAssistant, entry: PassionWaveConfigEntry
) -> tuple[str | None, str | None]:
    """Return Bridge first, then S3, matching the safe flash sequence."""
    bridge_entry_id = _bridge_config_entry_id(hass, entry)
    s3_entry_id = entry_value(entry, CONF_S3_CONFIG_ENTRY_ID)
    bridge = (
        entity_by_original_name(hass, bridge_entry_id, FIRMWARE_UPDATE_ORIGINAL_NAME)
        if bridge_entry_id
        else None
    )
    s3 = entity_by_original_name(hass, s3_entry_id, FIRMWARE_UPDATE_ORIGINAL_NAME)
    return bridge, s3


async def async_setup_entry(
    hass: HomeAssistant,
    entry: PassionWaveConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the customer-facing dual firmware update."""
    bridge, s3 = _source_update_entities(hass, entry)
    registry = er.async_get(hass)
    for entity_id in (bridge, s3):
        if not entity_id:
            continue
        registry_entry = registry.async_get(entity_id)
        if registry_entry and registry_entry.hidden_by is None:
            registry.async_update_entity(
                entity_id, hidden_by=er.RegistryEntryHider.INTEGRATION
            )
    async_add_entities([PassionWaveFirmwareUpdate(entry, bridge, s3)])


class PassionWaveFirmwareUpdate(PassionWaveEntity, UpdateEntity):
    """Install Bridge and S3 firmware as one recoverable operation."""

    _attr_device_class = UpdateDeviceClass.FIRMWARE
    _attr_entity_category = EntityCategory.CONFIG
    _attr_supported_features = UpdateEntityFeature.INSTALL
    _attr_translation_key = "firmware"
    _attr_title = "PassionWave Rotaryknob"
    _attr_should_poll = False

    def __init__(
        self,
        entry: PassionWaveConfigEntry,
        bridge_entity_id: str | None,
        s3_entity_id: str | None,
    ) -> None:
        super().__init__(entry, "firmware")
        self._bridge_entity_id = bridge_entity_id
        self._s3_entity_id = s3_entity_id
        self._attr_in_progress = False
        self._attr_update_percentage: int | None = None
        self._phase = "idle"

    def _source_state(self, entity_id: str | None) -> Any:
        return self.hass.states.get(entity_id) if entity_id else None

    @property
    def available(self) -> bool:
        """Require both processors before offering a coordinated update."""
        return all(
            state is not None and state.state not in (STATE_UNAVAILABLE, STATE_UNKNOWN)
            for state in (
                self._source_state(self._bridge_entity_id),
                self._source_state(self._s3_entity_id),
            )
        )

    @property
    def installed_version(self) -> str | None:
        """Expose one version, while making a mixed pair explicit."""
        versions = self._versions(ATTR_INSTALLED_VERSION)
        if not all(versions):
            return None
        if versions[0] == versions[1]:
            return versions[0]
        return f"Bridge {versions[0]} / S3 {versions[1]}"

    @property
    def latest_version(self) -> str | None:
        """Offer only releases that exist for both processors."""
        versions = self._versions(ATTR_LATEST_VERSION)
        if versions[0] and versions[0] == versions[1]:
            return versions[0]
        if not any(versions):
            installed = self._versions(ATTR_INSTALLED_VERSION)
            if installed[0] and installed[0] == installed[1]:
                return installed[0]
        return None

    @property
    def extra_state_attributes(self) -> dict[str, str | None]:
        """Keep per-chip state visible for diagnosis and recovery."""
        installed = self._versions(ATTR_INSTALLED_VERSION)
        latest = self._versions(ATTR_LATEST_VERSION)
        return {
            "phase": self._phase,
            "bridge_installed_version": installed[0],
            "s3_installed_version": installed[1],
            "bridge_latest_version": latest[0],
            "s3_latest_version": latest[1],
        }

    def _versions(self, attribute: str) -> tuple[str | None, str | None]:
        values: list[str | None] = []
        for entity_id in (self._bridge_entity_id, self._s3_entity_id):
            state = self._source_state(entity_id)
            value = state.attributes.get(attribute) if state else None
            normalized = str(value).strip() if value is not None else ""
            if not normalized and attribute == ATTR_INSTALLED_VERSION:
                registry_entry = (
                    er.async_get(self.hass).async_get(entity_id) if entity_id else None
                )
                device = (
                    dr.async_get(self.hass).async_get(registry_entry.device_id)
                    if registry_entry and registry_entry.device_id
                    else None
                )
                normalized = device.sw_version if device and device.sw_version else ""
            values.append(normalized or None)
        return values[0], values[1]

    def version_is_newer(self, latest_version: str, installed_version: str) -> bool:
        """Treat either outdated processor or a mixed pair as an update."""
        del installed_version
        return any(
            version != latest_version
            for version in self._versions(ATTR_INSTALLED_VERSION)
        )

    async def async_install(
        self,
        version: str | None,
        backup: bool,
        **kwargs: Any,
    ) -> None:
        """Update Bridge first, verify reconnect, then update the S3."""
        del kwargs
        if backup:
            raise HomeAssistantError("Firmware backups are not supported by the device")
        target = version or self.latest_version
        if not target:
            raise HomeAssistantError("Bridge and S3 do not advertise the same release")
        if not self._bridge_entity_id or not self._s3_entity_id:
            raise HomeAssistantError("Both firmware endpoints are required")

        self._attr_in_progress = True
        self._attr_update_percentage = 0
        self._phase = "bridge"
        self.async_write_ha_state()
        try:
            await self._async_install_source(self._bridge_entity_id, target)
            self._attr_update_percentage = 50
            self._phase = "s3"
            self.async_write_ha_state()
            await self._async_install_source(self._s3_entity_id, target)
            self._attr_update_percentage = 100
            self._phase = "complete"
        except Exception:
            self._phase = "failed"
            raise
        finally:
            self._attr_in_progress = False
            self.async_write_ha_state()

    async def _async_install_source(self, entity_id: str, target: str) -> None:
        state = self.hass.states.get(entity_id)
        if state and state.attributes.get(ATTR_INSTALLED_VERSION) == target:
            return

        changed = asyncio.Event()

        @callback
        def async_source_changed(event: Event[EventStateChangedData]) -> None:
            new_state = event.data["new_state"]
            if (
                new_state is not None
                and new_state.attributes.get(ATTR_INSTALLED_VERSION) == target
            ):
                changed.set()

        remove_listener = async_track_state_change_event(
            self.hass, [entity_id], async_source_changed
        )
        try:
            await self.hass.services.async_call(
                "update",
                "install",
                {ATTR_ENTITY_ID: entity_id},
                blocking=True,
            )
            state = self.hass.states.get(entity_id)
            if state and state.attributes.get(ATTR_INSTALLED_VERSION) == target:
                return
            await asyncio.wait_for(changed.wait(), timeout=UPDATE_TIMEOUT_SECONDS)
        except TimeoutError as err:
            raise HomeAssistantError(
                f"{entity_id} did not reconnect with firmware {target}"
            ) from err
        finally:
            remove_listener()

    async def async_added_to_hass(self) -> None:
        """Mirror native source changes without polling."""
        await super().async_added_to_hass()
        sources = [
            entity_id
            for entity_id in (self._bridge_entity_id, self._s3_entity_id)
            if entity_id
        ]
        if not sources:
            return

        @callback
        def async_source_changed(event: Event[EventStateChangedData]) -> None:
            self.async_write_ha_state()

        self.async_on_remove(
            async_track_state_change_event(self.hass, sources, async_source_changed)
        )
