"""Run production C++ outfit selection against boundaries and compound weather."""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class AvatarResolverTests(unittest.TestCase):
    def test_native_weather_rules(self):
        compiler = shutil.which("c++") or shutil.which("g++") or shutil.which("clang++")
        if compiler is None:
            self.skipTest("Native C++ compiler required; exercised separately on build host")
        source = r'''
#include "weather_avatar.h"
#include <cassert>
using namespace weather_avatar;
constexpr uint32_t now=1790575200;
Context weather(int16_t t, uint8_t condition) {
  Context c; c.mode=FORECAST; c.fetched_at=c.start_utc=now;
  c.end_utc=now+14400; c.temperature_min_tenths=c.temperature_max_tenths=t;
  c.flags=TEMP_VALID|CONDITIONS_KNOWN|WIND_VALID|PROBABILITY_VALID;
  c.conditions=condition_bit(condition); c.first_condition=condition;
  return c;
}
int main() {
  struct Boundary {int16_t t; Thermal band;};
  for (auto b: {Boundary{-1,Thermal::FROST}, {0,Thermal::COLD},
      {99,Thermal::COLD}, {100,Thermal::COOL}, {159,Thermal::COOL},
      {160,Thermal::MILD}, {219,Thermal::MILD}, {220,Thermal::WARM},
      {279,Thermal::WARM}, {280,Thermal::HOT}}) {
    auto o=resolve(weather(b.t,13),now); assert(o.valid && o.thermal==b.band);
  }
  auto c=weather(320,13); auto o=resolve(c,now);
  assert(o.sun_hat && o.asset_index(false)==50 && o.asset_index(true)==51);
  c=weather(320,2); assert(!resolve(c,now).sun_hat);
  c=weather(240,4); o=resolve(c,now);
  assert(o.scene==Scene::FOG && o.thermal==Thermal::WARM && o.protection==Protection::DRY);
  c=weather(230,1); o=resolve(c,now); assert(o.scene==Scene::NIGHT && o.thermal==Thermal::WARM);
  c.conditions|=condition_bit(13); c.first_condition=13;
  assert(resolve(c,now).scene==Scene::EVERYDAY);
  c=weather(-30,14); o=resolve(c,now);
  assert(o.protection==Protection::WIND && o.thermal==Thermal::FROST && o.reference_motif==8);
  c=weather(240,13); c.wind_tenths=199; assert(resolve(c,now).protection==Protection::DRY);
  c.wind_tenths=200; assert(resolve(c,now).protection==Protection::WIND);
  c.flags &= ~WIND_VALID; assert(resolve(c,now).protection==Protection::DRY);
  c.flags |= GUST_VALID; c.gust_tenths=350; assert(resolve(c,now).windy);
  c=weather(210,10); o=resolve(c,now); assert(o.liquid_rain && o.reference_motif==9);
  c=weather(100,10); assert(resolve(c,now).reference_motif==10);
  c=weather(20,10); o=resolve(c,now); assert(o.reference_motif==21 && o.scene==Scene::RAIN);
  assert(o.protection==Protection::WET && o.thermal==Thermal::COLD);
  c=weather(260,9); o=resolve(c,now); assert(o.scene==Scene::POURING && o.thermal==Thermal::WARM);
  c=weather(-20,12); o=resolve(c,now); assert(o.scene==Scene::MIX && o.protection==Protection::SNOW);
  c=weather(-20,11); c.flags|=PRECIPITATION_VALID; c.precipitation_tenths=10;
  o=resolve(c,now); assert(o.scene==Scene::SNOW && !o.liquid_rain && !o.wet_unknown);
  c=weather(180,13); c.precipitation_probability=49; assert(resolve(c,now).protection==Protection::DRY);
  c.precipitation_probability=50; o=resolve(c,now);
  assert(o.wet_unknown && !o.liquid_rain && o.protection==Protection::WET);
  c=weather(220,6); o=resolve(c,now); assert(o.scene==Scene::LIGHTNING && !o.liquid_rain);
  c.flags|=WET_PHASE_UNKNOWN; assert(resolve(c,now).scene==Scene::LIGHTNING);
  c.flags|=LIQUID_RAIN; assert(resolve(c,now).scene==Scene::LIGHTNING_RAIN);
  c.conditions|=condition_bit(5); o=resolve(c,now); assert(o.scene==Scene::HAIL && o.lightning);
  c.flags&=~TEMP_VALID; o=resolve(c,now); assert(!o.valid && o.hail && o.lightning && o.asset_index(false)==48);
  c=weather(200,3); assert(resolve(c,now).asset_index(true)==49);
  c=weather(200,13); assert(resolve(c,now+1200).valid); assert(!resolve(c,now+1201).valid);
  assert(!resolve(c,now-1).valid); assert(!resolve(c,0).valid);
  c.mode=CURRENT; c.end_utc=now+1200; c.provider_at=now-1201;
  assert(!resolve(c,now).valid); c.provider_at=now-1200; assert(resolve(c,now).valid);
  c=weather(200,13); c.end_utc=now+3600; assert(!resolve(c,now).valid);
  c=weather(200,13); c.start_utc=now+3600; c.end_utc=c.start_utc+14400;
  assert(resolve(c,now).valid); // Explicit next-full-hour forecast window.
  c.start_utc++; c.end_utc++; assert(!resolve(c,now).valid);
  c=weather(200,13); c.schema=2; assert(!resolve(c,now).valid);
  c=weather(200,13); c.flags&=~CONDITIONS_KNOWN; assert(!resolve(c,now).valid);
  c=weather(200,0); assert(!resolve(c,now).valid);
  // Every HA condition, thermal band, identity and wet/wind combination maps
  // to a real bounded asset and keeps its thermal protection under hazards.
  for (int code=1;code<=15;code++) for (int t: {-60,60,120,180,240,320})
    for (int flags: {0,int(LIQUID_RAIN),int(WET_PHASE_UNKNOWN),int(WIND_VALID)}) {
      c=weather(t,code); c.flags|=flags; c.wind_tenths=250;
      o=resolve(c,now); assert(o.valid && o.thermal==thermal_band(t));
      assert(o.asset_index(false)<52 && o.asset_index(true)<52);
      if (t<0) assert(!o.sun_hat && o.thermal==Thermal::FROST);
    }
}
'''
        # initializer_list is required by the test fixture, not the firmware.
        source = "#include <initializer_list>\n" + source
        with tempfile.TemporaryDirectory(prefix="pw-avatar-resolver-") as directory:
            src, binary = Path(directory) / "rules.cpp", Path(directory) / "rules"
            src.write_text(source)
            subprocess.run([compiler, "-std=c++17", "-Wall", "-Wextra", "-Werror",
                            "-I", str(ROOT / "esphome"), str(src), "-o", str(binary)],
                           capture_output=True, text=True, check=True)
            subprocess.run([str(binary)], capture_output=True, text=True, check=True)


if __name__ == "__main__":
    unittest.main()
