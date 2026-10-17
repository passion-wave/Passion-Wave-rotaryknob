"""Require all firmware outfit keys to resolve to immutable final-size JPEGs."""
import hashlib
import json
from pathlib import Path
import re
import unittest

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "assets/weather-avatar"


class AvatarAssetTests(unittest.TestCase):
    def test_complete_outfit_pack_and_embedded_bytes(self):
        manifest = json.loads((ART / "manifest.json").read_text())
        entries = manifest["images"]
        self.assertEqual([e["index"] for e in entries], list(range(52)))
        self.assertEqual(len({e["key"] for e in entries}), 52)
        for variant in ("brown_brown", "blond_hazel"):
            keys = {e["key"] for e in entries if e["variant"] == variant}
            required = {f"{variant}/{band}-{protection}"
                        for band in ("hot", "warm", "mild", "cool", "cold", "frost")
                        for protection in ("dry", "wind", "wet", "snow")}
            required |= {f"{variant}/neutral", f"{variant}/hot-sunhat"}
            self.assertEqual(keys, required)
        header = (ROOT / "esphome/weather_avatar_assets.h").read_text()
        blobs = {}
        for name, array in re.findall(r"uint8_t (jpeg_\d+)\[\] = \{(.*?)\};", header, re.S):
            blobs[name] = bytes(int(v, 16) for v in re.findall(r"0x([0-9a-f]{2})", array))
        slots = re.findall(r"\{(jpeg_\d+), sizeof\(jpeg_\d+\)\}, // (\d+): (\S+)", header)
        self.assertEqual(len(slots), 52)
        for entry, (name, index, key) in zip(entries, slots, strict=True):
            data = (ART / entry["file"]).read_bytes()
            with self.subTest(key=key):
                self.assertEqual(int(index), entry["index"])
                self.assertEqual(key, entry["key"])
                self.assertEqual(blobs[name], data)
                self.assertEqual(len(data), entry["bytes"])
                self.assertEqual(hashlib.sha256(data).hexdigest(), entry["sha256"])
                with Image.open(ART / entry["file"]) as image:
                    self.assertEqual(image.size, (368, 368))
                    self.assertEqual(image.format, "JPEG")
                    self.assertFalse(image.info.get("progressive", False))
                    image.load()
        self.assertLess(sum(map(len, blobs.values())), 1024 * 1024)
        self.assertEqual(manifest["embedded_unique_bytes"], sum(map(len, blobs.values())))
        for name, sha in manifest["sources"].items():
            self.assertEqual(hashlib.sha256((ART / "sources" / f"{name}.png").read_bytes()).hexdigest(), sha)


if __name__ == "__main__":
    unittest.main()
