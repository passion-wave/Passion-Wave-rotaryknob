#pragma once

#include <atomic>
#include <cstdio>
#include <ctime>
#include <string>
#include "esphome/components/runtime_image/runtime_image.h"
#include "esphome/core/log.h"
#include "esphome/core/hal.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "lvgl.h"
#include <src/misc/cache/instance/lv_image_cache.h>
#include "weather_avatar.h"
#include "weather_avatar_assets.h"

namespace weather_avatar {

// Decode only into the inactive image. LVGL and descriptor changes remain on
// its main task; the worker publishes completion using an acquire/release pair.
// Embedded JPEGs are already 368x368. No image resize is performed at runtime.
class Renderer {
 public:
  Renderer()
      : buffers_{
          {esphome::runtime_image::JPEG, esphome::image::IMAGE_TYPE_RGB565,
           esphome::image::TRANSPARENCY_OPAQUE},
          {esphome::runtime_image::JPEG, esphome::image::IMAGE_TYPE_RGB565,
           esphome::image::TRANSPARENCY_OPAQUE}} {}

  bool render(lv_obj_t *image, lv_obj_t *title, lv_obj_t *detail,
              const std::string &variant, uint32_t now) {
    const auto outfit = resolve(current_context, now);
    const uint8_t wanted = outfit.asset_index(variant == "blond_hazel");
    const bool was_ready = active_key_ == wanted;
    const uint32_t now_ms = esphome::millis();
    if (desired_key_ != wanted) {
      desired_key_ = wanted;
      transition_started_ms_ = now_ms;
    }
    // An expired recommendation must disappear immediately, before the neutral
    // JPEG has decoded. Never show stale clothing beside a no-data label.
    if (!outfit.valid && active_key_ != wanted) lv_obj_add_flag(image, LV_OBJ_FLAG_HIDDEN);

    if (job_state_.load(std::memory_order_acquire) == 2) {
      if (job_ok_ && job_key_ == wanted) {
        if (active_ >= 0) lv_image_cache_drop(buffers_[active_].get_lv_image_dsc());
        lv_image_cache_drop(buffers_[job_target_].get_lv_image_dsc());
        lv_image_set_src(image, buffers_[job_target_].get_lv_image_dsc());
        active_ = job_target_;
        active_key_ = job_key_;
        active_context_ = current_context;
        failed_key_ = -1;
      } else if (!job_ok_) {
        failed_key_ = job_key_;
        retry_at_ms_ = now_ms + 30000U;
        ESP_LOGW("weather_avatar", "Local JPEG decode failed for outfit %u", job_key_);
      }
      job_state_.store(0, std::memory_order_release);
    }
    if (active_key_ != wanted && job_state_.load(std::memory_order_acquire) == 0 &&
        (failed_key_ != wanted || static_cast<int32_t>(now_ms - retry_at_ms_) >= 0)) {
      job_key_ = wanted;
      job_target_ = active_ == 0 ? 1 : 0;
      // Discard LVGL's cached entry before the worker changes its descriptor.
      lv_image_cache_drop(buffers_[job_target_].get_lv_image_dsc());
      job_state_.store(1, std::memory_order_release);
      if (xTaskCreatePinnedToCore(worker_, "avatar_decode", 12288, this, 1,
                                  nullptr, 0) != pdPASS) {
        job_ok_ = false;
        job_state_.store(2, std::memory_order_release);
      }
    }

    const bool decode_failed = failed_key_ == wanted && active_key_ != wanted;
    const bool transition_expired = active_key_ != wanted &&
      (now_ms - transition_started_ms_ >= 2000U ||
       (active_ >= 0 && !context_is_fresh(active_context_, now)));
    if (active_key_ == wanted) {
      // The same artwork can also represent a fresh temperature/period update.
      active_context_ = current_context;
      lv_obj_remove_flag(image, LV_OBJ_FLAG_HIDDEN);
    } else if (active_ < 0 || decode_failed || transition_expired) {
      lv_obj_add_flag(image, LV_OBJ_FLAG_HIDDEN);
    }
    // Briefly retain a matching image/caption while decoding, but never let
    // failure, a stuck worker or an expired old context preserve stale advice.
    if (active_key_ == wanted || !outfit.valid || active_ < 0 ||
        decode_failed || transition_expired) {
      std::string heading = scene_label(outfit);
      if (outfit.valid && outfit.scene != Scene::EXCEPTIONAL) {
        char temperatures[48];
        std::snprintf(temperatures, sizeof(temperatures), "\n%s%.0f–%.0f °C",
                      current_context.flags & FELT_TEMPERATURE ? "Gefühlt " : "",
                      current_context.temperature_min_tenths / 10.0,
                      current_context.temperature_max_tenths / 10.0);
        heading += temperatures;
      }
      std::string description = outfit_label(outfit);
      if (outfit.valid) {
        description += "\n";
        description += period_(current_context);
        if (outfit.partial && !decode_failed && !transition_expired)
          description += " · teils unbekannt";
      }
      // Three short lines fit the 50 px detail area even on failure.
      if (decode_failed) description = "Bild nicht verfügbar\n" + description;
      else if (transition_expired && outfit.valid)
        description = "Bild wird geladen\n" + description;
      set_label_(title, heading, last_title_);
      set_label_(detail, description, last_detail_);
    }
    if (!was_ready && active_key_ == wanted) {
      ESP_LOGI("weather_avatar", "Outfit %u active, decoded buffers <= 541696 bytes", wanted);
    }
    return active_key_ == wanted;
  }

