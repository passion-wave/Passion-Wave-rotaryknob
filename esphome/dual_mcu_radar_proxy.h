#pragma once

#include <algorithm>
#include <array>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <string>
#include <vector>

#include <esp_http_client.h>
#include <esp_heap_caps.h>
#include <esp_netif_ip_addr.h>
#include <freertos/FreeRTOS.h>
#include <freertos/queue.h>
#include <freertos/task.h>
#include <mdns.h>

#include "dual_mcu_link.h"

namespace dual_mcu {

static constexpr size_t RADAR_CHUNK_BYTES = MAX_PAYLOAD - 6;
// Shared, single-flight compressed asset transport. Only the S3 keeps the
// completed byte vector; the ESP32 uses a bounded ten-chunk queue.
static constexpr size_t RADAR_MAX_BYTES = 512 * 1024;

enum class AssetKind : uint8_t {
  NONE = 0,
  RADAR = 1,
  MEDIA_COVER = 2,
  PHOTO = 3,
  HOUSE = 4,
};

inline const char *asset_kind_name(AssetKind kind) {
  switch (kind) {
    case AssetKind::RADAR: return "radar";
    case AssetKind::MEDIA_COVER: return "cover";
    case AssetKind::PHOTO: return "photo";
    case AssetKind::HOUSE: return "house";
    default: return "none";
  }
}

inline uint32_t radar_crc32_update(uint32_t crc, const uint8_t *data, size_t length) {
  crc = ~crc;
  for (size_t index = 0; index < length; index++) {
    crc ^= data[index];
    for (uint8_t bit = 0; bit < 8; bit++)
      crc = (crc >> 1) ^ (0xEDB88320UL & static_cast<uint32_t>(-(static_cast<int32_t>(crc & 1U))));
  }
  return ~crc;
}

class AssetBuffer {
 public:
  ~AssetBuffer() { this->clear(); }
  bool allocate(size_t capacity) {
    this->clear();
    if (capacity == 0 || capacity > RADAR_MAX_BYTES) return false;
    this->data_ = static_cast<uint8_t *>(
      heap_caps_malloc(capacity, MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT));
    if (this->data_ == nullptr)
      this->data_ = static_cast<uint8_t *>(
        heap_caps_malloc(capacity, MALLOC_CAP_8BIT));
    if (this->data_ == nullptr) return false;
    this->capacity_ = capacity;
    return true;
  }
  bool append(const uint8_t *data, size_t length) {
    if (data == nullptr || this->data_ == nullptr ||
        this->size_ + length > this->capacity_) return false;
    std::memcpy(this->data_ + this->size_, data, length);
    this->size_ += length;
    return true;
  }
  void clear() {
    if (this->data_ != nullptr) heap_caps_free(this->data_);
    this->data_ = nullptr;
    this->size_ = 0;
    this->capacity_ = 0;
  }
  bool empty() const { return this->size_ == 0; }
  size_t size() const { return this->size_; }
  uint8_t *data() { return this->data_; }
  const uint8_t *data() const { return this->data_; }

 private:
  uint8_t *data_{nullptr};
  size_t size_{0};
  size_t capacity_{0};
};

class RadarProxyServer {
 public:
  bool setup() {
    if (this->queue_ != nullptr) return true;
    this->queue_ = xQueueCreate(10, sizeof(TransferItem));
    return this->queue_ != nullptr;
  }

  bool start(const std::string &url) {
    if (url.empty() || url.size() >= this->url_.size() || this->busy()) return false;
    if (!this->setup()) return false;
    TransferItem stale{};
    while (xQueueReceive(this->queue_, &stale, 0) == pdTRUE) {}
    std::memcpy(this->url_.data(), url.c_str(), url.size() + 1);
    this->abort_ = false;
    this->last_progress_ms_ = millis();
    this->transfer_id_++;
    if (this->transfer_id_ == 0) this->transfer_id_ = 1;
    this->active_ = true;
    if (xTaskCreatePinnedToCore(task_entry_, "radar_proxy", 8192, this, 2,
                                &this->task_handle_, 0) != pdPASS) {
      this->active_ = false;
      this->task_handle_ = nullptr;
      return false;
    }
    return true;
  }

