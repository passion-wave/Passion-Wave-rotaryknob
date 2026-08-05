"""Static diagnostics for PassionWave."""

from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import INTEGRATION_VERSION
from .entity import PassionWaveConfigEntry, PassionWaveEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: PassionWaveConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the installed integration version sensor."""
    async_add_entities([PassionWaveVersionSensor(entry)])


class PassionWaveVersionSensor(PassionWaveEntity, SensorEntity):
    """Expose the integration version on the logical device."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_enabled_default = False
    _attr_icon = "mdi:puzzle"
    _attr_native_value = INTEGRATION_VERSION
    _attr_translation_key = "integration_version"

    def __init__(self, entry: PassionWaveConfigEntry) -> None:
        """Initialize the version sensor."""
        super().__init__(entry, "integration_version")
