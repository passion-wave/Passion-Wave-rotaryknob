"""Connectivity diagnostics for PassionWave."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import (
    Event,
    EventStateChangedData,
    HomeAssistant,
    callback,
)
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.event import async_track_state_change_event

from .const import (
    CONF_BRIDGE_REGISTRATION_ENTITY,
    CONF_S3_CONFIG_ENTRY_ID,
    MEDIA_ENTITY_ORIGINAL_NAME,
)
from .entity import (
    PassionWaveConfigEntry,
    PassionWaveEntity,
    entity_by_original_name,
    entry_value,
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: PassionWaveConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up processor connectivity diagnostics."""
    s3_entity = entity_by_original_name(
        hass,
        entry_value(entry, CONF_S3_CONFIG_ENTRY_ID),
        MEDIA_ENTITY_ORIGINAL_NAME,
    )
    bridge_entity = entry_value(entry, CONF_BRIDGE_REGISTRATION_ENTITY)
    async_add_entities(
        [
            PassionWaveSystemProblemSensor(entry, s3_entity, bridge_entity),
            PassionWaveConnectivitySensor(entry, "s3_connection", s3_entity),
            PassionWaveConnectivitySensor(entry, "bridge_connection", bridge_entity),
        ]
    )


def _source_connected(hass: HomeAssistant, entity_id: str | None) -> bool:
    """Return whether one native contract entity is currently available."""
    if not entity_id:
        return False
    state = hass.states.get(entity_id)
    return state is not None and state.state not in (
        STATE_UNAVAILABLE,
        STATE_UNKNOWN,
    )


class PassionWaveSystemProblemSensor(PassionWaveEntity, BinarySensorEntity):
    """Expose one customer-facing health result for both processors."""

    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_translation_key = "system_problem"

    def __init__(
        self,
        entry: PassionWaveConfigEntry,
        s3_entity_id: str | None,
        bridge_entity_id: str | None,
    ) -> None:
        super().__init__(entry, "system_problem")
        self._s3_entity_id = s3_entity_id
        self._bridge_entity_id = bridge_entity_id
        self._source_entity_ids = tuple(
            entity_id
            for entity_id in (s3_entity_id, bridge_entity_id)
            if entity_id
        )

    @property
    def is_on(self) -> bool:
        """Return true if either required processor is unavailable."""
        return len(self._source_entity_ids) != 2 or not all(
            _source_connected(self.hass, entity_id)
            for entity_id in self._source_entity_ids
        )

    @property
    def extra_state_attributes(self) -> dict[str, bool]:
        """Keep the two bounded health inputs available for support."""
        return {
            "s3_connected": _source_connected(self.hass, self._s3_entity_id),
            "bridge_connected": _source_connected(
                self.hass, self._bridge_entity_id
            ),
        }

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        if self._source_entity_ids:
            self.async_on_remove(
                async_track_state_change_event(
                    self.hass,
                    list(self._source_entity_ids),
                    lambda _event: self.async_write_ha_state(),
                )
            )


class PassionWaveConnectivitySensor(PassionWaveEntity, BinarySensorEntity):
    """Connectivity inferred from one native ESPHome contract entity."""

    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_enabled_default = False

    def __init__(
        self,
        entry: PassionWaveConfigEntry,
        translation_key: str,
        source_entity_id: str | None,
    ) -> None:
        """Initialize one processor status."""
        super().__init__(entry, translation_key)
        self._source_entity_id = source_entity_id
        self._attr_translation_key = translation_key

    @property
    def is_on(self) -> bool:
        """Return true while the native ESPHome endpoint is available."""
        return _source_connected(self.hass, self._source_entity_id)

    async def async_added_to_hass(self) -> None:
        """Follow the selected ESPHome endpoint without polling."""
        await super().async_added_to_hass()
        if not self._source_entity_id:
            return

        @callback
        def async_source_changed(
            event: Event[EventStateChangedData],
        ) -> None:
            self.async_write_ha_state()

        self.async_on_remove(
            async_track_state_change_event(
                self.hass,
                [self._source_entity_id],
                async_source_changed,
            )
        )
