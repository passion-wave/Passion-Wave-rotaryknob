"""Execute the production renderer with queued decoder/LVGL boundary doubles.

These checks exercise failure and ownership transitions; actual JPEG validity
and dimensions are independently checked by the production artwork tests.
"""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class AvatarRendererTests(unittest.TestCase):
    def test_async_ownership_failure_retry_and_last_request_wins(self):
        compiler = shutil.which("c++") or shutil.which("clang++") or shutil.which("g++")
        if compiler is None:
            self.skipTest("Native C++ compiler unavailable")
        files = {
            "fake.h": r'''
#pragma once
#include <cassert>
#include <cstdint>
#include <string>
namespace fake {
inline bool worker = false, decode_ok = true, create_ok = true;
inline uint32_t milliseconds = 0;
inline unsigned jobs = 0, lv_calls = 0;
inline void (*pending)(void *) = nullptr;
inline void *argument = nullptr;
inline void main_only() { assert(!worker); ++lv_calls; }
inline void finish(bool success = true) {
  assert(pending != nullptr); decode_ok = success;
  auto fn = pending; auto arg = argument; pending = nullptr;
  const auto calls = lv_calls;
  worker = true; fn(arg); worker = false;
  assert(lv_calls == calls); // No LVGL/cache/descriptor work in decoder task.
}
}
''',
            "lvgl.h": r'''
#pragma once
#include "fake.h"
struct lv_image_dsc_t { int key = -1; };
struct lv_obj_t {
  bool hidden = true;
  const lv_image_dsc_t *source = nullptr;
  std::string text;
};
constexpr int LV_OBJ_FLAG_HIDDEN = 1;
inline void lv_obj_add_flag(lv_obj_t *o, int) { fake::main_only(); o->hidden = true; }
inline void lv_obj_remove_flag(lv_obj_t *o, int) { fake::main_only(); o->hidden = false; }
inline void lv_image_set_src(lv_obj_t *o, const lv_image_dsc_t *d) { fake::main_only(); o->source = d; }
inline void lv_label_set_text(lv_obj_t *o, const char *v) { fake::main_only(); o->text = v; }
''',
            "src/misc/cache/instance/lv_image_cache.h": r'''
#pragma once
#include "lvgl.h"
inline void lv_image_cache_drop(const lv_image_dsc_t *) { fake::main_only(); }
''',
            "esphome/core/log.h": "#pragma once\n#define ESP_LOGW(...)\n#define ESP_LOGI(...)\n",
            "esphome/core/hal.h": r'''
#pragma once
#include "fake.h"
namespace esphome { inline uint32_t millis() { return fake::milliseconds; } }
''',
            "freertos/FreeRTOS.h": "#pragma once\nconstexpr int pdPASS = 1;\n",
            "freertos/task.h": r'''
#pragma once
#include "fake.h"
inline int xTaskCreatePinnedToCore(void (*fn)(void*), const char *, int,
                                  void *arg, int, void *, int) {
  assert(!fake::worker);
  if (!fake::create_ok) return 0;
  assert(fake::pending == nullptr);
  fake::pending = fn; fake::argument = arg; ++fake::jobs; return 1;
}
inline void vTaskDelete(void *) { assert(fake::worker); }
''',
            "esphome/components/runtime_image/runtime_image.h": r'''
#pragma once
#include "lvgl.h"
#include <cstddef>
namespace esphome::image {
enum ImageType { IMAGE_TYPE_RGB565 };
enum Transparency { TRANSPARENCY_OPAQUE };
}
namespace esphome::runtime_image {
enum ImageFormat { JPEG };
class RuntimeImage {
  lv_image_dsc_t descriptor_;
 public:
  RuntimeImage(ImageFormat, image::ImageType, image::Transparency) {}
  bool begin_decode(size_t) { assert(fake::worker); return true; }
  int feed_data(uint8_t *data, size_t size) {
    assert(fake::worker); descriptor_.key = *data;
    return fake::decode_ok ? int(size) : -1;
  }
  bool end_decode() { assert(fake::worker); return true; }
  int get_width() const { return 368; }
  int get_height() const { return 368; }
  void release() { assert(fake::worker); descriptor_.key = -1; }
  lv_image_dsc_t *get_lv_image_dsc() { fake::main_only(); return &descriptor_; }
};
}
''',
            "weather_avatar_assets.h": """#pragma once
#include <array>
#include <cstddef>
#include <cstdint>
namespace weather_avatar::assets {
struct Image { const uint8_t *data; size_t size; };
inline std::array<uint8_t, 52> bytes{};
inline std::array<Image, 52> images = [] {
  std::array<Image, 52> result{};
  for (unsigned i=0; i<52; ++i) { bytes[i]=i; result[i]={&bytes[i],1}; }
  return result;
}();
}
""",
            "test.cpp": r'''
#include "weather_avatar_render.h"
using namespace weather_avatar;
constexpr uint32_t epoch = 1790575200;
Context weather(int16_t t, uint32_t now=epoch) {
  Context c; c.mode=FORECAST; c.fetched_at=c.start_utc=now;
  c.end_utc=now+14400; c.temperature_min_tenths=c.temperature_max_tenths=t;
  c.flags=TEMP_VALID|CONDITIONS_KNOWN|WIND_VALID|PROBABILITY_VALID;
  c.conditions=condition_bit(2); c.first_condition=2;
  return c;
}
struct View {
  Renderer r;
  lv_obj_t image, title, detail;
  bool draw(uint32_t now=epoch, const char *variant="brown_brown") {
    return r.render(&image,&title,&detail,variant,now);
  }
  int key() const { return image.source ? image.source->key : -1; }
};
int main() {
  // Valid A -> desired B failure hides A; current advice + error is visible.
  View v; current_context=weather(180);
  assert(!v.draw() && v.image.hidden && fake::pending);
  fake::finish(); assert(v.draw() && !v.image.hidden && v.key()==2);
  current_context=weather(240); fake::milliseconds=100;
  assert(!v.draw() && !v.image.hidden && v.key()==2);
  fake::finish(false); assert(!v.draw());
  assert(v.image.hidden && v.title.text.find("24")!=std::string::npos);
  assert(v.detail.text.find("Bild nicht verfügbar")!=std::string::npos);
  assert(v.detail.text.find("T-Shirt")!=std::string::npos);
  const auto after_failure=fake::jobs;
  fake::milliseconds=30099; assert(!v.draw()); assert(fake::jobs==after_failure);
  fake::milliseconds=30100; assert(!v.draw()); assert(fake::jobs==after_failure+1);
  fake::finish(); assert(v.draw() && !v.image.hidden && v.key()==1);

  // Rapid A -> B -> C ignores the superseded completed B; worker never paints.
  current_context=weather(180); fake::milliseconds=40000;
  assert(!v.draw()); fake::finish(); assert(v.draw() && v.key()==2);
  current_context=weather(240); assert(!v.draw());
  current_context=weather(-50); assert(!v.draw() && v.key()==2);
  fake::finish(); assert(!v.draw() && v.key()==2 && fake::pending);
  fake::finish(); assert(v.draw() && v.key()==5);

  // A stalled job cannot leave old clothing visible for longer than 2 seconds.
  current_context=weather(180); fake::milliseconds=50000;
  assert(!v.draw() && !v.image.hidden);
  fake::milliseconds=51999; assert(!v.draw() && !v.image.hidden);
  fake::milliseconds=52000; assert(!v.draw() && v.image.hidden);
  assert(v.detail.text.find("Bild wird geladen")!=std::string::npos);
  fake::finish(); assert(v.draw() && !v.image.hidden);

  // The old context's TTL takes precedence even before the 2-second bound.
  current_context=weather(240,epoch+1201); fake::milliseconds=52100;
  assert(!v.draw(epoch+1201) && v.image.hidden);
  fake::finish(); assert(v.draw(epoch+1201) && !v.image.hidden);
  assert(!v.draw(epoch+2402) && v.image.hidden);
  assert(v.title.text=="Keine Wetterdaten");
  fake::finish(); assert(v.draw(epoch+2402) && v.key()==48);

  // With no UTC sync a failed neutral decode still retries on monotonic time.
  View no_clock; current_context={}; fake::milliseconds=0xfffffff0U;
  assert(!no_clock.draw(0)); fake::finish(false); assert(!no_clock.draw(0));
  const auto failed_jobs=fake::jobs;
  fake::milliseconds=0xfffffff0U+29999U;
  assert(!no_clock.draw(0) && fake::jobs==failed_jobs);
  fake::milliseconds=0xfffffff0U+30000U;
  assert(!no_clock.draw(0) && fake::jobs==failed_jobs+1);
  fake::finish(); assert(no_clock.draw(0) && no_clock.key()==48);

  // Task-allocation failure follows the same explicit error/retry path.
  View no_task; current_context=weather(180); fake::create_ok=false;
  assert(!no_task.draw()); assert(!no_task.draw());
  assert(no_task.image.hidden && no_task.detail.text.find("Bild nicht verfügbar")!=std::string::npos);
  fake::create_ok=true;
}
''',
        }
        with tempfile.TemporaryDirectory(prefix="pw-avatar-renderer-") as directory:
            base = Path(directory)
            for name, content in files.items():
                path = base / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content)
            # Copy unchanged production headers into the include fixture, so only
            # platform boundaries and immutable JPEG bytes are test doubles.
            for name in ("weather_avatar_render.h", "weather_avatar.h", "weather_avatar_context.h"):
                shutil.copyfile(ROOT / "esphome" / name, base / name)
            binary = base / "test"
            subprocess.run([compiler, "-std=c++17", "-Wall", "-Wextra", "-Werror",
                            "-I", str(base), str(base / "test.cpp"), "-o", str(binary)],
                           check=True, capture_output=True, text=True)
            subprocess.run([str(binary)], check=True, capture_output=True, text=True)


if __name__ == "__main__":
    unittest.main()
