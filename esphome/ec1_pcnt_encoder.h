#pragma once

#include <algorithm>
#include <cstdint>

#include "driver/gpio.h"
#include "driver/pulse_cnt.h"
#include "esp_err.h"

// EC1 exposes one active-low pulse output per direction. Two independent
// ESP32-S3 PCNT units count falling edges in hardware, even while LVGL or
// networking temporarily occupies the application loop.
namespace ec1_pcnt {

struct Batch {
  int32_t left{0};
  int32_t right{0};

  int32_t signed_steps() const { return right - left; }
  uint32_t pulse_count() const {
    const uint32_t left_pulses = left > 0 ? static_cast<uint32_t>(left) : 0U;
    const uint32_t right_pulses = right > 0 ? static_cast<uint32_t>(right) : 0U;
    return left_pulses + right_pulses;
  }
};

class Encoder {
 public:
  bool setup(int left_gpio, int right_gpio) {
    if (setup_attempted_) return ready_;
    setup_attempted_ = true;

    if (!configure_inputs_(left_gpio, right_gpio)) return false;
    const bool left_ready = setup_counter_(left_gpio, &left_unit_, &left_channel_);
    const bool right_ready = setup_counter_(right_gpio, &right_unit_, &right_channel_);
    ready_ = left_ready && right_ready;
    if (!ready_) return false;

    int left = 0;
    int right = 0;
    if (!read_counts_(&left, &right)) {
      ready_ = false;
      return false;
    }
    last_left_ = left;
    last_right_ = right;
    return true;
  }

  Batch take() {
    Batch batch;
    if (!ready_) return batch;

    int left = 0;
    int right = 0;
    if (!read_counts_(&left, &right)) return batch;

    batch.left = left - last_left_;
    batch.right = right - last_right_;
    last_left_ = left;
    last_right_ = right;

    // Counters only increase. A negative delta indicates an unexpected
    // peripheral reset and must not become a UI movement.
    if (batch.left < 0 || batch.right < 0) {
      read_errors_++;
      return {};
    }

    total_left_ += batch.left;
    total_right_ += batch.right;
    max_batch_ = std::max(max_batch_, batch.pulse_count());
    return batch;
  }

  bool ready() const { return ready_; }
  uint32_t read_errors() const { return read_errors_; }
  uint32_t max_batch() const { return max_batch_; }
  int64_t left_total() const { return total_left_ - diagnostic_origin_left_; }
  int64_t right_total() const { return total_right_ - diagnostic_origin_right_; }
  int64_t signed_total() const { return right_total() - left_total(); }

  // Reset only the published diagnostic origin. Hardware counters and UI
  // acquisition continue without a gap, so no pulse is discarded.
  void reset_diagnostics() {
    diagnostic_origin_left_ = total_left_;
    diagnostic_origin_right_ = total_right_;
    max_batch_ = 0;
  }

 private:
  static constexpr int kLowLimit = -32768;
  static constexpr int kHighLimit = 32767;
  static constexpr uint32_t kGlitchFilterNs = 10000;

  bool configure_inputs_(int left_gpio, int right_gpio) {
    if (left_gpio < 0 || right_gpio < 0 || left_gpio >= 64 || right_gpio >= 64) {
      read_errors_++;
      return false;
    }
    gpio_config_t config{};
    config.pin_bit_mask = (1ULL << static_cast<uint32_t>(left_gpio)) |
                          (1ULL << static_cast<uint32_t>(right_gpio));
    config.mode = GPIO_MODE_INPUT;
    config.pull_up_en = GPIO_PULLUP_ENABLE;
    config.pull_down_en = GPIO_PULLDOWN_DISABLE;
    config.intr_type = GPIO_INTR_DISABLE;
    return ok_(gpio_config(&config));
  }

  bool setup_counter_(int gpio, pcnt_unit_handle_t *unit,
                      pcnt_channel_handle_t *channel) {
    pcnt_unit_config_t unit_config{};
    unit_config.low_limit = kLowLimit;
    unit_config.high_limit = kHighLimit;
    unit_config.flags.accum_count = 1;
    if (!ok_(pcnt_new_unit(&unit_config, unit))) return false;

    pcnt_glitch_filter_config_t filter_config{};
    filter_config.max_glitch_ns = kGlitchFilterNs;
    if (!ok_(pcnt_unit_set_glitch_filter(*unit, &filter_config))) return false;

    pcnt_chan_config_t channel_config{};
    channel_config.edge_gpio_num = gpio;
    channel_config.level_gpio_num = -1;
    channel_config.flags.virt_level_io_level = 1;
    if (!ok_(pcnt_new_channel(*unit, &channel_config, channel))) return false;
    // EC1 outputs are active-low. Keep the explicit pulls after the PCNT GPIO
    // matrix has claimed the pin; otherwise an open/high phase can float and
    // couple movement pulses into both directional counters.
    if (!ok_(gpio_pullup_en(static_cast<gpio_num_t>(gpio)))) return false;
    if (!ok_(gpio_pulldown_dis(static_cast<gpio_num_t>(gpio)))) return false;
    if (!ok_(pcnt_channel_set_edge_action(
            *channel, PCNT_CHANNEL_EDGE_ACTION_HOLD,
            PCNT_CHANNEL_EDGE_ACTION_INCREASE))) return false;
    if (!ok_(pcnt_channel_set_level_action(
            *channel, PCNT_CHANNEL_LEVEL_ACTION_KEEP,
            PCNT_CHANNEL_LEVEL_ACTION_KEEP))) return false;

    // Watch points activate the driver's overflow accumulator.
    if (!ok_(pcnt_unit_add_watch_point(*unit, kLowLimit))) return false;
    if (!ok_(pcnt_unit_add_watch_point(*unit, kHighLimit))) return false;
    if (!ok_(pcnt_unit_enable(*unit))) return false;
    if (!ok_(pcnt_unit_clear_count(*unit))) return false;
    if (!ok_(pcnt_unit_start(*unit))) return false;
    return true;
  }

  bool read_counts_(int *left, int *right) {
    if (!ok_(pcnt_unit_get_count(left_unit_, left))) return false;
    if (!ok_(pcnt_unit_get_count(right_unit_, right))) return false;
    return true;
  }

  bool ok_(esp_err_t result) {
    if (result == ESP_OK) return true;
    last_error_ = result;
    read_errors_++;
    return false;
  }

  bool setup_attempted_{false};
  bool ready_{false};
  pcnt_unit_handle_t left_unit_{nullptr};
  pcnt_unit_handle_t right_unit_{nullptr};
  pcnt_channel_handle_t left_channel_{nullptr};
  pcnt_channel_handle_t right_channel_{nullptr};
  int last_left_{0};
  int last_right_{0};
  int64_t total_left_{0};
  int64_t total_right_{0};
  int64_t diagnostic_origin_left_{0};
  int64_t diagnostic_origin_right_{0};
  uint32_t read_errors_{0};
  uint32_t max_batch_{0};
  esp_err_t last_error_{ESP_OK};
};

inline Encoder encoder;

}  // namespace ec1_pcnt
