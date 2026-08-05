"""Config flow for PassionWave."""

from __future__ import annotations

import asyncio
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import (
    device_registry as dr,
    entity_registry as er,
    selector,
)
from homeassistant.helpers.service_info.zeroconf import ZeroconfServiceInfo

from .const import (
    BRIDGE_PROJECT_NAME,
    BRIDGE_REGISTRATION_ORIGINAL_NAME,
    CONF_BRIDGE_HOST,
    CONF_BRIDGE_REGISTRATION_ENTITY,
    CONF_BRIDGE_REGISTRATION_UNIQUE_ID,
    CONF_MA_CONFIG_ENTRY_ID,
    CONF_MEDIA_PLAYER,
    CONF_S3_CONFIG_ENTRY_ID,
    CONF_S3_HOST,
    DOMAIN,
    ESPHOME_API_PORT,
    LIGHT_ENTITY_ORIGINAL_NAMES,
    LIGHT_SLOT_KEYS,
    LIBRARY_FILTER_KEYS,
    LIBRARY_SELECTION_LIMIT,
    MEDIA_ENTITY_ORIGINAL_NAME,
    SHOW_ALL,
    S3_PROJECT_NAME,
)
from .media import normalize_library_page
from .pairing import (
    DiscoveredEndpoint,
    PairingError,
    ProvisioningWindowClosed,
    async_discover_endpoints,
    async_secure_pair_endpoint,
    cache_discovered_endpoint,
    endpoint_is_configured,
    schedule_esphome_discovery_suppression,
)


def _connection_schema(
    hass: HomeAssistant, defaults: dict[str, Any] | None = None
) -> vol.Schema:
    values = defaults or {}

    def required(key: str, options: list[selector.SelectOptionDict]) -> vol.Marker:
        return (
            vol.Required(key, default=values[key])
            if key in values
            else vol.Required(key, default=options[0]["value"])
            if len(options) == 1
            else vol.Required(key)
        )

    registry = er.async_get(hass)

    def entity_label(entry: er.RegistryEntry) -> str:
        state = hass.states.get(entry.entity_id)
        if state and (friendly_name := state.attributes.get("friendly_name")):
            return str(friendly_name)
        return entry.name or entry.original_name or entry.entity_id

    registration_options: list[selector.SelectOptionDict] = [
        {"value": entry.entity_id, "label": entity_label(entry)}
        for entry in registry.entities.values()
        if entry.platform == "esphome"
        and entry.original_name == BRIDGE_REGISTRATION_ORIGINAL_NAME
    ]
    s3_entry_ids = {
        entry.config_entry_id
        for entry in registry.entities.values()
        if entry.platform == "esphome"
        and entry.original_name == MEDIA_ENTITY_ORIGINAL_NAME
        and entry.config_entry_id
    }
    s3_entry_options: list[selector.SelectOptionDict] = [
        {"value": entry.entry_id, "label": entry.title}
        for entry in hass.config_entries.async_entries("esphome")
        if entry.entry_id in s3_entry_ids
    ]
    ma_entry_options: list[selector.SelectOptionDict] = [
        {"value": entry.entry_id, "label": entry.title}
        for entry in hass.config_entries.async_entries("music_assistant")
    ]
    media_player_options: list[selector.SelectOptionDict] = [
        {"value": entry.entity_id, "label": entity_label(entry)}
        for entry in registry.entities.values()
        if entry.platform == "music_assistant" and entry.domain == "media_player"
    ]

    return vol.Schema(
        {
            required(
                CONF_S3_CONFIG_ENTRY_ID, s3_entry_options
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(options=s3_entry_options)
            ),
            required(
                CONF_BRIDGE_REGISTRATION_ENTITY, registration_options
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(options=registration_options)
            ),
            required(
                CONF_MA_CONFIG_ENTRY_ID, ma_entry_options
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(options=ma_entry_options)
            ),
            required(CONF_MEDIA_PLAYER, media_player_options): selector.SelectSelector(
                selector.SelectSelectorConfig(options=media_player_options)
            ),
        }
    )


