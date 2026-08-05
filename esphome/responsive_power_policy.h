#pragma once

#include <cstdint>

#include <esp_err.h>
#include <esp_wifi.h>

#include "esphome/core/log.h"

namespace responsive_power {

// Switch Wi-Fi power-save only when the desired state changes. ESPHome owns
// Wi-Fi lifecycle and reconnects; failed calls are retried after reconnect.
class WifiPolicy {
 public:
  void update(bool external_power, bool latency_critical, uint32_t now_ms) {
    const wifi_ps_type_t desired =
      (external_power || latency_critical) ? WIFI_PS_NONE : WIFI_PS_MIN_MODEM;
    if (applied_ == static_cast<int>(desired) ||
        static_cast<int32_t>(now_ms - retry_after_ms_) < 0)
      return;

    const esp_err_t result = esp_wifi_set_ps(desired);
    if (result == ESP_OK) {
      applied_ = static_cast<int>(desired);
      retry_after_ms_ = 0;
      ESP_LOGI("responsive_power", "Wi-Fi policy: %s",
               desired == WIFI_PS_NONE ? "responsive" : "idle modem-sleep");
      return;
    }

    retry_after_ms_ = now_ms + 2000U;
    ESP_LOGD("responsive_power", "Wi-Fi policy deferred: %s",
             esp_err_to_name(result));
  }

 private:
  int applied_{-1};
  uint32_t retry_after_ms_{0};
};

inline WifiPolicy &wifi_policy() {
  static WifiPolicy instance;
  return instance;
}

}  // namespace responsive_power
