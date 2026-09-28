"""Exercise the actual bounded C++ wire codec and replay guard on a host."""

from pathlib import Path
import shutil
import subprocess
import tempfile

import unittest


class WeatherAvatarTransportTests(unittest.TestCase):
    def test_weather_context_roundtrip_and_replay(self):
        compiler = shutil.which("c++") or shutil.which("clang++") or shutil.which("g++")
        if compiler is None:
            self.skipTest("Host C++ compiler unavailable")
        root = Path(__file__).parents[1]
        source = r'''
    #include "weather_avatar_context.h"
    #include <cassert>
    using namespace weather_avatar;
    int main() {
      Context sent;
      sent.mode = FORECAST; sent.flags = TEMP_VALID | CONDITIONS_KNOWN | LIQUID_RAIN;
      sent.sequence = 7; sent.fetched_at = 1792909800; sent.provider_at = 1792900000;
      sent.start_utc = sent.fetched_at; sent.end_utc = sent.start_utc + 14400;
      sent.temperature_min_tenths = -31; sent.temperature_max_tenths = 199;
      sent.conditions = (1U << 7) | (1U << 5); sent.first_condition = 7;
      sent.precipitation_probability = 77; sent.wind_tenths = 255;
      sent.gust_tenths = 412; sent.precipitation_tenths = 53;
      uint8_t payload[CONTEXT_WIRE_SIZE]{};
      pack_context(sent, payload);
      Context received;
      assert(unpack_context(payload, sizeof(payload), &received));
      assert(received.temperature_min_tenths == -31);
      assert(received.temperature_max_tenths == 199);
      assert(received.conditions == sent.conditions);
      assert(received.first_condition == 7 && received.wind_tenths == 255);
      assert(received.gust_tenths == 412 && received.precipitation_tenths == 53);
      assert(received.provider_at == sent.provider_at);
      assert(update_context(received));
      assert(!update_context(received)); // replay is not a fresh fetch
      assert(current_context.fetched_at == sent.fetched_at);
      received.fetched_at--;
      received.sequence++;
      assert(!update_context(received));
      assert(!unpack_context(payload, sizeof(payload) - 1, &received));
      payload[0] = 2;
      assert(!unpack_context(payload, sizeof(payload), &received));
      payload[0] = 1; payload[1] = 255;
      assert(!unpack_context(payload, sizeof(payload), &received));
      payload[1] = 1; payload[31] = 101;
      assert(!unpack_context(payload, sizeof(payload), &received));
    }
    '''
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            (path / "test.cpp").write_text(source)
            subprocess.run([compiler, "-std=c++17", "-Wall", "-Wextra", "-Werror",
                            "-I", str(root / "esphome"), str(path / "test.cpp"),
                            "-o", str(path / "test")], check=True, capture_output=True)
            subprocess.run([str(path / "test")], check=True, capture_output=True)
