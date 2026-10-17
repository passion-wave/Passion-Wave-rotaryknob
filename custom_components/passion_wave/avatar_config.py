"""S3-owned avatar configuration; Home Assistant never replays cached options."""

from __future__ import annotations

import asyncio
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from .entity import entity_by_original_name

AVATAR_HAIR = "avatar_hair"
MORNING_AVATAR = "morning_avatar"
HAIR_OPTIONS = ("Avatar Haare Braun", "Avatar Haare Blond")
NATIVE_NAMES = {
    AVATAR_HAIR: "RotaryKnob Avatar Hair",
    MORNING_AVATAR: "RotaryKnob Morning Avatar",
}


def native_avatar_state(hass: HomeAssistant, s3_entry_id: str, key: str) -> tuple[str | None, Any]:
    """Resolve the currently live native entity belonging to this exact S3."""
    entity_id = entity_by_original_name(hass, s3_entry_id, NATIVE_NAMES[key])
    state = hass.states.get(entity_id) if entity_id else None
    if state is None:
        return entity_id, None
    if key == AVATAR_HAIR:
        return entity_id, state.state if state.state in HAIR_OPTIONS else None
    return entity_id, {"on": True, "off": False}.get(state.state)


async def async_set_avatar_setting(
    hass: HomeAssistant, s3_entry_id: str, key: str, value: str | bool,
) -> None:
    """Wait for authoritative S3 acknowledgement; offline is never success."""
    entity_id, current = native_avatar_state(hass, s3_entry_id, key)
    if entity_id is None or current is None:
        raise HomeAssistantError("The RotaryKnob display is offline or its avatar firmware is unavailable")
    if key == AVATAR_HAIR and value not in HAIR_OPTIONS:
        raise HomeAssistantError("Unknown avatar hair option")
    if key == MORNING_AVATAR and not isinstance(value, bool):
        raise HomeAssistantError("Morning avatar must be enabled or disabled")
    if value == current:
        return
    domain = "select" if key == AVATAR_HAIR else "switch"
    service = "select_option" if key == AVATAR_HAIR else "turn_on" if value else "turn_off"
    data: dict[str, Any] = {"entity_id": entity_id}
    if key == AVATAR_HAIR:
        data["option"] = value
    await hass.services.async_call(domain, service, data, blocking=True)
    for _ in range(50):
        _, reported = native_avatar_state(hass, s3_entry_id, key)
        if reported == value:
            return
        if reported is None:
            break
        await asyncio.sleep(0.1)
    raise HomeAssistantError("The RotaryKnob display did not confirm the avatar setting")
