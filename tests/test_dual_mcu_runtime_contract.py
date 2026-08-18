"""Static regression checks for the managed Dual-MCU authority boundary."""

from pathlib import Path
import unittest


ROOT = Path(__file__).parents[1]
BRIDGE = (ROOT / "esphome" / "dual-mcu-esp32-core.yaml").read_text()
S3 = (ROOT / "esphome" / "dual-mcu-s3-core.yaml").read_text()
S3_UI = (ROOT / "esphome" / "rotaryknob-s3-ui-core.yaml").read_text()
UI_NEXT = (ROOT / "esphome" / "ui_next_framework.h").read_text()
LIBRARY_PROXY = (
    ROOT / "esphome" / "dual_mcu_library_proxy.h"
).read_text()
BROKER = (ROOT / "custom_components" / "passion_wave" / "broker.py").read_text()
INTEGRATION = (
    ROOT / "custom_components" / "passion_wave" / "__init__.py"
).read_text()
POWER_POLICY = (
    ROOT / "esphome" / "responsive_power_policy.h"
).read_text()
MARCO_S3 = (ROOT / "esphome" / "managed-production-s3.yaml").read_text()
MARCO_BRIDGE = (
    ROOT / "esphome" / "managed-production-esp32.yaml"
).read_text()
TIMO_S3 = (ROOT / "esphome" / "managed-test-s3.yaml").read_text()
TIMO_BRIDGE = (ROOT / "esphome" / "managed-test-esp32.yaml").read_text()
FACTORY_S3 = (ROOT / "esphome" / "factory-s3.yaml").read_text()
FACTORY_BRIDGE = (ROOT / "esphome" / "factory-esp32.yaml").read_text()
MANAGED_COMMON = (ROOT / "esphome" / "managed-common.yaml").read_text()


