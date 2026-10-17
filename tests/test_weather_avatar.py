"""Weather quality, unit and S3-owned configuration regression coverage."""

import asyncio
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from homeassistant.exceptions import HomeAssistantError
from custom_components.passion_wave.weather_avatar import (
    CONDITIONS_KNOWN, GUST_VALID, LIQUID_RAIN, PROBABILITY_VALID,
    WET_PHASE_UNKNOWN, WIND_VALID, TEMP_VALID, PARTIAL_DATA, build_avatar_context, utc_timestamp,
)
from custom_components.passion_wave.avatar_config import (
    AVATAR_HAIR, HAIR_OPTIONS, MORNING_AVATAR, async_set_avatar_setting,
)
from custom_components.passion_wave.broker import _async_forecast_request
from custom_components.passion_wave.config_flow import PassionWaveOptionsFlow

NOW = datetime(2026, 10, 25, 6, 30, tzinfo=UTC)


def current(**attrs):
    return SimpleNamespace(state="sunny", last_updated=NOW, attributes={
        "temperature": 12, "temperature_unit": "°C", "wind_speed_unit": "km/h",
        "precipitation_unit": "mm", **attrs,
    })


def hours(**attrs):
    return [{"datetime": (NOW.replace(minute=0) + timedelta(hours=i)).isoformat(),
             "temperature": 20 - i, "condition": "sunny", **attrs}
            for i in range(5)]


def context(forecasts=None, state=None):
    return build_avatar_context(forecasts if forecasts is not None else hours(),
                                state or current(), fetched_at=int(NOW.timestamp()),
                                sequence=7, forecast_provider="met")


def test_four_hours_uses_next_complete_met_window_and_displays_its_actual_start():
    result = context()
    assert result["mode"] == 1
    assert result["start_utc"] == int(NOW.replace(minute=0).timestamp()) + 3600
    assert result["end_utc"] - result["start_utc"] == 14400
    assert result["temperature_min_tenths"] == 160
    assert result["temperature_max_tenths"] == 190
    assert result["fetched_at"] == int(NOW.timestamp())
    assert context(hours()[:-1])["mode"] == 2
    assert context(hours()[2:])["mode"] == 2


@pytest.mark.parametrize("provider", [None, "template", "unverified-provider"])
def test_unverified_provider_cannot_claim_interval_coverage(provider):
    result = build_avatar_context(hours(), current(), fetched_at=int(NOW.timestamp()),
                                  sequence=1, forecast_provider=provider)
    assert result["mode"] == 2


@pytest.mark.parametrize("invalid", [None, "not-a-temperature", float("nan"), float("inf"), True, -101, 71])
def test_bad_temperature_in_any_interval_falls_back_to_current(invalid):
    forecast = hours()
    forecast[2]["temperature"] = invalid
    result = context(forecast)
    assert result["mode"] == 2
    assert result["temperature_min_tenths"] == 120


def test_gap_duplicate_and_wrong_day_are_not_claimed_as_forecast():
    forecast = hours()
    assert context(forecast[:2] + forecast[3:])["mode"] == 2
    assert context(forecast + [forecast[2]])["mode"] == 2
    yesterday = [{**row, "datetime": (datetime.fromisoformat(row["datetime"]) - timedelta(days=1)).isoformat()}
                 for row in forecast]
    assert context(yesterday)["mode"] == 2


def test_utc_offset_and_dst_are_absolute_not_local_hour_guesses():
    assert utc_timestamp("2026-10-25T02:30:00+02:00") + 3600 == utc_timestamp("2026-10-25T02:30:00+01:00")
    assert utc_timestamp("2026-10-25T02:30:00") is None


def test_units_and_bounded_optionals_are_normalized():
    result = context(hours(temperature=68, wind_speed=10, wind_gust_speed=25,
                           precipitation=0.1, precipitation_probability=50),
                     current(temperature_unit="°F", wind_speed_unit="mph", precipitation_unit="in"))
    assert result["temperature_min_tenths"] == 200
    assert result["wind_tenths"] == 160
    assert result["gust_tenths"] == 402
    assert result["precipitation_tenths"] == 102
    assert result["flags"] & (WIND_VALID | GUST_VALID | PROBABILITY_VALID)
    assert result["flags"] & WET_PHASE_UNKNOWN
    assert not result["flags"] & LIQUID_RAIN