def _lights_schema(
    hass: HomeAssistant, defaults: dict[str, Any] | None = None
) -> vol.Schema:
    """Build four stable, user-readable light-slot selectors."""
    values = defaults or {}
    registry = er.async_get(hass)
    options: list[selector.SelectOptionDict] = [
        {"value": "", "label": "Nicht belegt / Not assigned"}
    ]
    for entry in registry.entities.values():
        if entry.domain != "light" or entry.disabled_by is not None:
            continue
        state = hass.states.get(entry.entity_id)
        friendly_name = state.attributes.get("friendly_name") if state else None
        options.append(
            {
                "value": entry.entity_id,
                "label": str(
                    friendly_name
                    or entry.name
                    or entry.original_name
                    or entry.entity_id
                ),
            }
        )
    options[1:] = sorted(options[1:], key=lambda item: item["label"].casefold())
    known_values = {option["value"] for option in options}
    for key in LIGHT_SLOT_KEYS:
        configured = values.get(key, "")
        if configured and configured not in known_values:
            options.append(
                {
                    "value": configured,
                    "label": f"Nicht mehr verfügbar · {configured}",
                }
            )
            known_values.add(configured)

    return vol.Schema(
        {
            vol.Required(key, default=values.get(key, "")): selector.SelectSelector(
                selector.SelectSelectorConfig(options=options)
            )
            for key in LIGHT_SLOT_KEYS
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
        page = normalize_library_page(response, media_type, 0, LIBRARY_SELECTION_LIMIT)
        return media_type, page["items"]

    return dict(
        await asyncio.gather(*(load(media_type) for media_type in LIBRARY_FILTER_KEYS))
    )


def _library_schema(
    catalogs: dict[str, list[dict[str, str]]],
    defaults: dict[str, Any] | None = None,
) -> vol.Schema:
    values = defaults or {}

    def field(media_type: str) -> tuple[vol.Marker, selector.SelectSelector]:
        key = LIBRARY_FILTER_KEYS[media_type]
        configured = values.get(key, [SHOW_ALL])
        selected = [configured] if isinstance(configured, str) else list(configured)
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


def _s3_config_entry_is_valid(hass: HomeAssistant, entry_id: str) -> bool:
    """Validate that the selected ESPHome entry owns the display contract."""
    entry = hass.config_entries.async_get_entry(entry_id)
    if entry is None or entry.domain != "esphome":
        return False
    return any(
        entity.platform == "esphome"
        and entity.config_entry_id == entry_id
        and entity.original_name == MEDIA_ENTITY_ORIGINAL_NAME
        for entity in er.async_get(hass).entities.values()
    )


def _current_s3_light_defaults(hass: HomeAssistant, entry_id: str) -> dict[str, str]:
    """Adopt existing firmware targets during blueprint-to-flow migration."""
    defaults = dict.fromkeys(LIGHT_SLOT_KEYS, "")
    names_to_keys = dict(zip(LIGHT_ENTITY_ORIGINAL_NAMES, LIGHT_SLOT_KEYS, strict=True))
    for entity in er.async_get(hass).entities.values():
        key = names_to_keys.get(entity.original_name)
        if (
            key is None
            or entity.platform != "esphome"
            or entity.config_entry_id != entry_id
        ):
            continue
        state = hass.states.get(entity.entity_id)
        if state is not None and state.state.startswith("light."):
            defaults[key] = state.state
    return defaults


class PassionWaveConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle the PassionWave config flow."""

    VERSION = 4

    def __init__(self) -> None:
        """Initialize the two-step flow."""
        self._pending_data: dict[str, Any] = {}
        self._entry_title = "PassionWave Rotaryknob"
        self._catalogs: dict[str, list[dict[str, str]]] = {}
        self._library_error = False
        self._discovered_endpoints: dict[str, DiscoveredEndpoint] = {}
        self._discovery_unique_id: str | None = None
        self._suggested_s3_host: str | None = None

    async def async_step_zeroconf(
        self, discovery_info: ZeroconfServiceInfo
    ) -> ConfigFlowResult:
        """Expose one PassionWave discovery tile per physical Rotaryknob."""
        mac_address = str(discovery_info.properties.get("mac", ""))
        if not mac_address:
            return self.async_abort(reason="endpoints_not_found")

        normalized_mac = dr.format_mac(mac_address)
        project_name = str(discovery_info.properties.get("project_name", ""))
        if project_name not in {S3_PROJECT_NAME, BRIDGE_PROJECT_NAME}:
            return self.async_abort(reason="endpoints_not_found")

        host = discovery_info.hostname.removesuffix(".")
        cache_discovered_endpoint(
            self.hass,
            DiscoveredEndpoint(
                host=host,
                port=getattr(discovery_info, "port", None) or ESPHOME_API_PORT,
                project_name=project_name,
                friendly_name=str(
                    discovery_info.properties.get("friendly_name", "") or host
                ),
                mac_address=normalized_mac,
            ),
        )
        schedule_esphome_discovery_suppression(self.hass, normalized_mac)
        if project_name == BRIDGE_PROJECT_NAME:
            return self.async_abort(reason="bridge_transport")

        self._discovery_unique_id = f"rotaryknob_{normalized_mac}"
        self._suggested_s3_host = host
        s3_entry = self.hass.config_entries.async_entry_for_domain_unique_id(
            "esphome", normalized_mac
        )
        if s3_entry and any(
            entry.options.get(
                CONF_S3_CONFIG_ENTRY_ID, entry.data.get(CONF_S3_CONFIG_ENTRY_ID)
            )
            == s3_entry.entry_id
            for entry in self.hass.config_entries.async_entries(DOMAIN)
        ):
            return self.async_abort(reason="already_configured")
        await self.async_set_unique_id(self._discovery_unique_id)
        self._abort_if_unique_id_configured()

        discovered = await async_discover_endpoints(self.hass)
        self._discovered_endpoints = {item.host: item for item in discovered}
        for endpoint in discovered:
            schedule_esphome_discovery_suppression(self.hass, endpoint.mac_address)
        return await self.async_step_pair()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Start secure pairing or continue with already paired endpoints."""
        has_registration = any(
            entry.platform == "esphome"
            and entry.original_name == BRIDGE_REGISTRATION_ORIGINAL_NAME
            for entry in er.async_get(self.hass).entities.values()
        )
        discovered = await async_discover_endpoints(self.hass)
        self._discovered_endpoints = {item.host: item for item in discovered}
        if has_registration and not any(
            not endpoint_is_configured(self.hass, endpoint) for endpoint in discovered
        ):
            return await self.async_step_connection(user_input)
        return await self.async_step_pair()

    async def async_step_pair(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Pair both processors without exposing their API keys."""
        errors: dict[str, str] = {}
        if user_input is not None:
            s3 = self._discovered_endpoints.get(user_input[CONF_S3_HOST])
            bridge = self._discovered_endpoints.get(user_input[CONF_BRIDGE_HOST])
            if s3 is None or bridge is None:
                errors["base"] = "endpoint_unavailable"
            else:
                try:
                    await async_secure_pair_endpoint(self.hass, s3, S3_PROJECT_NAME)
                    await async_secure_pair_endpoint(
                        self.hass, bridge, BRIDGE_PROJECT_NAME
                    )
                except ProvisioningWindowClosed:
                    errors["base"] = "provisioning_window_closed"
                except PairingError:
                    errors["base"] = "pairing_failed"
                else:
                    # ESPHome entity setup follows config-entry creation. Allow
                    # it a short bounded interval before showing the typed
                    # PassionWave connection selectors.
                    for _ in range(20):
                        if any(
                            entry.platform == "esphome"
                            and entry.original_name == BRIDGE_REGISTRATION_ORIGINAL_NAME
                            for entry in er.async_get(self.hass).entities.values()
                        ):
                            return await self.async_step_connection()
                        await asyncio.sleep(0.5)
                    return self.async_abort(reason="pairing_complete")

        def choices(project_name: str) -> list[selector.SelectOptionDict]:
            return [
                {
                    "value": endpoint.host,
                    "label": f"{endpoint.friendly_name} · {endpoint.host}",
                }
                for endpoint in self._discovered_endpoints.values()
                if endpoint.project_name == project_name
            ]

        s3_choices = choices(S3_PROJECT_NAME)
        bridge_choices = choices(BRIDGE_PROJECT_NAME)
        if not s3_choices or not bridge_choices:
            errors["base"] = "endpoints_not_found"
        s3_hosts = {item["value"] for item in s3_choices}
        suggested_s3 = (
            self._suggested_s3_host
            if self._suggested_s3_host in s3_hosts
            else s3_choices[0]["value"]
            if len(s3_choices) == 1
            else None
        )
        s3_field = (
            vol.Required(CONF_S3_HOST, default=suggested_s3)
            if suggested_s3
            else vol.Required(CONF_S3_HOST)
        )
        return self.async_show_form(
            step_id="pair",
            data_schema=vol.Schema(
                {
                    s3_field: selector.SelectSelector(
                        selector.SelectSelectorConfig(options=s3_choices)
                    ),
                    vol.Required(CONF_BRIDGE_HOST): selector.SelectSelector(
                        selector.SelectSelectorConfig(options=bridge_choices)
                    ),
                }
            ),
            errors=errors,
        )

    async def async_step_connection(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Create one PassionWave entry per physical dual-MCU system."""
        errors: dict[str, str] = {}
        if user_input is not None:
            registry = er.async_get(self.hass)
            registration = _registration_entry(
                registry, user_input[CONF_BRIDGE_REGISTRATION_ENTITY]
            )
            if not _s3_config_entry_is_valid(
                self.hass, user_input[CONF_S3_CONFIG_ENTRY_ID]
            ):
                errors["base"] = "invalid_s3_device"
            elif registration is None:
                errors["base"] = "invalid_bridge_registration_entity"
            else:
                await self.async_set_unique_id(
                    self._discovery_unique_id or registration.unique_id
                )
                self._abort_if_unique_id_configured()
                user_input[CONF_BRIDGE_REGISTRATION_UNIQUE_ID] = registration.unique_id
                s3_entry = self.hass.config_entries.async_get_entry(
                    user_input[CONF_S3_CONFIG_ENTRY_ID]
                )
                self._entry_title = (
                    s3_entry.title if s3_entry else registration.entity_id
                )
                self._pending_data = user_input
                return await self.async_step_lights()

        return self.async_show_form(
            step_id="connection",
            data_schema=_connection_schema(self.hass, user_input),
            errors=errors,
        )

    async def async_step_lights(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Assign the four customer-facing light positions."""
        if user_input is not None:
            return self.async_create_entry(
                title=self._entry_title,
                data={
                    **self._pending_data,
                    **user_input,
                    **{key: [SHOW_ALL] for key in LIBRARY_FILTER_KEYS.values()},
                },
            )
        return self.async_show_form(
            step_id="lights",
            data_schema=_lights_schema(
                self.hass,
                _current_s3_light_defaults(
                    self.hass,
                    self._pending_data[CONF_S3_CONFIG_ENTRY_ID],
                ),
            ),
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
            if not _s3_config_entry_is_valid(
                self.hass, user_input[CONF_S3_CONFIG_ENTRY_ID]
            ):
                errors["base"] = "invalid_s3_device"
            elif registration is None:
                errors["base"] = "invalid_bridge_registration_entity"
            else:
                user_input[CONF_BRIDGE_REGISTRATION_UNIQUE_ID] = registration.unique_id
                self._pending_data = user_input
                return await self.async_step_lights()
        defaults = {**self._entry.data, **self._entry.options}
        return self.async_show_form(
            step_id="init",
            data_schema=_connection_schema(self.hass, user_input or defaults),
            errors=errors,
        )

    async def async_step_lights(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Update the four light positions before optional media filters."""
        defaults = {**self._entry.data, **self._entry.options}
        if user_input is not None:
            self._pending_data.update(user_input)
            try:
                self._catalogs = await _async_load_catalogs(
                    self, self._pending_data[CONF_MA_CONFIG_ENTRY_ID]
                )
            except HomeAssistantError:
                self._library_error = True
            return await self.async_step_library()
        return self.async_show_form(
            step_id="lights",
            data_schema=_lights_schema(self.hass, defaults),
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
