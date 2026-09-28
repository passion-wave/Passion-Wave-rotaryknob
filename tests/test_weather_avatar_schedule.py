"""Execute the firmware scheduling policy, including Europe/Berlin DST edges."""
from pathlib import Path
import shutil
import re
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class AvatarScheduleTests(unittest.TestCase):
    def test_native_policy_and_dst(self):
        compiler = shutil.which("c++") or shutil.which("clang++") or shutil.which("g++")
        if compiler is None:
            self.skipTest("Native C++ compiler unavailable; run on the firmware build host")
        source = r'''
#include "weather_avatar_schedule.h"
#include <cassert>
#include <cstdlib>
using namespace weather_avatar;
std::time_t local_epoch(int year, int month, int day, int hour, int min=0, int sec=0) {
  std::tm t{};
  t.tm_year=year-1900; t.tm_mon=month-1; t.tm_mday=day;
  t.tm_hour=hour; t.tm_min=min; t.tm_sec=sec; t.tm_isdst=-1;
  return std::mktime(&t);
}
int main() {
  setenv("TZ", "Europe/Berlin", 1); tzset();
  assert(!morning_window(true, true, 5));
  assert(morning_window(true, true, 6));
  assert(morning_window(true, true, 9));
  assert(!morning_window(true, true, 10));
  assert(!morning_window(false, true, 7));
  assert(!morning_window(true, false, 7));
  assert(morning_action(true, false, false, false, 29999, 30000) == MorningAction::NONE);
  assert(morning_action(true, false, false, false, 30000, 30000) == MorningAction::ENTER);
  assert(morning_action(true, true, false, false, 99999, 30000) == MorningAction::NONE);
  assert(morning_action(true, false, true, true, 99999, 30000) == MorningAction::NONE);
  assert(morning_action(false, false, true, true, 99999, 30000) == MorningAction::LEAVE);
  assert(morning_action(true, true, true, true, 99999, 30000) == MorningAction::LEAVE);
  assert(morning_action(false, false, true, false, 99999, 30000) == MorningAction::NONE);
  assert(morning_action(false, true, true, false, 99999, 30000) == MorningAction::NONE);
  // Unsigned elapsed arithmetic remains correct through millis rollover.
  const uint32_t idle = uint32_t(1000) - uint32_t(0xffff8000U);
  assert(morning_action(true, false, false, false, idle, 30000) == MorningAction::ENTER);
  assert(next_morning_wake_seconds(0) == 900);
  assert(next_morning_wake_seconds(local_epoch(2026,9,28,5,59,59)) == 1);
  assert(next_morning_wake_seconds(local_epoch(2026,9,28,6)) == 86400);
  assert(next_morning_wake_seconds(local_epoch(2026,3,28,6)) == 23*3600);
  assert(next_morning_wake_seconds(local_epoch(2026,10,24,6)) == 25*3600);
  assert(next_morning_wake_seconds(local_epoch(2026,12,31,23)) == 7*3600);
}
'''
        with tempfile.TemporaryDirectory(prefix="pw-avatar-schedule-") as directory:
            src = Path(directory) / "schedule.cpp"
            executable = Path(directory) / "schedule"
            src.write_text(source)
            subprocess.run([compiler, "-std=c++17", "-Wall", "-Wextra", "-Werror",
                            "-I", str(ROOT / "esphome"), str(src), "-o", str(executable)],
                           check=True, capture_output=True, text=True)
            subprocess.run([str(executable)], check=True, capture_output=True, text=True)

    def test_ui_entry_and_gesture_contract(self):
        ui = (ROOT / "esphome/rotaryknob-s3-ui-core.yaml").read_text()
        framework = (ROOT / "esphome/ui_next_framework.h").read_text()
        self.assertIn("case ui_next::Action::WEATHER_AVATAR:", ui)
        self.assertIn("Action::WEATHER_AVATAR", framework)
        self.assertIn("84, 274, 204, 320", framework)
        encoder = ui.split("if (id(current_page) == 7) {", 1)[1].split("// UI Next's right-hand", 1)[0]
        self.assertIn("boost_screensaver_brightness", encoder)
        self.assertNotIn("return_from_screensaver", encoder)
        refresh = ui.split("  - id: refresh_weather_screensaver\n", 1)[1].split("  - id:", 1)[0]
        self.assertLess(refresh.index("id(refresh_avatar).execute();"), refresh.index("lv_img_set_src"))
        self.assertIn("id(screensaver_avatar_automatic)", ui)
        self.assertIn("next_morning_wake_seconds", ui)
        scheduler = ui.split("  - id: morning_avatar_tick\n", 1)[1].split("  - id:", 1)[0]
        self.assertNotIn("id(timer_running)", scheduler)
        self.assertIn("id(timer_finished)", scheduler)
        self.assertIn("${factory_onboarding_guard} && !id(factory_onboarding_completed)", scheduler)
        self.assertIn("id(touch_swipe_start_ms) != 0 && !id(screensaver_avatar_active)", scheduler)
        exit_script = ui.split("  - id: return_from_screensaver\n", 1)[1].split("  - id:", 1)[0]
        self.assertIn("lv_indev_wait_release(input)", exit_script)
        self.assertLess(exit_script.index("lv_indev_wait_release"),
                        exit_script.index("id(screensaver_avatar_active) = false"))

    def test_avatar_symbols_are_in_the_actual_font_and_keep_rain_phase(self):
        ui = (ROOT / "esphome/rotaryknob-s3-ui-core.yaml").read_text()
        refresh = ui.split("  - id: refresh_avatar\n", 1)[1].split("  - id:", 1)[0]
        font = ui.split("    id: media_icon_28\n", 1)[1].split("    id: media_icon_42", 1)[0]
        points = r"\\U[0-9A-Fa-f]{8}"
        self.assertTrue(set(re.findall(points, refresh)).issubset(set(re.findall(points, font))))
        rain = refresh.split("case weather_avatar::Scene::RAIN:", 1)[1].split("break;", 1)[0]
        self.assertIn("outfit.liquid_rain ?", rain)
        self.assertIn("current_context.first_condition == 13", refresh)
        self.assertIn("current_context.first_condition == 8", refresh)
        self.assertIn("if (outfit.lightning)", refresh)
        self.assertIn("else if (outfit.hail)", refresh)


if __name__ == "__main__":
    unittest.main()
