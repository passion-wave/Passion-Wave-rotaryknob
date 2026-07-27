import os
import time

from PIL import Image, ImageChops
from homeassistant.helpers.network import get_url

FLOORPLAN_BASE = "/config/www/passion-wave/floorplan/base.png"
FLOORPLAN_OUTPUT = "/config/www/passion-wave/floorplan-render/live.png"
FLOORPLAN_OUTPUT_TMP = FLOORPLAN_OUTPUT + ".tmp"
FLOORPLAN_LAYERS = {
    "light.passion_wave_floorplan_1": "layer-1.png",
    "light.passion_wave_floorplan_2": "layer-2.png",
    "light.passion_wave_floorplan_3": "layer-3.png",
    "light.passion_wave_floorplan_4": "layer-4.png",
}
FLOORPLAN_IMAGE_DIRECTORY = "/config/www/passion-wave/floorplan"
FLOORPLAN_PUBLIC_PATH = "/local/passion-wave/floorplan-render/live.png"
RADAR_PATH_ENTITY = "sensor.scrollwheel_rain_radar_image_path"


def _absolute_asset_url(path):
    """Return an ESP32-reachable LAN URL without relying on mDNS."""
    if not path or path in ("unknown", "unavailable"):
        return ""
    if path.startswith(("http://", "https://")):
        return path
    base_url = get_url(
        hass,
        allow_internal=True,
        allow_external=False,
        allow_cloud=False,
        allow_ip=True,
    ).rstrip("/")
    return base_url + "/" + path.lstrip("/")


def _publish_radar_asset_url(reason):
    """Expose the current radar image as an absolute URL over the ESPHome API."""
    relative_url = state.get(RADAR_PATH_ENTITY)
    absolute_url = _absolute_asset_url(relative_url)
    state.set(
        "pyscript.passion_wave_radar_asset_url",
        absolute_url or "unavailable",
        new_attributes={
            "friendly_name": "Passion Wave Radar Asset URL",
            "reason": reason or "state",
            "source_entity": RADAR_PATH_ENTITY,
            "source_url": relative_url or "",
            "status": "ready" if absolute_url else "source unavailable",
        },
    )


def _render_floorplan():
    """Compose the dashboard's visible light layers into a device-sized PNG."""
    with Image.open(FLOORPLAN_BASE) as source:
        composite = source.convert("RGB")

    active_layers = []
    for entity_id, filename in FLOORPLAN_LAYERS.items():
        if state.get(entity_id) != "on":
            continue
        layer_path = os.path.join(FLOORPLAN_IMAGE_DIRECTORY, filename)
        with Image.open(layer_path) as source:
            layer = source.convert("RGB")
        # This matches the dashboard's CSS `mix-blend-mode: lighten`.
        composite = ImageChops.lighter(composite, layer)
        active_layers.append(entity_id)

    # Preserve the 4:3 floorplan geometry and keep a small safe margin for the
    # circular display bezel. Never stretch the house into a square.
    rendered = composite.resize((340, 255), Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", (360, 360), (0, 0, 0))
    canvas.paste(rendered, (10, 52))
    # The display converts the image to RGB565. Quantizing to that exact
    # channel precision before PNG compression removes data the display could
    # not show anyway and substantially reduces HTTP/UART transfer size.
    canvas = canvas.point(
        [value & 0xF8 for value in range(256)]
        + [value & 0xFC for value in range(256)]
        + [value & 0xF8 for value in range(256)]
    )
    os.makedirs(os.path.dirname(FLOORPLAN_OUTPUT), exist_ok=True)
    canvas.save(
        FLOORPLAN_OUTPUT_TMP,
        format="PNG",
        optimize=True,
        compress_level=9,
    )
    # Keep headroom below ESPHome's fixed 64 KiB online-image input buffer.
    # Dense combinations of illuminated overlays can compress worse than the
    # normal floorplan. RGB332 remains a true RGB PNG and is only used as an
    # emergency fallback when the visually better RGB565 image exceeds 60 KiB.
    if os.path.getsize(FLOORPLAN_OUTPUT_TMP) > 60 * 1024:
        canvas = canvas.point(
            [value & 0xE0 for value in range(256)]
            + [value & 0xE0 for value in range(256)]
            + [value & 0xC0 for value in range(256)]
        )
        canvas.save(
            FLOORPLAN_OUTPUT_TMP,
            format="PNG",
            optimize=True,
            compress_level=9,
        )
    os.replace(FLOORPLAN_OUTPUT_TMP, FLOORPLAN_OUTPUT)
    return active_layers


def _publish_floorplan_revision(reason):
    """Invalidate the device image after the dashboard's visible state changed."""
    # Group scenes and automations commonly update several lights together.
    # The task name makes the latest invocation replace an older pending one,
    # so the ESP32/S3 pair renders only the settled state.
    task.unique("passion_wave_floorplan_revision")
    task.sleep(0.30)
    active_layers = _render_floorplan()
    revision = str(time.time_ns())
    asset_url = _absolute_asset_url(
        FLOORPLAN_PUBLIC_PATH + "?v=" + revision
    )
    state.set(
        "pyscript.passion_wave_floorplan_revision",
        revision,
        new_attributes={
            "friendly_name": "Passion Wave Floorplan Revision",
            "reason": reason or "state",
            "tracked_lights": len(FLOORPLAN_LAYERS),
            "active_light_layers": len(active_layers),
            "output": FLOORPLAN_PUBLIC_PATH,
            "asset_url": asset_url,
        },
    )


@state_trigger(
    "light.passion_wave_floorplan_1",
    "light.passion_wave_floorplan_2",
    "light.passion_wave_floorplan_3",
    "light.passion_wave_floorplan_4",
)
def passion_wave_floorplan_changed(trigger_type=None, var_name=None, **kwargs):
    _publish_floorplan_revision(var_name or trigger_type)


@state_trigger(RADAR_PATH_ENTITY)
def passion_wave_radar_changed(trigger_type=None, var_name=None, **kwargs):
    _publish_radar_asset_url(var_name or trigger_type)


@time_trigger("startup")
def passion_wave_floorplan_startup():
    _publish_radar_asset_url("startup")
    _publish_floorplan_revision("startup")


@time_trigger("period(0:10:00)")
def passion_wave_floorplan_periodic():
    """Also pick up replaced source images without requiring a HA restart."""
    _publish_floorplan_revision("periodic")


@service
def passion_wave_floorplan_refresh():
    """Force a new image on the rotary-knob without changing a light."""
    _publish_floorplan_revision("manual")
