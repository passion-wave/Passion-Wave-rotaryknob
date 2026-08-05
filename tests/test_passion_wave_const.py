"""Dependency-free tests for shared PassionWave target validation."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest


MODULE_PATH = (
    Path(__file__).parents[1] / "custom_components" / "passion_wave" / "const.py"
)
SPEC = importlib.util.spec_from_file_location("passion_wave_const", MODULE_PATH)
assert SPEC and SPEC.loader
CONSTANTS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CONSTANTS)


class LightTargetContractTests(unittest.TestCase):
    def test_real_customer_light_is_configured(self) -> None:
        self.assertTrue(
            CONSTANTS.is_configured_light_entity("light.wled_timo_main_2")
        )

    def test_public_placeholders_are_not_configured(self) -> None:
        for value in (
            "",
            "unknown",
            "light.passion_wave_light_1",
            "light.passion_wave_light_4",
        ):
            with self.subTest(value=value):
                self.assertFalse(CONSTANTS.is_configured_light_entity(value))


if __name__ == "__main__":
    unittest.main()