 private:
  esphome::runtime_image::RuntimeImage buffers_[2];
  std::atomic<uint8_t> job_state_{0}; // 0 idle, 1 worker owns target, 2 complete
  int active_{-1};
  int active_key_{-1};
  int failed_key_{-1};
  uint32_t retry_at_ms_{0};
  int desired_key_{-1};
  uint32_t transition_started_ms_{0};
  Context active_context_{};
  uint8_t job_key_{0};
  uint8_t job_target_{0};
  bool job_ok_{false};
  std::string last_title_, last_detail_;

  static void set_label_(lv_obj_t *label, const std::string &value, std::string &old) {
    if (old == value) return;
    lv_label_set_text(label, value.c_str());
    old = value;
  }

  static std::string period_(const Context &c) {
    if (c.mode == CURRENT) return "Jetzt";
    time_t start = c.start_utc, end = c.end_utc;
    struct tm local_start{}, local_end{};
    localtime_r(&start, &local_start);
    localtime_r(&end, &local_end);
    char text[32];
    std::snprintf(text, sizeof(text), "%02d:%02d–%02d:%02d Uhr",
                  local_start.tm_hour, local_start.tm_min,
                  local_end.tm_hour, local_end.tm_min);
    return text;
  }

  static void worker_(void *opaque) {
    auto &self = *static_cast<Renderer *>(opaque);
    const auto &asset = assets::images[self.job_key_];
    auto &buffer = self.buffers_[self.job_target_];
    buffer.release();
    bool success = asset.size > 0 && buffer.begin_decode(asset.size);
    if (success) {
      const int consumed = buffer.feed_data(const_cast<uint8_t *>(asset.data), asset.size);
      success = consumed == static_cast<int>(asset.size) && buffer.end_decode() &&
                buffer.get_width() == 368 && buffer.get_height() == 368;
    }
    if (!success) buffer.release();
    self.job_ok_ = success;
    self.job_state_.store(2, std::memory_order_release);
    vTaskDelete(nullptr);
  }
};

inline Renderer renderer;
inline bool render(lv_obj_t *image, lv_obj_t *title, lv_obj_t *detail,
                   const std::string &variant, uint32_t now_epoch) {
  return renderer.render(image, title, detail, variant, now_epoch);
}

} // namespace weather_avatar