  bool busy() const {
    return this->active_ || this->pending_valid_ ||
           (this->queue_ != nullptr && uxQueueMessagesWaiting(this->queue_) > 0);
  }

  bool poll_send(Link &link) {
    if (this->queue_ == nullptr) return false;
    if (this->busy() && this->last_progress_ms_ != 0 &&
        millis() - this->last_progress_ms_ > 12000UL) {
      // The peer may reboot after receiving a frame but before acknowledging
      // it. Do not keep retransmitting that old transfer forever.
      this->abort_ = true;
      this->pending_valid_ = false;
      this->awaiting_ack_ = false;
      TransferItem stale{};
      while (xQueueReceive(this->queue_, &stale, 0) == pdTRUE) {}
      return false;
    }
    if (this->pending_valid_ && this->awaiting_ack_ &&
        millis() - this->last_send_ms_ < 40) return false;
    if (!this->pending_valid_) {
      if (xQueueReceive(this->queue_, &this->pending_, 0) != pdTRUE) return false;
      this->pending_valid_ = true;
      this->awaiting_ack_ = false;
    }
    const TransferItem &item = this->pending_;
    uint8_t payload[MAX_PAYLOAD]{};
    write_u16_(payload, item.transfer_id);
    bool sent = false;
    if (item.kind == ItemKind::BEGIN) {
      write_u32_(&payload[2], item.total);
      sent = link.send(MessageType::RADAR_BEGIN, payload, 6);
    } else if (item.kind == ItemKind::CHUNK) {
      write_u32_(&payload[2], item.offset);
      std::memcpy(&payload[6], item.data.data(), item.length);
      sent = link.send(MessageType::RADAR_CHUNK, payload,
                       static_cast<uint8_t>(6 + item.length));
    } else if (item.kind == ItemKind::END) {
      write_u32_(&payload[2], item.total);
      write_u32_(&payload[6], item.crc32);
      sent = link.send(MessageType::RADAR_END, payload, 10);
    } else {
      payload[2] = item.error;
      sent = link.send(MessageType::RADAR_ERROR, payload, 3);
    }
    if (!sent) return false;
    this->last_send_ms_ = millis();
    if (item.kind == ItemKind::ERROR) {
      this->pending_valid_ = false;
    } else {
      this->awaiting_ack_ = true;
    }
    return true;
  }

  bool acknowledge(const Frame &frame) {
    if (frame.type != MessageType::RADAR_ACK || frame.length != 6 ||
        !this->pending_valid_ || !this->awaiting_ack_) return false;
    const uint16_t transfer_id = static_cast<uint16_t>(frame.payload[0]) |
                                 (static_cast<uint16_t>(frame.payload[1]) << 8);
    const uint32_t next_offset = Link::read_u32(&frame.payload[2]);
    uint32_t expected_offset = 0;
    if (this->pending_.kind == ItemKind::CHUNK)
      expected_offset = this->pending_.offset + this->pending_.length;
    else if (this->pending_.kind == ItemKind::END)
      expected_offset = this->pending_.total;
    if (transfer_id != this->pending_.transfer_id || next_offset != expected_offset)
      return false;
    this->pending_valid_ = false;
    this->awaiting_ack_ = false;
    this->last_progress_ms_ = millis();
    return true;
  }

 private:
  enum class ItemKind : uint8_t { BEGIN, CHUNK, END, ERROR };
  struct TransferItem {
    ItemKind kind{ItemKind::ERROR};
    uint16_t transfer_id{0};
    uint32_t offset{0};
    uint32_t total{0};
    uint32_t crc32{0};
    uint8_t error{0};
    uint8_t length{0};
    std::array<uint8_t, RADAR_CHUNK_BYTES> data{};
  };