def test_unknown_temperature_unit_is_not_celsius_and_missing_optional_is_not_zero():
    assert not context(state=current(temperature_unit="kelvin"))["flags"] & TEMP_VALID
    result = context(hours(wind_speed=40), current(wind_speed_unit="unknown"))
    assert not result["flags"] & (WIND_VALID | GUST_VALID | PROBABILITY_VALID)


def test_partial_optional_fields_keep_known_protection_and_report_the_gap():
    forecast = hours(wind_speed=5, precipitation_probability=0)
    forecast[1]["wind_speed"] = 35
    del forecast[2]["wind_speed"]
    result = context(forecast)
    assert result["wind_tenths"] == 350
    assert result["flags"] & WIND_VALID
    assert result["flags"] & PARTIAL_DATA


@pytest.mark.parametrize("unit,value,expected", [("mi/h", 10, 160), ("ft/s", 10, 109)])
def test_official_ha_imperial_wind_units(unit, value, expected):
    assert context(hours(wind_speed=value), current(wind_speed_unit=unit))["wind_tenths"] == expected


def test_quantization_does_not_cross_outfit_or_protection_boundaries():
    result = context(hours(temperature=21.99, precipitation_probability=49.9,
                           wind_speed=19.99, wind_gust_speed=34.99))
    assert result["temperature_min_tenths"] == 219
    assert result["precipitation_probability"] == 49
    assert not result["flags"] & WET_PHASE_UNKNOWN
    assert result["wind_tenths"] == 199
    assert result["gust_tenths"] == 349


@pytest.mark.parametrize("condition", ["snowy", "hail"])
def test_solid_precipitation_does_not_invent_liquid_rain(condition):
    result = context(hours(condition=condition, precipitation=2, precipitation_probability=80))
    assert not result["flags"] & (LIQUID_RAIN | WET_PHASE_UNKNOWN)


def test_rain_lightning_hail_conditions_survive_aggregation():
    forecast = hours()
    forecast[1]["condition"] = "lightning-rainy"
    forecast[2]["condition"] = "hail"
    result = context(forecast)
    assert result["flags"] & LIQUID_RAIN
    assert result["conditions"] & (1 << 7)
    assert result["conditions"] & (1 << 5)
    assert result["first_condition"] == 7


def test_unrecognized_conditions_are_not_sunshine():
    result = context(hours(condition="alien-weather"))
    assert result["conditions"] == 1
    assert not result["flags"] & CONDITIONS_KNOWN


def test_valid_hazard_survives_missing_temperature_without_inventing_an_outfit():
    forecast = hours(temperature=None, condition="hail")
    state = current(temperature=None)
    result = context(forecast, state)
    assert result["conditions"] & (1 << 5)
    assert result["mode"] == 1
    assert not result["flags"] & TEMP_VALID


def test_current_fallback_age_cannot_be_rejuvenated_by_refetch():
    state = current()
    state.last_updated = NOW - timedelta(seconds=1201)
    assert context([], state)["mode"] == 0
    state.last_updated = NOW - timedelta(seconds=1200)
    result = context([], state)
    assert result["mode"] == 2
    assert result["provider_at"] == int(state.last_updated.timestamp())
    assert result["fetched_at"] == int(NOW.timestamp())
    state.attributes["observation_time"] = (NOW - timedelta(hours=1)).isoformat()
    state.last_updated = NOW
    assert context([], state)["mode"] == 0
    state.attributes["observation_time"] = "2026-10-25T02:30:00"
    assert context([], state)["mode"] == 0


def test_hourly_provider_still_works_when_daily_forecast_is_unsupported():
    hass = SimpleNamespace(services=SimpleNamespace(async_call=AsyncMock(side_effect=[
        HomeAssistantError("daily unsupported"), {"weather.home": {"forecast": hours()}}
    ])), states=SimpleNamespace(get=lambda _: current()))
    with patch("custom_components.passion_wave.broker._async_send_to_bridge", new=AsyncMock()) as send, \
         patch("custom_components.passion_wave.broker.er.async_get", return_value=SimpleNamespace(
             async_get=lambda _: SimpleNamespace(platform="met"))), \
         patch("custom_components.passion_wave.broker.time.time", return_value=NOW.timestamp()):
        asyncio.run(_async_forecast_request(hass, object(), {"entity": "weather.home", "seq": 9}))
    assert send.call_count == 2
    assert send.call_args.args[3]["period"] == "avatar"


