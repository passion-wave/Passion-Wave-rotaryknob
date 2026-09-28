"""Normalize actual HA weather data into the bounded avatar protocol.

Only MET Norway's documented next_1_hours condition/precipitation semantics
are accepted as one-hour intervals. Temperature remains an hourly point
estimate, not a continuous measured minimum. Complete coverage of MET's next
four forecast hours, beginning at most one hour after fetching, is required.
Other providers and missing temperatures use the
explicit current fallback, retaining its original observation/update timestamp.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime
import math
from typing import Any

CONDITIONS = (
    "unknown", "clear-night", "cloudy", "exceptional", "fog", "hail",
    "lightning", "lightning-rainy", "partlycloudy", "pouring", "rainy",
    "snowy", "snowy-rainy", "sunny", "windy", "windy-variant",
)
TEMP_VALID = 1
CONDITIONS_KNOWN = 2
LIQUID_RAIN = 4
WET_PHASE_UNKNOWN = 8
PRECIPITATION_VALID = 32
WIND_VALID = 64
GUST_VALID = 128
PROBABILITY_VALID = 256
PARTIAL_DATA = 512
TTL_SECONDS = 20 * 60
WIND_FACTORS = {"km/h": 1, "m/s": 3.6, "mph": 1.609344,
                "mi/h": 1.609344, "ft/s": 1.09728, "kn": 1.852}


def utc_timestamp(value: object) -> int | None:
    """Accept explicit timezone offsets only; never guess the HA host zone."""
    try:
        parsed = value if isinstance(value, datetime) else datetime.fromisoformat(
            str(value).replace("Z", "+00:00")
        )
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            return None
        return int(parsed.timestamp())
    except (TypeError, ValueError, OverflowError):
        return None


def _number(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        result = float(value)
        return result if math.isfinite(result) else None
    except (TypeError, ValueError, OverflowError):
        return None


def _temperature(value: object, unit: object) -> float | None:
    result = _number(value)
    if result is None:
        return None
    if unit in ("°F", "F"):
        result = (result - 32) * 5 / 9
    elif unit not in ("°C", "C"):
        return None
    return result if -100 <= result <= 70 else None


def _scaled(value: object, unit: object, factors: Mapping[str, float]) -> float | None:
    result = _number(value)
    factor = factors.get(str(unit))
    return result * factor if result is not None and result >= 0 and factor else None


def _aggregate(
    samples: Sequence[Mapping[str, Any]], attrs: Mapping[str, Any],
) -> dict[str, int] | None:
    temperatures = [_temperature(item.get("temperature"), attrs.get("temperature_unit"))
                    for item in samples]
    if not samples:
        return None
    complete_temperatures = all(value is not None for value in temperatures)
    flags = TEMP_VALID if complete_temperatures else 0
    mask = 0
    first_condition = 0
    wind: list[float] = []
    gust: list[float] = []
    rain: list[float] = []
    probability: list[float] = []
    for index, item in enumerate(samples):
        condition = str(item.get("condition", "unknown"))
        code = CONDITIONS.index(condition) if condition in CONDITIONS else 0
        mask |= 1 << code
        if index == 0:
            first_condition = code
        if code:
            flags |= CONDITIONS_KNOWN
        if condition in ("rainy", "pouring", "lightning-rainy", "snowy-rainy"):
            flags |= LIQUID_RAIN
        speed = _scaled(item.get("wind_speed"), attrs.get("wind_speed_unit"),
                        WIND_FACTORS)
        gust_speed = _scaled(item.get("wind_gust_speed"), attrs.get("wind_speed_unit"),
                             WIND_FACTORS)
        amount = _scaled(item.get("precipitation"), attrs.get("precipitation_unit"),
                         {"mm": 1, "in": 25.4})
        chance = _number(item.get("precipitation_probability"))
        if speed is not None:
            wind.append(speed)
        if gust_speed is not None:
            gust.append(gust_speed)
        if amount is not None:
            rain.append(amount)
        if chance is not None and 0 <= chance <= 100:
            probability.append(chance)
        # HA's precipitation is phase-unspecified. Snow/hail is not liquid rain.
        if condition not in ("snowy", "hail") and (
            (amount is not None and amount > 0) or
            (chance is not None and 50 <= chance <= 100)
        ) and condition not in ("rainy", "pouring", "lightning-rainy", "snowy-rainy"):
            flags |= WET_PHASE_UNKNOWN
    if wind:
        flags |= WIND_VALID
    if gust:
        flags |= GUST_VALID
    if rain:
        flags |= PRECIPITATION_VALID
    if probability:
        flags |= PROBABILITY_VALID
    if len(wind) != len(samples) or len(probability) != len(samples) or mask & 1:
        flags |= PARTIAL_DATA
    return {
        "flags": flags,
        # The integer placeholders are never usable without TEMP_VALID. Keep
        # independent hazards when temperatures are incomplete; neutral artwork
        # can still display the valid thunder/hail notice.
        "temperature_min_tenths": math.floor(min(temperatures) * 10 + 1e-9) if complete_temperatures else 0,
        "temperature_max_tenths": math.ceil(max(temperatures) * 10 - 1e-9) if complete_temperatures else 0,
        "conditions": mask,
        "first_condition": first_condition,
        # Truncation preserves exact comparison boundaries (49.9% is not 50%,
        # 19.99 km/h is not 20). Temperatures bound the actual interval outward.
        "precipitation_probability": math.floor(max(probability, default=0)),
        "wind_tenths": min(65535, math.floor(max(wind, default=0) * 10 + 1e-9)),
        "gust_tenths": min(65535, math.floor(max(gust, default=0) * 10 + 1e-9)),
        "precipitation_tenths": min(65535, round(sum(rain) * 10)),
    }


def build_avatar_context(
    forecasts: Sequence[Mapping[str, Any]], current: object | None,
    *, fetched_at: int, sequence: int, forecast_provider: str | None = None,
) -> dict[str, int]:
    """Build a fresh context, preserving weather-data age independently."""
    context = {"schema": 1, "mode": 0, "flags": 0, "sequence": sequence,
               "fetched_at": fetched_at, "provider_at": 0,
               "start_utc": fetched_at, "end_utc": fetched_at}
    attrs = getattr(current, "attributes", {}) or {}
    # The generic HA schema describes a forecast point, not interval-start
    # semantics. Providers require an explicitly verified adapter before they
    # can assert four-hour coverage. The ordinary weather page is unaffected.
    if forecast_provider != "met":
        forecasts = []
    available = sorted([
        (timestamp, item)
        for item in forecasts if isinstance(item, Mapping)
        if (timestamp := utc_timestamp(item.get("datetime"))) is not None
        and timestamp >= fetched_at
    ], key=lambda pair: pair[0])
    start = available[0][0] if available else fetched_at
    end = start + 4 * 3600
    intervals = [(timestamp, item) for timestamp, item in available
                 if timestamp < end] if start - fetched_at <= 3600 else []
    cursor = start
    samples = []
    incomplete_forecast = None
    for timestamp, item in intervals:
        if timestamp != cursor:
            break
        samples.append(item)
        cursor = timestamp + 3600
    else:
        values = _aggregate(samples, attrs)
        if cursor >= end and values is not None:
            incomplete_forecast = {**context, **values, "mode": 1,
                                   "start_utc": start, "end_utc": end}
            # Forecast provider metadata is independent of the actual service fetch.
            incomplete_forecast["provider_at"] = utc_timestamp(attrs.get("forecast_updated_at")) or 0
            if values["flags"] & TEMP_VALID:
                return incomplete_forecast
    if current is not None and getattr(current, "state", "unknown") not in (
        "unknown", "unavailable",
    ):
        observed_raw = attrs.get("observation_time", attrs.get("datetime"))
        observed = utc_timestamp(observed_raw if observed_raw is not None
                                 else getattr(current, "last_updated", None))
        if observed is not None and 0 <= fetched_at - observed <= TTL_SECONDS:
            values = _aggregate([{**attrs, "condition": current.state}], attrs)
            if values is not None:
                context.update(values, mode=2, provider_at=observed,
                               end_utc=fetched_at + TTL_SECONDS)
                if values["flags"] & TEMP_VALID:
                    return context
    return incomplete_forecast or context
