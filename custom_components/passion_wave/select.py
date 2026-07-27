"""Configuration selects for PassionWave."""

from __future__ import annotations

from typing import Any

from homeassistant.components.select import SelectEntity
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import (
    CONF_MEDIA_PLAYER,
    LIGHT_SLOT_KEYS,
)
from .entity import (
    PassionWaveConfigEntry,
    PassionWaveEntity,
    entry_value,
    target_options,
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: PassionWaveConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up customer-editable target selects."""
    async_add_entities(
        [
            PassionWaveTargetSelect(
                entry,
                CONF_MEDIA_PLAYER,
                "playback_device",
                domain="media_player",
                platform="music_assistant",
            ),
            *[
                PassionWaveTargetSelect(
                    entry,
                    key,
                    f"light_position_{index}",
                    domain="light",
                    include_unassigned=True,
                )
                for index, key in enumerate(LIGHT_SLOT_KEYS, start=1)
            ],
        ]
    )


class PassionWaveTargetSelect(PassionWaveEntity, SelectEntity):
    """Select one Home Assistant target using a customer-readable label."""

    _attr_entity_category = EntityCategory.CONFIG

    def __init__(
        self,
        entry: PassionWaveConfigEntry,
        key: str,
        translation_key: str,
        *,
        domain: str,
        platform: str | None = None,
        include_unassigned: bool = False,
    ) -> None:
        """Initialize one dynamic target selector."""
        super().__init__(entry, translation_key)
        self._key = key
        self._domain = domain
        self._platform = platform
        self._include_unassigned = include_unassigned
        self._attr_translation_key = translation_key

    def _option_map(self) -> dict[str, str]:
        options = target_options(
            self.hass,
            domain=self._domain,
            platform=self._platform,
            include_unassigned=self._include_unassigned,
        )
        configured = entry_value(self._entry, self._key) or ""
        if configured not in options.values():
            label = (
                f"Nicht mehr verfügbar · {configured}"
                if self.hass.config.language.startswith("de")
                else f"No longer available · {configured}"
            )
            options[label] = configured
        return options

    @property
    def options(self) -> list[str]:
        """Return dynamic labels for currently available targets."""
        return list(self._option_map())

    @property
    def current_option(self) -> str | None:
        """Return the label matching the stored stable entity ID."""
        configured = entry_value(self._entry, self._key) or ""
        return next(
            (
                label
                for label, entity_id in self._option_map().items()
                if entity_id == configured
            ),
            None,
        )

    async def async_select_option(self, option: str) -> None:
        """Persist the selected target and trigger direct device sync."""
        option_map = self._option_map()
        if option not in option_map:
            raise ValueError(f"Unknown PassionWave target option: {option}")
        options = dict(self._entry.options)
        options[self._key] = option_map[option]
        self.hass.config_entries.async_update_entry(self._entry, options=options)

    async def async_added_to_hass(self) -> None:
        """Refresh labels and choices when the entity registry changes."""
        await super().async_added_to_hass()

        @callback
        def async_registry_updated(event: Event[dict[str, Any]]) -> None:
            self.async_write_ha_state()

        self.async_on_remove(
            self.hass.bus.async_listen(
                er.EVENT_ENTITY_REGISTRY_UPDATED,
                async_registry_updated,
            )
        )