  static void task_entry_(void *argument) {
    auto *server = static_cast<RadarProxyServer *>(argument);
    server->download_task_();
    server->task_handle_ = nullptr;
    server->active_ = false;
    vTaskDelete(nullptr);
  }

  bool enqueue_(const TransferItem &item) {
    if (this->queue_ == nullptr || this->abort_) return false;
    while (xQueueSend(this->queue_, &item, pdMS_TO_TICKS(100)) != pdTRUE) {
      if (!this->active_ || this->abort_) return false;
    }
    return true;
  }

  void enqueue_error_(uint8_t error) {
    TransferItem item{};
    item.kind = ItemKind::ERROR;
    item.transfer_id = this->transfer_id_;
    item.error = error;
    this->enqueue_(item);
  }

  void download_task_() {
    std::string download_url = this->url_.data();
    if (!this->resolve_local_url_(&download_url)) {
      this->enqueue_error_(15);
      return;
    }
    esp_http_client_config_t config{};
    config.url = download_url.c_str();
    config.method = HTTP_METHOD_GET;
    config.timeout_ms = 4000;
    config.disable_auto_redirect = false;
    config.max_redirection_count = 4;
    config.buffer_size = 1024;
    esp_http_client_handle_t client = esp_http_client_init(&config);
    if (client == nullptr) {
      this->enqueue_error_(1);
      return;
    }
    esp_err_t result = esp_http_client_open(client, 0);
    if (result != ESP_OK) {
      esp_http_client_cleanup(client);
      this->enqueue_error_(2);
      return;
    }
    const int64_t content_length = esp_http_client_fetch_headers(client);
    const int status = esp_http_client_get_status_code(client);
    if (status < 200 || status >= 300 || content_length > static_cast<int64_t>(RADAR_MAX_BYTES)) {
      esp_http_client_close(client);
      esp_http_client_cleanup(client);
      this->enqueue_error_(status < 200 || status >= 300 ? 3 : 4);
      return;
    }

    TransferItem begin{};
    begin.kind = ItemKind::BEGIN;
    begin.transfer_id = this->transfer_id_;
    begin.total = content_length > 0 ? static_cast<uint32_t>(content_length) : 0;
    if (!this->enqueue_(begin)) {
      esp_http_client_close(client);
      esp_http_client_cleanup(client);
      return;
    }

    uint32_t offset = 0;
    uint32_t crc = 0;
    bool failed = false;
    while (offset < RADAR_MAX_BYTES) {
      TransferItem chunk{};
      chunk.kind = ItemKind::CHUNK;
      chunk.transfer_id = this->transfer_id_;
      chunk.offset = offset;
      const int received = esp_http_client_read(
        client, reinterpret_cast<char *>(chunk.data.data()), chunk.data.size());
      if (received < 0) {
        failed = true;
        break;
      }
      if (received == 0) {
        if (esp_http_client_is_complete_data_received(client)) break;
        vTaskDelay(pdMS_TO_TICKS(2));
        continue;
      }
      chunk.length = static_cast<uint8_t>(received);
      crc = radar_crc32_update(crc, chunk.data.data(), chunk.length);
      if (!this->enqueue_(chunk)) {
        failed = true;
        break;
      }
      offset += chunk.length;
    }
    if (offset >= RADAR_MAX_BYTES && !esp_http_client_is_complete_data_received(client)) failed = true;
    esp_http_client_close(client);
    esp_http_client_cleanup(client);

    if (failed || offset == 0 || (content_length > 0 && offset != static_cast<uint32_t>(content_length))) {
      this->enqueue_error_(failed ? 5 : 6);
      return;
    }
    TransferItem end{};
    end.kind = ItemKind::END;
    end.transfer_id = this->transfer_id_;
    end.total = offset;
    end.crc32 = crc;
    this->enqueue_(end);
  }

