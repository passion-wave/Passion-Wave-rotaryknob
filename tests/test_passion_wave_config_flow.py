"""Focused tests for the PassionWave customer target flow."""

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from custom_components.passion_wave.config_flow import (
    PassionWaveConfigFlow,
    _connection_schema,
    _current_s3_light_defaults,
    _lights_schema,
)
from custom_components.passion_wave.const import (
    BRIDGE_PROJECT_NAME,
    BRIDGE_REGISTRATION_ORIGINAL_NAME,
    CONF_BRIDGE_REGISTRATION_ENTITY,
    CONF_LIGHT_SLOT_1,
    CONF_LIGHT_SLOT_2,
    CONF_LIGHT_SLOT_3,
    CONF_LIGHT_SLOT_4,
    CONF_MA_CONFIG_ENTRY_ID,
    CONF_MEDIA_PLAYER,
    CONF_S3_CONFIG_ENTRY_ID,
    LIGHT_ENTITY_ORIGINAL_NAMES,
    MEDIA_ENTITY_ORIGINAL_NAME,
)
from custom_components.passion_wave.entity import target_options
from custom_components.passion_wave.pairing import (
    async_suppress_pending_esphome_discovery,
)


class FakeStates:
    """Small state-machine subset used by schema builders."""

    def __init__(self, states):
        self._states = states

    def get(self, entity_id):
        return self._states.get(entity_id)


class FakeConfigEntries:
    """Small config-entry manager subset used by schema builders."""

    def __init__(self, entries):
        self._entries = entries

    def async_entries(self, domain):
        return [entry for entry in self._entries if entry.domain == domain]

    def async_get_entry(self, entry_id):
        return next(
            (entry for entry in self._entries if entry.entry_id == entry_id),
            None,
        )


class FakeFlowManager:
    """Config-flow subset that exposes a delayed ESPHome race."""

    def __init__(self, mac_address):
        self._mac_address = mac_address
        self._polls = 0
        self.aborted = []

    def async_progress_by_handler(self, handler, *, include_uninitialized):
        assert handler == "esphome"
        assert include_uninitialized is True
        self._polls += 1
        if self._polls < 3 or self.aborted:
            return []
        return [
            {
                "flow_id": "delayed-esphome-flow",
                "context": {"unique_id": self._mac_address},
            }
        ]

    def async_abort(self, flow_id):
        self.aborted.append(flow_id)


def _entity(
    entity_id,
    *,
    platform,
    original_name=None,
    config_entry_id=None,
    disabled_by=None,
):
    return SimpleNamespace(
        entity_id=entity_id,
        domain=entity_id.split(".", 1)[0],
        platform=platform,
        original_name=original_name,
        config_entry_id=config_entry_id,
        disabled_by=disabled_by,
        name=None,
    )


def _state(value, friendly_name=None):
    return SimpleNamespace(
        state=value,
        attributes=({"friendly_name": friendly_name} if friendly_name else {}),
    )


def test_bridge_discovery_stays_hidden_behind_passion_wave():
    """The Bridge matcher suppresses ESPHome without a second customer tile."""
    flow = PassionWaveConfigFlow()
    flow.hass = SimpleNamespace()
    discovery_info = SimpleNamespace(
        properties={
            "mac": "44:1d:64:91:8d:3c",
            "project_name": BRIDGE_PROJECT_NAME,
        },
        hostname="passionwave-knob-bridge-918d3c.local.",
    )

    with (
        patch(
            "custom_components.passion_wave.config_flow."
            "schedule_esphome_discovery_suppression"
        ) as suppress,
        patch(
            "custom_components.passion_wave.config_flow.cache_discovered_endpoint"
        ) as cache_endpoint,
    ):
        result = asyncio.run(flow.async_step_zeroconf(discovery_info))

    assert result["type"] == "abort"
    assert result["reason"] == "bridge_transport"
    suppress.assert_called_once_with(flow.hass, "44:1d:64:91:8d:3c")
    cached = cache_endpoint.call_args.args[1]
    assert cached.host == "passionwave-knob-bridge-918d3c.local"
    assert cached.project_name == BRIDGE_PROJECT_NAME


def test_delayed_esphome_discovery_is_suppressed():
    """A native ESPHome tile appearing after PassionWave is still removed."""
    mac_address = "44:1d:64:91:8d:3c"
    flow_manager = FakeFlowManager(mac_address)
    hass = SimpleNamespace(
        config_entries=SimpleNamespace(flow=flow_manager),
    )

    with (
        patch(
            "custom_components.passion_wave.pairing.asyncio.sleep",
            new=AsyncMock(),
        ),
        patch(
            "custom_components.passion_wave.pairing._existing_esphome_entry",
            side_effect=[None, None, None, object()],
        ),
    ):
        asyncio.run(async_suppress_pending_esphome_discovery(hass, mac_address))

    assert flow_manager.aborted == ["delayed-esphome-flow"]


