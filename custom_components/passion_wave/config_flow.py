"""Config flow for PassionWave."""

from __future__ import annotations

import asyncio
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult
from homeassistant.core import callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import (
    device_registry as dr,
    entity_registry as er,
    selector,
)

from .const import (
    BRIDGE_REGISTRATION_ORIGINAL_NAME,
    CONF_BRIDGE_REGISTRATION_ENTITY,
    CONF_BRIDGE_REGISTRATION_UNIQUE_ID,
    CONF_MA_CONFIG_ENTRY_ID,
    CONF_MEDIA_PLAYER,
    CONF_VISIBLE_PLAYLISTS,
    CONF_VISIBLE_PODCASTS,
    CONF_VISIBLE_RADIOS,
    DOMAIN,
    LIBRARY_FILTER_KEYS,
    LIBRARY_SELECTION_LIMIT,
    SHOW_ALL,
)
from .media import normalize_library_page


def _connection_schema(defaults: dict[str, Any] | None = None) -> vol.Schema:
    values = defaults or {}

    def required(key: str) -> vol.Marker:
        return (
            vol.Required(key, default=values[key])
            if key in values
            else vol.Required(key)
        )

    return vol.Schema(
        {
            required(CONF_BRIDGE_REGISTRATION_ENTITY): selector.EntitySelector(
                selector.EntitySelectorConfig(
                    domain="text",
                    integration="esphome",
                )
            ),
            required(CONF_MA_CONFIG_ENTRY_ID): selector.ConfigEntrySelector(
                selector.ConfigEntrySelectorConfig(integration="music_assistant")
            ),
            required(CONF_MEDIA_PLAYER): selector.EntitySelector(
                selector.EntitySelectorConfig(
                    domain="media_player",
                    integration="music_assistant",
                )
            ),
        }
    )


async def _async_load_catalogs(
    flow: config_entries.ConfigFlow | config_entries.OptionsFlow,
    config_entry_id: str,
) -> dict[str, list[dict[str, str]]]:
    """Load selectable Music Assistant catalogs concurrently."""

    async def load(media_type: str) -> tuple[str, list[dict[str, str]]]:
        response = await flow.hass.services.async_call(
            "music_assistant",
            "get_library",
            {
                "config_entry_id": config_entry_id,
                "media_type": media_type,
                "offset": 0,
                "limit": LIBRARY_SELECTION_LIMIT,
            },
            blocking=True,
            return_response=True,
        )
        page = normalize_library_page(
            response, media_type, 0, LIBRARY_SELECTION_LIMIT
        )
        return media_type, page["items"]

    return dict(
        await asyncio.gather(
            *(load(media_type) for media_type in LIBRARY_FILTER_KEYS)
        )
    )


def _library_schema(
    catalogs: dict[str, list[dict[str, str]]],
    defaults: dict[str, Any] | None = None,
) -> vol.Schema:
    values = defaults or {}

    def field(media_type: str) -> tuple[vol.Marker, selector.SelectSelector]:
        key = LIBRARY_FILTER_KEYS[media_type]
        configured = values.get(key, [SHOW_ALL])
        selected = (
            [configured] if isinstance(configured, str) else list(configured)
        )
        options: list[selector.SelectOptionDict] = [
            {"value": SHOW_ALL, "label": "Alle automatisch / All automatically"}
        ]
        known: set[str] = set()
        for item in catalogs.get(media_type, []):
            uri = item["uri"]
            if not uri or uri in known:
                continue
            known.add(uri)
            options.append({"value": uri, "label": item["name"]})
        for uri in selected:
            if uri != SHOW_ALL and uri not in known:
                options.append(
                    {
                        "value": uri,
                        "label": f"Nicht mehr verfügbar · {uri}",
                    }
                )
        return (
            vol.Optional(key, default=selected),
            selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=options,
                    multiple=True,
                    mode=selector.SelectSelectorMode.DROPDOWN,
                    sort=False,
                )
            ),
        )

    return vol.Schema(dict(field(media_type) for media_type in LIBRARY_FILTER_KEYS))


def _normalize_visibility(user_input: dict[str, Any]) -> dict[str, Any]:
    """Collapse mixed all/individual selections to the stable sentinel."""
    for key in LIBRARY_FILTER_KEYS.values():
        selected = list(dict.fromkeys(user_input.get(key, [])))
        user_input[key] = [SHOW_ALL] if SHOW_ALL in selected else selected
    return user_input