  bool resolve_local_url_(std::string *url) {
    if (url == nullptr) return false;
    const size_t scheme_end = url->find("://");
    if (scheme_end == std::string::npos) return true;
    const size_t authority_start = scheme_end + 3;
    const size_t authority_end = url->find_first_of("/?#", authority_start);
    const size_t host_end = url->find(':', authority_start);
    const size_t hostname_end =
      host_end != std::string::npos &&
          (authority_end == std::string::npos || host_end < authority_end)
        ? host_end
        : authority_end;
    const size_t effective_hostname_end =
      hostname_end == std::string::npos ? url->size() : hostname_end;
    if (effective_hostname_end <= authority_start) return true;
    const std::string hostname =
      url->substr(authority_start, effective_hostname_end - authority_start);
    static constexpr char suffix[] = ".local";
    if (hostname.size() <= sizeof(suffix) - 1 ||
        hostname.compare(hostname.size() - (sizeof(suffix) - 1),
                         sizeof(suffix) - 1, suffix) != 0) {
      return true;
    }

    char address[16]{};
    if (hostname == this->cached_mdns_host_.data() &&
        this->cached_mdns_address_[0] != '\0') {
      std::memcpy(address, this->cached_mdns_address_.data(), sizeof(address));
    } else {
      const std::string mdns_name =
        hostname.substr(0, hostname.size() - (sizeof(suffix) - 1));
      esp_ip4_addr_t resolved{};
      // Prefer the explicit mDNS lookup, but let esp_http_client perform its
      // normal resolver path when mDNS is temporarily unavailable. A failed
      // preflight must not turn an otherwise valid URL into proxy error 15.
      if (mdns_query_a(mdns_name.c_str(), 2000, &resolved) != ESP_OK)
        return true;
      std::snprintf(address, sizeof(address), IPSTR, IP2STR(&resolved));
      std::snprintf(this->cached_mdns_host_.data(),
                    this->cached_mdns_host_.size(), "%s", hostname.c_str());
      std::snprintf(this->cached_mdns_address_.data(),
                    this->cached_mdns_address_.size(), "%s", address);
    }
    url->replace(authority_start, hostname.size(), address);
    return true;
  }

  static void write_u16_(uint8_t *data, uint16_t value) {
    data[0] = static_cast<uint8_t>(value & 0xFF);
    data[1] = static_cast<uint8_t>((value >> 8) & 0xFF);
  }
  static void write_u32_(uint8_t *data, uint32_t value) {
    data[0] = static_cast<uint8_t>(value & 0xFF);
    data[1] = static_cast<uint8_t>((value >> 8) & 0xFF);
    data[2] = static_cast<uint8_t>((value >> 16) & 0xFF);
    data[3] = static_cast<uint8_t>((value >> 24) & 0xFF);
  }

  QueueHandle_t queue_{nullptr};
  TaskHandle_t task_handle_{nullptr};
  volatile bool active_{false};
  uint16_t transfer_id_{0};
  std::array<char, 513> url_{};
  TransferItem pending_{};
  bool pending_valid_{false};
  bool awaiting_ack_{false};
  uint32_t last_send_ms_{0};
  uint32_t last_progress_ms_{0};
  volatile bool abort_{false};
  std::array<char, 64> cached_mdns_host_{};
  std::array<char, 16> cached_mdns_address_{};
};

class RadarProxyClient {
 public:
  void set_available(bool available) {
    this->available_ = available;
    if (!available) this->reset_transfer_();
  }
  bool available() const { return this->available_; }
  bool active() const { return this->waiting_ || this->receiving_; }

  bool request(Link &link, AssetKind kind, bool force, uint8_t argument = 0) {
    const uint32_t now = millis();
    if (kind == AssetKind::NONE || !this->available_ || this->active() ||
        now < this->retry_after_ms_[kind_index_(kind)]) return false;
    const uint8_t payload[] = {
      static_cast<uint8_t>(kind),
      static_cast<uint8_t>(force ? 1 : 0),
      argument,
    };
    if (!link.send(MessageType::RADAR_REQUEST, payload, sizeof(payload))) return false;
    this->requested_kind_ = kind;
    this->waiting_ = true;
    this->started_ms_ = now;
    this->failure_pending_ = false;
    this->finished_ = false;
    this->completed_kind_ = AssetKind::NONE;
    this->failed_kind_ = AssetKind::NONE;
    return true;
  }