def test_connection_schema_exposes_all_customer_assignments():
    """Display, Bridge and Music Assistant choices remain visible."""
    entities = {
        "text.media": _entity(
            "text.media",
            platform="esphome",
            original_name=MEDIA_ENTITY_ORIGINAL_NAME,
            config_entry_id="s3-entry",
        ),
        "text.registration": _entity(
            "text.registration",
            platform="esphome",
            original_name=BRIDGE_REGISTRATION_ORIGINAL_NAME,
            config_entry_id="bridge-entry",
        ),
        "media_player.living_room": _entity(
            "media_player.living_room",
            platform="music_assistant",
            config_entry_id="ma-entry",
        ),
    }
    registry = SimpleNamespace(entities=entities)
    hass = SimpleNamespace(
        states=FakeStates(
            {
                "text.registration": _state("", "Rotaryknob Bridge registration"),
                "media_player.living_room": _state("idle", "Living room"),
            }
        ),
        config_entries=FakeConfigEntries(
            [
                SimpleNamespace(
                    entry_id="s3-entry",
                    domain="esphome",
                    title="PassionWave Rotaryknob",
                ),
                SimpleNamespace(
                    entry_id="ma-entry",
                    domain="music_assistant",
                    title="Music Assistant",
                ),
            ]
        ),
    )

    with patch(
        "custom_components.passion_wave.config_flow.er.async_get",
        return_value=registry,
    ):
        result = _connection_schema(hass)(
            {
                CONF_S3_CONFIG_ENTRY_ID: "s3-entry",
                CONF_BRIDGE_REGISTRATION_ENTITY: "text.registration",
                CONF_MA_CONFIG_ENTRY_ID: "ma-entry",
                CONF_MEDIA_PLAYER: "media_player.living_room",
            }
        )

    assert result[CONF_S3_CONFIG_ENTRY_ID] == "s3-entry"
    assert result[CONF_BRIDGE_REGISTRATION_ENTITY] == "text.registration"
    assert result[CONF_MA_CONFIG_ENTRY_ID] == "ma-entry"
    assert result[CONF_MEDIA_PLAYER] == "media_player.living_room"


def test_connection_form_routes_submit_to_connection_step():
    """Submitting assignments must not restart the user/pairing step."""
    registry = SimpleNamespace(entities={})
    hass = SimpleNamespace(
        states=FakeStates({}),
        config_entries=FakeConfigEntries([]),
    )
    flow = PassionWaveConfigFlow()
    flow.hass = hass

    with patch(
        "custom_components.passion_wave.config_flow.er.async_get",
        return_value=registry,
    ):
        result = asyncio.run(flow.async_step_connection())

    assert result["step_id"] == "connection"


def test_light_schema_supports_order_and_empty_positions():
    """Four ordered positions accept real lights and explicit empty slots."""
    light = _entity("light.vitrine", platform="hue")
    registry = SimpleNamespace(entities={light.entity_id: light})
    hass = SimpleNamespace(
        states=FakeStates({light.entity_id: _state("off", "Vitrine")})
    )

    with patch(
        "custom_components.passion_wave.config_flow.er.async_get",
        return_value=registry,
    ):
        result = _lights_schema(hass)(
            {
                CONF_LIGHT_SLOT_1: "light.vitrine",
                CONF_LIGHT_SLOT_2: "",
                CONF_LIGHT_SLOT_3: "",
                CONF_LIGHT_SLOT_4: "",
            }
        )

    assert result[CONF_LIGHT_SLOT_1] == "light.vitrine"
    assert result[CONF_LIGHT_SLOT_2] == ""


def test_existing_s3_light_targets_become_onboarding_defaults():
    """A retired blueprint's existing target values are adopted."""
    entities = {}
    states = {}
    for index, original_name in enumerate(LIGHT_ENTITY_ORIGINAL_NAMES, start=1):
        entity_id = f"text.light_slot_{index}"
        entities[entity_id] = _entity(
            entity_id,
            platform="esphome",
            original_name=original_name,
            config_entry_id="s3-entry",
        )
        states[entity_id] = _state(f"light.customer_{index}")
    registry = SimpleNamespace(entities=entities)
    hass = SimpleNamespace(states=FakeStates(states))

    with patch(
        "custom_components.passion_wave.config_flow.er.async_get",
        return_value=registry,
    ):
        defaults = _current_s3_light_defaults(hass, "s3-entry")

    assert defaults == {
        CONF_LIGHT_SLOT_1: "light.customer_1",
        CONF_LIGHT_SLOT_2: "light.customer_2",
        CONF_LIGHT_SLOT_3: "light.customer_3",
        CONF_LIGHT_SLOT_4: "light.customer_4",
    }


def test_device_select_options_disambiguate_duplicate_friendly_names():
    """Device-page selects stay understandable without losing stable IDs."""
    first = _entity("light.first", platform="hue")
    second = _entity("light.second", platform="matter")
    registry = SimpleNamespace(
        entities={first.entity_id: first, second.entity_id: second}
    )
    hass = SimpleNamespace(
        config=SimpleNamespace(language="de"),
        states=FakeStates(
            {
                first.entity_id: _state("off", "Leselicht"),
                second.entity_id: _state("on", "Leselicht"),
            }
        ),
    )

    with patch(
        "custom_components.passion_wave.entity.er.async_get",
        return_value=registry,
    ):
        options = target_options(hass, domain="light", include_unassigned=True)

    assert options["Nicht belegt"] == ""
    assert options["Leselicht · light.first"] == "light.first"
    assert options["Leselicht · light.second"] == "light.second"
