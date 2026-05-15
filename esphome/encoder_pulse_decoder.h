#pragma once

#include "driver/gpio.h"
#include "esp_err.h"
#include "esp_timer.h"
#include "esphome/core/log.h"
#include "freertos/FreeRTOS.h"
#include "freertos/portmacro.h"

#include <cstdint>

namespace rotary_encoder_tune {

struct PulseStats {
  uint32_t raw_left;
  uint32_t raw_right;
  uint32_t accepted_left;
  uint32_t accepted_right;
  uint32_t dropped_left;
  uint32_t dropped_right;
  uint32_t queued_left;
  uint32_t queued_right;
  uint32_t min_dt_left_us;
  uint32_t min_dt_right_us;
  uint32_t max_dt_left_us;
  uint32_t max_dt_right_us;
  uint32_t min_raw_dt_left_us;
  uint32_t min_raw_dt_right_us;
  uint32_t max_raw_dt_left_us;
  uint32_t max_raw_dt_right_us;
};

struct PulseCounter {
  volatile uint32_t raw_total = 0;
  volatile uint32_t accepted_total = 0;
  volatile uint32_t dropped_total = 0;
  volatile uint32_t raw_window = 0;
  volatile uint32_t accepted_window = 0;
  volatile uint32_t dropped_window = 0;
  volatile uint32_t queued = 0;
  volatile uint32_t last_raw_us = 0;
  volatile uint32_t last_accepted_us = 0;
  volatile uint32_t min_raw_dt_window_us = 0;
  volatile uint32_t max_raw_dt_window_us = 0;
  volatile uint32_t min_dt_window_us = 0;
  volatile uint32_t max_dt_window_us = 0;
};

static portMUX_TYPE encoder_mux = portMUX_INITIALIZER_UNLOCKED;
static PulseCounter left_counter;
static PulseCounter right_counter;
static volatile uint32_t edge_guard_us = 500;
static bool installed = false;

inline void handle_edge(PulseCounter *counter) {
  const uint32_t now_us = static_cast<uint32_t>(esp_timer_get_time());
  portENTER_CRITICAL_ISR(&encoder_mux);

  counter->raw_total += 1;
  counter->raw_window += 1;
  counter->queued += 1;

  const uint32_t last_raw_us = counter->last_raw_us;
  const uint32_t raw_dt_us = last_raw_us == 0 ? 0 : now_us - last_raw_us;
  counter->last_raw_us = now_us;
  if (raw_dt_us != 0) {
    if (counter->min_raw_dt_window_us == 0 || raw_dt_us < counter->min_raw_dt_window_us) {
      counter->min_raw_dt_window_us = raw_dt_us;
    }
    if (raw_dt_us > counter->max_raw_dt_window_us) {
      counter->max_raw_dt_window_us = raw_dt_us;
    }
  }

  if (raw_dt_us != 0 && raw_dt_us < edge_guard_us) {
    counter->dropped_total += 1;
    counter->dropped_window += 1;
  } else {
    const uint32_t last_us = counter->last_accepted_us;
    const uint32_t dt_us = last_us == 0 ? 0 : now_us - last_us;
    counter->accepted_total += 1;
    counter->accepted_window += 1;
    counter->last_accepted_us = now_us;
    if (dt_us != 0) {
      if (counter->min_dt_window_us == 0 || dt_us < counter->min_dt_window_us) {
        counter->min_dt_window_us = dt_us;
      }
      if (dt_us > counter->max_dt_window_us) {
        counter->max_dt_window_us = dt_us;
      }
    }
  }

  portEXIT_CRITICAL_ISR(&encoder_mux);
}

inline void left_isr(void *arg) {
  handle_edge(&left_counter);
}

inline void right_isr(void *arg) {
  handle_edge(&right_counter);
}

inline void setup_pin(gpio_num_t pin, gpio_isr_t handler) {
  gpio_config_t config = {};
  config.pin_bit_mask = 1ULL << static_cast<uint32_t>(pin);
  config.mode = GPIO_MODE_INPUT;
  config.pull_up_en = GPIO_PULLUP_ENABLE;
  config.pull_down_en = GPIO_PULLDOWN_DISABLE;
  config.intr_type = GPIO_INTR_NEGEDGE;
  gpio_config(&config);

  gpio_isr_handler_remove(pin);
  gpio_isr_handler_add(pin, handler, nullptr);
}

inline void setup(gpio_num_t left_pin, gpio_num_t right_pin, uint32_t debounce_micros) {
  edge_guard_us = debounce_micros;
  gpio_install_isr_service(0);
  setup_pin(left_pin, left_isr);
  setup_pin(right_pin, right_isr);
  installed = true;
}

inline uint32_t consume_left() {
  portENTER_CRITICAL(&encoder_mux);
  const uint32_t value = left_counter.queued;
  left_counter.queued = 0;
  portEXIT_CRITICAL(&encoder_mux);
  return value;
}

inline uint32_t consume_right() {
  portENTER_CRITICAL(&encoder_mux);
  const uint32_t value = right_counter.queued;
  right_counter.queued = 0;
  portEXIT_CRITICAL(&encoder_mux);
  return value;
}

inline PulseStats snapshot_and_reset_window() {
  PulseStats stats{};
  portENTER_CRITICAL(&encoder_mux);

  stats.raw_left = left_counter.raw_window;
  stats.raw_right = right_counter.raw_window;
  stats.accepted_left = left_counter.accepted_window;
  stats.accepted_right = right_counter.accepted_window;
  stats.dropped_left = left_counter.dropped_window;
  stats.dropped_right = right_counter.dropped_window;
  stats.queued_left = left_counter.queued;
  stats.queued_right = right_counter.queued;
  stats.min_dt_left_us = left_counter.min_dt_window_us;
  stats.min_dt_right_us = right_counter.min_dt_window_us;
  stats.max_dt_left_us = left_counter.max_dt_window_us;
  stats.max_dt_right_us = right_counter.max_dt_window_us;
  stats.min_raw_dt_left_us = left_counter.min_raw_dt_window_us;
  stats.min_raw_dt_right_us = right_counter.min_raw_dt_window_us;
  stats.max_raw_dt_left_us = left_counter.max_raw_dt_window_us;
  stats.max_raw_dt_right_us = right_counter.max_raw_dt_window_us;

  left_counter.raw_window = 0;
  right_counter.raw_window = 0;
  left_counter.accepted_window = 0;
  right_counter.accepted_window = 0;
  left_counter.dropped_window = 0;
  right_counter.dropped_window = 0;
  left_counter.min_dt_window_us = 0;
  right_counter.min_dt_window_us = 0;
  left_counter.max_dt_window_us = 0;
  right_counter.max_dt_window_us = 0;
  left_counter.min_raw_dt_window_us = 0;
  right_counter.min_raw_dt_window_us = 0;
  left_counter.max_raw_dt_window_us = 0;
  right_counter.max_raw_dt_window_us = 0;

  portEXIT_CRITICAL(&encoder_mux);
  return stats;
}

}  // namespace rotary_encoder_tune
