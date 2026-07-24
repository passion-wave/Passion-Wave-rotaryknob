import os
import time

from PIL import Image, ImageChops

FLOORPLAN_REVISION_TOPIC = "passion_wave/floorplan/revision"
FLOORPLAN_BASE = (
    "/config/www/images/"
    "Muehldorferstr_Night_Lighton_Level4_4k_Innenraum.png"
)
FLOORPLAN_OUTPUT = "/config/www/passion-wave/floorplan-render/live.png"
FLOORPLAN_OUTPUT_TMP = FLOORPLAN_OUTPUT + ".tmp"
FLOORPLAN_LAYERS = {
    "light.flur": "Muehldorferstr_Night_Lighton_Level4_4k_Flur.png",
    "light.wohnzimmer": "Muehldorferstr_Night_Lighton_Level4_4k_Wohnzimmer.png",
    "light.ankleide_5spot_3": "Muehldorferstr_Night_Lighton_Level4_4k_Ankleide.png",
    "light.schlafzimmer_decke": "Muehldorferstr_Night_Lighton_Level4_4k_Schlafzimmer.png",
    "light.badezimmer_spiegel": "Muehldorferstr_Night_Lighton_Level4_4k_Badezimmer.png",
    "light.hue_color_lamp_1": "Muehldorferstr_Night_Lighton_Level4_4k_Buero.png",
    "light.glightkuche": "Muehldorferstr_Night_Lighton_Level4_4k_Küche.png",
}
FLOORPLAN_IMAGE_DIRECTORY = "/config/www/images"


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
    service.call(
        "mqtt",
        "publish",
        topic=FLOORPLAN_REVISION_TOPIC,
        payload=revision,
        retain=True,
    )
    state.set(
        "pyscript.passion_wave_floorplan_revision",
        revision,
        new_attributes={
            "friendly_name": "Passion Wave Floorplan Revision",
            "reason": reason or "state",
            "tracked_lights": 7,
            "active_light_layers": len(active_layers),
            "output": "/local/passion-wave/floorplan-render/live.png",
        },
    )


@state_trigger(
    "light.flur",
    "light.wohnzimmer",
    "light.ankleide_5spot_3",
    "light.schlafzimmer_decke",
    "light.badezimmer_spiegel",
    "light.hue_color_lamp_1",
    "light.glightkuche",
)
def passion_wave_floorplan_changed(trigger_type=None, var_name=None, **kwargs):
    _publish_floorplan_revision(var_name or trigger_type)


@time_trigger("startup")
def passion_wave_floorplan_startup():
    _publish_floorplan_revision("startup")


@time_trigger("period(0:10:00)")
def passion_wave_floorplan_periodic():
    """Also pick up replaced source images without requiring a HA restart."""
    _publish_floorplan_revision("periodic")


@service
def passion_wave_floorplan_refresh():
    """Force a new image on the rotary-knob without changing a light."""
    _publish_floorplan_revision("manual")