def test_avatar_setting_fails_offline_without_sending_or_caching():
    hass = SimpleNamespace(services=SimpleNamespace(async_call=AsyncMock()))
    with patch("custom_components.passion_wave.avatar_config.native_avatar_state", return_value=(None, None)):
        with pytest.raises(HomeAssistantError):
            asyncio.run(async_set_avatar_setting(hass, "s3", AVATAR_HAIR, HAIR_OPTIONS[1]))
    hass.services.async_call.assert_not_called()


def test_avatar_setting_requires_authoritative_report_and_targets_exact_entity():
    hass = SimpleNamespace(services=SimpleNamespace(async_call=AsyncMock()))
    with patch("custom_components.passion_wave.avatar_config.native_avatar_state", side_effect=[
        ("select.knob_hair", HAIR_OPTIONS[0]), ("select.knob_hair", HAIR_OPTIONS[1]),
    ]):
        asyncio.run(async_set_avatar_setting(hass, "specific-s3", AVATAR_HAIR, HAIR_OPTIONS[1]))
    hass.services.async_call.assert_awaited_once_with("select", "select_option", {
        "entity_id": "select.knob_hair", "option": HAIR_OPTIONS[1],
    }, blocking=True)


def test_successful_service_call_without_s3_acknowledgement_is_not_success():
    hass = SimpleNamespace(services=SimpleNamespace(async_call=AsyncMock()))
    with patch("custom_components.passion_wave.avatar_config.native_avatar_state", return_value=(
        "select.knob_hair", HAIR_OPTIONS[0],
    )), patch("custom_components.passion_wave.avatar_config.asyncio.sleep", new=AsyncMock()):
        with pytest.raises(HomeAssistantError, match="did not confirm"):
            asyncio.run(async_set_avatar_setting(hass, "s3", AVATAR_HAIR, HAIR_OPTIONS[1]))
    assert hass.services.async_call.await_count == 1


def test_options_form_preserves_newer_local_change_when_field_was_untouched():
    entry = SimpleNamespace(data={"s3_config_entry_id": "s3"}, options={})
    flow = PassionWaveOptionsFlow(entry)
    flow.hass = SimpleNamespace()
    flow._avatar_initial = {AVATAR_HAIR: HAIR_OPTIONS[0], MORNING_AVATAR: True}
    with patch("custom_components.passion_wave.config_flow.native_avatar_state", side_effect=[
        ("select.hair", HAIR_OPTIONS[1]), ("switch.morning", True),
    ]), patch("custom_components.passion_wave.config_flow.async_set_avatar_setting", new=AsyncMock()) as set_value:
        result = asyncio.run(flow.async_step_avatar({AVATAR_HAIR: HAIR_OPTIONS[0], MORNING_AVATAR: True}))
    set_value.assert_not_called()
    assert result["data"] == {}


def test_partial_options_success_redisplays_actual_s3_state_and_retries_only_failed_field():
    entry = SimpleNamespace(data={"s3_config_entry_id": "s3"}, options={})
    flow = PassionWaveOptionsFlow(entry)
    flow.hass = SimpleNamespace()
    flow._avatar_initial = {AVATAR_HAIR: HAIR_OPTIONS[0], MORNING_AVATAR: True}
    with patch("custom_components.passion_wave.config_flow.native_avatar_state", side_effect=[
        ("select.hair", HAIR_OPTIONS[0]), ("switch.morning", True),
        ("select.hair", HAIR_OPTIONS[1]), ("switch.morning", True),
    ]), patch("custom_components.passion_wave.config_flow.async_set_avatar_setting",
              new=AsyncMock(side_effect=[None, HomeAssistantError("display disconnected")])):
        result = asyncio.run(flow.async_step_avatar({AVATAR_HAIR: HAIR_OPTIONS[1], MORNING_AVATAR: False}))
    assert result["errors"] == {"base": "avatar_unavailable"}
    defaults = {marker.schema: marker.default() for marker in result["data_schema"].schema}
    assert defaults == {AVATAR_HAIR: HAIR_OPTIONS[1], MORNING_AVATAR: True}
    assert flow._avatar_initial == defaults

    with patch("custom_components.passion_wave.config_flow.native_avatar_state", side_effect=[
        ("select.hair", HAIR_OPTIONS[1]), ("switch.morning", True),
    ]), patch("custom_components.passion_wave.config_flow.async_set_avatar_setting", new=AsyncMock()) as set_value:
        result = asyncio.run(flow.async_step_avatar({AVATAR_HAIR: HAIR_OPTIONS[1], MORNING_AVATAR: False}))
    set_value.assert_awaited_once_with(flow.hass, "s3", MORNING_AVATAR, False)
    assert result["type"] == "create_entry"