  bool begin(const Frame &frame) {
    if (frame.length != 6) return false;
    const uint16_t transfer_id = read_u16_(frame.payload.data());
    if (this->receiving_ && transfer_id == this->transfer_id_) return true;
    if (!this->waiting_) return false;
    const uint32_t total = read_u32_(&frame.payload[2]);
    if (total > RADAR_MAX_BYTES) return this->fail_(4);
    this->transfer_id_ = transfer_id;
    this->expected_total_ = total;
    const size_t capacity = total > 0 ? total : RADAR_MAX_BYTES;
    if (!this->bytes_.allocate(capacity)) return this->fail_(14);
    this->waiting_ = false;
    this->receiving_ = true;
    this->started_ms_ = millis();
    return true;
  }

  bool append(const Frame &frame) {
    if (frame.length < 7 || !this->receiving_) return false;
    const uint16_t id = read_u16_(frame.payload.data());
    const uint32_t offset = read_u32_(&frame.payload[2]);
    const size_t length = frame.length - 6;
    if (id != this->transfer_id_ || this->bytes_.size() + length > RADAR_MAX_BYTES)
      return this->fail_(7);
    if (offset < this->bytes_.size()) {
      if (offset + length <= this->bytes_.size() &&
          std::memcmp(this->bytes_.data() + offset,
                      &frame.payload[6], length) == 0) return true;
      return false;
    }
    if (offset != this->bytes_.size()) return false;
    if (!this->bytes_.append(&frame.payload[6], length)) return this->fail_(7);
    this->started_ms_ = millis();
    return true;
  }

  bool finish(const Frame &frame) {
    if (frame.length != 10) return false;
    const uint16_t id = read_u16_(frame.payload.data());
    const uint32_t total = read_u32_(&frame.payload[2]);
    if (this->finished_)
      return id == this->transfer_id_ && total == this->bytes_.size();
    if (!this->receiving_) return false;
    const uint32_t expected_crc = read_u32_(&frame.payload[6]);
    const uint32_t actual_crc = radar_crc32_update(0, this->bytes_.data(), this->bytes_.size());
    if (id != this->transfer_id_ || total != this->bytes_.size() ||
        (this->expected_total_ > 0 && total != this->expected_total_) ||
        expected_crc != actual_crc) return this->fail_(8);
    this->receiving_ = false;
    this->finished_ = true;
    this->completed_ = true;
    this->completed_kind_ = this->requested_kind_;
    this->retry_after_ms_[kind_index_(this->completed_kind_)] = 0;
    this->last_error_ = 0;
    return true;
  }

  bool send_ack(Link &link) const {
    if (!this->receiving_ && !this->finished_) return false;
    uint8_t payload[6]{};
    write_u16_(payload, this->transfer_id_);
    write_u32_(&payload[2], static_cast<uint32_t>(this->bytes_.size()));
    return link.send(MessageType::RADAR_ACK, payload, sizeof(payload));
  }

  void remote_error(const Frame &frame) {
    this->last_error_ = frame.length >= 3 ? frame.payload[2] : 9;
    this->fail_(this->last_error_);
  }

  void decode_failed() { this->fail_(13); }

  void tick() {
    if (this->active() && millis() - this->started_ms_ > 12000) this->fail_(10);
  }

  bool take_completed() {
    const bool value = this->completed_;
    this->completed_ = false;
    return value;
  }
  // The decode worker owns the completed bytes only until it reports done.
  // Release the compressed transfer immediately afterwards; the decoded
  // OnlineImage pixel buffer remains valid and independent.
  void release_completed_bytes() {
    if (!this->active()) this->bytes_.clear();
  }
  AssetKind completed_kind() const { return this->completed_kind_; }
  bool take_failure() {
    const bool value = this->failure_pending_;
    this->failure_pending_ = false;
    return value;
  }
  const AssetBuffer &bytes() const { return this->bytes_; }
  uint8_t last_error() const { return this->last_error_; }
  AssetKind failed_kind() const { return this->failed_kind_; }

