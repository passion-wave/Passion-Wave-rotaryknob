#pragma once

#include <cstdint>

#include "driver/gpio.h"
#include "esp_err.h"
#include "freertos/FreeRTOS.h"
#include "freertos/queue.h"

namespace dual_mcu {

class EncoderCapture {
 public:
  bool setup(gpio_num_t left_pin, gpio_num_t right_pin) {
    this->queue_ = xQueueCreateStatic(QUEUE_LENGTH, sizeof(int8_t), this->queue_storage_,
                                      &this->queue_struct_);
    if (this->queue_ == nullptr) return false;

    const uint64_t mask = (1ULL << static_cast<uint32_t>(left_pin)) |
                          (1ULL << static_cast<uint32_t>(right_pin));
    gpio_config_t config{};
    config.pin_bit_mask = mask;
    config.mode = GPIO_MODE_INPUT;
    config.pull_up_en = GPIO_PULLUP_ENABLE;
    config.pull_down_en = GPIO_PULLDOWN_DISABLE;
    config.intr_type = GPIO_INTR_NEGEDGE;
    if (gpio_config(&config) != ESP_OK) return false;

    const esp_err_t service_result = gpio_install_isr_service(ESP_INTR_FLAG_IRAM);
    if (service_result != ESP_OK && service_result != ESP_ERR_INVALID_STATE) return false;

    if (gpio_isr_handler_add(left_pin, left_isr_, this) != ESP_OK) return false;
    if (gpio_isr_handler_add(right_pin, right_isr_, this) != ESP_OK) return false;
    return true;
  }

  bool pop(int8_t *delta) {
    if (delta == nullptr || this->queue_ == nullptr) return false;
    return xQueueReceive(this->queue_, delta, 0) == pdTRUE;
  }

  uint32_t overflows() const { return this->overflows_; }

 private:
  static constexpr UBaseType_t QUEUE_LENGTH = 32;

  static void IRAM_ATTR left_isr_(void *arg) {
    static_cast<EncoderCapture *>(arg)->push_from_isr_(-1);
  }

  static void IRAM_ATTR right_isr_(void *arg) {
    static_cast<EncoderCapture *>(arg)->push_from_isr_(1);
  }

  void IRAM_ATTR push_from_isr_(int8_t delta) {
    BaseType_t high_priority_woken = pdFALSE;
    if (xQueueSendFromISR(this->queue_, &delta, &high_priority_woken) != pdTRUE) {
      this->overflows_++;
    }
    if (high_priority_woken == pdTRUE) portYIELD_FROM_ISR();
  }

  StaticQueue_t queue_struct_{};
  uint8_t queue_storage_[QUEUE_LENGTH * sizeof(int8_t)]{};
  QueueHandle_t queue_{nullptr};
  volatile uint32_t overflows_{0};
};

inline EncoderCapture encoder;

}  // namespace dual_mcu
