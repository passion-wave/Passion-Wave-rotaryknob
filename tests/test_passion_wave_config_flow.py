"""Focused tests for the PassionWave customer target flow."""

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import voluptuous as vol

from custom_components.passion_wave import _apply_processor_titles
from custom_components.passion_wave.config_flow import (
    PassionWaveConfigFlow,
    _assignment_error,
    _abort_matching_discovery_flows,
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
    CONF_PRODUCT_NAME,
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
        self.updated = []

    def async_entries(self, domain):
        return [entry for entry in self._entries if entry.domain == domain]

    def async_get_entry(self, entry_id):
        return next(
            (entry for entry in self._entries if entry.entry_id == entry_id),
            None,
        )

    def async_update_entry(self, entry, **changes):
        self.updated.append((entry.entry_id, changes))
        for key, value in changes.items():
            setattr(entry, key, value)


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
    unique_id=None,
):
    return SimpleNamespace(
        entity_id=entity_id,
        domain=entity_id.split(".", 1)[0],
        platform=platform,
        original_name=original_name,
        config_entry_id=config_entry_id,
        disabled_by=disabled_by,
        name=None,
        unique_id=unique_id,
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


def test_manual_onboarding_aborts_only_matching_discovery_flow():
    """A matching Zeroconf dialog must not block an explicit user flow."""
    progress = [
        {
            "flow_id": "manual-flow",
            "context": {
                "source": "user",
                "unique_id": "rotaryknob_20:6e:f1:a1:42:a4",
            },
        },
        {
            "flow_id": "marco-discovery",
            "context": {
                "source": "zeroconf",
                "unique_id": "rotaryknob_20:6e:f1:a1:42:a4",
            },
        },
        {
            "flow_id": "timo-discovery",
            "context": {
                "source": "zeroconf",
                "unique_id": "rotaryknob_20:6e:f1:a1:3c:8c",
            },
        },
    ]
    manager = SimpleNamespace(
        async_progress_by_handler=lambda handler, include_uninitialized: progress,
        async_abort=lambda flow_id: aborted.append(flow_id),
    )
    aborted = []
    hass = SimpleNamespace(config_entries=SimpleNamespace(flow=manager))

    _abort_matching_discovery_flows(
        hass,
        "manual-flow",
        "rotaryknob_20:6e:f1:a1:42:a4",
    )

    assert aborted == ["marco-discovery"]


def test_connection_schema_exposes_all_customer_assignments():
    """Display, Bridge and Music Assistant choices remain visible."""
    entities = {
        "text.media": _entity(
            "text.media",
            platform="esphome",
            original_name=MEDIA_ENTITY_ORIGINAL_NAME.replace(
                "Rotaryknob", "RotaryKnob"
            ),
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
                "text.registration": _state("", "RotaryKnob Bridge registration"),
                "media_player.living_room": _state("idle", "Living room"),
            }
        ),
        config_entries=FakeConfigEntries(
            [
                SimpleNamespace(
                    entry_id="s3-entry",
                    domain="esphome",
                    title="PassionWave RotaryKnob",
                    unique_id="20:6e:f1:a1:3c:8c",
                    data={"host": "timo-display.local"},
                ),
                SimpleNamespace(
                    entry_id="ma-entry",
                    domain="music_assistant",
                    title="Music Assistant",
                    unique_id="ma-entry",
                    data={},
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


def test_connection_schema_hides_processors_owned_by_another_product():
    """An assigned Marco processor cannot be selected while creating Timo."""
    entities = {
        "text.timo_media": _entity(
            "text.timo_media",
            platform="esphome",
            original_name=MEDIA_ENTITY_ORIGINAL_NAME,
            config_entry_id="s3-timo",
        ),
        "text.marco_media": _entity(
            "text.marco_media",
            platform="esphome",
            original_name=MEDIA_ENTITY_ORIGINAL_NAME,
            config_entry_id="s3-marco",
        ),
        "text.timo_registration": _entity(
            "text.timo_registration",
            platform="esphome",
            original_name=BRIDGE_REGISTRATION_ORIGINAL_NAME,
            config_entry_id="bridge-timo",
            unique_id="44:1d:64:91:8d:3c-registration",
        ),
        "text.marco_registration": _entity(
            "text.marco_registration",
            platform="esphome",
            original_name=BRIDGE_REGISTRATION_ORIGINAL_NAME,
            config_entry_id="bridge-marco",
            unique_id="44:1d:64:91:86:b4-registration",
        ),
    }
    entries = [
        SimpleNamespace(
            entry_id="s3-timo", domain="esphome", title="Timo", unique_id="a13c8c",
            data={"host": "timo-display.local"}, options={},
        ),
        SimpleNamespace(
            entry_id="s3-marco", domain="esphome", title="Marco", unique_id="a142a4",
            data={"host": "marco-display.local"}, options={},
        ),
        SimpleNamespace(
            entry_id="bridge-timo", domain="esphome", title="Timo Bridge",
            unique_id="918d3c", data={"host": "timo-bridge.local"}, options={},
        ),
        SimpleNamespace(
            entry_id="bridge-marco", domain="esphome", title="Marco Bridge",
            unique_id="9186b4", data={"host": "marco-bridge.local"}, options={},
        ),
        SimpleNamespace(
            entry_id="pw-marco", domain="passion_wave", title="Marco",
            unique_id="rotaryknob_a142a4",
            data={
                CONF_S3_CONFIG_ENTRY_ID: "s3-marco",
                CONF_BRIDGE_REGISTRATION_ENTITY: "text.marco_registration",
            },
            options={},
        ),
    ]
    hass = SimpleNamespace(
        states=FakeStates(
            {
                "text.timo_registration": _state(""),
                "text.marco_registration": _state("pw-marco"),
            }
        ),
        config_entries=FakeConfigEntries(entries),
    )

    with patch(
        "custom_components.passion_wave.config_flow.er.async_get",
        return_value=SimpleNamespace(entities=entities),
    ):
        schema = _connection_schema(hass)

    option_sets = {
        marker.schema: field.config["options"]
        for marker, field in schema.schema.items()
        if "options" in field.config
    }
    assert [item["value"] for item in option_sets[CONF_S3_CONFIG_ENTRY_ID]] == [
        "s3-timo"
    ]
    assert [
        item["value"]
        for item in option_sets[CONF_BRIDGE_REGISTRATION_ENTITY]
    ] == ["text.timo_registration"]
    assert "DISPLAY / S3 — Timo — ID A13C8C — timo-display.local" in {
        item["label"] for item in option_sets[CONF_S3_CONFIG_ENTRY_ID]
    }
    assert any(
        item["label"].startswith("BRIDGE / ESP32 —")
        and item["label"].endswith("timo-bridge.local")
        for item in option_sets[CONF_BRIDGE_REGISTRATION_ENTITY]
    )


def test_owned_bridge_is_rejected_and_current_options_owner_is_allowed():
    """The config flow cannot overwrite Marco, while Marco may keep its Bridge."""
    marco = SimpleNamespace(
        entry_id="pw-marco",
        domain="passion_wave",
        title="Marco",
        data={CONF_BRIDGE_REGISTRATION_ENTITY: "text.marco_registration"},
        options={},
    )
    hass = SimpleNamespace(
        states=FakeStates({"text.marco_registration": _state("pw-marco")}),
        config_entries=FakeConfigEntries([marco]),
    )
    selection = {
        CONF_S3_CONFIG_ENTRY_ID: "s3-timo",
        CONF_BRIDGE_REGISTRATION_ENTITY: "text.marco_registration",
    }

    assert _assignment_error(hass, selection, owner_entry_id=None) == (
        "bridge_already_owned"
    )
    assert _assignment_error(hass, selection, owner_entry_id="pw-marco") is None


def test_connection_requires_final_processor_confirmation():
    """No new entry proceeds to mutable setup before identities are confirmed."""
    registration = _entity(
        "text.timo_registration",
        platform="esphome",
        original_name=BRIDGE_REGISTRATION_ORIGINAL_NAME,
        config_entry_id="bridge-timo",
        unique_id="918d3c-registration",
    )
    registry = SimpleNamespace(
        entities={
            registration.entity_id: registration,
            "text.timo_media": _entity(
                "text.timo_media",
                platform="esphome",
                original_name=MEDIA_ENTITY_ORIGINAL_NAME,
                config_entry_id="s3-timo",
            ),
        },
        async_get=lambda entity_id: (
            registration if entity_id == registration.entity_id else None
        ),
    )
    entries = [
        SimpleNamespace(
            entry_id="s3-timo", domain="esphome", title="Timo Display",
            unique_id="a13c8c", data={"host": "timo-display.local"}, options={},
        ),
        SimpleNamespace(
            entry_id="bridge-timo", domain="esphome", title="Timo Bridge",
            unique_id="918d3c", data={"host": "timo-bridge.local"}, options={},
        ),
    ]
    hass = SimpleNamespace(
        states=FakeStates({registration.entity_id: _state("", "Timo Bridge")}),
        config_entries=FakeConfigEntries(entries),
    )
    flow = PassionWaveConfigFlow()
    flow.hass = hass
    flow.async_set_unique_id = AsyncMock()
    flow._abort_if_unique_id_configured = lambda: None
    user_input = {
        CONF_PRODUCT_NAME: "Wohnzimmer",
        CONF_S3_CONFIG_ENTRY_ID: "s3-timo",
        CONF_BRIDGE_REGISTRATION_ENTITY: registration.entity_id,
        CONF_MA_CONFIG_ENTRY_ID: "ma-entry",
        CONF_MEDIA_PLAYER: "media_player.move_2",
    }

    with (
        patch(
            "custom_components.passion_wave.config_flow.er.async_get",
            return_value=registry,
        ),
        patch(
            "custom_components.passion_wave.config_flow._s3_config_entry_is_valid",
            return_value=True,
        ),
        patch(
            "custom_components.passion_wave.config_flow.s3_product_unique_id",
            return_value="rotaryknob_a13c8c",
        ),
        patch(
            "custom_components.passion_wave.config_flow._abort_matching_discovery_flows"
        ),
    ):
        result = asyncio.run(flow.async_step_connection(user_input))

    assert result["type"] == "form"
    assert result["step_id"] == "confirm"
    assert result["description_placeholders"]["display"].startswith(
        "Wohnzimmer_rotaryknob_Display ← DISPLAY / S3"
    )
    assert result["description_placeholders"]["bridge"].startswith(
        "Wohnzimmer_rotaryknob_Bridge ← BRIDGE / ESP32"
    )
    assert flow._pending_data[CONF_BRIDGE_REGISTRATION_ENTITY] == (
        "text.timo_registration"
    )


def test_one_product_name_labels_both_esphome_processors():
    """The chosen customer name becomes two role-specific HA entry titles."""
    s3 = SimpleNamespace(
        entry_id="s3-timo", domain="esphome", title="PassionWave RotaryKnob"
    )
    bridge = SimpleNamespace(
        entry_id="bridge-timo",
        domain="esphome",
        title="PassionWave RotaryKnob Bridge",
    )
    manager = FakeConfigEntries([s3, bridge])
    registration = _entity(
        "text.timo_registration",
        platform="esphome",
        original_name=BRIDGE_REGISTRATION_ORIGINAL_NAME,
        config_entry_id="bridge-timo",
    )
    registry = SimpleNamespace(
        async_get=lambda entity_id: (
            registration if entity_id == registration.entity_id else None
        )
    )
    hass = SimpleNamespace(config_entries=manager)
    entry = SimpleNamespace(
        entry_id="pw-timo",
        title="PassionWave RotaryKnob",
        data={
            CONF_PRODUCT_NAME: "Wohnzimmer",
            CONF_S3_CONFIG_ENTRY_ID: "s3-timo",
            CONF_BRIDGE_REGISTRATION_ENTITY: registration.entity_id,
        },
        options={},
    )

    with patch(
        "custom_components.passion_wave.er.async_get", return_value=registry
    ):
        _apply_processor_titles(hass, entry)

    assert s3.title == "Wohnzimmer_rotaryknob_Display"
    assert bridge.title == "Wohnzimmer_rotaryknob_Bridge"
    assert entry.title == "Wohnzimmer_rotaryknob"
    assert manager.updated == [
        ("s3-timo", {"title": "Wohnzimmer_rotaryknob_Display"}),
        ("bridge-timo", {"title": "Wohnzimmer_rotaryknob_Bridge"}),
        ("pw-timo", {"title": "Wohnzimmer_rotaryknob"}),
    ]


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
    """Four ordered positions accept real lights and omitted empty slots."""
    light = _entity("light.vitrine", platform="hue")
    registry = SimpleNamespace(entities={light.entity_id: light})
    hass = SimpleNamespace(
        states=FakeStates({light.entity_id: _state("off", "Vitrine")})
    )

    with patch(
        "custom_components.passion_wave.config_flow.er.async_get",
        return_value=registry,
    ):
        schema = _lights_schema(hass)
        result = schema({CONF_LIGHT_SLOT_1: "light.vitrine"})

    assert result[CONF_LIGHT_SLOT_1] == "light.vitrine"
    assert result[CONF_LIGHT_SLOT_2] == ""
    assert result[CONF_LIGHT_SLOT_3] == ""
    assert result[CONF_LIGHT_SLOT_4] == ""
    assert all(isinstance(marker, vol.Optional) for marker in schema.schema)


def test_existing_s3_light_targets_become_onboarding_defaults():
    """A retired blueprint's existing target values are adopted."""
    entities = {}
    states = {}
    for index, original_name in enumerate(LIGHT_ENTITY_ORIGINAL_NAMES, start=1):
        entity_id = f"text.light_slot_{index}"
        entities[entity_id] = _entity(
            entity_id,
            platform="esphome",
            original_name=original_name.replace("Rotaryknob", "RotaryKnob"),
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
