"""Support controls for PassionWave."""

from __future__ import annotations

import asyncio

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import slugify

from .broker import bridge_config_entry_id
from .const import CONF_S3_CONFIG_ENTRY_ID
from .entity import PassionWaveConfigEntry, PassionWaveEntity, entry_value

SUPPORT_ON_ACTION = "support_diagnostics_on"
SUPPORT_OFF_ACTION = "support_diagnostics_off"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: PassionWaveConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the bounded support-mode control."""
    async_add_entities([PassionWaveSupportDiagnosticsSwitch(entry)])


class PassionWaveSupportDiagnosticsSwitch(PassionWaveEntity, SwitchEntity):
    """Enable temporary firmware diagnostics on both processors."""

    _attr_entity_category = EntityCategory.CONFIG
    _attr_icon = "mdi:bug-check-outline"
    _attr_translation_key = "support_diagnostics"

    def __init__(self, entry: PassionWaveConfigEntry) -> None:
        super().__init__(entry, "support_diagnostics")
        self._attr_is_on = False

    def _service(self, config_entry_id: str, action: str) -> str | None:
        config_entry = self.hass.config_entries.async_get_entry(config_entry_id)
        if config_entry is None:
            return None
        device_name = config_entry.data.get("device_name")
        if not isinstance(device_name, str) or not device_name:
            return None
        return f"{slugify(device_name)}_{action}"

    def _services(self, action: str) -> list[str]:
        ids = (
            entry_value(self._entry, CONF_S3_CONFIG_ENTRY_ID),
            bridge_config_entry_id(self.hass, self._entry),
        )
        return [
            service
            for config_entry_id in ids
            if isinstance(config_entry_id, str)
            and (service := self._service(config_entry_id, action)) is not None
        ]

    @property
    def available(self) -> bool:
        services = self._services(SUPPORT_ON_ACTION)
        return len(services) == 2 and all(
            self.hass.services.has_service("esphome", service)
            for service in services
        )

    async def _async_set_mode(self, enabled: bool) -> None:
        action = SUPPORT_ON_ACTION if enabled else SUPPORT_OFF_ACTION
        services = self._services(action)
        if len(services) != 2 or not all(
            self.hass.services.has_service("esphome", service)
            for service in services
        ):
            raise HomeAssistantError(
                "Both PassionWave processors must provide support diagnostics"
            )
        await asyncio.gather(
            *(
                self.hass.services.async_call(
                    "esphome", service, {}, blocking=True
                )
                for service in services
            )
        )
        self._attr_is_on = enabled
        self.async_write_ha_state()

    async def async_turn_on(self, **kwargs: object) -> None:
        await self._async_set_mode(True)

    async def async_turn_off(self, **kwargs: object) -> None:
        await self._async_set_mode(False)
