#!/usr/bin/env python3
"""Export reviewed atlas cells at final display size and embed baseline JPEGs.

The source cell mapping is deliberate: generation order is not a weather rule.
No generative edits, runtime resizing or network download occurs in this step.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "assets/weather-avatar"
BANDS = ("hot", "warm", "mild", "cool", "cold", "frost")
VARIANTS = ("brown_brown", "blond_hazel")
BACKGROUND = (7, 9, 11)
# Generator output layouts were inspected, rather than assuming requested grids.
LAYOUTS = {
    "dry": (4, (0, 310, 615, 925)),
    "wind": (4, (0, 360, 720, 1086)),
    "wet": (6, (0, 444, 875)),
    "snow": (6, (0, 460, 930)),
}
# Identical clothing is used for both identities. Thin wind shells cover both
# hot and warm bands. Warm wet/snow share light waterproof clothing; using a
# separate weather symbol must never alter the thermal layer.
CELLS = {
    "dry": [("dry", x) for x in (0, 1, 2, 3)] + [("wind", 4), ("wind", 5)] +
           [("dry", x) for x in (8, 9, 10, 11)] + [("wind", 10), ("wind", 11)],
    "wind": [("wind", x) for x in (1, 1, 2, 3, 4, 5, 7, 7, 8, 9, 10, 11)],
    "wet": [("wet", x) for x in range(12)],
    "snow": [("wet", 0), ("wet", 1)] + [("snow", x) for x in (2, 3, 4, 5)] +
            [("wet", 6), ("wet", 7)] + [("snow", x) for x in (8, 9, 10, 11)],
}


def export_cell(atlas: str, index: int) -> tuple[Image.Image, list[int]]:
    source = Image.open(ART / "sources" / f"{atlas}.png").convert("RGBA")
    matte = Image.new("RGBA", source.size, BACKGROUND + (255,))
    matte.alpha_composite(source)
    source = matte.convert("RGB")
    columns, rows = LAYOUTS[atlas]
    row, column = divmod(index, columns)
    region = [round(column * source.width / columns), rows[row],
              round((column + 1) * source.width / columns), rows[row + 1]]
    cell = source.crop(region)
    # A luminance threshold locates the full-body bounding rectangle only. It
    # does not replace or erase pixels inside the artwork.
    mask = cell.convert("L").point(lambda value: 255 if value > 45 else 0)
    bounds = mask.getbbox()
    if bounds is None:
        raise ValueError(f"Empty source cell: {atlas}/{index}")
    left, top, right, bottom = bounds
    cell = cell.crop((max(0, left - 4), max(0, top - 4),
                      min(cell.width, right + 4), min(cell.height, bottom + 4)))
    scale = min(198 / cell.height, 170 / cell.width)
    cell = cell.resize((round(cell.width * scale), round(cell.height * scale)), Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", (368, 368), BACKGROUND)
    canvas.paste(cell, ((368 - cell.width) // 2, 87 + (198 - cell.height) // 2))
    return canvas, region


def main() -> None:
    entries = []
    images = []
    for protection, cells in CELLS.items():
        for index, (atlas, cell) in enumerate(cells):
            variant, band = VARIANTS[index // 6], BANDS[index % 6]
            images.append((f"{variant}/{band}-{protection}", atlas, cell, variant, band, protection))
    images.extend([
        ("brown_brown/neutral", "dry", 2, VARIANTS[0], None, "neutral"),
        ("blond_hazel/neutral", "dry", 10, VARIANTS[1], None, "neutral"),
        ("brown_brown/hot-sunhat", "snow", 0, VARIANTS[0], "hot", "sunhat"),
        ("blond_hazel/hot-sunhat", "snow", 6, VARIANTS[1], "hot", "sunhat"),
    ])
    blobs = {}
    for index, (key, atlas, cell, variant, band, protection) in enumerate(images):
        image, region = export_cell(atlas, cell)
        destination = ART / "images" / f"{key}.jpg"
        destination.parent.mkdir(parents=True, exist_ok=True)
        image.save(destination, quality=90, subsampling=0, optimize=False, progressive=False)
        data = destination.read_bytes()
        sha = hashlib.sha256(data).hexdigest()
        blobs.setdefault(sha, data)
        entries.append({"index": index, "key": key, "variant": variant,
                        "thermal_band": band, "protection": protection,
                        "file": str(destination.relative_to(ART)), "width": 368, "height": 368,
                        "bytes": len(data), "sha256": sha, "source": f"sources/{atlas}.png",
                        "source_cell": cell, "source_region": region})
    manifest = {"schema_version": 1, "generator": "built-in image_gen",
                "exporter": "tools/export-weather-avatar.py", "native_size": [368, 368],
                "viewport": [360, 360], "total_file_bytes": sum(e["bytes"] for e in entries),
                "embedded_unique_bytes": sum(map(len, blobs.values())),
                "decoded_rgb565_double_buffer_bytes": 368 * 368 * 2 * 2,
                "sources": {name: hashlib.sha256((ART / "sources" / f"{name}.png").read_bytes()).hexdigest()
                            for name in LAYOUTS}, "images": entries}
    (ART / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    (ART / "SHA256SUMS").write_text("".join(f'{e["sha256"]}  {e["file"]}\n' for e in entries))
    # Generated header is committed. Builds consume only these immutable bytes;
    # JPEG export library/platform versions cannot alter firmware during CI.
    lines = ["// Generated by tools/export-weather-avatar.py; do not edit.", "#pragma once",
             "#include <cstddef>", "#include <cstdint>", "namespace weather_avatar::assets {",
             "struct Image { const uint8_t *data; size_t size; };"]
    names = {}
    for index, (sha, data) in enumerate(blobs.items()):
        name = f"jpeg_{index}"
        names[sha] = name
        lines.append(f"inline constexpr uint8_t {name}[] = {{")
        lines.extend("  " + ",".join(f"0x{b:02x}" for b in data[i:i+24]) + "," for i in range(0, len(data), 24))
        lines.append("};")
    lines.append("inline constexpr Image images[] = {")
    for entry in entries:
        name = names[entry["sha256"]]
        lines.append(f'  {{{name}, sizeof({name})}}, // {entry["index"]}: {entry["key"]}')
    lines.extend(["};", 'static_assert(sizeof(images)/sizeof(images[0]) == 52, "Avatar coverage");', "}"])
    (ROOT / "esphome/weather_avatar_assets.h").write_text("\n".join(lines) + "\n")
    print(f"Exported {len(entries)} outfits; {manifest['embedded_unique_bytes']} compressed bytes; two RGB565 buffers 541696 bytes.")


if __name__ == "__main__":
    main()