class DualMcuRuntimeContractTests(unittest.TestCase):
    def test_responsive_power_policy_is_enabled_for_all_customer_profiles(self) -> None:
        self.assertIn('responsive_power_policy_enabled: "true"', MARCO_S3)
        self.assertIn('responsive_power_policy_enabled: "true"', MARCO_BRIDGE)
        self.assertIn('responsive_power_policy_enabled: "true"', TIMO_S3)
        self.assertIn('responsive_power_policy_enabled: "true"', TIMO_BRIDGE)
        self.assertIn('responsive_power_policy_enabled: "true"', FACTORY_S3)
        self.assertIn('responsive_power_policy_enabled: "true"', FACTORY_BRIDGE)

    def test_power_policy_prioritizes_active_latency(self) -> None:
        self.assertIn("WIFI_PS_NONE : WIFI_PS_MIN_MODEM", POWER_POLICY)
        self.assertIn("recent_activity || asset_active", S3_UI)
        self.assertIn("bridge_last_interaction_ms", BRIDGE)
        self.assertGreaterEqual(
            BRIDGE.count("id(bridge_s3_external_power), true, millis()"), 2
        )
        self.assertIn("battery_deep_sleep_after_inactivity_ms", S3_UI)

    def test_runtime_snapshot_contains_presentation_metadata(self) -> None:
        for key in ("title", "artist", "friendly_name", "cover_url"):
            self.assertIn(f'"{key}"', BROKER)
        self.assertIn('root["title"].is<const char *>()', BRIDGE)

    def test_bridge_has_no_compile_time_media_subscription(self) -> None:
        self.assertNotIn("${ha_player}", BRIDGE)
        for legacy_id in (
            "bridge_ha_volume",
            "bridge_ha_media_position",
            "bridge_ha_media_duration",
            "bridge_media_state_text",
            "bridge_media_title_text",
            "bridge_media_artist_text",
            "bridge_media_entity_picture_text",
        ):
            self.assertNotIn(legacy_id, BRIDGE)

    def test_staged_bridge_snapshot_never_erases_s3_metadata(self) -> None:
        self.assertIn("bridge_media_presentation_authoritative", BRIDGE)
        snapshot = BRIDGE.split("id: send_bridge_snapshot", 1)[1]
        self.assertIn(
            "if (id(bridge_media_presentation_authoritative))", snapshot
        )

    def test_reconnect_snapshot_delivers_time_before_runtime_data(self) -> None:
        snapshot = BRIDGE.split("id: send_bridge_snapshot", 1)[1]
        snapshot = snapshot.split("id: execute_bridge_volume", 1)[0]
        time_position = snapshot.index("dual_mcu::MessageType::TIME_STATE")
        status_position = snapshot.index("dual_mcu::MessageType::BRIDGE_STATUS")
        self.assertLess(time_position, status_position)

    def test_ui_next_renders_and_reports_each_uart_media_title(self) -> None:
        media_text = S3.split("case dual_mcu::MessageType::MEDIA_TEXT:", 1)[1]
        media_text = media_text.split(
            "case dual_mcu::MessageType::MEDIA_COVER_URL_BEGIN:", 1
        )[0]
        self.assertIn("id(media_title_cache) = value", media_text)
        self.assertIn("refresh_ui_next_media_runtime).execute", media_text)
        renderer = S3_UI.split("id: refresh_ui_next_media_runtime", 1)[1]
        renderer = renderer.split("id: refresh_media_ui", 1)[0]
        self.assertIn("ui_next::framework.update_media", renderer)
        self.assertIn("rendered_media_title", renderer)
        self.assertIn("ui_next_rendered_media_title_text", renderer)

    def test_same_media_target_cannot_clear_a_newer_runtime_title(self) -> None:
        target = S3_UI.split('name: "RotaryKnob Media Entity ID"', 1)[1]
        target = target.split('name: "RotaryKnob Media Label"', 1)[0]
        guard = target.index("next_target == id(media_effective_entity_id)")
        clear = target.index("id(media_title_cache).clear()")
        self.assertLess(guard, clear)

    def test_playing_without_title_requests_authoritative_recovery(self) -> None:
        self.assertIn("media_snapshot_due", S3)
        self.assertIn('id(music_state_cache) == "playing"', S3)
        self.assertIn("id(media_title_cache).empty()", S3)
        self.assertIn("dual_mcu::MessageType::SNAPSHOT_REQUEST", S3)

    def test_periodic_target_write_is_followed_by_runtime_snapshot(self) -> None:
        reconcile = INTEGRATION.split("async def reconcile()", 1)[1]
        reconcile = reconcile.split("hass.async_create_task", 1)[0]
        target_position = reconcile.index("_async_sync_s3_targets")
        runtime_position = reconcile.index("_async_push_runtime_snapshot")
        self.assertLess(target_position, runtime_position)

    def test_ui_and_clock_readiness_are_measurable(self) -> None:
        self.assertIn("ui_next_ready_time_sensor", S3_UI)
        self.assertIn("ui_next_clock_ready_time_sensor", S3_UI)
        self.assertIn("ui_next_startup_status_text", S3_UI)

    def test_authoritative_runtime_schedules_cover_screensaver(self) -> None:
        handler = S3.split("case dual_mcu::MessageType::RUNTIME_STATE:", 1)[1]
        handler = handler.split("case dual_mcu::MessageType::MEDIA_STATE:", 1)[0]
        self.assertIn("media_cover_fullscreen_due_ms", handler)
        self.assertIn("millis() + 10000", handler)

    def test_runtime_cover_replacement_invalidates_lvgl_cache(self) -> None:
        self.assertGreaterEqual(
            S3_UI.count("lv_image_cache_drop(id(media_cover_image)"), 2
        )
        self.assertGreaterEqual(
            S3_UI.count("lv_image_cache_drop(id(media_page_cover_image)"), 2
        )
        completion = S3.split(
            "else if (kind == dual_mcu::AssetKind::MEDIA_COVER)", 1
        )[1]
        self.assertIn("lv_image_cache_drop", completion)

    def test_bridge_commands_use_only_the_integration_broker(self) -> None:
        self.assertNotIn("homeassistant.service:", BRIDGE)
        self.assertNotIn("homeassistant.action:", BRIDGE)
        self.assertIn("publish_bridge_ha_command", BRIDGE)
        self.assertIn("publish_bridge_play_request", BRIDGE)

    def test_s3_diagnostics_report_received_uart_state(self) -> None:
        self.assertNotIn("_async_sync_media_runtime", INTEGRATION)
        self.assertIn("id: !remove media_runtime_state_text", S3)
        self.assertIn("media_runtime_state_text).publish_state", S3)
        self.assertIn("media_runtime_title_text).publish_state", S3)
        self.assertIn("media_runtime_artist_text).publish_state", S3)
        self.assertIn("media_runtime_cover_url_text).publish_state", S3)

    def test_s3_removes_all_direct_runtime_subscriptions(self) -> None:
        for legacy_id in (
            "ha_volume_level",
            "ha_media_position",
            "ha_media_duration",
            "ha_weather_temperature",
            "ha_weather_humidity",
            "ha_weather_wind_speed",
            "ha_weather_precipitation_probability",
            "music_state",
            "media_title",
            "media_artist",
            "media_album_artist",
            "media_shuffle_state",
            "media_repeat_state",
            "media_entity_picture",
            "media_entity_picture_local",
            "media_image_url",
        ):
            self.assertIn(f"id: !remove {legacy_id}", S3)

        for standalone_script in (
            "refresh_light_detail_catalog",
            "refresh_dynamic_media_snapshot",
            "fetch_weather",
            "fetch_rain_eta",
        ):
            self.assertIn(f"id: !remove {standalone_script}", S3)

    def test_runtime_has_one_writer_and_one_transport(self) -> None:
        self.assertNotIn("MEDIA_RUNTIME_", INTEGRATION)
        self.assertNotIn("text.set_value", INTEGRATION)
        self.assertEqual(BROKER.count("BRIDGE_RECEIVE_RUNTIME_STATE_ACTION"), 2)

    def test_missing_bridge_library_cache_recovers_on_demand(self) -> None:
        request_handler = BRIDGE.split(
            "case dual_mcu::MessageType::LIBRARY_REQUEST:", 1
        )[1].split("case dual_mcu::MessageType::LIBRARY_ACK:", 1)[0]
        self.assertIn("library_server.ready", request_handler)
        self.assertIn("fetch_bridge_library_native).execute", request_handler)
        self.assertIn("LIBRARY_CHANGED releases", request_handler)
        self.assertIn("bool ready(LibraryKind kind) const", LIBRARY_PROXY)

    def test_light_name_cycles_locally_with_immediate_render(self) -> None:
        self.assertIn("LIGHT_CYCLE", UI_NEXT)
        self.assertIn("145, 55, Action::LIGHT_CYCLE", UI_NEXT)
        self.assertIn(
            "240, 136)) action = Action::LIGHT_CYCLE", UI_NEXT
        )
        action = S3_UI.split("case ui_next::Action::LIGHT_CYCLE:", 1)[1]
        action = action.split("case ui_next::Action::LIGHT_DETAILS:", 1)[0]
        self.assertIn("cycle_light_source", action)

        cycle = S3_UI.split("- id: cycle_light_source", 1)[1]
        cycle = cycle.split("- id: select_light_source", 1)[0]
        self.assertIn("for (int offset = 1; offset <= 4; offset++)", cycle)
        self.assertIn('"light.passion_wave_light_"', cycle)
        self.assertIn("ui_next::framework.prepare_light_source", cycle)
        self.assertIn("ui_next::framework.update_light", cycle)
        self.assertNotIn("send_ha_", cycle)
        self.assertNotIn("dual_mcu::link", cycle)

    def test_wled_action_validation_stops_at_matching_target(self) -> None:
        for start, end in (
            ("async def _async_execute_ha_action", "async def _async_execute_text_action"),
            ("async def _async_execute_text_action", "async def _async_library_request"),
        ):
            handler = BROKER.split(start, 1)[1].split(end, 1)[0]
            self.assertIn("for slot, key in enumerate(LIGHT_SLOT_KEYS)", handler)
            self.assertIn("is_configured_light_entity(light_entity)", handler)
            self.assertIn('catalog["target"]', handler)
            self.assertIn("break", handler)

    def test_media_playback_is_latest_command_wins(self) -> None:
        worker = BROKER.split("async def _async_run_playback_coordinator", 1)[1]
        worker = worker.split("async def _async_play_media", 1)[0]
        execute = BROKER.split("async def _async_execute_playback", 1)[1]
        execute = execute.split("async def _async_run_playback_coordinator", 1)[0]

        self.assertIn("latest_after(handled_generation)", worker)
        self.assertIn("is_current(command.generation)", worker)
        self.assertIn("mutation_lock", worker)
        self.assertIn('"enqueue": "replace"', execute)
        self.assertIn("_async_wait_for_track", execute)

    def test_normal_mode_uses_event_updates_with_fifteen_minute_guard(self) -> None:
        self.assertIn("timedelta(minutes=15)", INTEGRATION)
        self.assertIn("id: publish_configuration_snapshot", S3_UI)
        self.assertIn("interval: 15min", S3_UI)
        number_section = S3_UI.split("number:", 1)[1].split("text:", 1)[0]
        self.assertGreaterEqual(number_section.count("update_interval: never"), 8)
        self.assertNotIn("update_interval: 1s", number_section)
        self.assertIn("900000UL", S3)
        self.assertIn("900000UL", BRIDGE)

    def test_support_mode_controls_both_processors(self) -> None:
        self.assertIn("service: support_diagnostics_on", S3_UI)
        self.assertIn("service: support_diagnostics_off", S3_UI)
        self.assertIn("action: support_diagnostics_on", BRIDGE)
        self.assertIn("action: support_diagnostics_off", BRIDGE)
        self.assertIn("support_diagnostics_enabled) ? 1000UL : 900000UL", S3)
        self.assertIn("support_diagnostics_enabled) ? 1000UL : 900000UL", BRIDGE)

    def test_diagnostics_are_disabled_by_default(self) -> None:
        for source in (S3, S3_UI, BRIDGE):
            lines = source.splitlines()
            for index, line in enumerate(lines):
                if line.strip() != "entity_category: diagnostic":
                    continue
                following = "\n".join(lines[index + 1 : index + 3])
                self.assertIn("disabled_by_default:", following)
        command = BRIDGE.split('name: "PassionWave Command Envelope"', 1)[1]
        command = command.split("- platform:", 1)[0]
        self.assertIn("disabled_by_default: false", command)

    def test_native_processor_entities_are_hidden_behind_logical_device(self) -> None:
        self.assertIn("def _hide_native_entities(", INTEGRATION)
        self.assertIn("entry.version < 4", INTEGRATION)

    def test_beta16_clean_onboarding_uses_the_selected_s3_mac(self) -> None:
        """A new entry must never use the Bridge registration as product ID."""
        config_flow = (
            ROOT / "custom_components" / "passion_wave" / "config_flow.py"
        ).read_text()
        identity = (
            ROOT / "custom_components" / "passion_wave" / "identity.py"
        ).read_text()

        self.assertIn("VERSION = 4", config_flow)
        self.assertIn("s3_product_unique_id(", config_flow)
        self.assertNotIn(
            "self._discovery_unique_id or registration.unique_id", config_flow
        )
        self.assertIn('return f"rotaryknob_{normalized}"', identity)
        self.assertNotIn("entry.version < 5", INTEGRATION)

    def test_beta16_has_one_customer_update_and_local_versions(self) -> None:
        update = (
            ROOT / "custom_components" / "passion_wave" / "update.py"
        ).read_text()
        s3 = (ROOT / "esphome" / "dual-mcu-s3-core.yaml").read_text()
        bridge = (ROOT / "esphome" / "dual-mcu-esp32-core.yaml").read_text()
        ui = (ROOT / "esphome" / "rotaryknob-s3-ui-core.yaml").read_text()
        link = (ROOT / "esphome" / "dual_mcu_link.h").read_text()

        self.assertIn("internal: true", s3)
        self.assertIn("internal: true", bridge)
        self.assertIn("passion_wave_install_firmware", ui)
        self.assertIn("passion_wave_install_firmware", bridge)
        self.assertIn("JOB_WAIT_SECONDS = 24 * 60 * 60", update)
        self.assertIn('self._phase = "waiting_for_devices"', update)
        self.assertIn("VERSION_STATE = 57", link)
        self.assertIn('"Versionen"', ui)
        self.assertIn('value = "S3 ${project_version}"', ui)

    def test_beta19_update_transport_is_observable_and_target_checked(self) -> None:
        update = (
            ROOT / "custom_components" / "passion_wave" / "update.py"
        ).read_text()

        for processor in (S3_UI, BRIDGE):
            self.assertIn("target_version: string", processor)
            self.assertIn("update.check: passion_wave_firmware_update", processor)
            self.assertIn("manifest_mismatch:", processor)

        for processor in (S3, BRIDGE):
            self.assertIn('name: "Firmware Update Status"', processor)

        self.assertIn("ota_progress:", MANAGED_COMMON)

        self.assertIn("UpdateEntityFeature.PROGRESS", update)
        self.assertIn("await self._async_run_job(raise_on_failure=True)", update)
        self.assertIn("LEGACY_ACTIVATION_TIMEOUT_SECONDS", update)


if __name__ == "__main__":
    unittest.main()