def _registration_entry(
    registry: er.EntityRegistry, entity_id: str
) -> er.RegistryEntry | None:
    """Validate the firmware-side registration contract."""
    entry = registry.async_get(entity_id)
    if (
        entry is None
        or entry.platform != "esphome"
        or entry.original_name != BRIDGE_REGISTRATION_ORIGINAL_NAME
    ):
        return None
    return entry


class PassionWaveConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle the PassionWave config flow."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the two-step flow."""
        self._pending_data: dict[str, Any] = {}
        self._entry_title = "PassionWave Rotaryknob"
        self._catalogs: dict[str, list[dict[str, str]]] = {}
        self._library_error = False

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Create one PassionWave entry per physical dual-MCU system."""
        errors: dict[str, str] = {}
        if user_input is not None:
            registry = er.async_get(self.hass)
            registration = _registration_entry(
                registry, user_input[CONF_BRIDGE_REGISTRATION_ENTITY]
            )
            if registration is None:
                errors["base"] = "invalid_bridge_registration_entity"
            else:
                await self.async_set_unique_id(registration.unique_id)
                self._abort_if_unique_id_configured()
                user_input[CONF_BRIDGE_REGISTRATION_UNIQUE_ID] = (
                    registration.unique_id
                )
                device = (
                    dr.async_get(self.hass).async_get(registration.device_id)
                    if registration.device_id
                    else None
                )
                self._entry_title = (
                    (device.name_by_user or device.name)
                    if device
                    else registration.entity_id
                )
                self._pending_data = user_input
                try:
                    self._catalogs = await _async_load_catalogs(
                        self, user_input[CONF_MA_CONFIG_ENTRY_ID]
                    )
                except HomeAssistantError:
                    self._library_error = True
                return await self.async_step_library()

        return self.async_show_form(
            step_id="user",
            data_schema=_connection_schema(user_input),
            errors=errors,
        )

    async def async_step_library(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Select the visible Music Assistant entries."""
        if user_input is not None:
            return self.async_create_entry(
                title=self._entry_title,
                data={
                    **self._pending_data,
                    **_normalize_visibility(user_input),
                },
            )
        return self.async_show_form(
            step_id="library",
            data_schema=_library_schema(self._catalogs),
            errors={"base": "library_unavailable"} if self._library_error else {},
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Return the options flow."""
        return PassionWaveOptionsFlow(config_entry)


class PassionWaveOptionsFlow(config_entries.OptionsFlow):
    """Update PassionWave targets without YAML or a blueprint."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self._entry = config_entry
        self._pending_data: dict[str, Any] = {}
        self._catalogs: dict[str, list[dict[str, str]]] = {}
        self._library_error = False

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Show the typed target selectors."""
        errors: dict[str, str] = {}
        if user_input is not None:
            registration = _registration_entry(
                er.async_get(self.hass),
                user_input[CONF_BRIDGE_REGISTRATION_ENTITY],
            )
            if registration is None:
                errors["base"] = "invalid_bridge_registration_entity"
            else:
                user_input[CONF_BRIDGE_REGISTRATION_UNIQUE_ID] = (
                    registration.unique_id
                )
                self._pending_data = user_input
                try:
                    self._catalogs = await _async_load_catalogs(
                        self, user_input[CONF_MA_CONFIG_ENTRY_ID]
                    )
                except HomeAssistantError:
                    self._library_error = True
                return await self.async_step_library()
        defaults = {**self._entry.data, **self._entry.options}
        return self.async_show_form(
            step_id="init",
            data_schema=_connection_schema(user_input or defaults),
            errors=errors,
        )

    async def async_step_library(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Update the visible Music Assistant entries."""
        defaults = {**self._entry.data, **self._entry.options}
        if user_input is not None:
            return self.async_create_entry(
                title="",
                data={
                    **self._pending_data,
                    **_normalize_visibility(user_input),
                },
            )
        return self.async_show_form(
            step_id="library",
            data_schema=_library_schema(self._catalogs, defaults),
            errors={"base": "library_unavailable"} if self._library_error else {},
        )