 private:
  bool fail_(uint8_t error) {
    const AssetKind failed_kind =
      this->requested_kind_ != AssetKind::NONE
        ? this->requested_kind_
        : this->completed_kind_;
    // A failed photo, cover or house must never stall a radar request.
    // HTTP source errors receive a longer, per-kind cooldown; transient
    // transport/decode failures retry quickly, with radar getting the
    // shortest recovery path.
    const bool radar = failed_kind == AssetKind::RADAR;
    const uint32_t cooldown_ms =
      error == 3 ? (radar ? 2000U : 30000U)
                 : (radar ? 750U : 5000U);
    if (failed_kind != AssetKind::NONE)
      this->retry_after_ms_[kind_index_(failed_kind)] =
        millis() + cooldown_ms;
    this->failed_kind_ = failed_kind;
    this->last_error_ = error;
    this->waiting_ = false;
    this->receiving_ = false;
    this->completed_ = false;
    this->finished_ = false;
    this->failure_pending_ = true;
    this->bytes_.clear();
    this->requested_kind_ = AssetKind::NONE;
    return false;
  }
  static constexpr size_t kind_index_(AssetKind kind) {
    const size_t index = static_cast<size_t>(kind);
    return index < 5 ? index : 0;
  }
  void reset_transfer_() {
    this->waiting_ = false;
    this->receiving_ = false;
    this->completed_ = false;
    this->finished_ = false;
    this->bytes_.clear();
    this->requested_kind_ = AssetKind::NONE;
    this->completed_kind_ = AssetKind::NONE;
    this->failed_kind_ = AssetKind::NONE;
  }
  static uint16_t read_u16_(const uint8_t *data) {
    return static_cast<uint16_t>(data[0]) | (static_cast<uint16_t>(data[1]) << 8);
  }
  static uint32_t read_u32_(const uint8_t *data) {
    return static_cast<uint32_t>(data[0]) |
           (static_cast<uint32_t>(data[1]) << 8) |
           (static_cast<uint32_t>(data[2]) << 16) |
           (static_cast<uint32_t>(data[3]) << 24);
  }
  static void write_u16_(uint8_t *data, uint16_t value) {
    data[0] = static_cast<uint8_t>(value & 0xFF);
    data[1] = static_cast<uint8_t>((value >> 8) & 0xFF);
  }
  static void write_u32_(uint8_t *data, uint32_t value) {
    data[0] = static_cast<uint8_t>(value & 0xFF);
    data[1] = static_cast<uint8_t>((value >> 8) & 0xFF);
    data[2] = static_cast<uint8_t>((value >> 16) & 0xFF);
    data[3] = static_cast<uint8_t>((value >> 24) & 0xFF);
  }

  bool available_{false};
  bool waiting_{false};
  bool receiving_{false};
  bool completed_{false};
  bool finished_{false};
  bool failure_pending_{false};
  uint16_t transfer_id_{0};
  uint32_t expected_total_{0};
  uint32_t started_ms_{0};
  std::array<uint32_t, 5> retry_after_ms_{};
  uint8_t last_error_{0};
  AssetKind requested_kind_{AssetKind::NONE};
  AssetKind completed_kind_{AssetKind::NONE};
  AssetKind failed_kind_{AssetKind::NONE};
  AssetBuffer bytes_{};
};

inline RadarProxyServer radar_server;
inline RadarProxyClient radar_client;
// S3-only decode hand-off. Compressed transport storage remains owned by the
// client until the worker reports completion; UI/LVGL mutations stay in the
// main ESPHome loop.
inline volatile bool asset_decode_running{false};
inline volatile bool asset_decode_done{false};
inline volatile bool asset_decode_success{false};
inline volatile uint8_t asset_decode_kind{0};
inline volatile uint8_t asset_decode_argument{0};
inline volatile uint8_t asset_decode_radar_target{0};
inline volatile uint32_t asset_decode_duration_ms{0};

}  // namespace dual_mcu
